"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import (
    List,
    Optional,
    Union,
    Tuple,
    Callable,
    DefaultDict,
    Iterable,
    NamedTuple,
    TypeVar,
)

import enum
import collections

import clr.lexer as lexer


class Parser:
    """
    A wrapper class for parsing a list of tokens.
    """

    def __init__(self, tokens: List[lexer.Token]) -> None:
        self.tokens = tokens
        self.current = 0

    def done(self) -> bool:
        """
        Returns whether the whole token list has been consumed.
        """
        return self.current == len(self.tokens)

    def prev(self) -> lexer.Token:
        """
        Returns the previous token.
        """
        return self.tokens[self.current - 1]

    def curr(self) -> Optional[lexer.Token]:
        """
        Returns the current token, or None if there are no more tokens to parse.
        """
        return None if self.done() else self.tokens[self.current]

    def advance(self) -> Optional[lexer.Token]:
        """
        Consumes a token and returns it, if there are no tokens left returns None.
        """
        if self.done():
            return None

        self.current += 1
        return self.prev()

    def check(self, kind: lexer.TokenType) -> bool:
        """
        Checks if the current token is of a given type.
        """
        curr = self.curr()
        if curr:
            return curr.kind == kind
        return False

    def match(self, kind: lexer.TokenType) -> bool:
        """
        Checks if the current token is of a given type, and advances past it if it is.
        """
        result = self.check(kind)
        if result:
            self.current += 1
        return result

    def curr_region(self) -> lexer.SourceView:
        """
        Returns a source view of the current token (or the previous if the parser is done).
        """
        curr = self.curr()
        if curr:
            return curr.lexeme
        return self.prev().lexeme


class ParseError:
    """
    Parse error class, contains a message and a region of source the error applies to.
    """

    def __init__(self, message: str, region: lexer.SourceView) -> None:
        self.message = message
        self.region = region

    def display(self) -> str:
        """
        Returns a string of information about the error.
        """
        # TODO:
        # Line number, highlight region in context, formatting, e.t.c.
        return f"{self.message}: {self.region}"


class ParseNode:
    """
    Base class for nodes of the parse tree.
    """

    def pprint(self) -> str:
        """
        Pretty prints the node back as a part of valid Clear code.
        """
        raise NotImplementedError()


def indent(orig: str) -> str:
    """
    Indents a string with four spaces.
    """
    return "\n".join(f"    {line}" for line in orig.splitlines())


class ParseTree(ParseNode):
    """
    The root node of the parse tree, contains a list of declarations.

    ParseTree : ParseDecl* ;
    """

    def __init__(self, decls: List["ParseDecl"]) -> None:
        self.decls = decls

    def pprint(self) -> str:
        return "\n".join(decl.pprint() for decl in self.decls)

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseTree", List[ParseError]]:
        """
        Parses a ParseTree from a Parser.
        """
        decls = []
        errors = []
        while not parser.done():
            decl, errs = ParseDecl.parse(parser)
            decls.append(decl)
            errors.extend(errs)
        return ParseTree(decls), errors


def parse_tokens(tokens: List[lexer.Token]) -> Tuple[ParseTree, List[ParseError]]:
    """
    Parses a ParseTree from a list of tokens.
    """
    return ParseTree.parse(Parser(tokens))


class ParseDecl(ParseNode):
    """
    Parse node for a generic declaration.

    ParseDecl : ParseValueDecl | ParseFuncDecl | ParseStmt ;
    """

    def __init__(
        self, decl: Union["ParseValueDecl", "ParseFuncDecl", "ParseStmt"]
    ) -> None:
        self.decl = decl

    def pprint(self) -> str:
        return self.decl.pprint()

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseDecl", List[ParseError]]:
        """
        Parses a ParseDecl from a Parser.
        """
        if parser.match(lexer.TokenType.VAL):
            val_decl, errs = ParseValueDecl.finish(parser)
            return ParseDecl(val_decl), errs
        if parser.match(lexer.TokenType.FUNC):
            func_decl, errs = ParseFuncDecl.finish(parser)
            return ParseDecl(func_decl), errs
        stmt_decl, errs = ParseStmt.parse(parser)
        return ParseDecl(stmt_decl), errs


