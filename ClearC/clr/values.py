"""
This module provides clr module scope constants such as debug flags
or file format specification values.
"""
from enum import Enum

DEBUG = False
DEBUG_ASSEMBLE = False


class OpCode(Enum):
    """
    This class enumerates the possible opcodes for .clr.b files
    along with their byte values as ints.
    """

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
    DEFINE_LOCAL = 9
    LOAD_LOCAL = 10
    # Built-ins
    INT = 11
    BOOL = 12
    NUM = 13
    STR = 14
    CLOCK = 15
    # Statements
    PRINT = 16
    PRINT_BLANK = 17
    RETURN = 18
    RETURN_VOID = 19
    POP = 20
    # Arithmetic operators
    NEGATE = 21
    ADD = 22
    SUBTRACT = 23
    MULTIPLY = 24
    DIVIDE = 25
    # Comparison operators
    LESS = 26
    NLESS = 27
    GREATER = 28
    NGREATER = 29
    EQUAL = 30
    NEQUAL = 31
    # Boolean operators
    NOT = 32
    # Scoping
    PUSH_SCOPE = 33
    POP_SCOPE = 34
    # Control flow
    JUMP = 35
    JUMP_IF_NOT = 36
    LOOP = 37
    # Functions
    LOAD_PARAM = 38
    START_FUNCTION = 39
    CALL = 40
    # Closures
    CLOSURE = 41
    LOAD_UPVALUE = 42
    SET_UPVALUE = 43
    # Structs
    STRUCT = 44
    GET_FIELD = 45
    SET_FIELD = 46

    def __str__(self):
        return "OP_" + self.name
