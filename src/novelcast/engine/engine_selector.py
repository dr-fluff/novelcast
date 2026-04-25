class EngineSelector:

    def __init__(self, fanficfare_engine, adapter_engine=None):
        self.engines = [fanficfare_engine]
        if adapter_engine:
            self.engines.append(adapter_engine)

    def get_engine(self, url: str):
        for engine in self.engines:
            if engine.can_handle(url):
                return engine

        raise ValueError(f"No engine found for URL: {url}")