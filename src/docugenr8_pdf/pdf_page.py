import zlib

from docugenr8_shared.colors import MaterialColors
from docugenr8_shared.dto import DtoFragment
from docugenr8_shared.dto import DtoTextArea

from .core import Collector
from .core import PdfObj
from .pdf_content import PdfContent
from .pdf_font import PdfFont


class PdfPage:
    def __init__(self, page_width: float, page_height: float) -> None:
        self.page_obj: None | PdfObj = None
        self._pagefont_num: int = 1
        self._fontname_to_pagefontname: dict[str, str] = {}
        self._pagefontname_fontresource: dict[str, PdfFont] = {}
        self._page_width: float = page_width
        self._page_height: float = page_height
        self._page_contents = PdfContent()
        self.resources_obj: None | PdfObj = None
        self.contents_obj: None | PdfObj = None

    def get_pagefontname(self, font_name: str, pdf_fonts: dict[str, PdfFont]):
        if font_name in self._fontname_to_pagefontname:
            return self._fontname_to_pagefontname[font_name]
        pagefontname = f"F{self._pagefont_num}"
        self._fontname_to_pagefontname[font_name] = pagefontname
        self._pagefontname_fontresource[pagefontname] = pdf_fonts[font_name]
        self._pagefont_num += 1
        return pagefontname

    def calc_y(self, y: float, height: float | None = None):
        """Change y coordinate from top-to-bottom to bottom-to-top
        and moves content origin to bottom-left."""
        if height is None:
            return self._page_height - y
        return self._page_height - y - height

    def generate_pdf_obj(self, collector: Collector):
        self.page_obj = collector.new_obj()
        self.resources_obj = collector.new_obj()
        self.contents_obj = collector.new_obj()

    def add_dto_page_contents(
        self, contents: list[object], pdf_fonts: dict[str, PdfFont]
    ) -> None:
        for content in contents:
            match content:
                case DtoTextArea():
                    self.generate_text_area(content, pdf_fonts)
                case _:
                    raise ValueError("Type not defined.")

    def draw_text_area(self, dto_text_area: DtoTextArea) -> None:
        self._page_contents.add_rectangle(
            x=dto_text_area.x,
            y=self.calc_y(dto_text_area.y, dto_text_area.height),
            width=dto_text_area.width,
            height=dto_text_area.height,
            fill_color=MaterialColors.Gray100,
            line_color=MaterialColors.Gray600,
        )
        for paragraph in dto_text_area.paragraphs:
            self._page_contents.add_rectangle(
                x=paragraph.x,
                y=self.calc_y(paragraph.y, paragraph.height),
                width=paragraph.width,
                height=paragraph.height,
                fill_color=MaterialColors.Teal100,
                line_color=MaterialColors.Teal600,
            )
            for text_line in paragraph.textlines:
                self._page_contents.add_rectangle(
                    x=text_line.x,
                    y=self.calc_y(text_line.y, text_line.height),
                    width=text_line.width,
                    height=text_line.height,
                    fill_color=MaterialColors.Yellow100,
                    line_color=MaterialColors.Yellow600,
                )
                for word in text_line.words:
                    self._page_contents.add_rectangle(
                        x=word.x,
                        y=self.calc_y(word.y, word.height),
                        width=word.width,
                        height=word.height,
                        fill_color=MaterialColors.DeepOrange100,
                        line_color=MaterialColors.DeepOrange600,
                    )
                    # for fragment in word.fragments:
                    #     self._page_contents.add_rectangle(
                    #         x=fragment.x,
                    #         y=self.calc_y(
                    #             fragment.y,
                    #             fragment.height),
                    #         width=fragment.width,
                    #         height=fragment.height,
                    #         fill_color=MaterialColors.Purple100,
                    #         line_color=MaterialColors.Purple600,
                    #         )

    def check_and_update_text_state(
        self,
        current_state: tuple[float, tuple[float, float, float], str]
        | tuple[None, None, None],
        fragment: DtoFragment,
        pdf_fonts: dict[str, PdfFont],
    ) -> tuple[float, tuple[float, float, float], str]:
        new_state = (
            fragment.font_size,
            fragment.font_color,
            fragment.font_name,
        )
        if (
            current_state[0] is None
            or current_state[1] is None
            or current_state[2] is None
        ) or new_state != current_state:
            page_font_name = self.get_pagefontname(fragment.font_name, pdf_fonts)
            self._page_contents.add_page_font_with_size(
                page_font_name, fragment.font_size
            )
            self._page_contents.add_fill_color(fragment.font_color)
            return new_state
        return current_state

    def draw_text_fragment(self, fragment: DtoFragment, pdf_font: PdfFont) -> None:
        cid_in_bytes = bytearray()
        for char in fragment.chars:
            cid = pdf_font.get_cid_in_bytes(char)
            if cid is not None:
                cid_in_bytes.extend(cid)
        if len(cid_in_bytes) > 0:
            self._page_contents.add_text(
                fragment.x, self.calc_y(fragment.baseline), cid_in_bytes
            )

    def generate_text_area(
        self, dto_text_area: DtoTextArea, pdf_fonts: dict[str, PdfFont]
    ):
        self._page_contents.add_savestate()
        self.draw_text_area(dto_text_area)
        current_state = (None, None, None)
        for fragment in dto_text_area.fragments:
            current_state = self.check_and_update_text_state(
                current_state, fragment, pdf_fonts
            )
            self.draw_text_fragment(fragment, pdf_fonts[fragment.font_name])
        self._page_contents.add_restore_state()

    def build(
        self,
        should_compress: bool,
    ):
        if self.page_obj is None:
            raise ValueError("Page object not initialized.")
        if self.resources_obj is None:
            raise ValueError("Resources object not initialized.")
        if self.contents_obj is None:
            raise ValueError("Contents object not initialized.")
        self.page_obj.set_attribute_value(
            "/MediaBox", f"[0 0 {self._page_width} {self._page_height}]"
        )
        self.page_obj.set_attribute_value("/Resources", self.resources_obj)
        self.resources_obj.set_attribute_value(
            "/ProcSet", "[/PDF /Text /ImageB /ImageC /ImageI]"
        )
        self.resources_obj.set_attribute_value("/XObject", "<<\t>>")
        self.page_obj.add_attribute_value("/Contents", self.contents_obj)
        if should_compress:
            self.contents_obj.extend_stream(zlib.compress(self._page_contents.stream))
            self.contents_obj.set_attribute_value("/Filter", "/FlateDecode")
        else:
            self.contents_obj.extend_stream(self._page_contents.stream)
        fonts_dict = {}
        for page_fontname, font in self._pagefontname_fontresource.items():
            page_fontname_formatted = f"/{page_fontname}"
            fonts_dict[page_fontname_formatted] = font.obj_num
        self.resources_obj.set_attribute_value("/Font", fonts_dict)
