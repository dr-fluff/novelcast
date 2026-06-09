# novelcast/parser/patreon_parser.py

from novelcast.parser.base import BaseParser, Story
from typing import Optional


class PatreonParser(BaseParser):
    """
    Parser for Patreon engine output.
    
    Takes the raw dict from PatreonEngine.fetch() and converts to Story format.
    Unlike EpubParser, chapters already have full content from the engine.
    """
    
    def parse(self, data: dict) -> Story:
        """
        Convert Patreon engine output to Story format.
        
        Input (from PatreonEngine.fetch()):
        {
            "title": str,
            "author": str,
            "url": str,
            "chapters": list[int],
            "format": "chapters",
            "raw": {
                "chapters": list[dict with number, title, content],
                "post_count": int,
                ...
            }
        }
        
        Output (Story format):
        {
            "title": str,
            "author": str,
            "chapters": list[Chapter]
        }
        """
        
        # Get chapters from raw data (they already have content from engine)
        raw = data.get("raw", {})
        raw_chapters = raw.get("chapters", [])
        
        # Convert to Story format
        chapters = [
            {
                "number": ch.get("number"),
                "title": ch.get("title", f"Chapter {ch.get('number')}"),
                "content": ch.get("content", ""),
            }
            for ch in raw_chapters
        ]
        
        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters,
        }