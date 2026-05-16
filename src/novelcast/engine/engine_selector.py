# novelcast/engine/engine_selector.py
class EngineSelector:

    def __init__(self, engines):
        self.engines = engines

    def get_engine(self, url: str):

        for engine in self.engines:
            if engine.can_handle(url):
                return engine

        raise ValueError(f"No engine found for URL: {url}")