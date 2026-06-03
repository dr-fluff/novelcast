# tests/test_search_service.py

import pytest
from novelcast.services.search_service import SearchService, ParsedQuery, SITE_REGISTRY

service = SearchService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(raw: str) -> ParsedQuery:
    return service.parse_query(raw)

def urls(raw: str) -> list[str]:
    return [r.url for r in service.build_search_urls(parse(raw))]

def kinds(raw: str) -> list[str]:
    return [r.kind for r in service.build_search_urls(parse(raw))]

def sites(raw: str) -> list[str]:
    return [r.site for r in service.build_search_urls(parse(raw))]


# ---------------------------------------------------------------------------
# Direct URLs
# ---------------------------------------------------------------------------

class TestDirectUrls:
    def test_royalroad_fiction_url(self):
        q = parse("https://www.royalroad.com/fiction/75345/changeling")
        assert q.site == "royalroad"
        assert q.id_type == "numeric_id"
        assert q.resolved_url == "https://www.royalroad.com/fiction/75345"

    def test_royalroad_fiction_url_no_slug(self):
        q = parse("https://www.royalroad.com/fiction/75345")
        assert q.resolved_url == "https://www.royalroad.com/fiction/75345"

    def test_scribblehub_fiction_url(self):
        q = parse("https://www.scribblehub.com/series/12345/some-title")
        assert q.site == "scribblehub"
        assert q.id_type == "numeric_id"
        assert q.resolved_url == "https://www.scribblehub.com/series/12345"

    def test_royalroad_author_profile_url(self):
        q = parse("https://www.royalroad.com/profile/105290")
        assert q.site == "royalroad"
        assert q.id_type == "author"
        assert q.resolved_url == "https://www.royalroad.com/profile/105290/fictions"

    def test_scribblehub_author_profile_url(self):
        q = parse("https://www.scribblehub.com/profile/9999/")
        assert q.site == "scribblehub"
        assert q.id_type == "author"


# ---------------------------------------------------------------------------
# Site + numeric ID
# ---------------------------------------------------------------------------

class TestSiteNumericId:
    def test_royalroad_numeric(self):
        q = parse("royalroad:75345")
        assert q.site == "royalroad"
        assert q.id_type == "numeric_id"
        assert q.resolved_url == "https://www.royalroad.com/fiction/75345"

    def test_rr_alias_numeric(self):
        q = parse("rr:75345")
        assert q.site == "royalroad"
        assert q.resolved_url == "https://www.royalroad.com/fiction/75345"

    def test_scribblehub_numeric(self):
        q = parse("scribblehub:12345")
        assert q.site == "scribblehub"
        assert q.resolved_url == "https://www.scribblehub.com/series/12345"

    def test_sh_alias_numeric(self):
        q = parse("sh:12345")
        assert q.site == "scribblehub"
        assert q.resolved_url == "https://www.scribblehub.com/series/12345"


# ---------------------------------------------------------------------------
# Site + title
# ---------------------------------------------------------------------------

class TestSiteTitle:
    @pytest.mark.parametrize("raw", [
        "royalroad:Changeling",
        "rr:Changeling",
        "royalroad : Changeling",
        "royalroad :Changeling",
        "royalroad: Changeling",
        "royal road:Changeling",
        "royal-road:Changeling",
    ])
    def test_royalroad_title_variants(self, raw):
        q = parse(raw)
        assert q.site == "royalroad"
        assert q.id_type == "title"
        assert q.identifier == "Changeling"
        assert q.resolved_url is None

    def test_scribblehub_title(self):
        q = parse("scribblehub:Changeling")
        assert q.site == "scribblehub"
        assert q.id_type == "title"
        assert q.identifier == "Changeling"

    def test_title_with_spaces(self):
        q = parse("rr:The Progenitor of Bloodlines")
        assert q.identifier == "The Progenitor of Bloodlines"

    def test_title_search_url_contains_query(self):
        result_urls = urls("rr:Changeling")
        assert len(result_urls) == 1
        assert "Changeling" in result_urls[0]
        assert "royalroad.com" in result_urls[0]


# ---------------------------------------------------------------------------
# Author searches
# ---------------------------------------------------------------------------

