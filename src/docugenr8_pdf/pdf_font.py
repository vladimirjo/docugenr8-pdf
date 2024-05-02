import logging
import re
import zlib
from io import BytesIO

from fontTools import subset
from fontTools import ttLib

from .core import Collector
from .core import PdfObj


MAX_TWO_BYTE_VALUE = 65535
CARRIAGE_RETURN = 13
TAB = 9
NEW_LINE = 10
SPACE = 32
NOT_DEFINED = 0
REPLACEMENT_CHARACTER = 65533
FORBIDDEN_CIDS = {bytes([10]),   # ASCII 10 - new line
                   bytes([13]),   # ASCII 13 - carriage return
                   bytes([37]),   # ASCII 37 - %
                   bytes([40]),   # ASCII 40 - (
                   bytes([41]),   # ASCII 41 - )
                   bytes([47]),   # ASCII 47 - /
                   bytes([60]),   # ASCII 60 - <
                   bytes([62]),   # ASCII 62 - >
                   bytes([91]),   # ASCII 91 - [
                   bytes([92]),   # ASCII 92 - \
                   bytes([93]),   # ASCII 93 - ]
                   bytes([123]),  # ASCII 123 - {
                   bytes([125])}  # ASCII 125 - }



class PdfFont:
    def __init__(self, font_name: str, font_raw_data: bytes) -> None:
        self.name = font_name
        self.ttfont = ttLib.TTFont(
            BytesIO(font_raw_data),
            recalcTimestamp=False
            )
        self.cmap = self.ttfont.getBestCmap()
        self.cid_counter = 1
        self.char_code_point_to_cid: dict[int, int] = {}
        self.cid_info: dict[int,       # cid
                            tuple[
                                int,   # width
                                int,   # char code point
                                str,   # glyph name
                                ]] = {}
        self.generated_font_name = "MPDFAA+" + \
            re.sub("[ ()]", "", self.ttfont["name"].getBestFullName())  # type: ignore
        self.scale = 1000 / self.ttfont["head"].unitsPerEm  # type: ignore
        self.cap_height = self.get_cap_height()
        self.flags = self.get_flags()
        self.ascent = round(self.ttfont["hhea"].ascent * self.scale)  # type: ignore
        self.descent = round(self.ttfont["hhea"].descent * self.scale)  # type: ignore
        self.fontbbox = (f"[{self.ttfont['head'].xMin * self.scale:.0f}"  # type: ignore
                         f" {self.ttfont['head'].yMin * self.scale:.0f}"  # type: ignore
                         f" {self.ttfont['head'].xMax * self.scale:.0f}"  # type: ignore
                         f" {self.ttfont['head'].yMax * self.scale:.0f}]")  # type: ignore
        self.italic_angle = int(self.ttfont["post"].italicAngle)  # type: ignore
        self.stem_v = round(
            50 + int(pow((self.ttfont["OS/2"].usWeightClass / 65), 2)))  # type: ignore
        self.missing_width = round(
            self.scale * self.ttfont["hmtx"].metrics[".notdef"][0])  # type: ignore
        self.set_not_defined_unicode_value()
        self.obj_num: None | PdfObj = None
        self.obj_descendant_fonts: None | PdfObj = None
        self.obj_to_unicode: None | PdfObj = None
        self.obj_font_descriptor: None | PdfObj = None
        self.obj_font_file_2: None | PdfObj = None
        self.obj_cid_to_gid: None | PdfObj = None

    def get_cap_height(self):
        try:
            cap_height = self.ttfont["OS/2"].sCapHeight  # type: ignore
        except AttributeError:
            cap_height = self.ttfont["hhea"].ascent  # type: ignore
        return round(cap_height * self.scale)

    def get_flags(self):
        flags = 0x0000004  # SYMBOLIC
        if self.ttfont["post"].isFixedPitch:  # type: ignore
            flags |= 0x0000001  # FIXED_PITCH
        if self.ttfont["post"].italicAngle != 0:  # type: ignore
            flags |= 0x0000040  # ITALIC
        if self.ttfont["OS/2"].usWeightClass >= 600:  # type: ignore  # noqa: PLR2004
            flags |= 0x0040000  # FORCE_BOLD
        return flags

    def font_subset(self):
        options = subset.Options(notdef_outline=True, recommended_glyphs=True)
        options.drop_tables += ["GDEF", "GSUB", "GPOS", "MATH", "hdmx"]
        logging.getLogger("fontTools.subset").setLevel(logging.CRITICAL)
        subsetter = subset.Subsetter(options)
        subsetter.populate(
            glyphs=[value[2] for value in self.cid_info.values()]
            )
        subsetter.subset(self.ttfont)
        self.ttfont.getReverseGlyphMap(rebuild=True)

    def generate_gid_map_in_bytes(self):
        cid_to_gid = {}
        for cid, info in self.cid_info.items():
            cid_to_gid[cid] = self.ttfont.getGlyphID(
                info[2]).to_bytes(2, "big")
        b = bytearray()
        for position in range(MAX_TWO_BYTE_VALUE + 1):
            if position in cid_to_gid:
                b.extend(cid_to_gid[position])
                continue
            b.extend(b"\x00\x00")
        return b

    def set_not_defined_unicode_value(
        self) -> None:
        glyph_name = ".notdef"
        glyph_width = self.ttfont["hmtx"].metrics[glyph_name][0]  # type: ignore
        self.cid_info[NOT_DEFINED] = (
            round(self.scale * glyph_width + 0.001),
            REPLACEMENT_CHARACTER,
            glyph_name)

    def get_cid_in_bytes(self, input_string: str) -> bytes | None:
        b = bytearray()
        for char in input_string:
            char_code_point = ord(char)
            if char_code_point in {CARRIAGE_RETURN, TAB, NEW_LINE}:
                return None
            if char_code_point not in self.char_code_point_to_cid:
                try:
                    glyph_name = self.cmap[char_code_point]
                    glyph_width = self.ttfont["hmtx"].metrics[glyph_name][0]  # type: ignore
                    self.char_code_point_to_cid[char_code_point] = (
                        self.cid_counter)
                    self.cid_info[self.cid_counter] = (
                        round(self.scale * glyph_width + 0.001),
                        char_code_point,
                        glyph_name)
                    self._increase_cid()
                except KeyError:
                    # for unicodes not defined in font
                    self.char_code_point_to_cid[char_code_point] = NOT_DEFINED
            b.extend(
                self.char_code_point_to_cid[char_code_point].to_bytes(2, "big"))
        return bytes(b)


    def _increase_cid(
        self
        ) -> None:
        self.cid_counter += 1
        if self.cid_counter > MAX_TWO_BYTE_VALUE:
            raise ValueError("The cid number has exceeded the limit.")
        byte_value = self.cid_counter.to_bytes(2, byteorder="big")
        if (byte_value[0].to_bytes(1, "big") in FORBIDDEN_CIDS
            or byte_value[1].to_bytes(1, "big") in FORBIDDEN_CIDS):
            self._increase_cid()

    def generate_pdf_obj(self, collector: Collector):
        self.obj_num = collector.new_obj()
        self.obj_descendant_fonts = collector.new_obj()
        self.obj_to_unicode = collector.new_obj()
        self.obj_font_descriptor = collector.new_obj()
        self.obj_font_file_2 = collector.new_obj()
        self.obj_cid_to_gid = collector.new_obj()

    def _font_obj_build(self) -> None:
        if self.obj_num is None:
            raise ValueError("Font object is missing.")
        self.obj_num.set_attribute_value("/Type", "/Font")
        self.obj_num.set_attribute_value("/Subtype", "/Type0")
        self.obj_num.set_attribute_value("/Encoding", "/Identity-H")
        self.obj_num.set_attribute_value(
            "/BaseFont", f"/{self.generated_font_name}")
        if self.obj_descendant_fonts is None:
            raise ValueError("Descendant fonts object is missing.")
        self.obj_num.set_attribute_value(
            "/DescendantFonts", [self.obj_descendant_fonts])
        if self.obj_to_unicode is None:
            raise ValueError("To Unicode object is missing.")
        self.obj_num.set_attribute_value("/ToUnicode", self.obj_to_unicode)

    def _descendant_fonts_obj_build(self) -> None:
        if self.obj_descendant_fonts is None:
            raise ValueError("Descendant fonts object is missing.")
        self.obj_descendant_fonts.set_attribute_value("/Type", "/Font")
        self.obj_descendant_fonts.set_attribute_value(
            "/Subtype", "/CIDFontType2")
        self.obj_descendant_fonts.set_attribute_value(
            "/BaseFont", f"/{self.generated_font_name}")
        self.obj_descendant_fonts.set_attribute_value(
            "/DW", self.missing_width)
        self.obj_descendant_fonts.set_attribute_value(
            "/CIDSystemInfo",
            {
                "/Supplement": "0",
                "/Ordering": "(UCS)",
                "/Registry": "(Adobe)"}
            )
        if self.obj_font_descriptor is None:
            raise ValueError("Font descriptor object is missing.")
        self.obj_descendant_fonts.set_attribute_value(
            "/FontDescriptor",
            self.obj_font_descriptor)
        if self.obj_cid_to_gid is None:
            raise ValueError("Cid to Gid object is missing.")
        self.obj_descendant_fonts.set_attribute_value(
            "/CIDToGIDMap", self.obj_cid_to_gid)
        cid_widths = []
        for cid, info in self.cid_info.items():
            cid_widths.append(f"{cid} {cid} {info[0]}")
        self.obj_descendant_fonts.set_attribute_value("/W", cid_widths)

    def _font_descriptor_obj_build(self) -> None:
        if self.obj_font_descriptor is None:
            raise ValueError("Font descriptor object is missing.")
        self.obj_font_descriptor.set_attribute_value("/Type", "/FontDescriptor")
        self.obj_font_descriptor.set_attribute_value(
            "/FontName", f"/{self.generated_font_name}")
        self.obj_font_descriptor.set_attribute_value(
            "/CapHeight", f"{self.cap_height}")
        self.obj_font_descriptor.set_attribute_value(
            "/StemV", f"{self.stem_v}")
        self.obj_font_descriptor.set_attribute_value(
            "/Ascent", f"{self.ascent}")
        self.obj_font_descriptor.set_attribute_value("/Flags", f"{self.flags}")
        self.obj_font_descriptor.set_attribute_value(
            "/Descent", f"{self.descent}")
        self.obj_font_descriptor.set_attribute_value(
            "/ItalicAngle", f"{self.italic_angle}")
        self.obj_font_descriptor.set_attribute_value(
            "/MissingWidth", f"{self.missing_width}")
        self.obj_font_descriptor.set_attribute_value(
            "/FontBBox", f"{self.fontbbox}")
        if self.obj_font_file_2 is None:
            raise ValueError("Font file 2 object is missing.")
        self.obj_font_descriptor.set_attribute_value(
            "/FontFile2",
            self.obj_font_file_2)

    def _font_file_2_build(self, should_compress: bool) -> None:
        if self.obj_font_file_2 is None:
            raise ValueError("Font descriptor object is missing.")
        self.font_subset()
        ttfont_bytesio = BytesIO()
        self.ttfont.save(ttfont_bytesio)
        ttfont_bytes = ttfont_bytesio.getvalue()
        ttfont_size = len(ttfont_bytes)
        self.obj_font_file_2.set_attribute_value("/Length1", ttfont_size)
        if should_compress:
            self.obj_font_file_2.set_attribute_value("/Filter", "/FlateDecode")
            self.obj_font_file_2.extend_stream(zlib.compress(ttfont_bytes))
        else:
            self.obj_font_file_2.extend_stream(ttfont_bytes)

    def _cid_to_gid_map_build(self, should_compress: bool) -> None:
        if self.obj_cid_to_gid is None:
            raise ValueError("Cid to Gid object is missing.")
        gid_map_in_bytes = self.generate_gid_map_in_bytes()
        if should_compress:
            self.obj_cid_to_gid.set_attribute_value("/Filter", "/FlateDecode")
            self.obj_cid_to_gid.extend_stream(zlib.compress(gid_map_in_bytes))
        else:
            self.obj_cid_to_gid.extend_stream(gid_map_in_bytes)

    def _to_unicode_build(self) -> None:
        if self.obj_to_unicode is None:
            raise ValueError("To Unicode object is missing.")
        self.obj_to_unicode.extend_stream(
            "/CIDInit /ProcSet findresource begin")
        self.obj_to_unicode.extend_stream("12 dict begin")
        self.obj_to_unicode.extend_stream("begincmap")
        self.obj_to_unicode.extend_stream("/CIDSystemInfo")
        self.obj_to_unicode.extend_stream("<</Registry (Adobe)")
        self.obj_to_unicode.extend_stream("/Ordering (UCS)")
        self.obj_to_unicode.extend_stream("/Supplement 0")
        self.obj_to_unicode.extend_stream(">> def")
        self.obj_to_unicode.extend_stream("/CMapName /Adobe-Identity-UCS def")
        self.obj_to_unicode.extend_stream("/CMapType 2 def")
        self.obj_to_unicode.extend_stream("1 begincodespacerange")
        self.obj_to_unicode.extend_stream("<0000> <FFFF>")
        self.obj_to_unicode.extend_stream("endcodespacerange")
        self.obj_to_unicode.extend_stream(
            f"{len(self.cid_info)} beginbfchar")
        for cid, info in self.cid_info.items():
            self.obj_to_unicode.extend_stream(f"<{cid:04X}> <{info[1]:04X}>")
        self.obj_to_unicode.extend_stream("endbfchar")
        self.obj_to_unicode.extend_stream("endcmap")
        self.obj_to_unicode.extend_stream(
            "CMapName currentdict /CMap defineresource pop")
        self.obj_to_unicode.extend_stream("end")
        self.obj_to_unicode.extend_stream("end")


    def build(self,
              should_compress: bool):
        self._font_obj_build()
        self._descendant_fonts_obj_build()
        self._font_descriptor_obj_build()
        self._font_file_2_build(should_compress)
        self._cid_to_gid_map_build(should_compress)
        self._to_unicode_build()
