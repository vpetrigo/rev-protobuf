from revpbuf import core

import io


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


def test_read_identifier() -> None:
    inp = io.BytesIO(b"\x08")
    field_id = core.read_identifier(inp)

    assert field_id.field_no == 1, "Invalid field number"
    assert field_id.wire_type == 0, "Invalid wire type"

    inp = io.BytesIO(b"\xf8\x3f")
    field_id = core.read_identifier(inp)

    assert field_id.field_no == 1023, "Invalid field number"
    assert field_id.wire_type == 0, "Invalid wire type"

    inp = io.BytesIO(b"\xf9\x3f")
    field_id = core.read_identifier(inp)

    assert field_id.field_no == 1023, "Invalid field number"
    assert field_id.wire_type == 1, "Invalid wire type"

    inp = io.BytesIO(b"\xfa\x3f")
    field_id = core.read_identifier(inp)

    assert field_id.field_no == 1023, "Invalid field number"
    assert field_id.wire_type == 2, "Invalid wire type"

    inp = io.BytesIO(b"\xfd\x3f")
    field_id = core.read_identifier(inp)

    assert field_id.field_no == 1023, "Invalid field number"
    assert field_id.wire_type == 5, "Invalid wire type"
