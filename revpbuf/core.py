import io

from collections import namedtuple
from typing import Iterable, Optional

# Core parsing. This handles the most low-level deserialization.
# No guessing going on here. These functions return None on EOF.

ProtoId = namedtuple("ProtoId", ["field_no", "wire_type"])


def _iter_bytes(stream: io.BufferedIOBase) -> Iterable[bytes]:
    byte = stream.read1(1)

    while len(byte) != 0:
        yield byte
        byte = stream.read1(1)


def read_varint(file) -> int:
    varint = 0
    pos = 0

    for byte in _iter_bytes(file):
        num = ord(byte)
        has_next = (num & 0b1000_0000) != 0
        value = num & 0b0111_1111
        varint |= value << pos
        pos += 7

        if not has_next:
            break

    return varint if pos != 0 else None


def read_identifier(file) -> Optional[ProtoId]:
    identifier = read_varint(file)

    if identifier is None:
        return None

    return ProtoId(identifier >> 3, identifier & 0b111)


def read_value(file, wire_type):
    if wire_type == 0:
        return read_varint(file)
    elif wire_type == 1:
        c = file.read(8)
        if not len(c):
            return None
        assert (len(c) == 8)
        return c
    elif wire_type == 2:
        length = read_varint(file)
        if length is None:
            return None
        c = file.read(length)
        assert (len(c) == length)
        return io.BytesIO(c)
    elif wire_type == 3 or wire_type == 4:
        assert True
    elif wire_type == 5:
        c = file.read(4)
        if len(c) == 0:
            return None
        assert (len(c) == 4)
        return c

    raise Exception("Unknown wire type %d" % wire_type)
