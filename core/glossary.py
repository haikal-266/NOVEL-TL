"""
Glossary & Continuous Learning Manager for Novel Translation.
Persistently stores and accumulates terms, character names, and author-intended
ateji (ruby text) across all scraped and translated novels in SQLite.
"""

import os
import re
import sqlite3
import datetime
from typing import Dict, List, Tuple, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "glossary.db")

# Regex to detect Katakana strings (including prolonged sound mark ー)
KATAKANA_RE = re.compile(r"^[\u30A0-\u30FFー]+$")

# Common ateji loanword readings or proper nouns
RUBY_TAG_RE = re.compile(
    r"<ruby>(?P<base>[^<]+)(?:<rp>[^<]*</rp>)?<rt>(?P<reading>[^<]+)</rt>(?:<rp>[^<]*</rp>)?</ruby>",
    re.IGNORECASE | re.DOTALL
)


class GlossaryManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS terms (
                    term_ja TEXT PRIMARY KEY,
                    term_en TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    source_work_id TEXT,
                    occurrences INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS work_terms (
                    work_id TEXT,
                    term_ja TEXT,
                    term_en TEXT,
                    category TEXT DEFAULT 'general',
                    PRIMARY KEY (work_id, term_ja)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS character_genders (
                    name_ja TEXT PRIMARY KEY,
                    gender TEXT NOT NULL,
                    work_id TEXT,
                    created_at TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_work_terms_work ON work_terms(work_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_char_genders_work ON character_genders(work_id)")

            # Seed default known characters
            default_chars = [
                ("レティーナ", "FEMALE", "n2800hm"),
                ("クルーゼス", "MALE", "n2800hm"),
                ("ノール", "MALE", "n6287ep"),
                ("リーン", "FEMALE", "n6287ep"),
                ("イネス", "FEMALE", "n6287ep"),
                ("デナ", "FEMALE", "n8611bv"),
                ("ロツェ", "FEMALE", "n8611bv"),
                ("アネット", "FEMALE", "n8611bv"),
                ("修司", "MALE", "n8611bv"),
                ("エルブラス", "MALE", "n8611bv"),
            ]
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for name, gender, wid in default_chars:
                cur.execute("""
                    INSERT OR IGNORE INTO character_genders (name_ja, gender, work_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (name, gender, wid, now))

            conn.commit()

    def harvest_ruby_ateji(self, html: str, work_id: str = "") -> List[Tuple[str, str]]:
        """
        Extract ateji ruby pairs from chapter HTML where author intended Katakana reading.
        E.g. <ruby>聖騎士<rt>パラディン</rt></ruby> -> ('聖騎士', 'パラディン')
        """
        if not html or "<ruby>" not in html:
            return []

        harvested = []
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for match in RUBY_TAG_RE.finditer(html):
            base = re.sub(r"<[^>]+>", "", match.group("base")).strip()
            reading = re.sub(r"<[^>]+>", "", match.group("reading")).strip()

            # We focus on Ateji: Kanji base with Katakana reading (e.g. 聖騎士 -> パラディン)
            if not base or not reading:
                continue

            # Check if reading is pure Katakana or Latin loanword
            is_katakana = bool(KATAKANA_RE.match(reading))
            is_latin = bool(re.match(r"^[A-Za-z0-9\s\-]+$", reading))

            if (is_katakana and len(reading) >= 2) or is_latin:
                harvested.append((base, reading))

        if harvested:
            with self._get_connection() as conn:
                cur = conn.cursor()
                for base, reading in harvested:
                    cur.execute("""
                        INSERT INTO terms (term_ja, term_en, category, source_work_id, occurrences, created_at, updated_at)
                        VALUES (?, ?, 'ateji', ?, 1, ?, ?)
                        ON CONFLICT(term_ja) DO UPDATE SET
                            occurrences = occurrences + 1,
                            updated_at = excluded.updated_at
                    """, (base, reading, work_id, now, now))

                    if work_id:
                        cur.execute("""
                            INSERT OR REPLACE INTO work_terms (work_id, term_ja, term_en, category)
                            VALUES (?, ?, ?, 'ateji')
                        """, (work_id, base, reading))
                conn.commit()

        return harvested

    def substitute_ruby_in_html(self, html: str) -> str:
        """
        Transform ateji ruby tags into their Katakana readings before text extraction,
        so the NMT model translates the author-intended loanword (e.g. パラディン -> Paladin)
        instead of translating the literal kanji.
        """
        if not html or "<ruby>" not in html:
            return html

        def replace_ruby(m):
            base = re.sub(r"<[^>]+>", "", m.group("base")).strip()
            reading = re.sub(r"<[^>]+>", "", m.group("reading")).strip()
            if KATAKANA_RE.match(reading) and len(reading) >= 2 and re.search(r"[\u4e00-\u9fff]", base):
                # Ateji: replace kanji with katakana reading
                return reading
            # Standard furigana: keep base
            return base

        return RUBY_TAG_RE.sub(replace_ruby, html)

    def add_term(self, term_ja: str, term_en: str, category: str = "custom", work_id: str = "") -> None:
        """Add or update a specific term in the persistent glossary."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO terms (term_ja, term_en, category, source_work_id, occurrences, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(term_ja) DO UPDATE SET
                    term_en = excluded.term_en,
                    category = excluded.category,
                    updated_at = excluded.updated_at
            """, (term_ja.strip(), term_en.strip(), category, work_id, now, now))
            if work_id:
                cur.execute("""
                    INSERT OR REPLACE INTO work_terms (work_id, term_ja, term_en, category)
                    VALUES (?, ?, ?, ?)
                """, (work_id, term_ja.strip(), term_en.strip(), category))
            conn.commit()

    def get_terms(self, work_id: str = "") -> Dict[str, str]:
        """Fetch all active glossary terms (work-specific overriding global)."""
        terms: Dict[str, str] = {}
        with self._get_connection() as conn:
            cur = conn.cursor()
            # 1. Global terms
            cur.execute("SELECT term_ja, term_en FROM terms")
            for row in cur.fetchall():
                terms[row["term_ja"]] = row["term_en"]

            # 2. Work-specific terms
            if work_id:
                cur.execute("SELECT term_ja, term_en FROM work_terms WHERE work_id = ?", (work_id,))
                for row in cur.fetchall():
                    terms[row["term_ja"]] = row["term_en"]

        return terms

    def apply_post_glossary(self, text: str, work_id: str = "") -> str:
        """Apply glossary substitutions to the English output."""
        if not text:
            return ""
        terms = self.get_terms(work_id)
        if not terms:
            return text

        # Sort by length descending to replace longest phrases first
        for ja_k, en_v in sorted(terms.items(), key=lambda x: len(x[0]), reverse=True):
            if ja_k in text:
                text = text.replace(ja_k, en_v)

        return text

    def set_character_gender(self, name_ja: str, gender: str, work_id: str = "") -> None:
        """Register or update a character's gender ('FEMALE' or 'MALE')."""
        gender = gender.upper().strip()
        if gender not in ("FEMALE", "MALE"):
            raise ValueError(f"Invalid gender '{gender}'. Must be 'FEMALE' or 'MALE'.")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO character_genders (name_ja, gender, work_id, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name_ja) DO UPDATE SET
                    gender = excluded.gender,
                    work_id = CASE WHEN excluded.work_id != '' THEN excluded.work_id ELSE character_genders.work_id END
            """, (name_ja.strip(), gender, work_id, now))
            conn.commit()

    def get_character_genders(self, work_id: str = "") -> Dict[str, str]:
        """Fetch all registered character genders (work-specific prioritized)."""
        genders: Dict[str, str] = {}
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name_ja, gender, work_id FROM character_genders")
            rows = cur.fetchall()
            # General/fallback first
            for r in rows:
                if not r["work_id"]:
                    genders[r["name_ja"]] = r["gender"]
            # Work specific overrides
            if work_id:
                for r in rows:
                    if r["work_id"] == work_id:
                        genders[r["name_ja"]] = r["gender"]
            else:
                for r in rows:
                    genders[r["name_ja"]] = r["gender"]
        return genders

    def get_stats(self) -> Dict[str, int]:
        """Return total terms and ateji accumulated."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM terms")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM terms WHERE category = 'ateji'")
            ateji = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT work_id) FROM work_terms")
            works = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM character_genders")
            chars = cur.fetchone()[0]
            return {
                "total_terms": total,
                "ateji_terms": ateji,
                "novels_indexed": works,
                "characters_registered": chars
            }


# Singleton instance
_glossary_instance: Optional[GlossaryManager] = None

def get_glossary_manager() -> GlossaryManager:
    global _glossary_instance
    if _glossary_instance is None:
        _glossary_instance = GlossaryManager()
    return _glossary_instance

