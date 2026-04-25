class FanFicFareParser:

    def parse(self, data: dict) -> dict:

        raw = data["raw"]
        chapters = raw.get("chapters", [])

        normalized = []

        for i, ch in enumerate(chapters, start=1):
            normalized.append({
                "number": i,
                "title": ch.get("title", f"Chapter {i}"),
                "content": ch.get("content", "")
            })

        return {
            "title": data["title"],
            "author": data["author"],
            "chapters": normalized
        }