from clr.errors import parse_error
from clr.tokens import TokenType
from clr.ast.type_annotations import (
    IdentifierTypeAnnotation,
    FunctionTypeAnnotation,
    SIMPLE_TYPES,
    VOID_TYPE,
)


class VoidType:
    def __init__(self):
        self.as_annotation = VOID_TYPE

    def accept(self, type_visitor):
        type_visitor.visit_void_type(self)


class SimpleType:
    def __init__(self, token, as_annotation):
        self.token = token
        self.as_annotation = as_annotation

    def accept(self, type_visitor):
        type_visitor.visit_simple_type(self)


def parse_simple_type(parser):
    err = parse_error("Expected simple type!", parser)
    parser.consume(TokenType.IDENTIFIER, err)
    token = parser.get_prev()
    if token.lexeme not in SIMPLE_TYPES:
        if token.token_type == TokenType.IDENTIFIER:
            as_annotation = IdentifierTypeAnnotation(token.lexeme)
        else:
            err()
    else:
        as_annotation = SIMPLE_TYPES[token.lexeme]
    return SimpleType(token, as_annotation)


class FunctionType:
    def __init__(self, params, return_type, as_annotation):
        self.params = params
        self.return_type = return_type
        self.as_annotation = as_annotation

    def accept(self, type_visitor):
        type_visitor.visit_func_type(self)


def parse_function_type(parser):
    parser.consume(TokenType.FUNC, parse_error("Expected function type!", parser))
    parser.consume(
        TokenType.LEFT_PAREN, parse_error("Expected parameter types!", parser)
    )
    params = []
    while not parser.match(TokenType.RIGHT_PAREN):
        param_type = parse_type(parser)
        params.append(param_type)
        if not parser.check(TokenType.RIGHT_PAREN):
            parser.consume(
                TokenType.COMMA,
                parse_error("Expected comma to delimit parameters!", parser),
            )
    return_type = parse_type(parser)
    as_annotation = FunctionTypeAnnotation(
        return_type=return_type.as_annotation,
        signature=list(map(lambda param: param.as_annotation, params)),
    )
    return FunctionType(params, return_type, as_annotation)


def parse_type(parser):
    if parser.check(TokenType.FUNC):
        return parse_function_type(parser)
    return parse_simple_type(parser)
