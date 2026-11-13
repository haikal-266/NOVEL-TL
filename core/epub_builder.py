"""
EPUB Builder Module
Creates clean, beautifully formatted EPUB books from translated novel chapters.
Supports Translated-only, Bilingual (JA + Translation), and Raw modes.
"""

import os
import re
import html
from typing import List, Dict, Optional
import ebooklib
from ebooklib import epub


def clean_english_text(text: str) -> str:
    """Clean Japanese-specific symbols and quotation marks for pure English reading."""
    if not text:
        return ""
    # Remove music note symbols often produced by translation models for wave dashes
    text = text.replace("♪", "").replace("〜", " - ").replace("～", " - ")
    # Replace Japanese corner brackets and decorative brackets
    text = text.replace("「", '"').replace("」", '"')
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("『", "'").replace("』", "'")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("【", "[").replace("】", "]")
    text = text.replace("〔", "[").replace("〕", "]")
    text = text.replace("〈", "<").replace("〉", ">")
    text = text.replace("《", "<<").replace("》", ">>")
    # Fullwidth Japanese punctuation to standard ASCII
    text = text.replace("！", "!").replace("？", "?")
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("・", " · ").replace("：", ": ")
    # Replace fullwidth space
    text = text.replace("\u3000", " ")
    # Clean redundant spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

DEFAULT_CSS = """
@charset "utf-8";

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, sans-serif;
    line-height: 1.6;
    margin: 2% 4%;
    font-size: 1.0em;
    color: #1a1a1a;
    background-color: transparent;
}

p {
    text-indent: 0 !important;
    margin-top: 0 !important;
    margin-bottom: 0.85em !important;
}

@media (prefers-color-scheme: dark) {
    body {
        color: #e2e8f0;
    }
    .ja-text {
        color: #94a3b8 !important;
    }
    .novel-meta {
        color: #94a3b8 !important;
        border-color: #334155 !important;
    }
    h1.chapter-title, h1.title-heading {
        border-color: #334155 !important;
    }
}

h1.chapter-title {
    font-size: 1.35em;
    font-weight: 700;
    text-align: center;
    margin: 1.2em 0 1.0em 0;
    padding-bottom: 0.4em;
    border-bottom: 1px solid #cbd5e1;
    line-height: 1.3;
}

h1.title-heading {
    font-size: 1.6em;
    font-weight: bold;
    text-align: center;
    margin: 1.5em 0 0.8em 0;
    padding-bottom: 0.5em;
    border-bottom: 2px solid #cbd5e1;
    line-height: 1.3;
}

.novel-meta {
    text-align: center;
    margin-bottom: 1.8em;
    font-size: 0.9em;
    color: #64748b;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 1.2em;
}

.novel-meta p {
    text-indent: 0 !important;
    margin: 0.3em 0;
}

/* Standard paragraph: NO tab/indent, comfortable modern novel spacing */
p.story-p {
    text-indent: 0 !important;
    margin-top: 0 !important;
    margin-bottom: 0.85em !important;
    word-break: break-word;
    line-height: 1.6;
}

/* Blank line / scene pause: clean scene break */
p.blank-line {
    text-indent: 0 !important;
    margin: 1.2em 0 !important;
    height: 0.5em;
    font-size: 0.5em;
    line-height: 0.5em;
}

/* Dialogue lines: NO tab/indent, distinct spacing between speakers */
p.dialogue {
    text-indent: 0 !important;
    margin-top: 0 !important;
    margin-bottom: 0.85em !important;
    word-break: break-word;
    line-height: 1.6;
}

/* Bilingual block */
div.bilingual-block {
    margin-bottom: 1.0em;
}

.ja-text {
    font-size: 0.85em;
    color: #64748b;
    line-height: 1.4;
    margin-bottom: 0.25em;
    text-indent: 0 !important;
}

.tl-text {
    font-size: 1.0em;
    line-height: 1.6;
    text-indent: 0 !important;
    margin-bottom: 0.8em;
}

/* Synopsis page */
.synopsis-box {
    background-color: rgba(148, 163, 184, 0.08);
    border-left: 4px solid #3b82f6;
    padding: 1.2em 1.5em;
    margin: 1.5em 0;
    border-radius: 4px;
}

.synopsis-box p {
    text-indent: 0;
    margin: 0.6em 0;
}
"""


