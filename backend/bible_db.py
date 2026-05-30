import os
import sqlite3
import json
import requests


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
DB_PATH   = os.path.join(DATA_DIR, "bible.db")

KJV_JSON_PATH = os.path.join(DATA_DIR, "KJV.json")
BSB_JSON_PATH = os.path.join(DATA_DIR, "BSB.json")

KJV_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/KJV.json"
BSB_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/BSB.json"


SUPPORTED_TRANSLATIONS = ["KJV", "BSB"]

def download_file(url: str, dest: str) -> None:
    if os.path.exists(dest):
        print(f"[bible_db] Already exists: {dest}")
        return

    print(f"[bible_db] Downloading {url} ...")
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    with open(dest, "wb") as f:
        f.write(resp.content)

    print(f"[bible_db] Saved to {dest}")


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT    NOT NULL,
            book        TEXT    NOT NULL,
            chapter     INTEGER NOT NULL,
            verse       INTEGER NOT NULL,
            text        TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_verse_lookup
        ON verses (translation, book, chapter, verse)
    """)
    conn.commit()


def load_json_translation(conn: sqlite3.Connection, json_path: str, translation_key: str) -> None:
    cur = conn.execute(
        "SELECT COUNT(*) FROM verses WHERE translation = ?",
        (translation_key,)
    )
    if cur.fetchone()[0] > 0:
        print(f"[bible_db] {translation_key} already loaded — skipping.")
        return

    print(f"[bible_db] Loading {translation_key} from {json_path} ...")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for book in data["books"]:
        book_name = book["name"]
        for chapter_obj in book["chapters"]:
            chapter_num = chapter_obj["chapter"]
            for verse_obj in chapter_obj["verses"]:
                rows.append((
                    translation_key,       # always UPPERCASE
                    book_name,
                    chapter_num,
                    verse_obj["verse"],
                    verse_obj["text"].strip()
                ))

    conn.executemany(
        "INSERT INTO verses (translation, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"[bible_db] Loaded {len(rows)} verses for {translation_key}.")


def setup() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    download_file(KJV_URL, KJV_JSON_PATH)
    download_file(BSB_URL, BSB_JSON_PATH)

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    load_json_translation(conn, KJV_JSON_PATH, "KJV")
    load_json_translation(conn, BSB_JSON_PATH, "BSB")
    conn.close()

    print("[bible_db] Setup complete.")

def get_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            "[bible_db] Database not found. Run bible_db.setup() first."
        )
    return sqlite3.connect(DB_PATH)

def get_verse(translation: str, book: str, chapter: int, verse: int) -> dict | None:
    t = translation.upper()   # always uppercase to match stored data
    conn = get_connection()

    try:
        cur = conn.execute(
            """SELECT book, chapter, verse, text
               FROM verses
               WHERE translation = ? AND book = ? AND chapter = ? AND verse = ?""",
            (t, book, chapter, verse)
        )
        row = cur.fetchone()

        if row is None:
            return None

        return {
            "book":      row[0],
            "chapter":   row[1],
            "verse":     row[2],
            "text":      row[3],
            "reference": f"{row[0]} {row[1]}:{row[2]}"
        }
    finally:
        conn.close()


def verse_exists(book: str, chapter: int, verse: int) -> bool:
    return get_verse("KJV", book, chapter, verse) is not None


def get_book_list(translation: str) -> list[str]:
    t = translation.upper()
    conn = get_connection()

    try:
        cur = conn.execute(
            """SELECT book FROM verses
               WHERE translation = ?
               GROUP BY book
               ORDER BY MIN(id)""",
            (t,)
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

ARABIC_TO_ROMAN = {
    "1 ": "I ",
    "2 ": "II ",
    "3 ": "III ",
}

def normalize_book_name(user_input: str) -> str:

    text = user_input.strip()
    for arabic, roman in ARABIC_TO_ROMAN.items():
        if text.startswith(arabic):
            return roman + text[len(arabic):]
    return text

def resolve_book_name(translation: str, user_input: str) -> str | None:
    books = get_book_list(translation)

    normalized = normalize_book_name(user_input.strip())
    target = normalized.lower()

    for book in books:
        if book.lower() == target:
            return book

    for book in books:
        if book.lower().startswith(target):
            return book

    return None


def search_verses(translation: str, query: str, limit: int = 10) -> list[dict]:
    
    t = translation.upper()
    conn = get_connection()

    try:
        cur = conn.execute(
            """SELECT book, chapter, verse, text
               FROM verses
               WHERE translation = ? AND text LIKE ?
               LIMIT ?""",
            (t, f"%{query}%", limit)
        )
        return [
            {
                "book":      row[0],
                "chapter":   row[1],
                "verse":     row[2],
                "text":      row[3],
                "reference": f"{row[0]} {row[1]}:{row[2]}"
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()


def get_all_verses(translation: str) -> list[dict]:
    t = translation.upper()
    conn = get_connection()

    try:
        cur = conn.execute(
            """SELECT book, chapter, verse, text
               FROM verses
               WHERE translation = ?
               ORDER BY id""",
            (t,)
        )
        return [
            {
                "book":      row[0],
                "chapter":   row[1],
                "verse":     row[2],
                "text":      row[3],
                "reference": f"{row[0]} {row[1]}:{row[2]}"
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()