import zlib

from docugenr8_shared.colors import MaterialColors
from docugenr8_shared.dto import DtoArc
from docugenr8_shared.dto import DtoBezier
from docugenr8_shared.dto import DtoCurve
from docugenr8_shared.dto import DtoEllipse
from docugenr8_shared.dto import DtoFragment
from docugenr8_shared.dto import DtoPoint
from docugenr8_shared.dto import DtoRectangle
from docugenr8_shared.dto import DtoTextArea
from docugenr8_shared.dto import DtoTextBox

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
        self._page_content = PdfContent()
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
        and moves content origin to bottom-left.
        """
        if height is None:
            return self._page_height - y
        return self._page_height - y - height

    def calc_trim(self, width: float, height: float, rounded_corner: float) -> float:
        if width < height:
            trim = (width * (rounded_corner / 100)) / 2
        else:
            trim = (height * (rounded_corner / 100)) / 2
        return trim

    def generate_pdf_obj(self, collector: Collector):
        self.page_obj = collector.new_obj()
        self.resources_obj = collector.new_obj()
        self.contents_obj = collector.new_obj()

    def add_dto_page_contents(
        self,
        contents: list[object],
        pdf_fonts: dict[str, PdfFont],
        debug: bool,
    ) -> None:
        for content in contents:
            match content:
                case DtoTextArea():
                    self.generate_text_area(content, pdf_fonts, debug)
                case DtoTextBox():
                    self.generate_text_box(content, pdf_fonts, debug)
                case DtoCurve():
                    self.generate_curve(content)
                case DtoRectangle():
                    self.generate_rectangle(content)
                case DtoArc():
                    self.generate_arc(content)
                case DtoEllipse():
                    self.generate_ellipse(content)
                case _:
                    raise ValueError("Type not defined in pdf module.")

    def draw_text_area(self, dto_text_area: DtoTextArea) -> None:
        self._page_content.add_rectangle(
            x=dto_text_area.x,
            y=self.calc_y(dto_text_area.y, dto_text_area.height),
            width=dto_text_area.width,
            height=dto_text_area.height,
            fill_color=MaterialColors.Gray100,
            line_color=MaterialColors.Gray600,
        )
        for paragraph in dto_text_area.paragraphs:
            self._page_content.add_rectangle(
                x=paragraph.x,
                y=self.calc_y(paragraph.y, paragraph.height),
                width=paragraph.width,
                height=paragraph.height,
                fill_color=MaterialColors.Teal100,
                line_color=MaterialColors.Teal600,
            )
            for text_line in paragraph.textlines:
                self._page_content.add_rectangle(
                    x=text_line.x,
                    y=self.calc_y(text_line.y, text_line.height),
                    width=text_line.width,
                    height=text_line.height,
                    fill_color=MaterialColors.Yellow100,
                    line_color=MaterialColors.Yellow600,
                )
                for word in text_line.words:
                    self._page_content.add_rectangle(
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
        current_state: tuple[float, tuple[float, float, float], str] | tuple[None, None, None],
        fragment: DtoFragment,
        pdf_fonts: dict[str, PdfFont],
    ) -> tuple[float, tuple[float, float, float], str]:
        new_state = (
            fragment.font_size,
            fragment.font_color,
            fragment.font_name,
        )
        if (
            current_state[0] is None or current_state[1] is None or current_state[2] is None
        ) or new_state != current_state:
            page_font_name = self.get_pagefontname(fragment.font_name, pdf_fonts)
            self._page_content.add_page_font_with_size(page_font_name, fragment.font_size)
            self._page_content.add_fill_color(fragment.font_color)
            return new_state
        return current_state

    def draw_text_fragment(self, fragment: DtoFragment, pdf_font: PdfFont) -> None:
        cid_in_bytes = bytearray()
        for char in fragment.chars:
            cid = pdf_font.get_cid_in_bytes(char)
            if cid is not None:
                cid_in_bytes.extend(cid)
        if len(cid_in_bytes) > 0:
            self._page_content.add_text(fragment.x, self.calc_y(fragment.baseline), cid_in_bytes)

    def generate_text_area(
        self,
        dto_text_area: DtoTextArea,
        pdf_fonts: dict[str, PdfFont],
        debug: bool,
    ) -> None:
        self._page_content.add_savestate()
        if debug:
            self.draw_text_area(dto_text_area)
        current_state = (None, None, None)
        for fragment in dto_text_area.fragments:
            current_state = self.check_and_update_text_state(current_state, fragment, pdf_fonts)
            self.draw_text_fragment(fragment, pdf_fonts[fragment.font_name])
        self._page_content.add_restore_state()

    def generate_text_box(
        self,
        dto_textbox: DtoTextBox,
        pdf_fonts: dict[str, PdfFont],
        debug: bool,
    ) -> None:
        self._page_content.add_rectangle(
            dto_textbox._x,
            self.calc_y(dto_textbox._y, dto_textbox._height),
            dto_textbox._width,
            dto_textbox._height,
            dto_textbox._fill_color,
            dto_textbox._line_color,
            dto_textbox._line_width,
            dto_textbox._line_pattern,
        )
        if dto_textbox._text_area is not None:
            self.generate_text_area(dto_textbox._text_area, pdf_fonts, debug)

    def generate_curve(self, dto_curve: DtoCurve) -> None:
        self._page_content.add_savestate()
        if dto_curve._fill_color is not None:
            self._page_content.add_fill_color(dto_curve._fill_color)
        if dto_curve._line_color is not None:
            self._page_content.add_line_color(dto_curve._line_color)
            self._page_content.add_line_width(dto_curve._line_width)
            self._page_content.add_line_pattern(dto_curve._line_pattern)
        for index, point in enumerate(dto_curve._path):
            if (index == 0) and isinstance(point, DtoPoint):
                self._page_content.add_path_start_point(point._x, self.calc_y(point._y))
                continue
            if isinstance(point, DtoPoint):
                self._page_content.add_path_move_point(point._x, self.calc_y(point._y))
                continue
            if isinstance(point, DtoBezier):
                self._page_content.add_path_control_point(point._cp1_x, self.calc_y(point._cp1_y))
                self._page_content.add_path_control_point(point._cp2_x, self.calc_y(point._cp2_y))
                self._page_content.add_path_end_point(point._endp_x, self.calc_y(point._endp_y))
        if dto_curve._closed:
            self._page_content.add_path_close_line()
        if dto_curve._fill_color is not None and dto_curve._line_color is not None:
            self._page_content.add_path_both_stroke_and_fill()
        if dto_curve._fill_color is not None and dto_curve._line_color is None:
            self._page_content.add_path_fill()
        if dto_curve._fill_color is None and dto_curve._line_color is not None:
            self._page_content.add_path_stroke()
        self._page_content.add_restore_state()

    def generate_rectangle(self, dto_rectangle: DtoRectangle):
        self._page_content.add_savestate()
        if dto_rectangle.fill_color is not None:
            self._page_content.add_fill_color(dto_rectangle.fill_color)
        if dto_rectangle.line_color is not None:
            self._page_content.add_line_color(dto_rectangle.line_color)
            self._page_content.add_line_width(dto_rectangle.line_width)
            self._page_content.add_line_pattern(dto_rectangle.line_pattern)
        if (
            dto_rectangle.rounded_corner_top_left == 0
            and dto_rectangle.rounded_corner_top_right == 0
            and dto_rectangle.rounded_corner_bottom_right == 0
            and dto_rectangle.rounded_corner_bottom_left == 0
        ):
            self._page_content.add_rectangle_without_formatting(
                dto_rectangle.x,
                self.calc_y(dto_rectangle.y, dto_rectangle.height),
                dto_rectangle.width,
                dto_rectangle.height,
            )
        else:
            x = dto_rectangle.x
            y = dto_rectangle.y
            width = dto_rectangle.width
            height = dto_rectangle.height
            # if width < height:
            #     trim: float = (width * (dto_rectangle._rounded_corners / 100)) / 2
            # else:
            #     trim: float = (height * (dto_rectangle._rounded_corners / 100)) / 2
            # first point
            self._page_content.add_path_start_point(
                x + self.calc_trim(width, height, dto_rectangle.rounded_corner_top_left), self.calc_y(y)
            )
            # second point
            self._page_content.add_path_move_point(
                x + width - self.calc_trim(width, height, dto_rectangle.rounded_corner_top_right), self.calc_y(y)
            )
            # third point
            if dto_rectangle.rounded_corner_top_right != 0:
                self._page_content.add_arc(
                    x + width - self.calc_trim(width, height, dto_rectangle.rounded_corner_top_right),
                    self.calc_y(y),
                    x + width,
                    self.calc_y(y + self.calc_trim(width, height, dto_rectangle.rounded_corner_top_right)),
                )
            # fourth point
            self._page_content.add_path_move_point(
                x + width,
                self.calc_y(y + height - self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_right)),
            )
            # fifth point
            if dto_rectangle.rounded_corner_bottom_right != 0:
                self._page_content.add_arc(
                    x + width,
                    self.calc_y(y + height - self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_right)),
                    x + width - self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_right),
                    self.calc_y(y + height),
                )
            # sixth point
            self._page_content.add_path_move_point(
                x + self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_left), self.calc_y(y + height)
            )
            # seventh point
            if dto_rectangle.rounded_corner_bottom_left != 0:
                self._page_content.add_arc(
                    x + self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_left),
                    self.calc_y(y + height),
                    x,
                    self.calc_y(y + height - self.calc_trim(width, height, dto_rectangle.rounded_corner_bottom_left)),
                )
            # eigth point
            self._page_content.add_path_move_point(
                x, self.calc_y(y + self.calc_trim(width, height, dto_rectangle.rounded_corner_top_left))
            )
            # ninth point
            if dto_rectangle.rounded_corner_top_left != 0:
                self._page_content.add_arc(
                    x,
                    self.calc_y(y + self.calc_trim(width, height, dto_rectangle.rounded_corner_top_left)),
                    x + self.calc_trim(width, height, dto_rectangle.rounded_corner_top_left),
                    self.calc_y(y),
                )
            # close line
            self._page_content.add_path_close_line()
        if dto_rectangle.fill_color is not None and dto_rectangle.line_color is not None:
            self._page_content.add_path_both_stroke_and_fill()
        if dto_rectangle.fill_color is not None and dto_rectangle.line_color is None:
            self._page_content.add_path_fill()
        if dto_rectangle.fill_color is None and dto_rectangle.line_color is not None:
            self._page_content.add_path_stroke()
        self._page_content.add_restore_state()

    def generate_arc(self, dto_arc: DtoArc) -> None:
        if dto_arc._line_color is None:
            return
        self._page_content.add_savestate()
        self._page_content.add_line_color(dto_arc._line_color)
        self._page_content.add_line_width(dto_arc._line_width)
        self._page_content.add_line_pattern(dto_arc._line_pattern)
        self._page_content.add_path_start_point(dto_arc.x1, self.calc_y(dto_arc.y1))
        self._page_content.add_arc(dto_arc.x1, self.calc_y(dto_arc.y1), dto_arc.x2, self.calc_y(dto_arc.y2))
        self._page_content.add_path_stroke()
        self._page_content.add_restore_state()

    def generate_ellipse(self, dto_ellipse: DtoEllipse) -> None:
        self._page_content.add_savestate()
        has_fill = False
        has_stroke = False
        if dto_ellipse.fill_color is not None and dto_ellipse.line_color is not None:
            has_fill = True
            has_stroke = True
            self._page_content.add_fill_color(dto_ellipse.fill_color)
            self._page_content.add_line_color(dto_ellipse.line_color)
            self._page_content.add_line_width(dto_ellipse.line_width)
            self._page_content.add_line_pattern(dto_ellipse.line_pattern)
        if dto_ellipse.fill_color is not None and dto_ellipse.line_color is None:
            has_fill = True
            has_stroke = False
            self._page_content.add_fill_color(dto_ellipse.fill_color)
        if dto_ellipse.fill_color is None and dto_ellipse.line_color is not None:
            has_fill = False
            has_stroke = True
            self._page_content.add_line_color(dto_ellipse.line_color)
            self._page_content.add_line_width(dto_ellipse.line_width)
            self._page_content.add_line_pattern(dto_ellipse.line_pattern)

        x = dto_ellipse.x
        y = dto_ellipse.y
        width = dto_ellipse.width
        height = dto_ellipse.height
        self._page_content.add_path_start_point(x, self.calc_y(y + height / 2))
        self._page_content.add_arc(x, self.calc_y(y + height / 2), (x + width / 2), self.calc_y(y))
        self._page_content.add_arc((x + width / 2), self.calc_y(y), (x + width), self.calc_y(y + height / 2))
        self._page_content.add_arc((x + width), self.calc_y(y + height / 2), (x + width / 2), self.calc_y(y + height))
        self._page_content.add_arc((x + width / 2), self.calc_y(y + height), x, self.calc_y(y + height / 2))
        self._page_content.add_path_close_line()

        self._page_content.add_fill_and_shape(has_fill, has_stroke)
        self._page_content.add_restore_state()

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
        self.page_obj.set_attribute_value("/MediaBox", f"[0 0 {self._page_width} {self._page_height}]")
        self.page_obj.set_attribute_value("/Resources", self.resources_obj)
        self.resources_obj.set_attribute_value("/ProcSet", "[/PDF /Text /ImageB /ImageC /ImageI]")
        self.resources_obj.set_attribute_value("/XObject", "<<\t>>")
        self.page_obj.add_attribute_value("/Contents", self.contents_obj)
        if should_compress:
            self.contents_obj.extend_stream(zlib.compress(self._page_content.stream))
            self.contents_obj.set_attribute_value("/Filter", "/FlateDecode")
        else:
            self.contents_obj.extend_stream(self._page_content.stream)
        fonts_dict = {}
        for page_fontname, font in self._pagefontname_fontresource.items():
            page_fontname_formatted = f"/{page_fontname}"
            fonts_dict[page_fontname_formatted] = font.obj_num
        self.resources_obj.set_attribute_value("/Font", fonts_dict)
