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


class MessageRepr:
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
    def from_bytes(cls, payload: bytes) -> Optional[VarintRepr]:
        value = read_varint(io.BytesIO(payload))

        return cls(value) if value is not None else None

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

    def get_fields(self) -> Sequence[Sequence[Union[str, Any]]]:
        return (
            ("chunk", self.chunk.hex(" ")),
            ("str", self.str),
            ("sub-msg", self.msg),
        )

    def accept(self, printer: BaseProtoPrinter) -> str:
        return super().accept(printer)

    @property
    def chunk(self) -> bytes:
        return self._chunk_repr

    @property
    def str(self) -> str:
        return self._str_repr

    @property
    def msg(self) -> MessageRepr:
        return self._message_repr


def zigzag_decode(number: int) -> int:
    return (number >> 1) ^ -(number & 1)


def parse_fixed32(payload: bytes) -> Fixed32Repr:
    return Fixed32Repr(payload)


def parse_fixed64(payload: bytes) -> Fixed64Repr:
    return Fixed64Repr(payload)


def parse_chunk(payload: bytes) -> ChunkRepr:
    return ChunkRepr(payload)


def parse_varint(value: int) -> VarintRepr:
    return VarintRepr(value)


def parse_fixed32_stream(stream: io.BufferedIOBase) -> Fixed32Repr:
    payload = read_value(stream, WireType.Fixed32)

    return Fixed32Repr(payload)


def parse_fixed64_stream(stream: io.BufferedIOBase) -> Fixed64Repr:
    payload = read_value(stream, WireType.Fixed64)

    return Fixed64Repr(payload)


def parse_chunk_stream(stream: io.BufferedIOBase) -> ChunkRepr:
    value = read_value(stream, WireType.LengthDelimited)

    return ChunkRepr(value)


def parse_varint_stream(stream: io.BufferedIOBase) -> VarintRepr:
    value = read_value(stream, WireType.Varint)

    return parse_varint(value)


def parse_proto(payload: bytes) -> Optional[MessageRepr]:
    stream = io.BytesIO(payload)
    message = MessageRepr()
    handlers = {
        WireType.Varint: parse_varint_stream,
        WireType.Fixed64: parse_fixed64_stream,
        WireType.Fixed32: parse_fixed32_stream,
        WireType.LengthDelimited: parse_chunk_stream
    }

    while True:
        try:
            field = FieldDescriptor(stream)
            field_repr = handlers[field.proto_id.wire_type](stream)
            message.add_field(Field(field, field_repr))

            if len(stream.read1(1)) == 1:
                stream.seek(-1, io.SEEK_CUR)
            else:
                break
        except ValueError:
            return None

    return message
