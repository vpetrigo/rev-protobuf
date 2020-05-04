import io

from enum import Enum
from collections import namedtuple
from typing import Iterable, Optional, Union

# Core parsing. This handles the most low-level deserialization.
# No guessing going on here. These functions return None on EOF.

ProtoId = namedtuple("ProtoId", ["field_no", "wire_type"])


class WireType(Enum):
    Varint = 0
    Fixed64 = 1
    LengthDelimited = 2
    StartGroup = 3
    EndGroup = 4
    Fixed32 = 5


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


def read_fixed(stream: io.BufferedIOBase, wire_type: int) -> Optional[int]:
    fixed_width = {WireType.Fixed32: 4, WireType.Fixed64: 8}
    data = stream.read1(fixed_width[WireType(wire_type)])

    if len(data) == 0 or len(data) != fixed_width[wire_type]:
        return None

    return int.from_bytes(data, byteorder="little")


def read_length_delimited(stream: io.BufferedIOBase) -> Optional[bytes]:
    length = read_varint(stream)

    if length is None:
        return None

    data = stream.read1(length)
    assert len(data) == length

    return data


def read_value(stream: io.BufferedIOBase,
               wire_type: int) -> Optional[Union[int, bytes]]:
    wire_type = WireType(wire_type)

    if wire_type == WireType.Varint:
        return read_varint(stream)
    elif wire_type == WireType.Fixed32 or wire_type == WireType.Fixed64:
        return read_fixed(stream, wire_type)
    elif wire_type == WireType.LengthDelimited:
        return read_length_delimited(stream)
    elif wire_type == WireType.StartGroup or wire_type == WireType.EndGroup:
        assert True

    raise Exception("Unknown wire type %d" % wire_type)
