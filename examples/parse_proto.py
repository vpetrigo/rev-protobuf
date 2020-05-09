#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pathlib
import sys

if __name__ == "__main__":
    cur_dir = pathlib.Path(__file__).parent.absolute()
    sys.path.append(str(cur_dir.parent))

    from utils import Printer
    from revpbuf.parser import parse_proto, MessageRepr


def proto_print(message: MessageRepr, level: int = 0) -> None:
    printer = Printer()
    printer.level = level

    for field in message.fields:
        field.field_desc.accept(printer)
        field.field_repr.accept(printer)


if __name__ == "__main__":
    proto_string1 = bytes.fromhex(
        "08 96 01 12 0A 50 68 6F 6E 65 20 42 6F 6F"
        "6B 18 01 22 0F 0A 0B 41 6C 65 78 20 49 76"
        "61 6E 6F 76 10 01 22 0F 0A 0B 56 6F 76 61"
        "20 50 65 74 72 6F 76 10 02"
    )
    proto_string2 = bytes.fromhex("08 96 01 12 02 08 02")

    for proto_string in (proto_string1, proto_string2):
        print("=" * 32, "Message", "=" * 32)
        result = parse_proto(proto_string)
        proto_print(result)
        print("=" * 73)
