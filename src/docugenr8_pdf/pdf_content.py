from math import cos
from math import radians
from math import sin


class PdfContent:  # noqa: PLR0904
    def __init__(self):
        self.pdf_version = "1.3"
        self.stream: bytearray = bytearray()

    def add_savestate(self) -> None:
        output = "q\n".encode("ascii")
        self.stream.extend(output)

    def add_clipping(self) -> None:
        output = "W n\n".encode("ascii")
        self.stream.extend(output)

    def add_fill_color(self, rgb: tuple[int, int, int]) -> None:
        pdf_r = rgb[0] / 255
        pdf_g = rgb[1] / 255
        pdf_b = rgb[2] / 255
        output = f"{pdf_r} {pdf_g} {pdf_b} rg\n"
        self.stream.extend(output.encode("ascii"))

    def add_page_font_with_size(
        self,
        page_font: str,
        font_size: float
        ) -> None:
        output = f"BT /{page_font} {font_size} Tf ET\n"
        self.stream.extend(output.encode("ascii"))

    def add_line_color(self, rgb: tuple[int, int, int]) -> None:
        pdf_r = rgb[0] / 255
        pdf_g = rgb[1] / 255
        pdf_b = rgb[2] / 255
        output = f"{pdf_r} {pdf_g} {pdf_b} RG\n"
        self.stream.extend(output.encode("ascii"))

    def add_line_pattern(
        self, pattern: tuple[float, float, float, float, float]
    ) -> None:
        # Line Cap
        # 0 - Butt cap, 1 - Round cap, 2 - Projecting square cap
        line_cap = pattern[0]
        # Line join
        # 0 - Miter join, 1 - Round join, 2 - Bevel join
        line_join = pattern[1]
        # Dash pattern
        # [on off] phase
        dash_pattern_on = pattern[2]
        dash_pattern_off = pattern[3]
        dash_pattern_phase = pattern[4]

        line_cap_string = f"{line_cap} J "
        line_join_string = f"{line_join} j "
        dash_pattern_string = (
            f"[{dash_pattern_on} {dash_pattern_off}] {dash_pattern_phase} d"
        )
        output = line_cap_string + line_join_string + dash_pattern_string + "\n"
        self.stream.extend(output.encode("ascii"))

    def add_line_width(self, line_width: float) -> None:
        output = f"{line_width} w\n"
        self.stream.extend(output.encode("ascii"))

    def add_path_start_point(self, x: float, y: float) -> None:
        output = f"{x} {y} m "
        self.stream.extend(output.encode("ascii"))

    def add_path_control_point(self, x: float, y: float) -> None:
        output = f"{x} {y} "
        self.stream.extend(output.encode("ascii"))

    def add_path_end_point(self, x: float, y: float) -> None:
        output = f"{x} {y} c "
        self.stream.extend(output.encode("ascii"))

    def add_path_move_point(self, x: float, y: float) -> None:
        output = f"{x} {y} l "
        self.stream.extend(output.encode("ascii"))

    def add_path_close_line(self) -> None:
        output = "h "
        self.stream.extend(output.encode("ascii"))

    def add_path_fill(self) -> None:
        output = "f\n"
        self.stream.extend(output.encode("ascii"))

    def add_path_stroke(self) -> None:
        output = "S\n"
        self.stream.extend(output.encode("ascii"))

    def add_path_both_stroke_and_fill(self) -> None:
        output = "B\n"
        self.stream.extend(output.encode("ascii"))

    def add_rectangle_without_formatting(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        has_fill: bool,
        has_stroke: bool,
    ) -> None:
        style = ""
        if has_fill is True and has_stroke is True:
            style = "B"
        if has_fill is True and has_stroke is False:
            style = "f"
        if has_fill is False and has_stroke is True:
            style = "S"
        if has_fill is False and has_stroke is False:
            style = ""
        output = f"{x} {y} {width} {height} re {style}\n"
        self.stream.extend(output.encode("ascii"))

    def add_restore_state(self) -> None:
        output = "Q\n"
        self.stream.extend(output.encode("ascii"))

    def add_rotate(self, x_pos: float, y_pos: float, degrees: float) -> None:
        cos_r = cos(radians(degrees))
        sin_r = sin(radians(degrees))
        output = (
            f"1 0 0 1 {x_pos} {y_pos} cm\n"
            f"{cos_r} "
            f"{sin_r} "
            f"-{sin_r} "
            f"{sin_r} "
            f"0 0 cm\n"
            f"1 0 0 1 -{x_pos} -{y_pos} cm\n"
        )
        self.stream.extend(output.encode("ascii"))

    def add_text(self, x: float, y: float, cid_bytes: bytes) -> None:
        output = bytearray()
        x1 = str(x).encode("ascii")
        y1 = str(y).encode("ascii")
        output.extend(b"BT %b %b Td (%b) Tj ET\n" % (x1, y1, cid_bytes))
        self.stream.extend(output)

    def add_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill_color: None | tuple[int, int, int],
        line_color: None | tuple[int, int, int],
        line_width: float = 1.0,
        line_pattern: tuple[float, float, float, float, float] = (
            0,
            0,
            0,
            0,
            0,
        ),
    ) -> None:
        self.add_savestate()
        has_fill = False
        has_stroke = False
        if fill_color is not None and line_color is not None:
            has_fill = True
            has_stroke = True
            self.add_fill_color(fill_color)
            self.add_line_color(line_color)
            self.add_line_width(line_width)
            self.add_line_pattern(line_pattern)
        if fill_color is not None and line_color is None:
            has_fill = True
            has_stroke = False
            self.add_fill_color(fill_color)
        if fill_color is None and line_color is not None:
            has_fill = False
            has_stroke = True
            self.add_line_color(line_color)
            self.add_line_width(line_width)
            self.add_line_pattern(line_pattern)
        self.add_rectangle_without_formatting(
            x, y, width, height, has_fill, has_stroke
        )
        self.add_restore_state()
