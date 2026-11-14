"""
Web Novel Scraper Module
Supports extracting novel details, table of contents, and episode content
from Kakuyomu (kakuyomu.jp) and Shousetsuka ni Narou / Syosetu (ncode.syosetu.com).
"""

import re
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from .glossary import get_glossary_manager

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Cookie": "over18=yes"
}

def fetch_html(url: str, retries: int = 3) -> str:
    """Fetch HTML content from URL with retry mechanism."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if attempt == retries - 1:
                raise RuntimeError(f"HTTP Error {e.code} when fetching {url}: {e.reason}")
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Error fetching {url}: {e}")
    return ""


def parse_kakuyomu_url(url_or_id: str) -> Tuple[str, Optional[str]]:
    """
    Parse a Kakuyomu URL or ID string into (work_id, episode_id).
    Accepts:
      - https://kakuyomu.jp/works/2912051607243271731/episodes/2912051607330854893
      - https://kakuyomu.jp/works/2912051607243271731
      - 2912051607243271731
    """
    url_or_id = url_or_id.strip()
    
    # Check for episode pattern
    ep_match = re.search(r"/works/(\d+)/episodes/(\d+)", url_or_id)
    if ep_match:
        return ep_match.group(1), ep_match.group(2)
    
    # Check for work pattern
    work_match = re.search(r"/works/(\d+)", url_or_id)
    if work_match:
        return work_match.group(1), None
    
    # Check for raw numeric ID
    if url_or_id.isdigit():
        return url_or_id, None
    
    raise ValueError(f"Could not parse Kakuyomu URL or ID: {url_or_id}")


def parse_syosetu_url(url_or_id: str) -> Tuple[str, Optional[str]]:
    """
    Parse a Syosetu (Shousetsuka ni Narou) URL or Ncode into (ncode, episode_id).
    Accepts:
      - https://ncode.syosetu.com/n1184mz/2/
      - https://ncode.syosetu.com/n1184mz/
      - https://novel18.syosetu.com/n1184mz/
      - n1184mz
    """
    url_or_id = url_or_id.strip()
    # Check for episode pattern e.g. /n1184mz/2/
    m_ep = re.search(r"syosetu\.com/([a-zA-Z0-9]+)/(\d+)", url_or_id)
    if m_ep:
        return m_ep.group(1).lower(), m_ep.group(2)

    # Check for work pattern e.g. /n1184mz/
    m_work = re.search(r"syosetu\.com/([a-zA-Z0-9]+)", url_or_id)
    if m_work:
        return m_work.group(1).lower(), None

    # Check for raw ncode e.g. n1184mz (must start with n or match ncode pattern)
    if re.match(r"^n\d{4}[a-z]+$", url_or_id, re.IGNORECASE):
        return url_or_id.lower(), None

    raise ValueError(f"Could not parse Syosetu URL or Ncode: {url_or_id}")


def parse_novel_url(url_or_id: str) -> Tuple[str, str, Optional[str]]:
    """
    Auto-detect source and parse URL or ID.
    Returns (source, work_id, episode_id)
    where source is 'kakuyomu' or 'syosetu'.
    """
    url_or_id = url_or_id.strip()
    if "syosetu.com" in url_or_id or re.match(r"^n\d{4}[a-z]+$", url_or_id, re.IGNORECASE):
        work_id, episode_id = parse_syosetu_url(url_or_id)
        return "syosetu", work_id, episode_id
    else:
        work_id, episode_id = parse_kakuyomu_url(url_or_id)
        return "kakuyomu", work_id, episode_id


class KakuyomuScraper:
    def __init__(self, work_id: str):
        self.work_id = work_id
        self.work_url = f"https://kakuyomu.jp/works/{work_id}"
        self._work_soup: Optional[BeautifulSoup] = None
        self._novel_info: Optional[Dict] = None

    def get_novel_info(self) -> Dict:
        """Fetch and return novel metadata and full table of contents."""
        if self._novel_info:
            return self._novel_info

        html = fetch_html(self.work_url)
        soup = BeautifulSoup(html, "html.parser")
        self._work_soup = soup

        # 1. Novel Title
        title = ""
        title_el = soup.select_one("#workTitle, [class*='workTitle'], h1")
        if title_el:
            title = title_el.get_text(strip=True)
        if not title and soup.title:
            title = soup.title.get_text(strip=True).split("（")[0].replace(" - カクヨム", "").strip()

        # 2. Author
        author = "Unknown Author"
        author_el = soup.select_one("#workAuthor-activityName, [class*='author'], [class*='ActivityName']")
        if author_el:
            author = author_el.get_text(strip=True)

        # 3. Synopsis / Description
        synopsis = ""
        catchphrase_el = soup.select_one("#catchphrase, [class*='catchphrase']")
        catchphrase = catchphrase_el.get_text(strip=True) if catchphrase_el else ""
        
        intro_el = soup.select_one("#introduction, [class*='introduction']")
        introduction = intro_el.get_text("\n", strip=True) if intro_el else ""
        
        synopsis_parts = [p for p in [catchphrase, introduction] if p]
        synopsis = "\n\n".join(synopsis_parts)

        # 4. Table of Contents (Episodes)
        episodes = []
        seen_ids = set()

        # Approach A: Parse Next.js Apollo state (__NEXT_DATA__)
        # Essential for novels with volumes / accordions / pagination (> 7 episodes)
        next_data_el = soup.find("script", id="__NEXT_DATA__")
        if next_data_el and next_data_el.string:
            try:
                import json
                nd = json.loads(next_data_el.string)
                apollo = nd.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})

                # Priority 1: Traverse Work.tableOfContentsV2 in volume order
                work_node = apollo.get(f"Work:{self.work_id}") or apollo.get(self.work_id)
                toc_v2 = work_node.get("tableOfContentsV2") if isinstance(work_node, dict) else None

                if toc_v2 and isinstance(toc_v2, list):
                    for toc_item in toc_v2:
                        ref = toc_item.get("__ref")
                        toc_chap = apollo.get(ref) if ref else toc_item
                        if isinstance(toc_chap, dict) and "episodeUnions" in toc_chap:
                            for item in toc_chap["episodeUnions"]:
                                ep_ref = item.get("__ref")
                                ep = apollo.get(ep_ref) if ep_ref else item
                                if isinstance(ep, dict) and ep.get("__typename") == "Episode":
                                    ep_id = str(ep.get("id"))
                                    if ep_id not in seen_ids:
                                        seen_ids.add(ep_id)
                                        episodes.append({
                                            "index": len(episodes) + 1,
                                            "id": ep_id,
                                            "title": ep.get("title") or f"Chapter {len(episodes) + 1}",
                                            "url": f"https://kakuyomu.jp/works/{self.work_id}/episodes/{ep_id}",
                                            "date": ep.get("publishedAt", "")
                                        })

                # Priority 2: Fallback scan across all Apollo state objects
                if not episodes:
                    for k, v in apollo.items():
                        if isinstance(v, dict) and "episodeUnions" in v:
                            for item in v["episodeUnions"]:
                                ref = item.get("__ref")
                                ep = apollo.get(ref) if ref else item
                                if isinstance(ep, dict) and ep.get("__typename") == "Episode":
                                    ep_id = str(ep.get("id"))
                                    if ep_id not in seen_ids:
                                        seen_ids.add(ep_id)
                                        episodes.append({
                                            "index": len(episodes) + 1,
                                            "id": ep_id,
                                            "title": ep.get("title") or f"Chapter {len(episodes) + 1}",
                                            "url": f"https://kakuyomu.jp/works/{self.work_id}/episodes/{ep_id}",
                                            "date": ep.get("publishedAt", "")
                                        })
            except Exception as e:
                print(f"[KakuyomuScraper] Apollo TOC parsing warning: {e}")

        # Approach B (Fallback): Parse raw HTML <a> tags if __NEXT_DATA__ is absent
        if not episodes:
            toc_items = soup.find_all("a", href=re.compile(rf"/works/{self.work_id}/episodes/(\d+)"))
            idx = 1
            for a in toc_items:
                href = a.get("href", "")
                match = re.search(rf"/works/{self.work_id}/episodes/(\d+)", href)
                if not match:
                    continue
                ep_id = match.group(1)
                if ep_id in seen_ids:
                    continue
                if "1話目から読む" in a.get_text():
                    continue

                seen_ids.add(ep_id)
                title_node = a.select_one("[class*='WorkTocSection_title'], [class*='title']")
                if title_node:
                    ep_title = title_node.get_text(strip=True)
                else:
                    ep_title = a.get_text(strip=True)
                    ep_title = re.sub(r"\d{4}年\d{1,2}月\d{1,2}日.*$", "", ep_title).strip()

                date_node = a.select_one("[class*='WorkTocSection_date'], time")
                ep_date = date_node.get_text(strip=True) if date_node else ""

                episodes.append({
                    "index": idx,
                    "id": ep_id,
                    "title": ep_title or f"Chapter {idx}",
                    "url": f"https://kakuyomu.jp/works/{self.work_id}/episodes/{ep_id}",
                    "date": ep_date
                })
                idx += 1

        self._novel_info = {
            "work_id": self.work_id,
            "title": title or f"Kakuyomu Novel {self.work_id}",
            "author": author,
            "synopsis": synopsis,
            "url": self.work_url,
            "total_episodes": len(episodes),
            "episodes": episodes
        }
        return self._novel_info

    def get_episode_content(self, episode_id: str) -> Dict:
        """Fetch and parse an individual episode's title and paragraphs."""
        ep_url = f"https://kakuyomu.jp/works/{self.work_id}/episodes/{episode_id}"
        html = fetch_html(ep_url)
        soup = BeautifulSoup(html, "html.parser")

        # Episode Title
        ep_title = ""
        title_el = soup.select_one(".widget-episodeTitle, [class*='EpisodeTitle'], [class*='episodeTitle'], h2.js-vertical-composition-item")
        if title_el:
            ep_title = title_el.get_text(strip=True)
        elif soup.title:
            ep_title = soup.title.get_text(strip=True).split(" - ")[0].strip()

        # Episode Body
        body_el = soup.select_one(".widget-episodeBody, [class*='episodeBody']")
        if not body_el:
            raise RuntimeError(f"Could not find episode body content at {ep_url}")

        # Harvest and apply ruby ateji readings
        glossary = get_glossary_manager()
        glossary.harvest_ruby_ateji(str(body_el), work_id=self.work_id)
        body_clean_html = glossary.substitute_ruby_in_html(str(body_el))
        body_clean_html = re.sub(r"<(rt|rp)[^>]*>.*?</\1>", "", body_clean_html, flags=re.DOTALL)
        clean_body = BeautifulSoup(body_clean_html, "html.parser")

        raw_p_list = body_el.find_all("p")
        clean_p_list = clean_body.find_all("p")

        paragraphs = []
        for p_raw, p_clean in zip(raw_p_list, clean_p_list):
            raw_text = p_raw.get_text().strip()
            if not raw_text or (p_raw.find("br") and not raw_text):
                paragraphs.append({
                    "raw": "",
                    "clean": "",
                    "is_blank": True
                })
                continue

            clean_text = p_clean.get_text().strip()
            paragraphs.append({
                "raw": raw_text,
                "clean": clean_text,
                "is_blank": False
            })

        return {
            "work_id": self.work_id,
            "source": "kakuyomu",
            "episode_id": episode_id,
            "title": ep_title,
            "url": ep_url,
            "paragraphs": paragraphs
        }