class ParseValueDecl(ParseNode):
    """
    Parse node for a value declaration.

    ParseValueDecl : "val" identifier (ParseType)? "=" ParseExpr ";" ;
    """

    def __init__(
        self,
        ident: Union[lexer.Token, ParseError],
        val_type: Optional["ParseType"],
        expr: "ParseExpr",
    ):
        self.ident = ident
        self.val_type = val_type
        self.expr = expr

    def pprint(self) -> str:
        ident_str = "<error>" if isinstance(self.ident, ParseError) else str(self.ident)
        type_str = self.val_type.pprint() if self.val_type else ""
        return f"val {ident_str} {type_str} = {self.expr.pprint()};"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseValueDecl", List[ParseError]]:
        """
        Parses a ParseValueDecl from a Parser, given that the "val" keyword has already been
        consumed.
        """
        errors = []

        if parser.match(lexer.TokenType.IDENTIFIER):
            ident: Union[lexer.Token, ParseError] = parser.prev()
        else:
            ident = ParseError("missing value name", parser.curr_region())
            errors.append(ident)

        val_type = None
        if not parser.match(lexer.TokenType.EQUALS):
            val_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.EQUALS):
                errors.append(
                    ParseError(
                        "missing '=' for value initializer", parser.curr_region()
                    )
                )

        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)

        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError("missing ';' to end value initializer", parser.curr_region())
            )

        return ParseValueDecl(ident, val_type, expr), errors


class ParseFuncDecl(ParseNode):
    """
    Parse node for a function declaration.

    ParseFuncDecl : "func" identifier ParseParams ParseType ParseBlockStmt ;
    """

    def __init__(
        self,
        ident: Union[lexer.Token, ParseError],
        params: List[Tuple["ParseType", Union[lexer.Token, ParseError]]],
        return_type: "ParseType",
        block: "ParseBlockStmt",
    ) -> None:
        self.ident = ident
        self.params = params
        self.return_type = return_type
        self.block = block

    def pprint(self) -> str:
        ident_str = "<error>" if isinstance(self.ident, ParseError) else str(self.ident)

        def param_gen() -> Iterable[str]:
            for param_type, param_ident in self.params:
                ident_str = (
                    "<error>"
                    if isinstance(param_ident, ParseError)
                    else str(param_ident)
                )
                yield f"{param_type.pprint()} {ident_str}"

        param_str = ", ".join(param_gen())
        return f"func {ident_str}({param_str}) {self.return_type.pprint()} {self.block.pprint()}"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseFuncDecl", List[ParseError]]:
        """
        Parses a ParseFuncDecl from a Parser, given that the "func" keyword has already been
        consumed.
        """
        errors = []
        if parser.match(lexer.TokenType.IDENTIFIER):
            ident: Union[lexer.Token, ParseError] = parser.prev()
        else:
            ident = ParseError("missing function name", parser.curr_region())
            errors.append(ident)

        def parse_param(
            parser: Parser
        ) -> Tuple["ParseType", Union[lexer.Token, ParseError]]:
            param_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            if parser.match(lexer.TokenType.IDENTIFIER):
                return param_type, parser.prev()
            return (
                param_type,
                ParseError("missing parameter name", parser.curr_region()),
            )

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                ParseError("missing '(' to begin parameters", parser.curr_region())
            )
        params, errs = parse_tuple(parser, parse_param)
        errors.extend(errs)
        return_type, errs = ParseType.parse(parser)
        errors.extend(errs)
        block, errs = ParseBlockStmt.parse(parser)
        errors.extend(errs)
        return ParseFuncDecl(ident, params, return_type, block), errors


T = TypeVar("T")  # pylint: disable=invalid-name


def parse_tuple(
    parser: Parser, parse_func: Callable[[Parser], T]
) -> Tuple[List[T], List[ParseError]]:
    """
    Given that the opening '(' has already been consumed, parse the elements of a tuple (a,b,...)
    form into a list using a parameter function to parse each element.
    """
    opener = parser.prev()
    if parser.match(lexer.TokenType.RIGHT_PAREN):
        return [], []
    errors = []
    pairs = [parse_func(parser)]
    while not parser.match(lexer.TokenType.RIGHT_PAREN):
        if parser.done():
            errors.append(ParseError("unclosed '('", opener.lexeme))
            break
        if not parser.match(lexer.TokenType.COMMA):
            errors.append(ParseError("missing ',' delimiter", parser.curr_region()))
        pairs.append(parse_func(parser))
    return pairs, errors


