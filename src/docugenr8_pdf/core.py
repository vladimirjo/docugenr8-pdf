from __future__ import annotations

import hashlib
from datetime import datetime


class PdfObj:
    def __init__(
        self,
        obj_num: int
        ) -> None:
        self.obj_num = obj_num
        self.attributes: dict[
            str,
            str | float | list | dict | PdfObj
            ] = {}
        self.stream = bytearray()

    def set_attribute_value(
        self,
        attribute: str,
        value: str | float | list | dict | PdfObj
    ) -> None:
        self.attributes[attribute] = value

    def add_attribute_value(
        self,
        attribute: str,
        value: str | float | list | dict | PdfObj
    ) -> None:
        if attribute not in self.attributes:
            arr = []
            arr.append(value)
            self.attributes[attribute] = arr
            return
        attribute_value = self.attributes[attribute]
        if isinstance(attribute_value, list):
            attribute_value.append(value)
            return
        arr = []
        arr.append(self.attributes[attribute])
        arr.append(value)
        self.attributes[attribute] = arr

    def get_attribute_value(self, attribute: str):
        if attribute in self.attributes:
            return self.attributes[attribute]
        return None

    def extend_stream(self, value: str | bytes | bytearray) -> None:
        if not isinstance(value, str | bytes | bytearray):
            raise TypeError(
                "Only strings, bytes and bytearrays can be added to stream"
            )
        if isinstance(value, str):
            b = bytearray(value.encode("ascii"))
            b.extend(b"\n")
            self.stream.extend(b)
        else:
            self.stream.extend(value)
        self.set_attribute_value("/Length", len(self.stream))

    def build(self):
        buffer = bytearray()
        buffer.extend(b"%d 0 obj" % self.obj_num)
        obj_attr = build_attributes(self.attributes) + "\n"
        buffer.extend(obj_attr.encode("ascii"))
        if len(self.stream) > 0:
            buffer.extend(b"stream\n")
            buffer.extend(self.stream)
            if buffer[-1:] != b"\n":
                buffer.extend(b"\n")
            buffer.extend(b"endstream\n")
        buffer.extend(b"endobj\n")
        return buffer

class Collector:
    def __init__(self) -> None:
        self.obj_counter = 0
        self.objects: list[PdfObj] = []
        self.buffer = bytearray()
        self.generate_catalog_and_pages_objects()
        self.info: None | bytes = None

    def generate_catalog_and_pages_objects(self) -> None:
        self.catalog_obj: PdfObj = self.new_obj()
        self.pages_obj: PdfObj = self.new_obj()
        self.catalog_obj.set_attribute_value("/Pages", self.pages_obj)

    def new_obj(self, type_obj=None) -> PdfObj:
        self.obj_counter += 1
        obj = PdfObj(self.obj_counter)
        self.objects.append(obj)
        if type_obj is not None:
            obj.set_attribute_value("/Type", type_obj)
        return obj

    def build_pdf(self) -> bytes:
        obj_offsets = []
        # header
        b = self.buffer
        b.extend(b"%PDF-1.3\n%\xE2\xE3\xCF\xD3\n")
        # body
        for obj in self.objects:
            obj_offsets.append(len(b))
            b.extend(obj.build())
        # cross-reference table
        xref_start = len(b)
        b.extend(b"xref\n0 %d\n" % (len(self.objects) + 1))
        b.extend(b"0000000000 65535 f\n")
        for offset in obj_offsets:
            b.extend(b"%010d 00000 n\n" % offset)
        # trailer
        b.extend(b"trailer\n<<\n")
        b.extend(b"\t/Root %d 0 R\n" % self.catalog_obj.obj_num)
        b.extend(b"\t/Size %d\n" % (len(self.objects) + 1))
        b.extend(b"\t/ID [%b]\n" % generate_id(b))
        if self.info is not None:
            b.extend(b"\t/Info %b\n" % self.info)
        b.extend(b">>\n")
        b.extend(b"startxref\n")
        b.extend(b"%d\n" % xref_start)
        b.extend(b"%%EOF")
        return bytes(b)

def build_attributes(
    value: str | float | list | dict | PdfObj,
    tab: int = 1
    ) -> str:
    # base case
    if isinstance(value, str | float | int):
        return f"{value}"
    # base case
    if isinstance(value, PdfObj):
        return f"{value.obj_num} 0 R"
    # recursion with type of list
    if isinstance(value, list):
        obj_list = [build_attributes(item, tab) for item in value]
        result = "["
        for obj_item in obj_list:
            result += obj_item + " "
        result = result[:-1]
        result += "]"
        return result
    # recursion with type of dict
    if isinstance(value, dict):
        tabs = tab * "\t"
        result = "\n" + tabs[:-1] + "<<\n"
        for key in value:
            result += (tabs + key + " "
                       + build_attributes(value[key], tab + 1) + "\n")
        result += tabs[:-1] + ">>"
        return result
    raise TypeError(f"The value of a type {type(value).__name__} "
                    "cannot be added to attributes.")

def get_reference(obj: PdfObj) -> str:
    if not isinstance(obj, PdfObj):
        raise TypeError("Cannot create a reference string without PdfObj")
    return f"{obj.obj_num} 0 R"

def generate_id(buffer: bytes | bytearray) -> bytes:
    now = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
    salted_buffer = buffer + now
    id_hash = hashlib.new("md5", usedforsecurity=False)
    id_hash.update(salted_buffer)
    hash_hex = id_hash.hexdigest().upper()
    return f"<{hash_hex}><{hash_hex}>".encode("ascii")
