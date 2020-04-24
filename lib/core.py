import io

# Core parsing. This handles the most low-level deserialization.
# No guessing going on here. These functions return None on EOF.


def read_varint(file):
    result = 0
    pos = 0
    while True:
        b = file.read(1)

        if len(b) == 0:
            assert pos == 0
            return None

        b = b[0]

        result |= ((b & 0x7F) << pos)
        pos += 7

        if b & 0x80 == 0:
            assert (b != 0 or pos == 7)
            return result


def read_identifier(file):
    identifier = read_varint(file)

    if identifier is None:
        return None, None

    return identifier >> 3, identifier & 0x07


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
        return wire_type == 3
    elif wire_type == 5:
        c = file.read(4)
        if len(c) == 0:
            return None
        assert (len(c) == 4)
        return c

    raise Exception("Unknown wire type %d" % wire_type)