class ParseStmt(ParseNode):
    """
    Parse node for a generic statement.

    ParseStmt : ParsePrintStmt
              | ParseBlockStmt
              | ParseIfStmt
              | ParseWhileStmt
              | ParseReturnStmt
              | ParseExprStmt
              ;
    """

    def __init__(
        self,
        stmt: Union[
            "ParsePrintStmt",
            "ParseBlockStmt",
            "ParseIfStmt",
            "ParseWhileStmt",
            "ParseReturnStmt",
            "ParseExprStmt",
        ],
    ) -> None:
        self.stmt = stmt

    def pprint(self) -> str:
        return self.stmt.pprint()

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseStmt", List[ParseError]]:
        """
        Parses a ParseStmt from a Parser.
        """
        if parser.match(lexer.TokenType.PRINT):
            print_stmt, errs = ParsePrintStmt.finish(parser)
            return ParseStmt(print_stmt), errs
        if parser.match(lexer.TokenType.LEFT_BRACE):
            block_stmt, errs = ParseBlockStmt.finish(parser)
            return ParseStmt(block_stmt), errs
        if parser.match(lexer.TokenType.IF):
            if_stmt, errs = ParseIfStmt.finish(parser)
            return ParseStmt(if_stmt), errs
        if parser.match(lexer.TokenType.WHILE):
            while_stmt, errs = ParseWhileStmt.finish(parser)
            return ParseStmt(while_stmt), errs
        if parser.match(lexer.TokenType.RETURN):
            return_stmt, errs = ParseReturnStmt.finish(parser)
            return ParseStmt(return_stmt), errs
        expr_stmt, errs = ParseExprStmt.parse(parser)
        return ParseStmt(expr_stmt), errs


class ParsePrintStmt(ParseNode):
    """
    Parse node for a print statement.

    ParsePrintStmt : "print" ParseExpr ";" ;
    """

    def __init__(self, expr: "ParseExpr") -> None:
        self.expr = expr

    def pprint(self) -> str:
        return f"print {self.expr.pprint()};"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParsePrintStmt", List[ParseError]]:
        """
        Parses a ParsePrintStmt from a Parser, given that the "print" keyword has already been
        consumed.
        """
        errors = []
        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError("missing ';' to end print statement", parser.curr_region())
            )
        return ParsePrintStmt(expr), errors


class ParseBlockStmt(ParseNode):
    """
    Parse node for a block statement.

    ParseBlockStmt : "{" ParseDecl* "}" ;
    """

    def __init__(self, decls: List[ParseDecl]) -> None:
        self.decls = decls

    def pprint(self) -> str:
        inner_str = indent("\n".join(decl.pprint() for decl in self.decls))
        return f"{{\n{inner_str}\n}}"

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseBlockStmt", List[ParseError]]:
        """
        Parses a ParseBlockStmt from a Parser.
        """
        if parser.match(lexer.TokenType.LEFT_BRACE):
            return ParseBlockStmt.finish(parser)

        return (
            ParseBlockStmt(decls=[]),
            [ParseError("expected '{' to start block", parser.curr_region())],
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseBlockStmt", List[ParseError]]:
        """
        Parses a ParseBlockStmt from a Parser, given that the open brace has already been consumed.
        """
        errors = []
        decls = []
        open_brace = parser.prev()
        while not parser.match(lexer.TokenType.RIGHT_BRACE):
            if parser.done():
                errors.append(ParseError("unclosed block", open_brace.lexeme))
                break
            decl, errs = ParseDecl.parse(parser)
            decls.append(decl)
            errors.extend(errs)
        return ParseBlockStmt(decls), errors


class ParseIfStmt(ParseNode):
    """
    Parse node for an if statement.

    ParseIfStmt : "if" "(" ParseExpr ")" ParseBlockStmt
                ( "else" "if" "(" ParseExpr ")" ParseBlockStmt )*
                ( "else" ParseBlockStmt )?
                ;
    """

    def __init__(
        self,
        pairs: List[Tuple["ParseExpr", ParseBlockStmt]],
        fallback: Optional[ParseBlockStmt],
    ) -> None:
        self.pairs = pairs
        self.fallback = fallback

    def pprint(self) -> str:
        def conds() -> Iterable[str]:
            first = True
            for cond_expr, cond_block in self.pairs:
                else_str = "else" if not first else ""
                yield f"{else_str} if ({cond_expr.pprint()}) {cond_block.pprint()}"
                first = False

        conds_str = " ".join(conds())
        else_str = f"else {self.fallback.pprint()}" if self.fallback else ""
        return f"{conds_str} {else_str}"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseIfStmt", List[ParseError]]:
        """
        Parses a ParseIfStmt from a Parser, given that the "if" keyword has already been consumed.
        """
        errors = []
        pairs = []
        fallback = None

        def parse_cond() -> None:
            if not parser.match(lexer.TokenType.LEFT_PAREN):
                errors.append(
                    ParseError("missing '(' to start condition", parser.curr_region())
                )
            cond, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    ParseError("missing ')' to end condition", parser.curr_region())
                )
            block, errs = ParseBlockStmt.parse(parser)
            errors.extend(errs)
            pairs.append((cond, block))

        # parse the if block
        parse_cond()
        while parser.match(lexer.TokenType.ELSE):
            if parser.match(lexer.TokenType.IF):
                # parse an else if block
                parse_cond()
            else:
                # parse the else block
                fallback, errs = ParseBlockStmt.parse(parser)
                errors.extend(errs)
                break
        return ParseIfStmt(pairs, fallback), errors


