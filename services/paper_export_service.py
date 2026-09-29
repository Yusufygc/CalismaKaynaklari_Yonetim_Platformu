import csv
import io
import re

from services.citation_service import CitationService

_CSV_COLUMNS = ("Title", "Authors", "Year", "Venue", "DOI", "URL", "Citations", "Open Access")
_BIBTEX_KEY = re.compile(r"^@article\{([^,]+),", re.MULTILINE)


def _metadata(paper: dict) -> dict:
    """Market sonucu (QML dict'i) -> `CitationService` metadata'si."""
    return {
        "authors": paper.get("authors") or [],
        "year": paper.get("year"),
        "venue": paper.get("venue") or "",
        "doi": paper.get("doi") or "",
    }


def _unique_key(key: str, used: set[str]) -> str:
    """Ayni yazar+yil+ilk kelime cakismasinda 'a', 'b', ... eki ekler."""
    candidate, suffix = key, 0
    while candidate in used:
        suffix += 1
        candidate = f"{key}{chr(ord('a') + (suffix - 1) % 26)}{'' if suffix <= 26 else suffix}"
    used.add(candidate)
    return candidate


class PaperExportService:
    """Arama sonucu / secili makale listelerini BibTeX ve CSV olarak disa aktarir (saf, dosyaya yazmaz)."""

    @staticmethod
    def bibtex(papers: list[dict]) -> str:
        used: set[str] = set()
        entries = []
        for paper in papers:
            entry = CitationService.format(paper.get("title") or "", _metadata(paper), "bibtex")
            match = _BIBTEX_KEY.search(entry)
            if match:
                key = _unique_key(match.group(1), used)
                entry = entry.replace(f"@article{{{match.group(1)},", f"@article{{{key},", 1)
            entries.append(entry)
        return "\n\n".join(entries) + ("\n" if entries else "")

    @staticmethod
    def csv(papers: list[dict]) -> str:
        """Excel'in Turkce karakterleri dogru acmasi icin cagiran tarafin `utf-8-sig` ile yazmasi onerilir."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(_CSV_COLUMNS)
        for paper in papers:
            writer.writerow(
                [
                    paper.get("title") or "",
                    "; ".join(paper.get("authors") or []),
                    paper.get("year") or "",
                    paper.get("venue") or "",
                    paper.get("doi") or "",
                    paper.get("url") or "",
                    paper.get("citationCount") or 0,
                    "yes" if paper.get("isOpenAccess") else "no",
                ]
            )
        return buffer.getvalue()
