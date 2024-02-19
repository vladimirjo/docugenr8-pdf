from datetime import datetime

from .collector import Collector


class PdfInfo:
    def __init__(self, coll: Collector) -> None:
        self._coll = coll
        # Document's title
        self.title = None
        # The date and time the document was created, formatted as a date
        self.subject = None
        # Any keywords associated with this document.
        self.creation_date = None
        # The date and time the document was most recently modified, formatted as a date.
        self.mod_date = None
        # The name of the person(s) who created the document.
        self.author = None
        # The software used to author the original document that was used as the basis for conversion to PDF.
        # If the PDF was created directly, the value may be left blank or may be the same as the Producer.
        self.creator = None
        # The name of the product that created the PDF.
        self.producer = None
        # The document’s subject.
        self.keywords = None

    def has_value(self):
        list1 = [
            self.title,
            self.subject,
            self.creation_date,
            self.mod_date,
            self.author,
            self.creator,
            self.producer,
            self.keywords,
        ]
        # values = [x for x in list1 if x is not None]
        if len([x for x in list1 if x is not None]) > 0:
            return True
        return False

    def get_pdf_date(self, date: datetime):
        timezone_hours = date.strftime("%z")[:3]
        timezone_seconds = date.strftime("%z")[-2:]
        return (
            "D:"
            + date.strftime("%Y%m%d%H%M%S")
            + timezone_hours
            + "'"
            + timezone_seconds
            + "'"
        )

    def build(self):
        info_handle = self._coll.new_obj()
        self._coll.info = b"%d 0 R\n" % info_handle.obj_num
        if self.title is not None:
            info_handle.attr_set("/Title", "(" + self.title + ")")
        if self.subject is not None:
            info_handle.attr_set("/Subject", "(" + self.subject + ")")
        if self.creation_date is not None:
            pdf_date = self.get_pdf_date(self.creation_date)
            info_handle.attr_set("/CreationDate", "(" + pdf_date + ")")
        if self.mod_date is not None:
            info_handle.attr_set("/ModDate", "(" + self.mod_date + ")")
        if self.author is not None:
            info_handle.attr_set("/Author", "(" + self.author + ")")
        if self.creator is not None:
            info_handle.attr_set("/Creator", "(" + self.creator + ")")
        if self.producer is not None:
            info_handle.attr_set("/Producer", "(" + self.producer + ")")
        if self.keywords is not None:
            info_handle.attr_set("/Keywords", "(" + self.keywords + ")")