class TestAuthorSearch:
    def test_global_author_prefix(self):
        q = parse("author:Mecanimus")
        assert q.site is None
        assert q.id_type == "author"
        assert q.identifier == "Mecanimus"

    def test_global_author_prefix_whitespace(self):
        q = parse("author : Mecanimus")
        assert q.identifier == "Mecanimus"

    def test_global_author_searches_all_sites(self):
        result_sites = sites("author:Mecanimus")
        assert "royalroad" in result_sites
        assert "scribblehub" in result_sites

    def test_global_author_only_author_kind(self):
        result_kinds = kinds("author:Mecanimus")
        assert all(k == "author" for k in result_kinds)

    def test_site_scoped_author(self):
        q = parse("royalroad:author:Mecanimus")
        assert q.site == "royalroad"
        assert q.id_type == "author"
        assert q.identifier == "Mecanimus"

    def test_site_scoped_author_alias(self):
        q = parse("rr:author:Mecanimus")
        assert q.site == "royalroad"
        assert q.id_type == "author"

    def test_scribblehub_author(self):
        q = parse("sh:author:SomeWriter")
        assert q.site == "scribblehub"
        assert q.id_type == "author"
        assert q.identifier == "SomeWriter"

    def test_site_scoped_author_search_url(self):
        result_urls = urls("rr:author:Mecanimus")
        assert len(result_urls) == 1
        assert "royalroad.com" in result_urls[0]
        assert "Mecanimus" in result_urls[0]

    def test_author_profile_url_direct(self):
        result_urls = urls("https://www.royalroad.com/profile/105290")
        assert result_urls == ["https://www.royalroad.com/profile/105290/fictions"]


# ---------------------------------------------------------------------------
# Bare keyword (title_and_author, all sites)
# ---------------------------------------------------------------------------

class TestBareKeyword:
    def test_bare_title(self):
        q = parse("Changeling")
        assert q.site is None
        assert q.id_type == "title_and_author"
        assert q.identifier == "Changeling"

    def test_bare_author_name(self):
        q = parse("Mecanimus")
        assert q.site is None
        assert q.id_type == "title_and_author"

    def test_bare_searches_all_sites(self):
        result_sites = sites("Changeling")
        assert "royalroad" in result_sites
        assert "scribblehub" in result_sites

    def test_bare_searches_both_kinds(self):
        result_kinds = kinds("Changeling")
        assert "fiction" in result_kinds
        assert "author" in result_kinds

    def test_bare_multiword(self):
        q = parse("He Who Fights With Monsters")
        assert q.identifier == "He Who Fights With Monsters"
        assert q.id_type == "title_and_author"

    def test_bare_generates_four_urls(self):
        # 2 sites × 2 kinds = 4 search URLs
        result = service.build_search_urls(parse("Changeling"))
        assert len(result) == 4


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unknown_site_prefix_raises(self):
        with pytest.raises(ValueError, match="Unknown site prefix"):
            parse("wattpad:Changeling")

    def test_unknown_site_prefix_message(self):
        with pytest.raises(ValueError, match="wattpad"):
            parse("wattpad:Changeling")


# ---------------------------------------------------------------------------
# build_search_urls structure
# ---------------------------------------------------------------------------

class TestBuildSearchUrls:
    def test_resolved_url_returns_single_result(self):
        q = parse("royalroad:75345")
        results = service.build_search_urls(q)
        assert len(results) == 1
        assert results[0].url == "https://www.royalroad.com/fiction/75345"
        assert results[0].kind == "fiction"

    def test_site_title_returns_one_fiction_url(self):
        results = service.build_search_urls(parse("rr:Changeling"))
        assert len(results) == 1
        assert results[0].kind == "fiction"
        assert results[0].site == "royalroad"

    def test_global_author_returns_one_per_site(self):
        results = service.build_search_urls(parse("author:Mecanimus"))
        assert len(results) == len(SITE_REGISTRY)
        assert all(r.kind == "author" for r in results)

    def test_search_urls_encode_spaces(self):
        results = service.build_search_urls(parse("rr:He Who Fights"))
        assert "+" in results[0].url or "%20" in results[0].url