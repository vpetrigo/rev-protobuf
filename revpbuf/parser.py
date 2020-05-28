# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import os
import string
import struct
from typing import Any, Optional, Sequence, Union, List

from .core import read_varint, read_value, WireType, FieldDescriptor, BaseTypeRepr, BaseProtoPrinter


class Field:
    def __init__(
        self, field_desc: FieldDescriptor, field_repr: BaseTypeRepr
    ) -> None:
        self.field_desc = field_desc
        self.field_repr = field_repr

    def __repr__(self) -> str:
        return (
            f"Field {self.field_desc.field_no}"
            f" - type <{self.field_desc.wire_type}>{os.linesep}"
            f"\t{self.field_repr}"
        )


class MessageRepr(BaseTypeRepr):
    def __init__(self) -> None:
        self._fields: List[Field] = []

    def __repr__(self) -> str:
        return f"{os.linesep}".join([repr(field) for field in self._fields])

    @property
    def fields(self) -> Sequence[Field]:
        return self._fields

    def add_field(self, field: Field) -> None:
        self._fields.append(field)


class VarintRepr(BaseTypeRepr):
    __slots__ = ("_int_repr", "_sint_repr")

    def __init__(self, value: int):
        self._int_repr = value
        self._sint_repr = zigzag_decode(self._int_repr)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}:{os.linesep}"
            f"\tsint: {self.sint}{os.linesep}"
            f"\tuint: {self.int}"
        )
        return "\n".join(lines)

    def to_display_compactly(self, type, lines):
        try:
            return self.types[type]["compact"]
        except KeyError:
            pass

        for line in lines:
            if "\n" in line or len(line) > self.compact_max_line_length:
                return False
        if sum(len(line) for line in lines) > self.compact_max_length:
            return False
        return True

    def hex_dump(self, file, mark=None):
        lines = []
        offset = 0
        decorate = lambda i, x: \
            x if (mark is None or offset + i < mark) else x

        while True:
            chunk = list(file.read(self.bytes_per_line))
            if not len(chunk):
                break
            padded_chunk = chunk + [None
                                   ] * max(0, self.bytes_per_line - len(chunk))
            hexdump = " ".join(
                "  " if x is None else decorate(i, "%02X" % x)
                for i, x in enumerate(padded_chunk)
            )
            printable_chunk = "".join(
                decorate(i,
                         chr(x) if 0x20 <= x < 0x7F else ".")
                for i, x in enumerate(chunk)
            )
            lines.append("%04x   %s  %s" % (offset, hexdump, printable_chunk))
            offset += len(chunk)
        return ("\n".join(lines), offset)

    # Error handling

    def safe_call(self, handler, x, *wargs):
        chunk = False
        try:
            chunk = x.read()
            print("CHUNK:", chunk)
            x = BytesIO(chunk)
        except Exception:
            pass

        try:
            return handler(x, *wargs)
        except Exception as e:
            self.errors_produced.append(e)
            hex_dump = "" if chunk is False else "\n\n%s\n" % self.hex_dump(
                BytesIO(chunk), x.tell()
            )[0]
            return "{}: {}{}".format(
                "ERROR",
                self.indent(format_exc()).strip(), self.indent(hex_dump)
            )

    def parse(self, data, *args):
        return self.safe_call(self.match_handler("message"), data, *args)

    # Select suitable native type to use

    def match_native_type(self, ty) -> _NativeTypeDescriptor:
        print("match_native_type:", ty)

        type_primary = ty.split(" ")[0]
        print(type_primary)

        return self.native_types.get(
            type_primary, self.native_types[self.default_handler]
        )

    def match_handler(self, ty, wire_type=None) -> Callable[[Any, int], Any]:
        print("match_handler:", ty, wire_type)
        native_type = self.match_native_type(ty)

        if wire_type is not None and wire_type != native_type[1]:
            raise Exception(
                "Found wire type %d (%s), wanted type %d (%s)" % (
                    wire_type, self.default_handlers[wire_type],
                    native_type.wire_type, ty
                )
            )
        print("match_handler:", native_type)
        return native_type.parser
