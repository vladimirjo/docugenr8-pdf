from .collector import Collector
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pdfobj import PdfObj
    from ..core import Document

from .document_info import DocumentInfo
from .pdf_settings import PDFSettings


class Pdf:
    def __init__(self, document: Document) -> None:
        self.document = document
        self._collector = Collector()
        self._objs: dict[str, PdfObj] = self._set_objs()
        self.info = DocumentInfo(self._collector)
        self.pages: list[Page] = []
        self.fonts: dict[str, Font] = {}
        self.pdf_settings = PDFSettings()

    def _set_objs(self):
        objs = dict()
        objs["catalog"] = self._collector.new_obj("/Catalog")
        objs["pages"] = self._collector.new_obj("/Pages")
        return objs

    def build(self):
        self._collector.root_obj = self._objs["catalog"]
        self._objs["catalog"].attr_set("/Pages", self._objs["pages"])
        if self.info.has_value():
            self.info.build()
        self._objs["pages"].attr_set("/Count", len(self.pages))
        for font in self.fonts.values():
            font._add_collector(self._collector)
        for page_num, page in enumerate(self.pages):
            page._add_collector(self._collector)
            page.build(
                page_num + 1,
                len(self.pages),
                self.pdf_settings.compression,
                self.pdf_settings.decimal_precision,
            )
            page._page_obj.attr_set("/Parent", self._objs["pages"])
            self._objs["pages"].attr_add("/Kids", page._page_obj)
        for font in self.fonts.values():
            font.build(self.pdf_settings.compression)

    def output(self, file: str):
        self.build()
        with open(file, "wb") as f:
            f.write(self._collector.build_pdf())
