import hashlib
from datetime import datetime

from .pdfobj import PdfObj


class Collector:
    def __init__(self) -> None:
        self.obj_counter = int()
        self.objects: list[PdfObj] = list()
        self.buffer = bytearray()
        self.root_obj: PdfObj | None = None
        self.info: None | bytes = None

    def file_id(self, buffer: bytes | bytearray):
        now = datetime.now().strftime("%Y%m%d%H%M%S").encode("ascii")
        bytes = buffer + now
        id_hash = hashlib.new("md5", usedforsecurity=False)  # nosec B324
        id_hash.update(bytes)
        hash_hex = id_hash.hexdigest().upper()
        return f"<{hash_hex}><{hash_hex}>".encode("ascii")

    def new_obj(self, type=None):
        self.obj_counter += 1
        obj = PdfObj(self.obj_counter)
        self.objects.append(obj)
        if type != None:
            obj.attr_set("/Type", type)
        return obj

    def get_reference(self, obj: PdfObj):
        if not isinstance(obj, PdfObj):
            raise TypeError("Cannot create a reference string without PdfObj")
        return f"{obj.obj_num} 0 R"

    def build_pdf(self) -> bytearray:
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
        if self.root_obj is None:
            b.extend(b"\t/Root 1 0 R\n")
        else:
            b.extend(b"\t/Root %d 0 R\n" % self.root_obj.obj_num)
        b.extend(b"\t/Size %d\n" % (len(self.objects) + 1))
        b.extend(b"\t/ID [%b]\n" % self.file_id(b))
        if self.info is not None:
            b.extend(b"\t/Info %b\n" % self.info)
        b.extend(b">>\n")
        b.extend(b"startxref\n")
        b.extend(b"%d\n" % xref_start)
        b.extend(b"%%EOF")
        return b
