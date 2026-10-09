#!/usr/bin/env python3
"""
Semantic Scholar Academic Graph Search & Citation Discovery Engine
Integrates the official Semantic Scholar API with authenticated rate limiting,
extracts TLDR summaries, citation impact metrics, and official BibTeX.

Style compliant with codebase: Python 3.10+, typing, argparse, zero emojis.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = "title,authors,year,citationCount,influentialCitationCount,tldr,abstract,citationStyles,openAccessPdf,externalIds,venue"


def load_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieve Semantic Scholar API key from CLI argument, env var, or .env file."""
    if explicit_key:
        return explicit_key

    env_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if env_key:
        return env_key

    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SEMANTIC_SCHOLAR_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


def get_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Build HTTP request headers including API key."""
    headers = {
        "User-Agent": "AdaptiveAgentMemoryResearch/1.0 (academic; +https://github.com)"
    }
    key = load_api_key(api_key)
    if key:
        headers["x-api-key"] = key
    return headers


LAST_REQUEST_TIME = 0.0


def s2_request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    max_retries: int = 3
) -> requests.Response:
    """Execute a rate-limited request against Semantic Scholar with backoff."""
    global LAST_REQUEST_TIME

    headers = get_headers(api_key)

    for attempt in range(max_retries):
        elapsed = time.time() - LAST_REQUEST_TIME
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)

        LAST_REQUEST_TIME = time.time()
        response = requests.get(url, headers=headers, params=params, timeout=20)

        if response.status_code == 429:
            backoff = 2.5 * (attempt + 1)
            print(f"Rate limit reached (429). Retrying in {backoff:.1f}s (attempt {attempt+1}/{max_retries})...", file=sys.stderr)
            time.sleep(backoff)
            continue

        response.raise_for_status()
        return response

    response.raise_for_status()
    return response


def search_semantic_scholar(
    query: str,
    limit: int = 5,
    year_range: Optional[str] = None,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search papers via Semantic Scholar Academic Graph API."""
    url = f"{BASE_URL}/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": DEFAULT_FIELDS
    }
    if year_range:
        params["year"] = year_range

    response = s2_request(url, params=params, api_key=api_key)
    data = response.json()
    return data.get("data", [])


