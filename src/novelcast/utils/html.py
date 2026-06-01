import re

from bs4 import BeautifulSoup


def clean_html_description(html: str) -> str:
    """Convert HTML descriptions into readable plain text while preserving links."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        text = a.get_text(" ", strip=True)
        if href:
            replacement = f"{text} ({href})" if text else href
        else:
            replacement = text
        a.replace_with(replacement)

    text = soup.get_text(separator="\n", strip=True)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n\n".join(lines)