class ParseWhileStmt(ParseNode):
    """
    Parse node for a while statement.

    ParseWhileStmt : "while" ( "(" ParseExpr ")" )? ParseBlockStmt ;
    """

    def __init__(self, cond: Optional["ParseExpr"], block: ParseBlockStmt) -> None:
        self.cond = cond
        self.block = block

    def pprint(self) -> str:
        cond_str = f"({self.cond.pprint()}) " if self.cond else ""
        return f"while {cond_str}{self.block.pprint()}"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseWhileStmt", List[ParseError]]:
        """
        Parses a ParseWhileStmt from a Parser, given that the "while" keyword has already been
        consumed.
        """
        errors = []
        cond = None
        if parser.match(lexer.TokenType.LEFT_PAREN):
            cond, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    ParseError("missing ')' to end condition", parser.curr_region())
                )
        block, errs = ParseBlockStmt.parse(parser)
        errors.extend(errs)
        return ParseWhileStmt(cond, block), errors


class ParseReturnStmt(ParseNode):
    """
    Parse node for a return statement.

    ParseReturnStmt : "return" ParseExpr? ";" ;
    """

    def __init__(self, expr: Optional["ParseExpr"]) -> None:
        self.expr = expr

    def pprint(self) -> str:
        if not self.expr:
            return "return;"
        return f"return {self.expr.pprint()};"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseReturnStmt", List[ParseError]]:
        """
        Parses a ParseReturnStmt from a Parser, given that the "return" keyword has already been
        consumed.
        """
        errors = []
        expr = None
        if not parser.match(lexer.TokenType.SEMICOLON):
            expr, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.SEMICOLON):
                errors.append(
                    ParseError(
                        "missing ';' to end return statement", parser.curr_region()
                    )
                )
        return ParseReturnStmt(expr), errors


class ParseExprStmt(ParseNode):
    """
    Parse node for an expression statement.

    ParseExprStmt : ParseExpr ";" ;
    """

    def __init__(self, expr: "ParseExpr") -> None:
        self.expr = expr

    def pprint(self) -> str:
        return f"{self.expr.pprint()};"

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseExprStmt", List[ParseError]]:
        """
        Parses a ParseExprStmt from a Parser.
        """
        errors = []
        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError(
                    "missing ';' to end expression statement", parser.curr_region()
                )
            )
        return ParseExprStmt(expr), errors


class ParseType(ParseNode):
    """
    Parse node for a type.

    ParseType : ( "(" ParseType ")" | ParseFuncType | ParseAtomType ) ( "?" )? ;
    """

    def __init__(self, type_node: Union["ParseFuncType", "ParseAtomType"]) -> None:
        self.type_node = type_node
        self.optional = False

    def pprint(self) -> str:
        if self.optional:
            return f"({self.type_node.pprint()})?"
        return self.type_node.pprint()

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseType", List[ParseError]]:
        """
        Parse a ParseType from a Parser.
        """
        errors = []
        if parser.match(lexer.TokenType.LEFT_PAREN):
            result, errs = ParseType.parse(parser)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    ParseError("missing ')' to end type grouping", parser.curr_region())
                )
        elif parser.match(lexer.TokenType.FUNC):
            func_type, errs = ParseFuncType.finish(parser)
            errors.extend(errs)
            result = ParseType(func_type)
        else:
            atom_type, errs = ParseAtomType.parse(parser)
            errors.extend(errs)
            result = ParseType(atom_type)

        if parser.match(lexer.TokenType.QUESTION_MARK):
            result.optional = True

        return result, errors


