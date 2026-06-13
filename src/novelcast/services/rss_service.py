import logging

logger = logging.getLogger(__name__)


class RssService:
    def __init__(self, readers: list):
        self.readers = readers

    def run_all(self) -> list[dict]:
        logger.debug("RssService.run_all started | readers=%d", len(self.readers))

        all_items = []

        for reader in self.readers:
            try:
                logger.debug("Running reader | %s", type(reader).__name__)

                items = reader.run()

                logger.debug(
                    "Reader finished | %s | items=%d",
                    type(reader).__name__,
                    len(items),
                )

                all_items.extend(items)

            except Exception:
                logger.exception("Reader failed | %s", type(reader).__name__)

        logger.debug("RssService finished | total_items=%d", len(all_items))

        return all_items