class SyosetuScraper:
    def __init__(self, ncode: str):
        self.ncode = ncode.lower().strip()
        self.work_id = self.ncode
        self.source = "syosetu"
        self.work_url = f"https://ncode.syosetu.com/{self.ncode}/"
        self._novel_info: Optional[Dict] = None

    def get_novel_info(self) -> Dict:
        """Fetch and return Syosetu novel metadata and full table of contents."""
        if self._novel_info:
            return self._novel_info

        html = fetch_html(self.work_url)
        soup = BeautifulSoup(html, "html.parser")

        # 1. Title
        title = ""
        title_el = soup.select_one(".p-novel__title, .novel_title, h1")
        if title_el:
            title = title_el.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True).replace(" - 小説家になろう", "").strip()

        # 2. Author
        author = "Unknown Author"
        author_el = soup.select_one(".p-novel__author, .novel_writername")
        if author_el:
            author = author_el.get_text(strip=True).replace("作者：", "").strip()

        # 3. Synopsis
        synopsis = ""
        synopsis_el = soup.select_one(".p-novel__summary, #novel_ex")
        if synopsis_el:
            synopsis = synopsis_el.get_text("\n", strip=True)

        # 4. Episodes & Pagination
        episodes = []
        seen_ids = set()

        def extract_episodes_from_soup(s_page):
            pattern = re.compile(rf"/{self.ncode}/(\d+)/?$")
            for a in s_page.find_all("a", href=True):
                m = pattern.search(a["href"])
                if not m:
                    continue
                ep_id = m.group(1)
                if ep_id in seen_ids:
                    continue
                seen_ids.add(ep_id)
                ep_title = a.get_text(strip=True)

                ep_date = ""
                parent = a.find_parent(["div", "dd", "tr", "li"])
                if parent:
                    date_el = parent.select_one(".p-eplist__update, .long_update, dt")
                    if date_el:
                        ep_date = date_el.get_text(strip=True)

                episodes.append({
                    "index": int(ep_id),
                    "id": ep_id,
                    "title": ep_title or f"Chapter {ep_id}",
                    "url": f"https://ncode.syosetu.com/{self.ncode}/{ep_id}/",
                    "date": ep_date
                })

        extract_episodes_from_soup(soup)

        # Check for multi-page pagination (?p=2, ?p=3, ...)
        pager_links = soup.find_all("a", href=re.compile(r"\?p=(\d+)"))
        max_page = 1
        for a in pager_links:
            m = re.search(r"\?p=(\d+)", a["href"])
            if m:
                max_page = max(max_page, int(m.group(1)))

        if max_page > 1:
            for p_num in range(2, max_page + 1):
                p_url = f"https://ncode.syosetu.com/{self.ncode}/?p={p_num}"
                try:
                    p_html = fetch_html(p_url)
                    p_soup = BeautifulSoup(p_html, "html.parser")
                    extract_episodes_from_soup(p_soup)
                except Exception as e:
                    print(f"[SyosetuScraper] Page {p_num} TOC warning: {e}")

        # Check if single-chapter short story (短編) with honbun on main page
        if not episodes:
            body_check = soup.select_one(".p-novel__body, #novel_honbun")
            if body_check:
                episodes.append({
                    "index": 1,
                    "id": "1",
                    "title": title or "Chapter 1",
                    "url": self.work_url,
                    "date": ""
                })

        # Sort episodes strictly by episode number
        episodes.sort(key=lambda x: x["index"])

        for i, ep in enumerate(episodes):
            ep["index"] = i + 1

        self._novel_info = {
            "work_id": self.ncode,
            "source": "syosetu",
            "title": title or f"Syosetu Novel {self.ncode}",
            "author": author,
            "synopsis": synopsis,
            "url": self.work_url,
            "total_episodes": len(episodes),
            "episodes": episodes
        }
        return self._novel_info

    def get_episode_content(self, episode_id: str) -> Dict:
        """Fetch and parse Syosetu episode paragraphs."""
        ep_url = f"https://ncode.syosetu.com/{self.ncode}/{episode_id}/"
        try:
            html = fetch_html(ep_url)
        except Exception:
            # Fallback to main page for short stories
            html = fetch_html(self.work_url)
            ep_url = self.work_url

        soup = BeautifulSoup(html, "html.parser")

        # Episode Title
        ep_title = ""
        title_el = soup.select_one(".p-novel__title, .novel_subtitle")
        if title_el:
            ep_title = title_el.get_text(strip=True)
        elif soup.title:
            ep_title = soup.title.get_text(strip=True).split(" - ")[0].strip()

        # Episode Body
        body_el = soup.select_one(".p-novel__body, #novel_honbun")
        if not body_el:
            raise RuntimeError(f"Could not find episode body content at {ep_url}")

        # Harvest and apply ruby ateji readings
        glossary = get_glossary_manager()
        glossary.harvest_ruby_ateji(str(body_el), work_id=self.work_id)
        body_clean_html = glossary.substitute_ruby_in_html(str(body_el))
        body_clean_html = re.sub(r"<(rt|rp)[^>]*>.*?</\1>", "", body_clean_html, flags=re.DOTALL)
        clean_body = BeautifulSoup(body_clean_html, "html.parser")

        raw_p_list = body_el.find_all("p")
        clean_p_list = clean_body.find_all("p")

        paragraphs = []
        for p_raw, p_clean in zip(raw_p_list, clean_p_list):
            raw_text = p_raw.get_text().strip()
            if not raw_text or (p_raw.find("br") and not raw_text):
                paragraphs.append({
                    "raw": "",
                    "clean": "",
                    "is_blank": True
                })
                continue

            clean_text = p_clean.get_text().strip()
            paragraphs.append({
                "raw": raw_text,
                "clean": clean_text,
                "is_blank": False
            })

        return {
            "work_id": self.ncode,
            "source": "syosetu",
            "episode_id": episode_id,
            "title": ep_title or f"Chapter {episode_id}",
            "url": ep_url,
            "paragraphs": paragraphs
        }


def get_novel_scraper(url_or_id: str):
    """Factory function returning the appropriate scraper instance."""
    source, work_id, _ = parse_novel_url(url_or_id)
    if source == "syosetu":
        return SyosetuScraper(work_id)
    return KakuyomuScraper(work_id)
