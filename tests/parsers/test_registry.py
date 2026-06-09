import pytest

from novelcast.parser import (
    ParserRegistry,
    PatreonParser,
    HtmlParser,
)


def test_register_and_get_parser():
    registry = ParserRegistry()

    parser = PatreonParser()
    registry.register("patreon", parser)

    assert registry.get("patreon") is parser


def test_unknown_parser_raises():
    registry = ParserRegistry()

    with pytest.raises(ValueError):
        registry.get("unknown")


def test_multiple_parsers():
    registry = ParserRegistry()

    registry.register("patreon", PatreonParser())
    registry.register("html", HtmlParser())

    assert isinstance(registry.get("patreon"), PatreonParser)
    assert isinstance(registry.get("html"), HtmlParser)