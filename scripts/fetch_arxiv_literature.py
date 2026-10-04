#!/usr/bin/env python3
"""
Automated ArXiv Literature Search, Download, and Analysis Engine
Retrieves academic research papers via the official ArXiv API,
formats IEEE/BibTeX citations, downloads PDFs, and extracts full text.

Style compliant with codebase: Python 3.10+, typing, argparse, zero emojis.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import arxiv
import pymupdf
import requests


def sanitize_filename(name: str, max_len: int = 60) -> str:
    """Sanitize string for safe filesystem usage."""
    clean = re.sub(r'[^a-zA-Z0-9_\- ]', '', name)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    return clean[:max_len]


def generate_bibtex_key(result: arxiv.Result) -> str:
    """Generate a standard AuthorYearFirstWord BibTeX key."""
    author_last = "Unknown"
    if result.authors:
        parts = result.authors[0].name.strip().split()
        if parts:
            author_last = sanitize_filename(parts[-1]).lower()
    
    year = result.published.year if result.published else 2026
    
    # First substantive word in title (ignore stopwords)
    stopwords = {"a", "an", "the", "on", "in", "for", "and", "of", "to", "with", "towards", "via"}
    title_words = re.findall(r'[a-zA-Z0-9]+', result.title.lower())
    first_substantive = "paper"
    for w in title_words:
        if w not in stopwords and len(w) > 2:
            first_substantive = w
            break

    return f"{author_last}{year}{first_substantive}"


def format_bibtex(result: arxiv.Result) -> str:
    """Format an ArXiv result as an IEEE-compliant BibTeX entry."""
    key = generate_bibtex_key(result)
    arxiv_id = result.get_short_id()
    authors_str = " and ".join(a.name for a in result.authors)
    year = result.published.year if result.published else 2026
    clean_title = re.sub(r'\s+', ' ', result.title).strip()

    bib = [
        f"@article{{{key},",
        f"  title={{{{{clean_title}}}}},",
        f"  author={{{authors_str}}},",
        f"  journal={{arXiv preprint arXiv:{arxiv_id}}},",
        f"  year={{{year}}},",
        f"  eprint={{{arxiv_id}}},",
        f"  archivePrefix={{arXiv}},",
        f"  primaryClass={{{result.primary_category}}}",
        "}"
    ]
    return "\n".join(bib)


def search_arxiv_papers(
    query: str,
    max_results: int = 5,
    sort_criterion: str = "relevance"
) -> List[arxiv.Result]:
    """Execute search against official ArXiv API."""
    sort_map = {
        "relevance": arxiv.SortCriterion.Relevance,
        "submitted_date": arxiv.SortCriterion.SubmittedDate,
        "updated_date": arxiv.SortCriterion.LastUpdatedDate,
    }
    selected_sort = sort_map.get(sort_criterion, arxiv.SortCriterion.Relevance)

    client = arxiv.Client(
        page_size=max_results,
        delay_seconds=1.0,
        num_retries=3
    )

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=selected_sort,
        sort_order=arxiv.SortOrder.Descending
    )

    results = list(client.results(search))
    return results


def download_paper(result: arxiv.Result, output_dir: Path) -> Path:
    """Download PDF file of the ArXiv paper via HTTP stream."""
    output_dir.mkdir(parents=True, exist_ok=True)
    short_id = result.get_short_id().replace("/", "_")
    title_slug = sanitize_filename(result.title, max_len=40)
    filename = f"{short_id}_{title_slug}.pdf"
    target_path = output_dir / filename

    if target_path.exists() and target_path.stat().st_size > 1024:
        return target_path

    headers = {"User-Agent": "AdaptiveAgentMemoryResearch/1.0 (academic; +https://arxiv.org)"}
    pdf_url = result.pdf_url
    if not pdf_url.endswith(".pdf"):
        pdf_url = f"{pdf_url}.pdf"

    resp = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()

    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    return target_path


def extract_pdf_sections(pdf_path: Path, max_pages: int = 3) -> Dict[str, Any]:
    """Extract metadata and text from the leading pages of a PDF."""
    if not pdf_path.exists():
        return {"error": f"File {pdf_path} not found"}

    doc = pymupdf.open(str(pdf_path))
    num_pages = len(doc)
    extracted_text = []

    pages_to_read = min(num_pages, max_pages)
    for p_idx in range(pages_to_read):
        page = doc[p_idx]
        extracted_text.append(page.get_text())

    full_sample = "\n--- [PAGE BREAK] ---\n".join(extracted_text)
    
    # Basic section heuristic extraction
    abstract_match = re.search(r'Abstract[—:\s](.*?)(?:1\s+Introduction|Categories|Keywords)', full_sample, re.DOTALL | re.IGNORECASE)
    abstract_text = abstract_match.group(1).strip() if abstract_match else ""

    doc.close()
    return {
        "num_pages": num_pages,
        "pages_sampled": pages_to_read,
        "abstract_extracted": abstract_text[:1000],
        "sample_text": full_sample[:3000]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search, download, and extract ArXiv research papers."
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        required=True,
        help="Search query string (e.g. 'agent memory negative transfer')"
    )
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=5,
        help="Maximum number of papers to retrieve (default: 5)"
    )
    parser.add_argument(
        "--sort",
        type=str,
        choices=["relevance", "submitted_date", "updated_date"],
        default="relevance",
        help="Sorting criterion (default: relevance)"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download PDF files for all retrieved papers"
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract text from downloaded PDFs using PyMuPDF"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="research_papers",
        help="Directory to save downloaded PDFs (default: research_papers)"
    )
    parser.add_argument(
        "--bibtex",
        action="store_true",
        help="Display generated BibTeX entries in terminal"
    )
    parser.add_argument(
        "--save-bibtex",
        type=str,
        default=None,
        help="Optional file path to append generated BibTeX entries (e.g. paper/references.bib)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("ARXIV LITERATURE SEARCH ENGINE")
    print(f"Query:        {args.query}")
    print(f"Max Results:  {args.max_results}")
    print(f"Sort Order:   {args.sort}")
    print(f"Output Dir:   {args.output_dir}")
    print("=" * 70)

    try:
        results = search_arxiv_papers(
            query=args.query,
            max_results=args.max_results,
            sort_criterion=args.sort
        )
    except Exception as e:
        print(f"Error querying ArXiv API: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("No papers matched the query.")
        return

    print(f"\nRetrieved {len(results)} paper(s):\n")

    out_dir = Path(args.output_dir)
    bibtex_entries = []

    for idx, r in enumerate(results, 1):
        arxiv_id = r.get_short_id()
        year = r.published.year if r.published else "N/A"
        authors = ", ".join(a.name for a in r.authors[:3])
        if len(r.authors) > 3:
            authors += " et al."

        print(f"[{idx}] {r.title}")
        print(f"    Authors:   {authors} ({year})")
        print(f"    ArXiv ID:  {arxiv_id} [Primary: {r.primary_category}]")
        print(f"    PDF URL:   {r.pdf_url}")
        print(f"    Published: {r.published.strftime('%Y-%m-%d') if r.published else 'N/A'}")
        
        # Format BibTeX
        bib_entry = format_bibtex(r)
        bibtex_entries.append(bib_entry)

        # Download PDF if requested
        if args.download or args.extract:
            print(f"    Downloading PDF to {out_dir}...")
            pdf_path = download_paper(r, out_dir)
            print(f"    Downloaded: {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")

            if args.extract:
                info = extract_pdf_sections(pdf_path, max_pages=2)
                print(f"    Total Pages: {info.get('num_pages')}")
                if info.get("abstract_extracted"):
                    clean_abs = re.sub(r'\s+', ' ', info['abstract_extracted'])[:250]
                    print(f"    Abstract Snippet: {clean_abs}...")

        print("-" * 70)

    if args.bibtex:
        print("\n" + "=" * 70)
        print("GENERATED BIBTEX ENTRIES")
        print("=" * 70)
        for b in bibtex_entries:
            print(b)
            print()

    if args.save_bibtex:
        target_bib = Path(args.save_bibtex)
        target_bib.parent.mkdir(parents=True, exist_ok=True)
        with open(target_bib, "a", encoding="utf-8") as f:
            f.write("\n\n% --- Automatically Added via fetch_arxiv_literature.py ---\n")
            for b in bibtex_entries:
                f.write(b + "\n\n")
        print(f"Appended {len(bibtex_entries)} BibTeX entries to {target_bib}")


if __name__ == "__main__":
    main()
