# novelcast/utils/link_icons.py
"""Maps a URL's domain to an icon, for displaying recognizable site icons
next to author links (Instagram, X, Patreon, RoyalRoad, etc.).

Most sites are covered by Font Awesome's brand icon set. A few niche
sites (RoyalRoad, ScribbleHub, ...) don't have a Font Awesome icon, so
those are served as small custom images from /static/images/link-icons/.
"""

from urllib.parse import urlparse

# Font Awesome icon classes, keyed by domain.
_FA_ICON_MAP = {
    "instagram.com": "fa-brands fa-instagram",
    "twitter.com": "fa-brands fa-x-twitter",
    "x.com": "fa-brands fa-x-twitter",
    "facebook.com": "fa-brands fa-facebook",
    "tiktok.com": "fa-brands fa-tiktok",
    "youtube.com": "fa-brands fa-youtube",
    "youtu.be": "fa-brands fa-youtube",
    "patreon.com": "fa-brands fa-patreon",
    "reddit.com": "fa-brands fa-reddit",
    "discord.gg": "fa-brands fa-discord",
    "discord.com": "fa-brands fa-discord",
    "wattpad.com": "fa-brands fa-wattpad",
    "amazon.com": "fa-brands fa-amazon",
    "goodreads.com": "fa-brands fa-goodreads",
    "wordpress.com": "fa-brands fa-wordpress",
    "medium.com": "fa-brands fa-medium",
    "github.com": "fa-brands fa-github",
    "linkedin.com": "fa-brands fa-linkedin",
    "threads.net": "fa-brands fa-threads",
    "bsky.app": "fa-brands fa-bluesky",
    "mastodon.social": "fa-brands fa-mastodon",
    "ko-fi.com": "fa-solid fa-mug-hot",
    "buymeacoffee.com": "fa-solid fa-mug-hot",
    "linktr.ee": "fa-solid fa-link",
    "substack.com": "fa-solid fa-envelope-open-text",
}

# Custom image icons (no Font Awesome equivalent), keyed by domain.
# Paths are relative to /static/.
_CUSTOM_ICON_MAP = {
    "royalroad.com": "images/link-icons/royalroad.svg",
    "scribblehub.com": "images/link-icons/scribblehub.svg",
}

_DEFAULT_FA_ICON = "fa-solid fa-link"


def _normalize_host(url: str) -> str | None:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None

    if not host:
        return None

    if host.startswith("www."):
        host = host[4:]

    return host.split(":", 1)[0]  # strip a port if present


def _match_domain(host: str, domain_map: dict) -> str | None:
    for domain, value in domain_map.items():
        if host == domain or host.endswith("." + domain):
            return value
    return None


def link_icon(url: str) -> dict:
    host = _normalize_host(url)
    if not host:
        return {"type": "fa", "class": _DEFAULT_FA_ICON}

    fa_class = _match_domain(host, _FA_ICON_MAP)
    if fa_class:
        return {"type": "fa", "class": fa_class}

    # Fallback: live favicon for anything without a Font Awesome icon
    return {"type": "img", "src": f"https://www.google.com/s2/favicons?domain={host}&sz=32"}


def icon_for_url(url: str) -> str:
    """Backward-compatible helper: returns a Font Awesome class string only.
    Prefer link_icon() in new templates so custom site icons render too."""
    result = link_icon(url)
    return result["class"] if result["type"] == "fa" else _DEFAULT_FA_ICON
