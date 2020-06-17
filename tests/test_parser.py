import io
from typing import Sequence, Any

import pytest

from revpbuf import parser


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x00\x00\x20\x3e", (1042284544, 1042284544, 0.15625)),
        (b"\x00\x00\x20\xbe", (-1105199104, 3189768192, -0.15625))
    ]
)
def test_parser_fixed32_normal_input(
    test_input: bytes, expected: tuple
) -> None:
    fixed32 = parser.parse_fixed32(test_input)
    fixed32_stream = parser.parse_fixed32_stream(io.BytesIO(test_input))

    fixed_checker(fixed32, expected)
    fixed_checker(fixed32_stream, expected)


@pytest.mark.parametrize(
    "test_input,expected", [
        (
            b"\x00\x00\x00\x00\x00\x00\x00\x40",
            (4611686018427387904, 4611686018427387904, 2.0)
        ),
        (
            b"\x00\x00\x00\x00\x00\x00\x00\xc0",
            (-4611686018427387904, 13835058055282163712, -2.0)
        )
    ]
)
def test_parser_fixed64_normal_input(
    test_input: bytes, expected: tuple
) -> None:
    fixed64 = parser.parse_fixed64(test_input)
    fixed64_stream = parser.parse_fixed64_stream(io.BytesIO(test_input))

    fixed_checker(fixed64, expected)
    fixed_checker(fixed64_stream, expected)


def fixed_checker(value: parser.FixedRepr, expected: tuple) -> None:
    assert value.int == expected[0]
    assert value.uint == expected[1]
    assert value.float == expected[2]


@pytest.mark.parametrize(
    "test_input,expected", [
        (1, -1), (4294967294, 2147483647),
        (9223372036854775808, 4611686018427387904)
    ]
)
def test_zigzag_decode_normal_input(test_input: int, expected: int) -> None:
    assert parser.zigzag_decode(test_input) == expected


def test_parser_message_normal_input() -> None:
    payload = b"\x68\x67"
    chunk = parser.parse_chunk(payload)

    assert chunk.chunk == payload
    assert chunk.str == "hg"


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x96\x01", (150, 75)), (b"\x7f", (127, -64)),
        (b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01", (2**64 - 1, -2**63))
    ]
)
def test_parser_varint_stream_normal_input(
    test_input: bytes, expected: tuple
) -> None:
    varint = parser.parse_varint_stream(io.BytesIO(test_input))

    assert varint.int == expected[0]
    assert varint.sint == expected[1]


@pytest.mark.parametrize(
    "test_input,expected", [
        (b"\x02\x68\x67", (b"hg", "hg", 2)),
        (b"\x10" + b"\x68" * 16, (b"h" * 16, "h" * 16, 16)),
        (b"\x02\x96\x01", (b"\x96\x01", None, 2))
    ]
)
def test_parser_chunk_stream_normal_input(
    test_input: bytes, expected: tuple
) -> None:
    chunk = parser.parse_chunk_stream(io.BytesIO(test_input))

    assert chunk.chunk == expected[0]
    assert chunk.str == expected[1]
    assert len(chunk.chunk) == expected[2]


def check_fields(fields: Sequence[Any], expected_fields: Sequence[Any]) -> None:
    assert len(fields) == len(expected_fields)
    assert all(
        [
            f1 if f1[0] == f2[0] and f1[1] == f2[1] else False
            for f1, f2 in zip(fields, expected_fields)
        ]
    )


def test_varint_get_fields() -> None:
    varint = parser.VarintRepr(1)
    expected_fields = (("sint", -1), ("uint", 1))
    varint_fields = varint.get_fields()

    check_fields(varint_fields, expected_fields)


def test_fixed_get_fields() -> None:
    fixed32 = parser.Fixed32Repr(b"\x00\x00\x00\x00")
    fixed64 = parser.Fixed64Repr(b"\x00\x00\x00\x00\x00\x00\x00\x00")
    expected_fields = (("sint", 0), ("uint", 0), ("float", 0.0))
    fixed32_fields = fixed32.get_fields()
    fixed64_fields = fixed64.get_fields()

    for fixed_fields in (fixed32_fields, fixed64_fields):
        assert len(fixed_fields) == len(expected_fields)
    assert all(
        [
            f1 if f1[0] == f2[0] and f1[1] == f2[1] else False
            for f1, f2 in zip(fixed_fields, expected_fields)
        ]
    )
