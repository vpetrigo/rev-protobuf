import io

import pytest

from revpbuf import core


def test_read_varint_normal_input() -> None:
    input1 = io.BytesIO(b"\x01")
    input2 = io.BytesIO(b"\x7f")
    input3 = io.BytesIO(b"\xff\x01")
    input4 = io.BytesIO(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01")

    assert core.read_varint(input1) == 1
    assert core.read_varint(input2) == 127
    assert core.read_varint(input3) == 255
    assert core.read_varint(input4) == 2**64 - 1


def test_read_varint_malformed_input() -> None:
    input1 = io.BytesIO(b"\xff")
    input2 = io.BytesIO(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff")

    assert core.read_varint(input1) is None
    assert core.read_varint(input2) is None


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x08", core.ProtoId(1, 0)), (b"\xf8\x3f", core.ProtoId(1023, 0)),
        (b"\xf9\x3f", core.ProtoId(1023, 1)),
        (b"\xfa\x3f", core.ProtoId(1023, 2)),
        (b"\xfd\x3f", core.ProtoId(1023, 5))
    ]
)
def test_read_identifier(test_input: bytes, expected: core.ProtoId) -> None:
    field_id = core.read_identifier(io.BytesIO(test_input))

    assert field_id.field_no == expected.field_no, "Invalid field number"
    assert field_id.wire_type == expected.wire_type, "Invalid wire type"
