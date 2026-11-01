# novelcast/services/scrapers/exceptions.py

class ScraperUnavailableError(RuntimeError):
    """An external service required by a scraper is unavailable."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(message)
        

