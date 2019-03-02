
import re
from enum import Enum
from clr.errors import emit_error
from clr.trie import Trie, TrieResult
from clr.values import TokenType,\
                       keyword_types, simple_tokens, equal_suffix_tokens

class Token:

    def __init__(self, token_type, lexeme, line):
        self.token_type = token_type
        self.lexeme = lexeme
        self.line = line

    def __repr__(self):
        return f'Token({self.token_type}, \'{self.lexeme}\', {self.line})'

class ScanState(Enum):

    NUMBER = 0,
    DECIMAL = 1,
    STRING = 2,
    IDENTIFIER = 3,
    ANY = 4

def token_info(token):

    return f'<line {str(token.line)}> "{token.lexeme}"'

def store_acc(token_type, acc, line, tokens):

    tokens.append(Token(token_type, ''.join(acc), line))
    del acc[:]

def scan_number(char, acc, line, keyword_trie, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    elif char == '.':
        acc.append(char)
        return True, ScanState.DECIMAL, line
    elif char == 'i':
        store_acc(TokenType.NUMBER, acc, line, tokens)
        tokens.append(Token(TokenType.INTEGER_SUFFIX, 'i', line))
        num_token = tokens[-2]
        suff_token = tokens[-1]
        return True, ScanState.ANY, line
    else:
        store_acc(TokenType.NUMBER, acc, line, tokens)
        return False, ScanState.ANY, line

def scan_decimal(char, acc, line, keyword_trie, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    else:
        store_acc(TokenType.NUMBER, acc, line, tokens)
        return False, ScanState.ANY, line

def scan_string(char, acc, line, keyword_trie, tokens):

    if char == '"':
        if char == '\n':
            line += 1
        acc.append(char)
        store_acc(TokenType.STRING, acc, line, tokens)
        return True, ScanState.ANY, line
    else:
        acc.append(char)
        return True, None, line

def scan_identifier(char, acc, line, keyword_trie, tokens):

    if char.isalpha() or char.isdigit() or char == '_':
        result, _ = keyword_trie.step(char)
        acc.append(char)
        if result == TrieResult.FINISH:
            lexeme = ''.join(acc)
            store_acc(keyword_types[lexeme], acc, line, tokens)
            return True, ScanState.ANY, line
        return True, None, line
    else:
        store_acc(TokenType.IDENTIFIER, acc, line, tokens)
        return False, ScanState.ANY, line

def scan_any(char, acc, line, keyword_trie, tokens):

    if char in simple_tokens:
        tokens.append(Token(simple_tokens[char], char, line))
        return None, line
    elif (char == '=' and tokens
            and tokens[-1].lexeme in equal_suffix_tokens
            and tokens[-1].token_type != TokenType.EQUAL_EQUAL):
        suffix_type = equal_suffix_tokens[tokens[-1].lexeme]
        tokens[-1] = Token(suffix_type.present,
                           tokens[-1].lexeme + '=',
                           line)
        return None, line
    elif char in equal_suffix_tokens:
        suffix_type = equal_suffix_tokens[char]
        tokens.append(Token(suffix_type.nonpresent, char, line))
        return None, line
    elif char.isdigit():
        # TODO: Negative number literals?
        acc.append(char)
        return ScanState.NUMBER, line
    elif char == '"':
        acc.append(char)
        return ScanState.STRING, line
    elif char == '\n':
        return None, line + 1
    elif char.isspace():
        tokens.append(Token(TokenType.SPACE, ' ', line))
        return None, line
    elif char.isalpha() or char == '_':
        if tokens and tokens[-1].token_type in keyword_types.values():
            acc.extend(tokens[-1].lexeme)
            del tokens[-1]
        else:
            keyword_trie.reset()
        keyword_trie.step(char)
        acc.append(char)
        return ScanState.IDENTIFIER, line
    else:
        emit_error(f'Unrecognized character \'{char}\'')()

def tokenize(source):

    # Replace // followed by a string of non-newline characters with nothing
    source = re.sub(r'//.*', '', source)

    keyword_trie = Trie(keyword_types)
    scan_state = ScanState.ANY
    tokens = []
    acc = []
    line = 1

    for char in source:
        if scan_state != ScanState.ANY:
            consumed, next_state, line = {
                ScanState.NUMBER : scan_number,
                ScanState.DECIMAL : scan_decimal,
                ScanState.STRING : scan_string,
                ScanState.IDENTIFIER : scan_identifier
            }.get(scan_state, emit_error(
                f'Unknown scanning state! {scan_state}'
            ))(char, acc, line, keyword_trie, tokens)
            if next_state:
                scan_state = next_state
            if consumed:
                continue
        next_state, line = scan_any(char, acc, line, keyword_trie, tokens)
        if next_state:
            scan_state = next_state

    tokens = [token for token in tokens
            if token.token_type != TokenType.SPACE]
    tokens.append(Token(TokenType.EOF, '', line))

    return tokens

