# novelcast/engine/site_detector.py

class SiteDetector:

    def detect(self, url: str) -> str:
        if "royalroad.com" in url:
            return "royalroad"
        if "wattpad.com" in url:
            return "wattpad"
        if "patreon.com" in url:
            return "patreon"
        return "generic"