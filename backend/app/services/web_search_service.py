# import re
# import urllib.parse
# from typing import List, Dict, Any
# import httpx
# from backend.app.config import settings

# SAP_AUTHORITATIVE_FALLBACKS: List[Dict[str, Any]] = [
#     {
#         "keywords": ["ariba", "procurement cloud", "supplier lifecycle", "sourcing"],
#         "title": "SAP Ariba Strategic Sourcing and Procurement Overview",
#         "url": "https://help.sap.com/docs/ARIBA_SOURCING/overview",
#         "domain": "help.sap.com",
#         "snippet": "SAP Ariba provides cloud-based procurement, spend management, and supply chain collaboration solutions. It integrates with SAP S/4HANA via Cloud Integration Gateway (CIG) to exchange purchase orders, contracts, and invoices electronically."
#     },
#     {
#         "keywords": ["successfactors", "employee central", "hr cloud", "ec"],
#         "title": "SAP SuccessFactors Employee Central Administration Guide",
#         "url": "https://help.sap.com/docs/SAP_SUCCESSFACTORS_EMPLOYEE_CENTRAL",
#         "domain": "help.sap.com",
#         "snippet": "SAP SuccessFactors Employee Central is the core cloud HR system for global workforce management, organizational structures, time management, and payroll integration with SAP ERP HCM."
#     },
#     {
#         "keywords": ["btp", "business technology platform", "extension suite", "cap", "rap"],
#         "title": "SAP Business Technology Platform (BTP) Architecture Guide",
#         "url": "https://help.sap.com/docs/BTP/architecture-overview",
#         "domain": "help.sap.com",
#         "snippet": "SAP Business Technology Platform (SAP BTP) brings together application development, data and analytics, integration, and AI capabilities. It supports SAP Cloud Application Programming Model (CAP) and ABAP RESTful Application Programming Model (RAP)."
#     },
#     {
#         "keywords": ["rise with sap", "s/4hana cloud", "cloud transformation", "clean core"],
#         "title": "RISE with SAP S/4HANA Cloud Implementation Guide",
#         "url": "https://help.sap.com/docs/SAP_S4HANA_CLOUD/implementation-framework",
#         "domain": "help.sap.com",
#         "snippet": "RISE with SAP offers business-transformation-as-a-service, guiding organizations to SAP S/4HANA Cloud with continuous innovations, cloud ERP infrastructure, and clean core extension methodologies."
#     },
#     {
#         "keywords": ["concur", "travel", "expense"],
#         "title": "SAP Concur Expense and Travel Integration with S/4HANA",
#         "url": "https://help.sap.com/docs/CONCUR_INTEGRATION",
#         "domain": "help.sap.com",
#         "snippet": "SAP Concur automates travel booking and expense reporting. Integration with SAP ERP and SAP S/4HANA automatically posts financial journal entries for employee expense reimbursements."
#     }
# ]

# class WebSearchService:
#     def __init__(self):
#         self.client = httpx.Client(timeout=6.0, headers={"User-Agent": "SAP-Knowledge-Assistant/1.0"})

#     def search_sap_authoritative(self, query: str) -> List[Dict[str, Any]]:
#         """
#         Searches authoritative SAP resources (help.sap.com, community.sap.com).
#         Uses live search if possible, with authoritative SAP Help Portal repository fallback.
#         """
#         query_lower = query.lower()
#         results: List[Dict[str, Any]] = []

#         # Try live search if web fallback is enabled
#         try:
#             encoded = urllib.parse.quote(f"site:help.sap.com {query}")
#             url = f"https://html.duckduckgo.com/html/?q={encoded}"
#             resp = self.client.get(url)
#             if resp.status_code == 200:
#                 # Extract results from HTML
#                 matches = re.findall(
#                     r'<a class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
#                     resp.text,
#                     re.IGNORECASE | re.DOTALL
#                 )
#                 for link, raw_snippet in matches[:3]:
#                     # Clean snippet text
#                     snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
#                     # Filter for SAP domains
#                     if "sap.com" in link:
#                         domain = "help.sap.com" if "help.sap.com" in link else "community.sap.com"
#                         results.append({
#                             "title": f"SAP Official Help Documentation: {query[:40]}",
#                             "url": link,
#                             "domain": domain,
#                             "snippet": snippet
#                         })
#         except Exception:
#             pass

#         # If live search returned no authoritative SAP links, check curated authoritative SAP Help Portal articles
#         if not results:
#             for item in SAP_AUTHORITATIVE_FALLBACKS:
#                 if any(kw in query_lower for kw in item["keywords"]):
#                     results.append({
#                         "title": item["title"],
#                         "url": item["url"],
#                         "domain": item["domain"],
#                         "snippet": item["snippet"]
#                     })

#         # If still empty but clearly an SAP query, construct an authoritative SAP Help Portal reference
#         if not results:
#             clean_term = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
#             results.append({
#                 "title": f"SAP Help Portal — Reference Guide for {clean_term[:45]}",
#                 "url": f"https://help.sap.com/docs/search?q={urllib.parse.quote(clean_term)}",
#                 "domain": "help.sap.com",
#                 "snippet": f"Official SAP documentation, configuration steps, and best practices for {clean_term} available through the SAP Help Portal."
#             })

#         return results

# web_search_service = WebSearchService()


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

        return any(
            domain in url_lower
            for domain in allowed_domains
        )

    @staticmethod
    def _clean_text(value: Any) -> str:
        """Clean HTML and unnecessary whitespace."""

        if not value:
            return ""

        text = str(value)

        text = re.sub(
            r"<[^>]+>",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

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
            print(
                f"[Tavily] Web search failed: {exc}"
            )
            return []

        results: List[Dict[str, Any]] = []

        for item in response.get("results", []):
            url = str(
                item.get("url", "")
            ).strip()

            if not url:
                continue

            # Only accept SAP sources.
            if not self._is_sap_source(url):
                continue

            title = self._clean_text(
                item.get("title", "")
            )

            snippet = self._clean_text(
                item.get("content", "")
            )

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