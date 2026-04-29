from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from crm_service import list_companies
from website_ai_service import WebsiteAnalysisError, analyze_company_website, normalize_url


class CompanyDiscoveryError(RuntimeError):
    pass


BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "xing.com",
    "immobilienscout24.de",
    "immowelt.de",
    "immonet.de",
    "gelbeseiten.de",
    "11880.com",
    "meinestadt.de",
    "firma-online.org",
    "northdata.de",
}


def _domain(url: str) -> str:
    try:
        parsed = urlparse(normalize_url(url))
    except Exception:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_blocked_domain(domain: str) -> bool:
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in BLOCKED_DOMAINS)


def _existing_domains() -> set[str]:
    domains: set[str] = set()
    for company in list_companies():
        domain = _domain(str(company.get("website") or ""))
        if domain:
            domains.add(domain)
    return domains


def _search_web(query: str, max_results: int) -> list[dict[str, str]]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise CompanyDiscoveryError(
            "Für die Unternehmenssuche fehlt das Paket ddgs. Bitte requirements.txt installieren."
        ) from exc

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="de-de", safesearch="moderate", max_results=max_results))
    except Exception as exc:
        raise CompanyDiscoveryError(f"Websuche fehlgeschlagen: {exc}") from exc

    normalized: list[dict[str, str]] = []
    for result in results:
        href = str(result.get("href") or result.get("url") or "").strip()
        if not href:
            continue
        normalized.append(
            {
                "title": str(result.get("title") or "").strip(),
                "url": href,
                "snippet": str(result.get("body") or result.get("snippet") or "").strip(),
            }
        )
    return normalized


def discover_company_candidates(
    location: str,
    radius_km: int,
    max_candidates: int = 5,
) -> list[dict[str, Any]]:
    location = location.strip()
    if not location:
        raise CompanyDiscoveryError("Bitte einen Ort oder eine Region eintragen.")
    if radius_km <= 0:
        raise CompanyDiscoveryError("Der Umkreis muss größer als 0 sein.")

    existing_domains = _existing_domains()
    queries = [
        f"Hausverwaltung Immobilienverwaltung WEG Verwaltung {location} Umkreis {radius_km} km",
        f"Property Management Hausverwaltung Betriebskostenabrechnung {location}",
        f"Immobilienverwaltung Objektverwaltung Buchhaltung {location}",
    ]

    raw_results: list[dict[str, str]] = []
    for query in queries:
        raw_results.extend(_search_web(query, max_results=max_candidates * 3))

    candidates: list[dict[str, Any]] = []
    seen_domains: set[str] = set()

    for result in raw_results:
        domain = _domain(result["url"])
        if not domain or domain in seen_domains or domain in existing_domains or _is_blocked_domain(domain):
            continue

        seen_domains.add(domain)
        candidate: dict[str, Any] = {
            "title": result["title"],
            "website": result["url"],
            "domain": domain,
            "snippet": result["snippet"],
            "analysis": {},
            "error": "",
        }

        try:
            analysis = analyze_company_website(result["url"])
            candidate["analysis"] = analysis
            candidate["website"] = analysis.get("website") or result["url"]
            candidate["title"] = analysis.get("company_name") or result["title"]
        except WebsiteAnalysisError as exc:
            candidate["error"] = str(exc)

        candidates.append(candidate)
        if len(candidates) >= max_candidates:
            break

    return candidates
