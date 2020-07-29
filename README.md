![PyPI - Python Version](https://img.shields.io/pypi/pyversions/revpbuf)
![PyPI](https://img.shields.io/pypi/v/revpbuf)
![Package Tests](https://github.com/vpetrigo/rev-protobuf/workflows/Package%20Tests/badge.svg)
[![codecov](https://codecov.io/gh/vpetrigo/rev-protobuf/branch/master/graph/badge.svg)](https://codecov.io/gh/vpetrigo/rev-protobuf) 

# Reverse packed Google Protobuf payload

Restore packed Google Protobuf message and reveal its value according to packed types.
For example, you have a packed Protobuf message represented as a byte string:

```
# Encoded varint value -1 (signed int) or 1 (unsigned int)
08 01
```

By using a `revpbuf` package you may decode that to the following:

```
Field 1 - type <WireType.Varint>
	sint: -1
	uint: 1
```

Python code that does such a conversion:

```python
from revpbuf import parser

proto_payload = bytes.fromhex("0801")
message_repr = parser.parse_proto(proto_payload)
```

Right now you have a message representation that you may print:

```python
class Printer(BaseProtoPrinter):
    def __init__(self):
        self.level = 0

    def visit(self, ty: Union[FieldDescriptor, BaseTypeRepr]) -> str:
        if isinstance(ty, FieldDescriptor):
            return self._visit_field_descriptor(ty)
        else:
            fields = ty.get_fields()

            if not any([f for f in fields if f[0] == "sub-msg"]):
                return self._visit_non_chunk(ty, fields)
            else:
                return self._visit_chunk(ty, fields)

    def _visit_field_descriptor(self, ty: FieldDescriptor) -> str:
        tabs = "\t" * self.level
        result = f"{tabs}Field {ty.field_no} - type <{ty.wire_type}>{os.linesep}"

        return result

    def _visit_non_chunk(
        self, _ty: BaseTypeRepr, fields: Sequence[Union[str, Any]]
    ) -> str:
        tabs_field = "\t" * (self.level + 1)
        result = f"{os.linesep}".join(
            [f"{tabs_field}{field[0]}: {field[1]}" for field in fields]
        )

        return f"{result}{os.linesep}"

    def _visit_chunk(
        self, _ty: BaseTypeRepr, fields: Sequence[Union[str, Any]]
    ) -> str:
        tabs_field = "\t" * (self.level + 1)
        str_stream = io.StringIO()

        for field in fields:
            if field[0] != "sub-msg":
                result = f"{tabs_field}{field[0]}: {field[1]}{os.linesep}"
                str_stream.write(result)
            else:
                if field[1] is not None:
                    result = f"{tabs_field}{field[0]}:{os.linesep}"
                    str_stream.write(result)
                    self.level += 2

                    for sub_msg_field in field[1].fields:
                        result = sub_msg_field.field_desc.accept(self)

                        if result is not None:
                            str_stream.write(result)

                        result = sub_msg_field.field_repr.accept(self)

                        if result is not None:
                            str_stream.write(result)

                    self.level -= 2

        return str_stream.getvalue()

# ...
def proto_print(message: MessageRepr) -> str:
    printer = Printer()
    str_stream = io.StringIO()

    for field in message.fields:
        str_stream.write(field.field_desc.accept(printer))
        str_stream.write(field.field_repr.accept(printer))

    return str_stream.getvalue()

proto_print(message_repr)
```

That would output the example field representation above:

```
Field 1 - type <WireType.Varint>
	sint: -1
	uint: 1
```

Example application may be found [here](examples/)
