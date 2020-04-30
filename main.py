#!/usr/bin/env python3

from revpbuf.types import StandardParser
import io

if __name__ == "__main__":
    # proto_string = io.BytesIO(b"\x08\x06")
    proto_s = bytes.fromhex(
        "08 96 01 12 0A 50 68 6F 6E 65 20 42 6F 6F 6B 18 01 22 0F 0A 0B 41 6C 65 78 20 49 76 61 6E 6F 76 10 01 22 0F 0A 0B 56 6F 76 61 20 50 65 74 72 6F 76 10 02"
    )
    proto_string = io.BytesIO(proto_s)
    parser = StandardParser()
    root_type = "root"

    if root_type not in parser.types:
        parser.types[root_type] = {}

    parser.types[root_type]["compact"] = False
    print(parser.parse(proto_string, root_type))
