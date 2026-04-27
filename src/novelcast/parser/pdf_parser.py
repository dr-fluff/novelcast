# novelcast/parser/pdf_parser.py

from novelcast.parser.base import BaseParser, Story


class PdfParser(BaseParser):

    def parse(self, data: dict) -> Story:
        pdf_path = data.get("file_path")

        # TODO: extract PDF text into chapters
        chapters = []

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters
        }