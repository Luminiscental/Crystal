import struct
import sys
from clr.errors import ClrCompileError
from clr.values import DEBUG
from clr.ast import Ast, parse_source
from clr.assemble import assemble


def main():

    if len(sys.argv) < 2:
        print("Please provide a file to compile")
        sys.exit(1)
    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    if DEBUG:
        print("src:", source_file_name)
        print("dest:", dest_file_name)
    with open(source_file_name, "r") as source_file:
        source = source_file.read()
    try:
        if DEBUG:
            print("Compiling:")
        ast = parse_source(source)
        # TODO: Gen debug symbols
        code = ast.gen_code()
        byte_code = assemble(code)
    except ClrCompileError as e:
        print("Could not compile:")
        print(e)
    else:
        print("Compiled successfully")
        with open(dest_file_name, "wb") as dest_file:
            dest_file.write(byte_code)


if __name__ == "__main__":

    main()
