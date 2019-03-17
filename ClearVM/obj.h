#ifndef clearvm_obj_h
#define clearvm_obj_h

#include "common.h"
#include "value.h"

typedef struct sVM VM;

typedef enum eObjType {

    OBJ_STRING,
    OBJ_FUNCTION

} ObjType;

typedef struct sObj {

    ObjType type;
    struct sObj *next;

} Obj;

bool isObjType(Value a, ObjType type);

typedef struct sObjString {

    Obj obj;
    size_t length;
    char *chars;

} ObjString;

char *makeRawStringFromNumber(double number, size_t *lengthOut);
Value makeStringFromLiteral(VM *vm, const char *string);
Value makeStringFromInteger(VM *vm, int32_t integer);
Value makeStringFromNumber(VM *vm, double number);

Value makeString(VM *vm, size_t length, char *string);
Value concatStrings(VM *vm, ObjString *first, ObjString *second);

typedef struct sObjFunction {

    Obj obj;
    uint8_t *code;
    uint8_t *ip;
    size_t size;

} ObjFunction;

Value makeFunction(VM *vm, uint8_t *code, size_t size);

#endif
