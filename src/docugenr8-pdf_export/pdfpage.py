import zlib

from ..core import Collector
from ..core import PdfObj
from ..resources.font.font import Font
from ..content.abstracts.simple import SimpleContent
from ..content.abstracts.composite import CompositeContent
from ..content.byte_objs.fontwsize import FontWithSize
from ..content.textarea import TextArea
from ..content.textbox import TextBox
from ..content.table import Table


class Page:
    def __init__(self, page_width: float, page_height: float) -> None:
        self._collector: Collector = None
        self._page_obj: PdfObj = None
        self._pagefont_num: int = 1
        self._fontname_to_pagefontname: dict[str, str] = {}
        self._pagefontname_fontresource: dict[str, Font] = {}
        self._page_width: float = page_width
        self._page_height: float = page_height
        self._page_contents: list[SimpleContent | CompositeContent] = []

    def _add_collector(self, collector: Collector):
        self._collector = collector
        self._page_obj = collector.new_obj()

    def get_pagefontname(self, fontname: str, fontresource: Font):
        if fontname in self._fontname_to_pagefontname.keys():
            return self._fontname_to_pagefontname[fontname]
        pagefontname = f"F{self._pagefont_num}"
        self._fontname_to_pagefontname[fontname] = pagefontname
        self._pagefontname_fontresource[pagefontname] = fontresource
        self._pagefont_num += 1
        return pagefontname

    def add_content(self, content: SimpleContent | CompositeContent) -> None:
        self._page_contents.append(content)

    def calc_pdf_y_coord(self, y: float, h: float | None = None):
        """Change y coordinate from top-to-bottom to bottom-to-top and moves content origin to bottom-left."""
        if h is None:
            return self._page_height - y
        else:
            return self._page_height - y - h

    def _inject_page_numbers(self, page_number, pages_total, content: TextArea):
        if (
            len(content.words_with_current_page_fragments) == 0
            and len(content.words_with_total_pages_fragments) == 0
        ):
            return
        content.inject_current_page(page_number)
        content.inject_total_pages(pages_total)
        # content.recalculate_fragments()
        # content._recalculate_lines()

    def build(
        self,
        page_number: int,
        pages_total: int,
        compression: bool,
        decimal_precision: int,
    ):
        contents = []
        for content in self._page_contents:
            # if isinstance(content, Table):
            #     for cell in content.cells:
            #         self._inject_page_numbers(page_number, pages_total, cell._text_box._textarea)
            # if isinstance(content, TextBox):
            #     self._inject_page_numbers(page_number, pages_total, content._textarea)
            if isinstance(content, TextArea):
                self._inject_page_numbers(page_number, pages_total, content)
            if isinstance(content, CompositeContent):
                contents.extend(content.to_contents())
        resources_obj = self._collector.new_obj()
        contents_obj = self._collector.new_obj()
        self._page_obj.attr_set(
            "/MediaBox", f"[0 0 {self._page_width} {self._page_height}]"
        )
        self._page_obj.attr_set("/Resources", resources_obj)
        resources_obj.attr_set(
            "/ProcSet", "[/PDF /Text /ImageB /ImageC /ImageI]"
        )
        resources_obj.attr_set("/XObject", "<<\t>>")
        self._page_obj.attr_add("/Contents", contents_obj)
        content_in_bytes = bytearray()
        for content in contents:
            # get fontname for page
            if isinstance(content, FontWithSize):
                page_fontname = self.get_pagefontname(
                    content.font.name, content.font
                )
                content.page_fontname = page_fontname
            if hasattr(content, "_y") and hasattr(content, "_height"):
                content._y = self.calc_pdf_y_coord(content._y, content._height)
            elif hasattr(content, "_y"):
                content._y = self.calc_pdf_y_coord(content._y)
            # round the float numbers to user specified precision
            for key, value in content.__dict__.items():
                if isinstance(value, float):
                    rounded_float = round(value, decimal_precision)
                    content.__setattr__(key, rounded_float)
                    continue
            content_in_bytes.extend(content.to_bytes())
        if compression == True:
            contents_obj.stream_add(zlib.compress(content_in_bytes))
            contents_obj.attr_set("/Filter", "/FlateDecode")
        else:
            contents_obj.stream_add(content_in_bytes)
        fonts_dict = {}
        for page_fontname, font in self._pagefontname_fontresource.items():
            page_fontname_formatted = f"/{page_fontname}"
            fonts_dict[page_fontname_formatted] = font._font_obj
        resources_obj.attr_set("/Font", fonts_dict)
