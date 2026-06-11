from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


class LinkExtractor:
    @staticmethod
    def extract(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            link = urljoin(base_url, anchor["href"].strip())
            if urlparse(link).scheme not in {"http", "https"} or link in seen:
                continue
            seen.add(link)
            links.append(link)

        return links