class ParseFuncType(ParseNode):
    """
    Parse node for a function type.

    ParseFuncType : "func" "(" ( ParseType ( "," ParseType )* )? ")" ParseType ;
    """

    def __init__(self, params: List[ParseType], return_type: ParseType) -> None:
        self.params = params
        self.return_type = return_type

    def pprint(self) -> str:
        params_str = ", ".join(param.pprint() for param in self.params)
        return f"func({params_str}) {self.return_type.pprint()}"

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseFuncType", List[ParseError]]:
        """
        Parse a ParseFuncType from a Parser given that the "func" keyword has already been
        consumed.
        """
        errors = []

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                ParseError("missing '(' to begin parameter types", parser.curr_region())
            )

        def parse_param(parser: Parser) -> ParseType:
            param_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            return param_type

        params, errs = parse_tuple(parser, parse_param)
        errors.extend(errs)

        return_type, errs = ParseType.parse(parser)
        errors.extend(errs)
        return ParseFuncType(params, return_type), errors


class ParseAtomType(ParseNode):
    """
    Parse node for an atomic type.

    ParseAtomType : identifier | "void" ;
    """

    def __init__(self, token: Union[lexer.Token, ParseError]) -> None:
        self.token = token

    def pprint(self) -> str:
        return "<error>" if isinstance(self.token, ParseError) else str(self.token)

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseAtomType", List[ParseError]]:
        """
        Parse a ParseAtomType from a Parser.
        """
        errors = []
        if parser.match(lexer.TokenType.IDENTIFIER):
            token: Union[lexer.Token, ParseError] = parser.prev()
        elif parser.match(lexer.TokenType.VOID):
            token = parser.prev()
        else:
            token = ParseError("expected type", parser.curr_region())
            errors.append(token)
        return ParseAtomType(token), errors


class ParseExpr(ParseNode):
    """
    Parse node for an expression.
    """

    def __init__(
        self,
        expr: Union[
            "ParseUnaryExpr",
            "ParseBinaryExpr",
            "ParseAtomExpr",
            "ParseCallExpr",
            ParseError,
        ],
    ) -> None:
        self.expr = expr

    def pprint(self) -> str:
        return "<error>" if isinstance(self.expr, ParseError) else self.expr.pprint()


class ParseUnaryExpr(ParseNode):
    """
    Prefix expression for a unary operator.
    """

    def __init__(self, operator: lexer.Token, target: ParseExpr) -> None:
        self.operator = operator
        self.target = target

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseExpr", List[ParseError]]:
        """
        Parse a unary expression from a Parser given that the operator has already been consumed.
        """
        operator = parser.prev()
        target, errs = pratt_parse(parser, PRATT_TABLE, precedence=Precedence.UNARY)
        return ParseExpr(ParseUnaryExpr(operator, target)), errs

    def pprint(self) -> str:
        return f"{self.operator}({self.target.pprint()})"


class ParseBinaryExpr(ParseNode):
    """
    Infix expression for a binary operator.
    """

    def __init__(
        self, left: ParseExpr, operator: lexer.Token, right: ParseExpr
    ) -> None:
        self.left = left
        self.operator = operator
        self.right = right

    @staticmethod
    def finish(parser: Parser, lhs: ParseExpr) -> Tuple["ParseExpr", List[ParseError]]:
        """
        Parse the right hand side of a binary expression from a Parser given that the operator has
        already been consumed.
        """
        left = lhs
        operator = parser.prev()
        prec = PRATT_TABLE[operator.kind].precedence
        right, errs = pratt_parse(parser, PRATT_TABLE, prec.next())
        return ParseExpr(ParseBinaryExpr(left, operator, right)), errs

    def pprint(self) -> str:
        return f"({self.left.pprint()}){self.operator}({self.right.pprint()})"


class ParseCallExpr(ParseNode):
    """
    Infix expression for a function call.
    """

    def __init__(self, function: ParseExpr, args: List[ParseExpr]) -> None:
        self.function = function
        self.args = args

    def pprint(self) -> str:
        args_str = ", ".join(arg.pprint() for arg in self.args)
        return f"{self.function.pprint()}({args_str})"

    @staticmethod
    def finish(parser: Parser, lhs: ParseExpr) -> Tuple["ParseExpr", List[ParseError]]:
        """
        Parse the call part of a function call expression given that the open parenthesis has
        already been consumed.
        """
        function = lhs
        errors = []

        def parse_arg(parser: Parser) -> ParseExpr:
            parse, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            return parse

        args, errs = parse_tuple(parser, parse_arg)
        errors.extend(errs)
        return ParseExpr(ParseCallExpr(function, args)), errors


