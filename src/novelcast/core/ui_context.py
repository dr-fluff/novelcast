def build_global_context(request: Request) -> dict:
    return {
        "app_name": "NovelCast",
        "request": request,
        "sort_options": [
            {"key": "title", "label": "Title"},
            {"key": "last_chapter", "label": "Downloaded Chapters"},
            {"key": "url", "label": "URL"},
        ],
        "chapter_sort_options": [
            {"key": "name", "label": "Name"},
            {"key": "reverse", "label": "Reverse"},
        ],
    }
    