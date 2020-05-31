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

    def get_fields(self) -> Sequence[Sequence[Union[str, Any]]]:
        return (
            ("sint", self.sint),
            ("uint", self.int),
        )

    def accept(self, printer: BaseProtoPrinter) -> str:
        return super().accept(printer)

    @classmethod
    def from_bytes(cls, payload: bytes):
        return cls(read_varint(io.BytesIO(payload)))

    @property
    def int(self) -> int:
        return self._int_repr

    @property
    def sint(self) -> int:
        return self._sint_repr


class FixedRepr(BaseTypeRepr):
    __slots__ = ("_float_repr", "_int_repr", "_uint_repr")

    def __init__(
        self, value: bytes, int_fmt: str, uint_fmt: str, float_fmt: str
    ) -> None:
        self._float_repr, *_ = struct.unpack(float_fmt, value)
        self._int_repr, *_ = struct.unpack(int_fmt, value)
        self._uint_repr, *_ = struct.unpack(uint_fmt, value)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}:{os.linesep}"
            f"\tsint: {self.int}{os.linesep}"
            f"\tuint: {self.uint}{os.linesep}"
            f"\tfloat: {self.float}"
        )

    def get_fields(self) -> Sequence[Sequence[Union[str, Any]]]:
        return (
            ("sint", self._int_repr), ("uint", self._uint_repr),
            ("float", self._float_repr)
        )

    def accept(self, printer: BaseProtoPrinter) -> str:
        return super().accept(printer)

    @classmethod
    def from_bytes(cls, payload: bytes):
        pass

    @property
    def float(self) -> float:
        return self._float_repr

    @property
    def int(self) -> int:
        return self._int_repr

    @property
    def uint(self) -> int:
        return self._uint_repr


class Fixed32Repr(FixedRepr):
    def __init__(self, value: bytes) -> None:
        super().__init__(value, "<i", "<I", "<f")


class Fixed64Repr(FixedRepr):
    def __init__(self, value: bytes) -> None:
        super().__init__(value, "<q", "<Q", "<d")


class ChunkRepr(BaseTypeRepr):
    def __init__(self, value: bytes) -> None:
        self._chunk_repr = value

        try:
            str_candidate = self._chunk_repr.decode()
            self._str_repr = str_candidate if all(
                c in string.printable for c in str_candidate
            ) else None
        except UnicodeDecodeError:
            self._str_repr = None

        self._message_repr = parse_proto(self._chunk_repr)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}:{os.linesep}"
            f"\tchunk: {self.chunk.hex(' ')}{os.linesep}"
            f"\tstr: {self.str}{os.linesep}"
            f"\tsub-msg:{os.linesep}\t\t{self.msg}"
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
