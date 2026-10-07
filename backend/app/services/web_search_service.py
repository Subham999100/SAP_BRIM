import re
from typing import List, Dict, Any

from tavily import TavilyClient

from backend.app.config import settings


class WebSearchService:
    """
    Web search service for SAP Assistant.

    Flow:
    1. Use Tavily for live web search.
    2. Prefer official SAP sources.
    3. Return actual title, URL, domain and snippet.
    4. Never generate fake/reference URLs.
    """

    def __init__(self):
        self.api_key = settings.WEB_SEARCH_API_KEY.strip()
        self.client = None

        if self.api_key:
            try:
                self.client = TavilyClient(api_key=self.api_key)
            except Exception:
                self.client = None

    @staticmethod
    def _is_sap_source(url: str) -> bool:
        """Check whether a result comes from an SAP domain."""
        url_lower = url.lower()
        allowed_domains = (
            "sap.com",
            "help.sap.com",
            "community.sap.com",
            "blogs.sap.com",
        )
        return any(domain in url_lower for domain in allowed_domains)

    @staticmethod
    def _clean_text(value: Any) -> str:
        """Clean HTML and unnecessary whitespace."""
        if not value:
            return ""
        text = str(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def search_sap_authoritative(
        self,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Search the live web using Tavily.
        SAP Assistant only accepts authoritative SAP-domain
        results for its SAP web fallback.
        """
        if not settings.WEB_FALLBACK_ENABLED:
            return []

        if not self.client:
            return []

        try:
            response = self.client.search(
                query=f"SAP {query}",
                search_depth="advanced",
                max_results=5,
                include_answer=False,
                include_raw_content=False,
                include_domains=[
                    "help.sap.com",
                    "community.sap.com",
                    "blogs.sap.com",
                    "sap.com",
                ],
            )
        except Exception as exc:
            print(f"[Tavily] Web search failed: {exc}")
            return []

        results: List[Dict[str, Any]] = []

        for item in response.get("results", []):
            url = str(item.get("url", "")).strip()
            if not url:
                continue

            # Only accept SAP sources.
            if not self._is_sap_source(url):
                continue

            title = self._clean_text(item.get("title", ""))
            snippet = self._clean_text(item.get("content", ""))

            if not title:
                title = "SAP Official Documentation"

            if not snippet:
                snippet = "No preview available."

            domain = "sap.com"
            if "help.sap.com" in url.lower():
                domain = "help.sap.com"
            elif "community.sap.com" in url.lower():
                domain = "community.sap.com"
            elif "blogs.sap.com" in url.lower():
                domain = "blogs.sap.com"

            results.append(
                {
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "snippet": snippet,
                }
            )

        return results[:5]


web_search_service = WebSearchService()