class ParseAtomExpr(ParseNode):
    """
    Prefix expression for an atomic value expression.
    """

    def __init__(self, token: lexer.Token) -> None:
        self.token = token

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseExpr", List[ParseError]]:
        """
        Parse an atomic value expression from a Parser given that the token has already been
        consumed.
        """
        token = parser.prev()
        return ParseExpr(ParseAtomExpr(token)), []

    def pprint(self) -> str:
        return str(self.token)


Comparison = Union[bool, "NotImplemented"]


@enum.unique
class Precedence(enum.Enum):
    """
    Enumerates the different precedences of infix expressions. The values respect the ordering.
    """

    NONE = 0
    ASSIGNMENT = 1
    OR = 2
    AND = 3
    EQUALITY = 4
    COMPARISON = 5
    TERM = 6
    FACTOR = 7
    UNARY = 8
    CALL = 9
    MAX = 10

    def __lt__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value >= other.value

    def next(self) -> "Precedence":
        """
        Returns the next highest precedence.
        """
        next_value = self.value + 1
        return Precedence(min(next_value, Precedence.MAX.value))


PrefixRule = Callable[[Parser], Tuple[ParseExpr, List[ParseError]]]
InfixRule = Callable[[Parser, ParseExpr], Tuple[ParseExpr, List[ParseError]]]


class PrattRule(NamedTuple):
    """
    Represents a rule for parsing a token within an expression.
    """

    prefix: Optional[PrefixRule] = None
    infix: Optional[InfixRule] = None
    precedence: Precedence = Precedence.NONE


PRATT_TABLE: DefaultDict[lexer.TokenType, PrattRule] = collections.defaultdict(
    PrattRule,
    {
        lexer.TokenType.LEFT_PAREN: PrattRule(
            infix=ParseCallExpr.finish, precedence=Precedence.CALL
        ),
        lexer.TokenType.MINUS: PrattRule(
            prefix=ParseUnaryExpr.finish,
            infix=ParseBinaryExpr.finish,
            precedence=Precedence.TERM,
        ),
        lexer.TokenType.PLUS: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.TERM
        ),
        lexer.TokenType.STAR: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.SLASH: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.OR: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.OR
        ),
        lexer.TokenType.AND: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.AND
        ),
        lexer.TokenType.STR_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.NUM_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.INT_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.IDENTIFIER: PrattRule(prefix=ParseAtomExpr.finish),
    },
)


def pratt_prefix(
    parser: Parser, table: DefaultDict[lexer.TokenType, PrattRule]
) -> Tuple[ParseExpr, List[ParseError]]:
    """
    Parses a prefix expression from a Parser using a pratt table.
    """
    start_token = parser.advance()
    if not start_token:
        err = ParseError("unexpected EOF; expected expression", parser.curr_region())
        return ParseExpr(err), [err]
    rule = table[start_token.kind]
    if not rule.prefix:
        err = ParseError("unexpected token; expected expression", start_token.lexeme)
        return ParseExpr(err), [err]
    return rule.prefix(parser)


def pratt_infix(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    expr: ParseExpr,
    precedence: Precedence,
) -> Optional[Tuple[ParseExpr, List[ParseError]]]:
    """
    Given an initial expression and precedence parses an infix expression from a Parser using a
    pratt table. If there are no infix extensions bound by the precedence returns None.
    """
    errors = []
    # See if there's an infix token
    # If not, there's no expression to parse
    token = parser.curr()
    if not token:
        return None
    rule = table[token.kind]
    if not rule.infix:
        return None
    # While the infix token is bound by the precedence of the expression
    while rule.precedence >= precedence:
        # Advance past the infix token and run its rule
        parser.advance()
        if rule.infix:  # Should always be true but mypy can't tell
            expr, errs = rule.infix(parser, expr)
            errors.extend(errs)
        # See if there's another infix token
        # If not, the expression is finished
        token = parser.curr()
        if not token:
            break
        rule = table[token.kind]
        if not rule.infix:
            break
    return expr, errors


def pratt_parse(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    precedence: Precedence = Precedence.ASSIGNMENT,
) -> Tuple[ParseExpr, List[ParseError]]:
    """
    Parses an expression bound by a given precedence from a Parser using a pratt table.
    """
    prefix_expr, errs = pratt_prefix(parser, table)
    infix_parse = pratt_infix(parser, table, prefix_expr, precedence)
    if infix_parse:
        return infix_parse[0], errs + infix_parse[1]
    return prefix_expr, errs
