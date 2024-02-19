from docugenr8_shared.dto import Dto

from .core import Collector
from .pdf_font import PdfFont

# from .pdf_info import PdfInfo
from .pdf_page import PdfPage
from .pdf_settings import PDFSettings


class Pdf:
    def __init__(self, dto: None | Dto = None) -> None:
        self._collector = Collector()
        self.fonts: dict[str, PdfFont] = {}
        # self.info = PdfInfo(self._collector)
        self.pages: list[PdfPage] = []
        self.settings = PDFSettings()
        if dto is not None:
            self._parse_dto(dto)

    def _parse_dto(self, dto: Dto) -> None:
        for dto_font in dto.fonts:
            pdf_font = PdfFont(dto_font.name, dto_font.raw_data)
            self.fonts[dto_font.name] = pdf_font
        for dto_page in dto.pages:
            pdf_page = PdfPage(dto_page.width, dto_page.height)
            self.pages.append(pdf_page)
            pdf_page.add_dto_page_contents(dto_page.contents, self.fonts)


    def _build_pdf_object_tree(self) -> None:
        self._collector.pages_obj.set_attribute_value(
            "/Count", len(self.pages))
        # if self.info.has_value():
        #     self.info.build()
        for page in self.pages:
            page.generate_pdf_obj(self._collector)
        for font in self.fonts.values():
            font.generate_pdf_obj(self._collector)

    def output_to_bytes(self) -> bytes:
        self._build_pdf_object_tree()
        for page in self.pages:
            page.build(
                self.settings.compression,
            )
            if page.page_obj is None:
                raise ValueError("Page object not defined.")
            page.page_obj.set_attribute_value(
                "/Parent", self._collector.pages_obj)
            self._collector.pages_obj.add_attribute_value(
                "/Kids", page.page_obj)
        for font in self.fonts.values():
            font.build(self.settings.compression)
        return self._collector.build_pdf()

    def output_to_file(self, file: str):
        b = self.output_to_bytes()
        with open(file, "wb") as f:
            f.write(b)
