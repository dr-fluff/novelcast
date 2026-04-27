# novelcast/parser/html_parser.py

from novelcast.parser.base import BaseParser, Story


class HtmlParser(BaseParser):

    def parse(self, data: dict) -> Story:
        html_path = data.get("file_path")

        # TODO: parse HTML into chapters
        chapters = []

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters
        }