#ifndef clearvm_obj_h
#define clearvm_obj_h

#include "common.h"
#include "value.h"

typedef struct sVM VM;

typedef enum eObjType {

    OBJ_STRING

} ObjType;

typedef struct sObj {

    ObjType type;
    struct sObj *next;

} Obj;

typedef struct sObjString {

    Obj obj;
    size_t length;
    char *chars;

} ObjString;

Value makeStringFromLiteral(VM *vm, const char *string);
Value makeStringFromInteger(VM *vm, int32_t integer);
Value makeStringFromNumber(VM *vm, double number);

Value makeString(VM *vm, size_t length, char *string);
Value concatStrings(VM *vm, ObjString *first, ObjString *second);
bool isObjType(Value a, ObjType type);

#endif
