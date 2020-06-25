# -*- coding: utf-8 -*-

from __future__ import annotations

import io
from enum import Enum
from typing import Iterable, Optional, Union, Sequence, Any


class WireType(Enum):
    Varint = 0
    Fixed64 = 1
    LengthDelimited = 2
    StartGroup = 3
    EndGroup = 4
    Fixed32 = 5


class BaseProtoPrinter:
    def visit(self, ty: Union[FieldDescriptor, BaseTypeRepr]) -> str:
        raise NotImplementedError


class BaseTypeRepr:
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def get_fields(self) -> Sequence[Sequence[str, Any]]:
        pass

    def accept(self, printer: BaseProtoPrinter) -> str:
        return printer.visit(self)


class ProtoId:
    __slots__ = ("field_no", "wire_type")

    def __init__(self, field_no: int, wire_type: int):
        self.field_no = field_no
        self.wire_type = WireType(wire_type)


class FieldDescriptor:
    __slots__ = ("proto_id", )

    def __init__(self, stream: io.BufferedIOBase) -> None:
        self.proto_id = read_identifier(stream)

        if self.proto_id is None:
            raise ValueError("Incorrect Protobuf stream")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"{{{self.field_no} - {self.wire_type}}}"
        )

    def accept(self, printer: BaseProtoPrinter) -> str:
        return printer.visit(self)

    @property
    def field_no(self) -> int:
        return self.proto_id.field_no

    @property
    def wire_type(self) -> WireType:
        return self.proto_id.wire_type


def _iter_bytes(stream: io.BufferedIOBase) -> Iterable[bytes]:
    byte = stream.read1(1)

    while len(byte) != 0:
        yield byte
        byte = stream.read1(1)


def read_varint(stream: io.BufferedIOBase) -> Optional[int]:
    varint = 0
    pos = 0
    has_next = False

    for byte in _iter_bytes(stream):
        num = ord(byte)
        has_next = (num & 0b1000_0000) != 0
        value = num & 0b0111_1111
        varint |= value << pos
        pos += 7

        if not has_next:
            break

    if has_next:
        # malformed varint as the last
        # byte should clear has_next flag
        return None

    return varint if pos != 0 else None


def read_identifier(stream: io.BufferedIOBase) -> Optional[ProtoId]:
    identifier = read_varint(stream)

    if identifier is None:
        return None

    return ProtoId(identifier >> 3, identifier & 0b111)


def read_fixed(stream: io.BufferedIOBase,
               wire_type: WireType) -> Optional[bytes]:
    fixed_width = {WireType.Fixed32: 4, WireType.Fixed64: 8}
    data = stream.read1(fixed_width[WireType(wire_type)])

    if len(data) == 0 or len(data) != fixed_width[wire_type]:
        return None

    return data


def read_length_delimited(stream: io.BufferedIOBase) -> Optional[bytes]:
    length = read_varint(stream)

    if length is None:
        return None

    data = stream.read1(length)

    return data if len(data) == length else None


def read_value(stream: io.BufferedIOBase,
               wire_type: WireType) -> Optional[Union[int, bytes]]:
    if wire_type == WireType.Varint:
        return read_varint(stream)
    elif wire_type == WireType.Fixed32 or wire_type == WireType.Fixed64:
        return read_fixed(stream, wire_type)
    elif wire_type == WireType.LengthDelimited:
        return read_length_delimited(stream)
    elif wire_type == WireType.StartGroup or wire_type == WireType.EndGroup:
        raise NotImplementedError(
            "Protobuf StartGroup and EndGroup is deprecated"
        )

    raise Exception(f"Unknown wire type {wire_type}")
