import io
from typing import Union, Any

import pytest

from revpbuf import core


def test_read_varint_normal_input() -> None:
    input1 = io.BytesIO(b"\x01")
    input2 = io.BytesIO(b"\x7f")
    input3 = io.BytesIO(b"\xff\x01")
    input4 = io.BytesIO(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01")
    input5 = io.BytesIO(b"\x96\x01")

    assert core.read_varint(input1) == 1
    assert core.read_varint(input2) == 127
    assert core.read_varint(input3) == 255
    assert core.read_varint(input4) == 2**64 - 1
    assert core.read_varint(input5) == 150


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
def test_read_identifier_normal_input(
    test_input: bytes, expected: core.ProtoId
) -> None:
    field_id = core.read_identifier(io.BytesIO(test_input))

    assert field_id.field_no == expected.field_no, "Invalid field number"
    assert field_id.wire_type == expected.wire_type, "Invalid wire type"


@pytest.mark.parametrize("test_input,expected", [
    (b"", None),
])
def test_read_identifier_invalid_input(
    test_input: bytes, expected: core.ProtoId
) -> None:
    field_id = core.read_identifier(io.BytesIO(test_input))

    assert field_id == expected


@pytest.mark.parametrize(
    "test_input,expected", [
        ((b"\x08\x01", core.WireType.Varint), 1),
        (
            (b"\x09\x00\x00\x00\x00\x00\x00\x00\x00", core.WireType.Fixed64),
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        ),
        ((b"\x0d\x00\x00\x00\x00", core.WireType.Fixed32), b"\x00\x00\x00\x00"),
        (
            (b"\x0a\x06" + b"\x68" * 6, core.WireType.LengthDelimited),
            b"\x68" * 6
        )
    ]
)
def test_read_value_normal_input(
    test_input: tuple, expected: Union[int, bytes]
) -> None:
    stream = io.BytesIO(test_input[0])
    field_id = core.read_identifier(stream)

    assert field_id.wire_type == test_input[1]

    payload = core.read_value(stream, test_input[1])

    assert payload == expected


@pytest.mark.parametrize(
    "test_input,expected", [
        ((b"\x08", core.WireType.Varint), None),
        ((b"\x09\x00\x00\x00\x00\x00", core.WireType.Fixed64), None),
        ((b"\x09", core.WireType.Fixed64), None),
        ((b"\x0d\x00\x00\x00", core.WireType.Fixed32), None),
        ((b"\x0d", core.WireType.Fixed32), None),
        ((b"\x0a\x06" + b"\x68" * 5, core.WireType.LengthDelimited), None),
        ((b"\x0a", core.WireType.LengthDelimited), None)
    ]
)
def test_read_value_valid_field_no_data(
    test_input: tuple, expected: Union[int, bytes]
) -> None:
    stream = io.BytesIO(test_input[0])
    field_id = core.read_identifier(stream)

    assert field_id.wire_type == test_input[1]

    payload = core.read_value(stream, test_input[1])

    assert payload == expected


@pytest.mark.parametrize(
    "test_input,expected", [
        ((b"\x0b", core.WireType.StartGroup), NotImplementedError),
        ((b"\x0c", core.WireType.EndGroup), NotImplementedError),
    ]
)
def test_read_value_groups(test_input: tuple, expected: Any) -> None:
    stream = io.BytesIO(test_input[0])
    field_id = core.read_identifier(stream)

    assert field_id.wire_type == test_input[1]

    with pytest.raises(expected):
        core.read_value(stream, test_input[1])


@pytest.mark.parametrize(
    "test_input,expected", [
        ((b"\x0f", 7), (ValueError, Exception)),
        ((b"\x0e", 6), (ValueError, Exception)),
    ]
)
def test_read_value_unknown_wire(test_input: tuple, expected: tuple) -> None:
    stream = io.BytesIO(test_input[0])

    with pytest.raises(expected[0]):
        core.read_identifier(stream)

    with pytest.raises(expected[1]):
        core.read_value(stream, test_input[1])


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x08", (1, core.WireType.Varint)),
        (b"\x09", (1, core.WireType.Fixed64)),
        (b"\x0a", (1, core.WireType.LengthDelimited)),
        (b"\x0b", (1, core.WireType.StartGroup)),
        (b"\x0c", (1, core.WireType.EndGroup)),
        (b"\x0d", (1, core.WireType.Fixed32)),
    ]
)
def test_field_descriptor_normal_input(
    test_input: bytes, expected: tuple
) -> None:
    stream = io.BytesIO(test_input)
    field_descriptor = core.FieldDescriptor(stream)

    assert field_descriptor.proto_id.field_no == expected[0]
    assert field_descriptor.proto_id.wire_type == expected[1]
    assert field_descriptor.field_no == expected[0]
    assert field_descriptor.wire_type == expected[1]


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x0e", ValueError),
        (b"\x0f", ValueError),
    ]
)
def test_field_descriptor_invalid_proto(test_input: bytes, expected) -> None:
    stream = io.BytesIO(test_input)

    with pytest.raises(expected):
        core.FieldDescriptor(stream)


def test_base_proto_printer() -> None:
    stream = io.BytesIO(b"\x08")

    with pytest.raises(NotImplementedError):
        core.BaseProtoPrinter().visit(core.FieldDescriptor(stream))
