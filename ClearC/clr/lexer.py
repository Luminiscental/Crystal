"""
Contains functions and definitions for lexing Clear code into a list of tokens.
"""

from typing import List, Optional, Iterable, Tuple

import enum
import re


class IncompatibleSourceError(Exception):
    """
    Custom exception for when source views expected to have the same source have different sources.
    """


class SourceView:
    """
    Represents a region within a Clear source string.
    """

    def __init__(self, source: str, start: int, end: int) -> None:
        self.start = start
        self.end = end
        self.source = source

    def __repr__(self) -> str:
        return f"SourceView[{str(self)}]"

    def __str__(self) -> str:
        return self.source[self.start : self.end + 1]

    @staticmethod
    def range(start: "SourceView", end: "SourceView") -> "SourceView":
        """
        Takes a start and end view and returns a view of the whole range between them.
        If they view separate sources raises an IncompatibleSourceError.
        """
        if start.source != end.source:
            raise IncompatibleSourceError()
        return SourceView(source=start.source, start=start.start, end=end.end)


@enum.unique
class TokenType(enum.Enum):
    """
    Enumerates the different types of tokens that can be in valid Clear source code.
    """

    # Non-definite tokens
    IDENTIFIER = enum.auto()
    INT_LITERAL = enum.auto()
    NUM_LITERAL = enum.auto()
    STR_LITERAL = enum.auto()
    # Keywords
    VAL = enum.auto()
    FUNC = enum.auto()
    IF = enum.auto()
    ELSE = enum.auto()
    WHILE = enum.auto()
    RETURN = enum.auto()
    PRINT = enum.auto()
    VOID = enum.auto()
    # Symbols
    EQUALS = enum.auto()
    COMMA = enum.auto()
    SEMICOLON = enum.auto()
    LEFT_BRACE = enum.auto()
    RIGHT_BRACE = enum.auto()
    LEFT_PAREN = enum.auto()
    RIGHT_PAREN = enum.auto()
    QUESTION_MARK = enum.auto()
    # Special
    ERROR = enum.auto()


class Token:
    """
    Represents a single token within a string of Clear source code.
    """

    def __init__(self, kind: TokenType, region: SourceView, lexeme: SourceView) -> None:
        self.kind = kind
        self.region = region
        self.lexeme = lexeme

    def __repr__(self) -> str:
        return f"Token(kind={self.kind}, region={self.region}, lexeme={self.lexeme})"

    def __str__(self) -> str:
        return str(self.lexeme)


class Lexer:
    """
    Class for walking over a source string and emitting tokens or skipping based on regex patterns.
    """

    tokens: List[Token]

    def __init__(self, source: str) -> None:
        self.source = source
        self.start = 0
        self.end = 0
        self.tokens = []

    def done(self) -> bool:
        """
        Returns whether the source has been fully used up or not.
        """
        return self.end == len(self.source)

    def reset(self) -> None:
        """
        Resets the lexer to the start of its source
        """
        self.start = 0
        self.end = 0

    def consume(self, pattern: str, kind: TokenType) -> bool:
        """
        Check if the pattern is matched, and if it is emit it as a token and move after it.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.end :])
        if match:
            literal = match.group(0)
            region = SourceView(
                source=self.source, start=self.start, end=self.end + len(literal) - 1
            )
            lexeme = SourceView(
                source=self.source, start=self.end, end=self.end + len(literal) - 1
            )
            self.tokens.append(Token(kind=kind, region=region, lexeme=lexeme))
            self.end += len(literal)
            self.start = self.end
            return True
        return False

    def skip(self, pattern: str) -> bool:
        """
        Check if the pattern is matched, and if it is move after it while leaving the start of
        the region before, so that the next consumed token will include this skipped region.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.end :])
        if match:
            literal = match.group(0)
            self.end += len(literal)
            return True
        return False

    def run(
        self,
        consume_rules: Optional[Iterable[Tuple[str, TokenType]]] = None,
        skip_rules: Optional[Iterable[str]] = None,
        fallback: Optional[Tuple[str, TokenType]] = None,
    ) -> None:
        """
        Given an optional iterable of patterns to consume to token types, an optional iterable of
        patterns to skip, and an optional fallback pattern to consume to a fallback token type,
        loops over the source with these rules until reaching the end, or until reaching something
        it can't consume.
        """
        while not self.done():
            if consume_rules and any(
                self.consume(pattern, kind) for pattern, kind in consume_rules
            ):
                continue
            if skip_rules and any(self.skip(pattern) for pattern in skip_rules):
                continue
            if not fallback or not self.consume(fallback[0], fallback[1]):
                break


def tokenize_source(source: str) -> List[Token]:
    """
    Given a string of Clear source code, lexes it into a list of tokens.
    """
    skip_rules = [r"//.*", r"\s+"]
    consume_rules = [
        (r"[a-zA-Z_][a-zA-Z0-9_]*", TokenType.IDENTIFIER),
        (r"[0-9]+i", TokenType.INT_LITERAL),
        (r"[0-9]+(\.[0-9]+)?", TokenType.NUM_LITERAL),
        (r"\".*?\"", TokenType.STR_LITERAL),
        (r"=", TokenType.EQUALS),
        (r",", TokenType.COMMA),
        (r";", TokenType.SEMICOLON),
        (r"{", TokenType.LEFT_BRACE),
        (r"}", TokenType.RIGHT_BRACE),
        (r"\(", TokenType.LEFT_PAREN),
        (r"\)", TokenType.RIGHT_PAREN),
        (r"\?", TokenType.QUESTION_MARK),
    ]
    fallback_rule = (r".", TokenType.ERROR)

    lexer = Lexer(source)
    lexer.run(consume_rules, skip_rules, fallback_rule)

    def keywordize(token: Token) -> Token:
        keywords = {
            "val": TokenType.VAL,
            "func": TokenType.FUNC,
            "void": TokenType.VOID,
            "if": TokenType.IF,
            "else": TokenType.ELSE,
            "while": TokenType.WHILE,
            "return": TokenType.RETURN,
            "print": TokenType.PRINT,
        }

        if token.kind == TokenType.IDENTIFIER:
            lexeme = str(token.lexeme)
            if lexeme in keywords:
                token.kind = keywords[lexeme]
        return token

    return [keywordize(token) for token in lexer.tokens]