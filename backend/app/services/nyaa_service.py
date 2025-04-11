import httpx
import feedparser
import urllib.parse
from typing import Optional

from app.core.config import settings


class NyaaResult:
    def __init__(self, entry):
        self.title: str = entry.get("title", "N/A")
        self.torrent_file_url: Optional[str] = entry.get("link")
        self.info_hash: Optional[str] = entry.get("nyaa_infohash")
        if not self.info_hash:
            self.info_hash = entry.get("nyaa:infohash")

        self.guid: Optional[str] = entry.get("guid")
        self.pubDate: Optional[str] = entry.get("published")
        self.seeders: Optional[int] = self._parse_int(entry.get("nyaa_seeders"))
        self.leechers: Optional[int] = self._parse_int(entry.get("nyaa_leechers"))
        self.downloads: Optional[int] = self._parse_int(entry.get("nyaa_downloads"))
        self.size: Optional[str] = entry.get("nyaa_size")
        self.category: Optional[str] = entry.get("nyaa_category")
        self.trusted: bool = entry.get("nyaa_trusted", "").lower() == "yes"
        self.remake: bool = entry.get("nyaa_remake", "").lower() == "yes"

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Safely parse an integer from string."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @property
    def magnet_link(self) -> Optional[str]:
        """Constructs a basic magnet link if info_hash is available."""
        if not self.info_hash:
            return None
        magnet = f"magnet:?xt=urn:btih:{self.info_hash}"
        encoded_title = urllib.parse.quote_plus(self.title)
        magnet += f"&dn={encoded_title}"
        # Add common trackers (optional, can increase chances of finding peers)
        # magnet += "&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce"
        # magnet += "&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce"
        return magnet

    def __repr__(self):
        return f"<NyaaResult title='{self.title}' hash='{self.info_hash}' seeders={self.seeders}>"


class NyaaService:
    async def search(self, query: str, category: str = "1_2") -> list[NyaaResult]:
        """Searches Nyaa.si using its RSS feed."""
        encoded_query = urllib.parse.quote_plus(query)
        # f=2 -> Trusted Only; c=1_2 -> Anime Eng-translated; q=query
        search_url = f"{settings.NYAA_RSS_URL}&q={encoded_query}&c={category}&f=2"

        results = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url, follow_redirects=True, timeout=20.0
                )
                response.raise_for_status()

            if not response.text:
                print(f"Empty response from Nyaa for query: {query}")
                return []

            feed = feedparser.parse(response.text)

            if feed.bozo:
                print(
                    f"Warning: feedparser encountered potential issues parsing Nyaa feed for query: {query}. Error: {feed.bozo_exception}"
                )

            for entry in feed.entries:
                results.append(NyaaResult(entry))

        except httpx.RequestError as exc:
            print(f"Nyaa search failed for query '{query}': {exc}")
            return []
        except httpx.HTTPStatusError as exc:
            print(
                f"Nyaa search returned HTTP error for query '{query}': {exc.response.status_code}"
            )
            return []
        except Exception as e:
            print(f"Unexpected error parsing Nyaa feed for query '{query}': {e}")
            return []

        return results


nyaa_service = NyaaService()