def get_paper_details(
    paper_id: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch complete metadata for a specific paper by ID or ArXiv ID."""
    url = f"{BASE_URL}/paper/{paper_id}"
    params = {"fields": DEFAULT_FIELDS}

    response = s2_request(url, params=params, api_key=api_key)
    return response.json()


def get_paper_citations(
    paper_id: str,
    limit: int = 5,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve papers that cite the specified paper."""
    url = f"{BASE_URL}/paper/{paper_id}/citations"
    params = {
        "limit": limit,
        "fields": "title,authors,year,citationCount,venue"
    }
    response = s2_request(url, params=params, api_key=api_key)
    data = response.json()
    return [item.get("citingPaper", {}) for item in data.get("data", [])]


def format_clean_bibtex(paper: Dict[str, Any]) -> str:
    """Extract or construct a clean BibTeX entry for the paper."""
    styles = paper.get("citationStyles", {})
    if styles and styles.get("bibtex"):
        return styles["bibtex"].strip()

    # Fallback BibTeX construction
    authors = paper.get("authors", [])
    author_last = "Unknown"
    if authors:
        parts = authors[0].get("name", "").split()
        if parts:
            author_last = re.sub(r'[^a-zA-Z0-9]', '', parts[-1]).lower()

    year = paper.get("year", 2026)
    title = paper.get("title", "Untitled")
    words = re.findall(r'[a-zA-Z0-9]+', title.lower())
    substantive = words[0] if words else "paper"
    for w in words:
        if len(w) > 3 and w not in {"with", "from", "that", "this", "towards"}:
            substantive = w
            break

    cite_key = f"{author_last}{year}{substantive}"
    author_str = " and ".join(a.get("name", "") for a in authors)
    venue = paper.get("venue", "arXiv preprint")

    return f"@article{{{cite_key},\n  title={{{{{title}}}}},\n  author={{{author_str}}},\n  journal={{{venue}}},\n  year={{{year}}}\n}}"


def main():
    parser = argparse.ArgumentParser(
        description="Search academic papers, citation metrics, and BibTeX via Semantic Scholar."
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Search query keywords (e.g. 'agent memory negative transfer')"
    )
    parser.add_argument(
        "--paper-id",
        type=str,
        help="Specific paper ID, DOI, or ArXiv ID (e.g. 'ARXIV:2308.10144')"
    )
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=5,
        help="Maximum number of papers to retrieve (default: 5)"
    )
    parser.add_argument(
        "--year",
        type=str,
        help="Year range filter (e.g. '2023-2026' or '2024')"
    )
    parser.add_argument(
        "--citations",
        action="store_true",
        help="Fetch papers that cite this work (requires --paper-id)"
    )
    parser.add_argument(
        "--bibtex",
        action="store_true",
        help="Display BibTeX entries in terminal"
    )
    parser.add_argument(
        "--save-bibtex",
        type=str,
        default=None,
        help="Optional file path to append generated BibTeX entries (e.g. paper/references.bib)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Override Semantic Scholar API key"
    )

    args = parser.parse_args()

    active_key = load_api_key(args.api_key)
    auth_status = "Authenticated (Key Present)" if active_key else "Unauthenticated (Public Tier)"

    print("=" * 70)
    print("SEMANTIC SCHOLAR ACADEMIC GRAPH ENGINE")
    print(f"Status:       {auth_status}")
    if args.query:
        print(f"Query:        {args.query}")
    if args.paper_id:
        print(f"Paper ID:     {args.paper_id}")
    print(f"Max Results:  {args.max_results}")
    print("=" * 70)

    # Mode 1: Citations lookup for a specific paper
    if args.paper_id and args.citations:
        try:
            citing_papers = get_paper_citations(args.paper_id, limit=args.max_results, api_key=args.api_key)
            print(f"\nFound {len(citing_papers)} citing paper(s) for {args.paper_id}:\n")
            for idx, p in enumerate(citing_papers, 1):
                authors = ", ".join(a.get("name", "") for a in p.get("authors", [])[:3])
                print(f"[{idx}] {p.get('title')}")
                print(f"    Authors:   {authors} ({p.get('year', 'N/A')})")
                print(f"    Citations: {p.get('citationCount', 0)}")
                print(f"    Venue:     {p.get('venue', 'N/A')}")
                print("-" * 70)
            return
        except Exception as e:
            print(f"Error fetching citations: {e}", file=sys.stderr)
            sys.exit(1)

    # Mode 2: Specific paper details lookup
    if args.paper_id and not args.query:
        try:
            paper = get_paper_details(args.paper_id, api_key=args.api_key)
            papers = [paper]
        except Exception as e:
            print(f"Error fetching paper {args.paper_id}: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.query:
        try:
            papers = search_semantic_scholar(
                query=args.query,
                limit=args.max_results,
                year_range=args.year,
                api_key=args.api_key
            )
        except Exception as e:
            print(f"Error searching Semantic Scholar: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Please provide either --query or --paper-id.", file=sys.stderr)
        sys.exit(1)

    if not papers:
        print("No papers matched the query.")
        return

    print(f"\nRetrieved {len(papers)} paper(s):\n")
    bibtex_entries = []

    for idx, p in enumerate(papers, 1):
        year = p.get("year", "N/A")
        authors = ", ".join(a.get("name", "") for a in p.get("authors", [])[:3])
        if len(p.get("authors", [])) > 3:
            authors += " et al."

        citations = p.get("citationCount", 0)
        influential = p.get("influentialCitationCount", 0)
        venue = p.get("venue", "N/A")
        tldr_obj = p.get("tldr")
        tldr_text = tldr_obj.get("text") if isinstance(tldr_obj, dict) else None

        ext_ids = p.get("externalIds", {})
        arxiv_id = ext_ids.get("ArXiv", "N/A") if ext_ids else "N/A"
        doi = ext_ids.get("DOI", "N/A") if ext_ids else "N/A"

        print(f"[{idx}] {p.get('title')}")
        print(f"    Authors:     {authors} ({year})")
        print(f"    Venue:       {venue} | ArXiv: {arxiv_id} | DOI: {doi}")
        print(f"    Impact:      {citations} total citations ({influential} highly influential)")
        
        if tldr_text:
            print(f"    TLDR:        {tldr_text}")
        elif p.get("abstract"):
            clean_abs = re.sub(r'\s+', ' ', p['abstract'])[:200]
            print(f"    Abstract:    {clean_abs}...")

        pdf_info = p.get("openAccessPdf")
        if pdf_info and pdf_info.get("url"):
            print(f"    Open Access: {pdf_info['url']}")

        bib = format_clean_bibtex(p)
        bibtex_entries.append(bib)
        print("-" * 70)

    if args.bibtex:
        print("\n" + "=" * 70)
        print("BIBTEX CITATIONS")
        print("=" * 70)
        for b in bibtex_entries:
            print(b)
            print()

    if args.save_bibtex:
        target_path = Path(args.save_bibtex)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as f:
            f.write("\n\n% --- Automatically Added via fetch_semanticscholar_literature.py ---\n")
            for b in bibtex_entries:
                f.write(b + "\n\n")
        print(f"Appended {len(bibtex_entries)} BibTeX entries to {target_path}")


if __name__ == "__main__":
    main()