class EPUBBuilder:
    def __init__(
        self,
        novel_info: Dict,
        mode: str = "translated",
        target_lang: str = "en"
    ):
        """
        novel_info: Dictionary containing work_id, title, author, synopsis, etc.
        mode: 'translated', 'bilingual', or 'raw'
        target_lang: 'en' or 'id'
        """
        self.novel_info = novel_info
        self.mode = mode
        self.target_lang = target_lang

        self.book = epub.EpubBook()
        self._chapters: List[epub.EpubHtml] = []
        self._init_metadata()

    def _init_metadata(self) -> None:
        work_id = self.novel_info.get("work_id", "000000")

        # In translated mode, use English metadata exclusively
        if self.mode == "translated":
            title = clean_english_text(
                self.novel_info.get("title_en")
                or self.novel_info.get("title_tl")
                or self.novel_info.get("title", f"Novel {work_id}")
            )
            author = clean_english_text(
                self.novel_info.get("author_en")
                or self.novel_info.get("author_tl")
                or self.novel_info.get("author", "Unknown Author")
            )
            synopsis = clean_english_text(
                self.novel_info.get("synopsis_en")
                or self.novel_info.get("synopsis_tl")
                or self.novel_info.get("synopsis", "")
            )
            subtitle = "LIGHT NOVEL • ENGLISH TRANSLATION"
        else:
            title = self.novel_info.get("title", f"Novel {work_id}")
            author = self.novel_info.get("author", "Unknown Author")
            synopsis = self.novel_info.get("synopsis", "")
            subtitle = "Bilingual Edition (Japanese & English)" if self.mode == "bilingual" else "Japanese Edition"

        self.display_title = title
        self.display_author = author
        self.display_synopsis = synopsis

        self.book.set_identifier(f"kakuyomu-{work_id}")
        self.book.set_title(title)
        self.book.set_language(self.target_lang if self.mode != "raw" else "ja")
        self.book.add_author(author)

        if synopsis:
            self.book.add_metadata("DC", "description", synopsis)

        # User requested: No EPUB cover (kosongin aja)

        # Add CSS
        self.nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/style.css",
            media_type="text/css",
            content=DEFAULT_CSS
        )
        self.book.add_item(self.nav_css)

        # Title Page (Book details only)
        self._create_title_page()

    def _create_title_page(self) -> None:
        title = self.display_title
        author = self.display_author
        url = self.novel_info.get("url", "")
        
        mode_desc = "English Translation" if self.target_lang == "en" else "Indonesian Translation"
        if self.mode == "bilingual":
            mode_desc = "Bilingual Edition (Japanese & English)"

        source_name = "Syosetu (Shousetsuka ni Narou)" if ("syosetu.com" in url or self.novel_info.get("source") == "syosetu") else "Kakuyomu Original"

        html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Title Page</title>
    <link rel="stylesheet" type="text/css" href="style/style.css" />
</head>
<body>
    <div style="text-align: center; margin-top: 3em;">
        <h1 class="title-heading">{html.escape(title)}</h1>
        <div class="novel-meta">
            <p><strong>Author:</strong> {html.escape(author)}</p>
            <p><strong>Edition:</strong> {mode_desc}</p>
            <p><strong>Source:</strong> <a href="{html.escape(url)}">{source_name}</a></p>
        </div>
    </div>
</body>
</html>"""
        tp = epub.EpubHtml(title="Book Details", file_name="titlepage.xhtml", lang=self.target_lang)
        tp.content = html_content
        tp.add_item(self.nav_css)
        self.book.add_item(tp)
        self._chapters.append(tp)

    def add_chapter(
        self,
        index: int,
        title_ja: str,
        title_tl: str,
        paragraphs: List[Dict]
    ) -> None:
        """
        paragraphs is a list of dicts:
          [{"ja": "...", "tl": "...", "is_blank": bool}, ...]
        """
        file_name = f"chapter_{index:03d}.xhtml"
        
        # Display title
        if self.mode == "raw":
            display_title = title_ja
        elif self.mode == "bilingual":
            clean_tl = clean_english_text(title_tl)
            display_title = f"{clean_tl} ({title_ja})" if clean_tl != title_ja else title_ja
        else:
            display_title = clean_english_text(title_tl or title_ja)

        body_html = [f'<h1 class="chapter-title">{html.escape(display_title)}</h1>']

        last_was_blank = True  # Suppress leading blank lines right below the title

        for p in paragraphs:
            is_blank = p.get("is_blank", False)
            ja_text = p.get("ja", "").strip()
            tl_text = clean_english_text(p.get("tl", "").strip())

            # Check if paragraph has actual content
            has_content = bool(tl_text or ja_text)
            if is_blank or not has_content:
                # Collapse multiple consecutive blank lines into at most one subtle pause
                if not last_was_blank:
                    body_html.append('<p class="blank-line">&nbsp;</p>')
                    last_was_blank = True
                continue

            last_was_blank = False

            if self.mode == "raw":
                is_diag = ja_text.startswith("「") or ja_text.startswith("『")
                cls = "dialogue" if is_diag else "story-p"
                body_html.append(f'<p class="{cls}">{html.escape(ja_text)}</p>')

            elif self.mode == "bilingual":
                body_html.append(
                    f'<div class="bilingual-block">'
                    f'  <div class="ja-text">{html.escape(ja_text)}</div>'
                    f'  <div class="tl-text">{html.escape(tl_text or ja_text)}</div>'
                    f'</div>'
                )

            else:  # translated mode (Pure English / Indonesian)
                text_to_show = tl_text or ja_text
                is_diag = (
                    text_to_show.startswith('"')
                    or text_to_show.startswith("'")
                    or text_to_show.startswith("“")
                    or text_to_show.startswith("‘")
                    or text_to_show.startswith("「")
                )
                cls = "dialogue" if is_diag else "story-p"
                body_html.append(f'<p class="{cls}">{html.escape(text_to_show)}</p>')

        # Suppress trailing blank lines before closing the chapter
        if body_html and body_html[-1] == '<p class="blank-line">&nbsp;</p>':
            body_html.pop()

        full_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{html.escape(display_title)}</title>
    <link rel="stylesheet" type="text/css" href="style/style.css" />
</head>
<body>
    {"".join(body_html)}
</body>
</html>"""

        chapter_item = epub.EpubHtml(
            title=display_title,
            file_name=file_name,
            lang=self.target_lang if self.mode != "raw" else "ja"
        )
        chapter_item.content = full_html
        chapter_item.add_item(self.nav_css)
        self.book.add_item(chapter_item)
        self._chapters.append(chapter_item)

    def build_and_save(self, output_path: str) -> str:
        """Finalize TOC, Nav, Spine, and write EPUB to disk."""
        # Setup Table of Contents (exclude cover, include title & chapters)
        self.book.toc = tuple(self._chapters)

        # Standard navigation items
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Spine defines reading order (no cover item)
        self.book.spine = ["nav"] + self._chapters

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        epub.write_epub(output_path, self.book)
        return os.path.abspath(output_path)
