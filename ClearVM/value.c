
#include "value.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"

Value makeBoolean(bool boolean) {

    Value result;

    result.type = VAL_BOOL;
    result.as.boolean = boolean;

    return result;
}

Value makeNumber(double number) {

    Value result;

    result.type = VAL_NUMBER;
    result.as.number = number;

    return result;
}

Value makeString(char *string) {

    Value result;

    result.type = VAL_STRING;
    result.as.string = string;

    return result;
}

Value concatStrings(char *first, char *second) {

    size_t sizeFirst = strlen(first);
    size_t sizeSecond = strlen(second);

    char *result = (char*) malloc(sizeFirst + sizeSecond + 1);
    result[sizeFirst] = '\0';
    strcpy(result, first);
    strcat(result, second);

    free(first);
    free(second);

    return makeString(result);
}

bool valuesEqual(Value a, Value b) {

    if (a.type != b.type) return false;

    switch (a.type) {
    
        case VAL_BOOL:

            return a.as.boolean == b.as.boolean;

        case VAL_NUMBER:

            return a.as.number == b.as.number;

        case VAL_STRING:

            return strcmp(a.as.string, b.as.string) == 0;
    }
}

void initValueArray(ValueArray *array) {

    array->values = NULL;
    array->capacity = 0;
    array->count = 0;
}

void writeValueArray(ValueArray *array, Value value) {

    if (array->capacity < array->count + 1) {

        int oldCapacity = array->capacity;
        array->capacity = GROW_CAPACITY(oldCapacity);
        array->values = GROW_ARRAY(array->values, Value, oldCapacity,
                array->capacity);
    }

    array->values[array->count++] = value;
}

void freeValueArray(ValueArray *array) {

    for (size_t i = 0; i < array->count; i++) {

        Value value = array->values[i];

        if (value.type == VAL_STRING) {

            free(value.as.string);
        }
    }

    FREE_ARRAY(Value, array->values, array->capacity);
    initValueArray(array);
}

void printValue(Value value, bool endLine) {

    switch (value.type) {

        case VAL_NUMBER: {

            printf("<num %g>", value.as.number);

        } break;

        case VAL_STRING: {

            printf("<str \"%s\">", value.as.string);

        } break;

        case VAL_BOOL: {

            printf("<bool %s>", value.as.boolean ? "true" : "false");

        } break;
    }

    if (endLine) printf("\n");
}

