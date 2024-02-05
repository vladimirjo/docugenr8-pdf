from __future__ import annotations


def render_pdf_object(obj: dict[str, str] | list[str] | str, tab: int = 1):
    # base case
    if not isinstance(obj, (list, dict, PdfObj)):
        return f"{obj}"
    # base case
    if isinstance(obj, PdfObj):
        return f"{obj.obj_num} 0 R"
    # recursion with type of list
    if isinstance(obj, list):
        obj_list: list[str] = []
        for item in obj:
            obj_list.append(render_pdf_object(item, tab))
        result = "["
        for obj in obj_list:
            result += obj + " "

        result = result[:-1]
        result += "]"
        return result
    # recursion with type of dict
    if isinstance(obj, dict):
        tabs = tab * "\t"
        result = "\n" + tabs[:-1] + "<<\n"
        for key in obj:
            value = render_pdf_object(obj[key], tab + 1)
            result += tabs + key + " " + value + "\n"
        result += tabs[:-1] + ">>"
        return result


class PdfObj:
    def __init__(self, obj_num: int) -> None:
        self.obj_num = obj_num
        self.attr = {}
        self.stream = bytearray()

    def attr_set(
        self, key: str, value: str | int | float | list | dict | PdfObj
    ):
        self.attr[key] = value

    def attr_add(
        self, key: str, value: str | int | float | list | dict | PdfObj
    ):
        if key not in self.attr:
            arr = []
            arr.append(value)
            self.attr[key] = arr
            return
        if not isinstance(self.attr[key], list):
            arr = []
            arr.append(self.attr[key])
            arr.append(value)
            self.attr[key] = arr
        else:
            self.attr[key].append(value)

    def attr_get(self, key: str):
        if key in self.attr:
            return self.attr[key]
        return None

    def stream_add(self, value: str | bytes | bytearray):
        if not isinstance(value, (str, bytes, bytearray)):
            raise TypeError(
                "Only strings, bytes and bytearray can be added to stream"
            )

        if isinstance(value, str):
            b = bytearray(value.encode("ascii"))
            b.extend(b"\n")
            self.stream.extend(b)
        else:
            self.stream.extend(value)

        self.attr["/Length"] = len(self.stream)

    def build(self):
        buffer = bytearray()

        buffer.extend(b"%d 0 obj" % self.obj_num)
        obj_attr = render_pdf_object(self.attr) + "\n"
        buffer.extend(obj_attr.encode("ascii"))

        if len(self.stream) > 0:
            buffer.extend(b"stream\n")
            buffer.extend(self.stream)
            if buffer[-1:] != b"\n":
                buffer.extend(b"\n")
            buffer.extend(b"endstream\n")

        buffer.extend(b"endobj\n")

        return buffer
