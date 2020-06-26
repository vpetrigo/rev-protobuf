# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import os
from typing import Any, Sequence, Union

from revpbuf.core import FieldDescriptor, BaseTypeRepr, BaseProtoPrinter


class Printer(BaseProtoPrinter):
    def __init__(self):
        self.level = 0

    def visit(self, ty: Union[FieldDescriptor, BaseTypeRepr]) -> None:
        if isinstance(ty, FieldDescriptor):
            self._visit_field_descriptor(ty)
        else:
            fields = ty.get_fields()

            if not any([f for f in fields if f[0] == "sub-msg"]):
                self._visit_non_chunk(ty, fields)
            else:
                self._visit_chunk(ty, fields)

    def _visit_field_descriptor(self, ty: FieldDescriptor) -> None:
        tabs = "\t" * self.level
        print(f"{tabs}Field {ty.field_no} - type <{ty.wire_type}>")

    def _visit_non_chunk(
        self, _ty: BaseTypeRepr, fields: Sequence[Union[str, Any]]
    ) -> None:
        tabs_field = "\t" * (self.level + 1)

        for field in fields:
            print(f"{tabs_field}{field[0]}: {field[1]}")

    def _visit_chunk(
        self, _ty: BaseTypeRepr, fields: Sequence[Union[str, Any]]
    ) -> None:
        tabs_field = "\t" * (self.level + 1)

        for field in fields:
            if field[0] != "sub-msg":
                print(f"{tabs_field}{field[0]}: {field[1]}")
            else:
                if field[1] is not None:
                    print(f"{tabs_field}{field[0]}:")
                    self.level += 2

                    for sub_msg_field in field[1].fields:
                        sub_msg_field.field_desc.accept(self)
                        sub_msg_field.field_repr.accept(self)

                    self.level -= 2
