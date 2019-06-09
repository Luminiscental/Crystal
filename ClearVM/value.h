#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

#define STR_MAX 512
#define NUM_PLACES 7
#define NUM_PRECISION 0.0000001

typedef enum {

    OBJ_STRING

} ObjectType;

typedef struct sObjectValue ObjectValue;
struct sObjectValue {

    ObjectType type;
    void *ptr;
    ObjectValue *next;
};

typedef struct {

    size_t length;
    char *data;

} StringObject;

typedef enum {

    VAL_BOOL,
    VAL_NIL,
    VAL_OBJ,
    VAL_INT,
    VAL_NUM

} ValueType;

typedef struct {

    ValueType type;

    union {

        bool b;
        int32_t s32;
        double f64;
        ObjectValue *obj;

    } as;

} Value;

typedef struct {

    Value *data;
    size_t count;
    size_t capacity;

} ValueList;

void initValueList(ValueList *list);

void growValueList(ValueList *list);
void appendValueList(ValueList *list, Value value);
Result getValueList(ValueList *list, size_t index, Value *out);
Result setValueList(ValueList *list, size_t index, Value value);

void freeValueList(ValueList *list);

#endif
