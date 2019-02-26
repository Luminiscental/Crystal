#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

typedef enum {

    VAL_NUMBER,
    VAL_BOOL,
    VAL_STRING

} ValueType;

typedef struct {

    ValueType type;

    union {

        bool boolean;
        double number;
        char *string;

    } as;

} Value;

Value makeBoolean(bool boolean);
Value makeNumber(double number);
Value makeString(char *string);
Value concatStrings(char *first, char *second);
bool valuesEqual(Value a, Value b);

typedef struct {

    size_t capacity;
    size_t count;
    Value *values;

} ValueArray;

void initValueArray(ValueArray *array);
void writeValueArray(ValueArray *array, Value value);
void freeValueArray(ValueArray *array);

void printValue(Value value, bool endLine);

#endif
