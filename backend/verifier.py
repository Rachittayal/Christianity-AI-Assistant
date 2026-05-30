import re
from bible_db import get_verse, resolve_book_name, verse_exists


REFERENCE_PATTERN = re.compile(
    r'\b((?:[1-3]|I{1,3})\s)?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(\d+):(\d+)(?:-\d+)?\b'
)


def extract_references(text: str) -> list[dict]:
    references = []

    for match in REFERENCE_PATTERN.finditer(text):
        prefix  = (match.group(1) or "").strip()   
        book    = match.group(2).strip()            
        chapter = int(match.group(3))
        verse   = int(match.group(4))

        full_book = f"{prefix} {book}".strip() if prefix else book

        references.append({
            "raw":     match.group(0),   
            "book":    full_book,
            "chapter": chapter,
            "verse":   verse,
        })

    return references


def verify_reference(ref: dict, translation: str = "KJV") -> dict:

    canonical_book = resolve_book_name(translation, ref["book"])
    if canonical_book is None:
        return {
            "status":  "flagged",
            "raw":     ref["raw"],
            "message": (
                f"'{ref['book']}' is not a recognized book of the Bible. "
                f"This reference may be inaccurate."
            ),
            "verse": None
        }

    verse_data = get_verse(translation, canonical_book, ref["chapter"], ref["verse"])

    if verse_data is None:
        # Book is real but this chapter/verse does not exist
        return {
            "status":  "flagged",
            "raw":     ref["raw"],
            "message": (
                f"'{ref['raw']}' — the book of {canonical_book} exists, "
                f"but chapter {ref['chapter']} verse {ref['verse']} was not found. "
                f"Please verify this reference."
            ),
            "verse": None
        }

    return {
        "status":  "verified",
        "raw":     ref["raw"],
        "message": "Verified",
        "verse":   verse_data
    }


def verify_text(text: str, translation: str = "KJV") -> dict:

    references = extract_references(text)

    if not references:
        return {
            "all_verified":   True,
            "results":        [],
            "flagged":        [],
            "verified_count": 0,
            "flagged_count":  0,
        }

    results = [verify_reference(ref, translation) for ref in references]

    flagged  = [r for r in results if r["status"] == "flagged"]
    verified = [r for r in results if r["status"] == "verified"]

    return {
        "all_verified":   len(flagged) == 0,
        "results":        results,
        "flagged":        flagged,
        "verified_count": len(verified),
        "flagged_count":  len(flagged),
    }


def build_warning_note(flagged: list[dict]) -> str:
    
    if not flagged:
        return ""

    lines = ["\n\n⚠️ **Scripture Reference Notice:**"]
    for item in flagged:
        lines.append(f"- {item['message']}")
    lines.append(
        "_Please verify these references independently "
        "using a Bible concordance or trusted Bible website._"
    )

    return "\n".join(lines)