class EpubParser:

    def parse(self, data: dict) -> dict:
        epub_path = data["epub_path"]

        # later: extract chapters via ebooklib
        return {
            "title": data["title"],
            "author": data["author"],
            "chapters": []
        }