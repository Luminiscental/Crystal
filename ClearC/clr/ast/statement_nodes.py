from clr.tokens import TokenType, token_info
from clr.errors import parse_error, emit_error
from clr.ast.return_annotations import ReturnAnnotation
from clr.ast.index_annotations import IndexAnnotation
from clr.ast.expression_nodes import parse_expr
from clr.ast.type_annotations import BUILTINS
from clr.ast.type_nodes import parse_type


def parse_stmt(parser):
    if parser.check(TokenType.PRINT):
        return PrintStmt(parser)
    if parser.check(TokenType.LEFT_BRACE):
        return BlockStmt(parser)
    if parser.check(TokenType.IF):
        return IfStmt(parser)
    if parser.check(TokenType.WHILE):
        return WhileStmt(parser)
    if parser.check(TokenType.RETURN):
        return RetStmt(parser)
    return ExprStmt(parser)


class StmtNode:
    def __init__(self, parser):
        self.return_annotation = ReturnAnnotation()
        self.first_token = parser.get_current()


class BlockStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = parse_decl(parser)
            self.declarations.append(decl)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_block_stmt(self)


class ExprStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )

    def accept(self, stmt_visitor):
        stmt_visitor.visit_expr_stmt(self)


class RetStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        self.return_token = parser.get_prev()
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after return statement!", parser),
        )

    def accept(self, stmt_visitor):
        stmt_visitor.visit_ret_stmt(self)


class WhileStmt(StmtNode):
    def __init__(self, parser):
        # TODO: Break statements
        super().__init__()
        parser.consume(
            TokenType.WHILE, parse_error("Expected while statement!", parser)
        )
        if not parser.check(TokenType.LEFT_BRACE):
            self.condition = parse_expr(parser)
        else:
            self.condition = None
        self.block = BlockStmt(parser)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_while_stmt(self)


class IfStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
        self.checks = [(parse_expr(parser), BlockStmt(parser))]
        self.otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_expr(parser)
                other_block = BlockStmt(parser)
                self.checks.append((other_cond, other_block))
            else:
                self.otherwise = BlockStmt(parser)
                break

    def accept(self, stmt_visitor):
        stmt_visitor.visit_if_stmt(self)


class PrintStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.PRINT, parse_error("Expected print statement!", parser)
        )
        if not parser.match(TokenType.SEMICOLON):
            self.value = parse_expr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon for print statement!", parser),
            )
        else:
            self.value = None

    def accept(self, stmt_visitor):
        stmt_visitor.visit_print_stmt(self)


def parse_decl(parser):
    if parser.check_one(VAL_TOKENS):
        return ValDecl(parser)
    if parser.check(TokenType.FUNC):
        return FuncDecl(parser)
    return parse_stmt(parser)


class DeclNode(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.index_annotation = IndexAnnotation()


class FuncDecl(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.LEFT_PAREN,
            parse_error("Expected '(' to start function parameters!", parser),
        )
        self.params = []
        # Consume parameters until we hit the closing paren
        while not parser.match(TokenType.RIGHT_PAREN):
            # Consume a type for the parameter
            param_type = parse_type(parser)
            # And then a name for the parameter
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
            )
            param_name = parser.get_prev()
            # Append the parameters as (type, name) tuples
            pair = (param_type, param_name)
            self.params.append(pair)
            # If we haven't hit the end there must be a comma before the next parameter
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        # Consume the return type
        self.return_type = parse_type(parser)
        # Consume the definition block
        self.block = BlockStmt(parser)
        self.upvalues = []

    def accept(self, decl_visitor):
        decl_visitor.visit_func_decl(self)


class ValDecl(DeclNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume_one(
            VAL_TOKENS, parse_error("Expected value declaration!", parser)
        )
        self.mutable = parser.get_prev().token_type == TokenType.VAR
        # Consume the variable name
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        # Consume the expression to initialize with
        self.initializer = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )

    def accept(self, decl_visitor):
        decl_visitor.visit_val_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}
