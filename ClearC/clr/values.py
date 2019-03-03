from collections import namedtuple, defaultdict
from enum import Enum

debug = False


class OpCode(Enum):

    # Constant storage
    STORE_CONST = 0
    INTEGER = 1
    NUMBER = 2
    STRING = 3
    # Constant generation
    LOAD_CONST = 4
    TRUE = 5
    FALSE = 6
    # Variables
    DEFINE_GLOBAL = 7
    LOAD_GLOBAL = 8
    # Built-ins
    TYPE = 9
    INT = 10
    BOOL = 11
    NUM = 12
    STR = 13
    # Statements
    PRINT = 14
    PRINT_BLANK = 15
    RETURN = 16
    POP = 17
    # Arithmetic operators
    NEGATE = 18
    ADD = 19
    SUBTRACT = 20
    MULTIPLY = 21
    DIVIDE = 22
    # Comparison operators
    LESS = 23
    NLESS = 24
    GREATER = 25
    NGREATER = 26
    EQUAL = 27
    NEQUAL = 28
    # Boolean operators
    NOT = 29

    def __str__(self):
        return "OP_" + self.name


class Precedence(Enum):

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
    PRIMARY = 10

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __cmp__(self, other):
        if self.value == other.value:
            return 0
        elif self.value < other.value:
            return -1
        else:
            return 1

    def next(self):
        return Precedence(self.value + 1)


class TokenType(Enum):

    # symbols
    LEFT_PAREN = 0
    RIGHT_PAREN = 1
    LEFT_BRACE = 2
    RIGHT_BRACE = 3
    COMMA = 4
    DOT = 5
    MINUS = 6
    PLUS = 7
    SEMICOLON = 8
    SLASH = 9
    STAR = 10
    BANG = 11
    BANG_EQUAL = 12
    EQUAL = 13
    EQUAL_EQUAL = 14
    GREATER = 15
    GREATER_EQUAL = 16
    LESS = 17
    LESS_EQUAL = 18
    # values
    IDENTIFIER = 19
    STRING = 20
    NUMBER = 21
    INTEGER_SUFFIX = 22
    # keywords
    AND = 23
    CLASS = 24
    ELSE = 25
    FALSE = 26
    FOR = 27
    FUNC = 28
    IF = 29
    OR = 30
    PRINT = 31
    RETURN = 32
    SUPER = 33
    THIS = 34
    TRUE = 35
    VAL = 36
    WHILE = 37
    # built-ins
    TYPE = 38
    INT = 39
    BOOL = 40
    NUM = 41
    STR = 42
    # special
    SPACE = 43
    EOF = 44


keyword_types = {
    "and": TokenType.AND,
    "class": TokenType.CLASS,
    "else": TokenType.ELSE,
    "false": TokenType.FALSE,
    "for": TokenType.FOR,
    "func": TokenType.FUNC,
    "if": TokenType.IF,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
    "return": TokenType.RETURN,
    "super": TokenType.SUPER,
    "this": TokenType.THIS,
    "true": TokenType.TRUE,
    "val": TokenType.VAL,
    "while": TokenType.WHILE,
    "type": TokenType.TYPE,
    "int": TokenType.INT,
    "bool": TokenType.BOOL,
    "num": TokenType.NUM,
    "str": TokenType.STR,
}

simple_tokens = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
}

SuffixType = namedtuple("SuffixType", "present nonpresent")

equal_suffix_tokens = {
    "!": SuffixType(TokenType.BANG_EQUAL, TokenType.BANG),
    "=": SuffixType(TokenType.EQUAL_EQUAL, TokenType.EQUAL),
    "<": SuffixType(TokenType.LESS_EQUAL, TokenType.LESS),
    ">": SuffixType(TokenType.GREATER_EQUAL, TokenType.GREATER),
}


class ParseRule:
    def __init__(self, prefix=None, infix=None, precedence=Precedence.NONE):
        self.prefix = prefix
        self.infix = infix
        self.precedence = precedence

    def fill(self, err):
        if not self.prefix:
            self.prefix = err
        if not self.infix:
            self.infix = err


def pratt_table(parser):

    return defaultdict(
        ParseRule,
        {
            TokenType.LEFT_PAREN: ParseRule(
                prefix=parser.finish_grouping, precedence=Precedence.CALL
            ),
            TokenType.MINUS: ParseRule(
                prefix=parser.finish_unary,
                infix=parser.finish_binary,
                precedence=Precedence.TERM,
            ),
            TokenType.PLUS: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.TERM
            ),
            TokenType.SLASH: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.FACTOR
            ),
            TokenType.STAR: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.FACTOR
            ),
            TokenType.NUMBER: ParseRule(prefix=parser.consume_number),
            TokenType.STRING: ParseRule(prefix=parser.consume_string),
            TokenType.TRUE: ParseRule(prefix=parser.consume_boolean),
            TokenType.FALSE: ParseRule(prefix=parser.consume_boolean),
            TokenType.AND: ParseRule(precedence=Precedence.AND),
            TokenType.OR: ParseRule(precedence=Precedence.OR),
            TokenType.BANG: ParseRule(prefix=parser.finish_unary),
            TokenType.EQUAL_EQUAL: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.EQUALITY
            ),
            TokenType.BANG_EQUAL: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.EQUALITY
            ),
            TokenType.LESS: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.COMPARISON
            ),
            TokenType.GREATER_EQUAL: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.COMPARISON
            ),
            TokenType.GREATER: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.COMPARISON
            ),
            TokenType.LESS_EQUAL: ParseRule(
                infix=parser.finish_binary, precedence=Precedence.COMPARISON
            ),
            TokenType.IDENTIFIER: ParseRule(prefix=parser.consume_variable_reference),
            TokenType.TYPE: ParseRule(
                prefix=parser.consume_builtin, precedence=Precedence.CALL
            ),
            TokenType.INT: ParseRule(
                prefix=parser.consume_builtin, precedence=Precedence.CALL
            ),
            TokenType.BOOL: ParseRule(
                prefix=parser.consume_builtin, precedence=Precedence.CALL
            ),
            TokenType.NUM: ParseRule(
                prefix=parser.consume_builtin, precedence=Precedence.CALL
            ),
            TokenType.STR: ParseRule(
                prefix=parser.consume_builtin, precedence=Precedence.CALL
            ),
        },
    )
