"""
RoyalRoad Novel Downloader
Usage: python rr_downloader.py --url <url> [--output_dir <path>]
"""
import sys
import re
import time
import zipfile
import tempfile
import argparse
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
RATE_LIMIT = 1.5
MAX_RETRIES = 3
TIMEOUT = 30


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:200] or "untitled"


def extract_novel_title(soup: BeautifulSoup, url: str) -> str:
    h1 = soup.find("h1")
    if h1:
        return sanitize_filename(h1.get_text(strip=True))
    match = re.search(r'/fiction/\d+/([^/]+)', url)
    if match:
        return match.group(1).replace('-', '_')
    return "novel"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_with_retry(session, url):
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[WARN] Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return None


def parse_chapter_list(session, url):
    print("Fetching table of contents...", flush=True)
    resp = fetch_with_retry(session, url)
    if not resp:
        print("[ERROR] Could not fetch novel page.")
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    chapters = []

    table = soup.find("table", {"class": "table"})
    if table:
        for i, row in enumerate(table.find_all("tr")):
            link = row.find("a")
            if link and link.get("href"):
                chapters.append({
                    "number": i + 1,
                    "title": sanitize_filename(link.get_text(strip=True)),
                    "url": urljoin(url, link["href"]),
                })
        if chapters:
            return chapters

    toc = soup.find("div", {"class": "chapter-list"}) or soup.find("div", {"class": "cc-list"})
    if toc:
        for i, link in enumerate(toc.find_all("a", href=True)):
            href = link["href"]
            if "chapter" in href.lower():
                chapters.append({
                    "number": i + 1,
                    "title": sanitize_filename(link.get_text(strip=True)),
                    "url": urljoin(url, href),
                })

    if not chapters:
        print("[ERROR] Could not find chapter list on page.")
        sys.exit(1)

    return chapters


_AUTHOR_NOTE_MARKERS = ("authors note:", "author's note:", "author note:")
_WATERMARK_INDICATORS = (
    "report any instance", "this tale has been",
    "this story has been", "not stolen versions", "support creative writers",
    "stolen content", "if detected on amazon",
    "taken without authorization", "read it on royal road",
)


def extract_chapter_content(session, url):
    resp = fetch_with_retry(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    inner = soup.find("div", class_="chapter-inner")
    if not inner:
        return None

    for tag in inner.find_all(["script", "style", "aside", "noscript"]):
        tag.decompose()
    for br in inner.find_all("br"):
        br.replace_with("\n")

    lines = [ln.strip() for ln in inner.get_text().split("\n") if ln.strip()]
    if not lines:
        return None

    for i, ln in enumerate(lines):
        for marker in _AUTHOR_NOTE_MARKERS:
            if ln.lower().startswith(marker):
                rest = [l for l in lines[i + 1:] if l]
                return "\n\n".join(rest) if rest else None

    clean_lines = [
        ln for ln in lines
        if not any(indicator in ln.lower() for indicator in _WATERMARK_INDICATORS)
    ]

    return "\n\n".join(clean_lines) if clean_lines else None


def main():
    parser = argparse.ArgumentParser(description="RoyalRoad Novel Downloader")
    parser.add_argument("--url", required=True, help="RoyalRoad novel URL")
    parser.add_argument("--output_dir", default="", help="Output folder path")
    args = parser.parse_args()

    url = args.url.strip()
    if "royalroad.com" not in url:
        print("[ERROR] URL does not appear to be a RoyalRoad novel.")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = build_session()
    title_resp = session.get(url, timeout=TIMEOUT)
    title_soup = BeautifulSoup(title_resp.text, "html.parser")
    novel_title = extract_novel_title(title_soup, url)
    chapters = parse_chapter_list(session, url)

    print(f"Novel: {novel_title}", flush=True)
    print(f"Chapters found: {len(chapters)}", flush=True)
    progress(0)

    failed = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        for idx, chapter in enumerate(chapters, 1):
            pct = int((idx / len(chapters)) * 95)
            progress(pct)
            print(f"[{'OK' if True else 'FAIL'}] [{idx}/{len(chapters)}] {chapter['title'][:60]}", flush=True)

            content = extract_chapter_content(session, chapter["url"])
            if content:
                filename = f"{idx:03d}_{chapter['title']}.txt"
                (tmp_path / filename).write_text(content, encoding="utf-8")
                print(f"[OK] {filename}", flush=True)
            else:
                print(f"[WARN] {chapter['title']} -- empty or failed", flush=True)
                failed.append(chapter["title"])

            time.sleep(RATE_LIMIT)

        zip_path = output_dir / f"{novel_title}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for txt_file in sorted(tmp_path.glob("*.txt")):
                zf.write(txt_file, txt_file.name)

    progress(100)

    if failed:
        print(f"[WARN] {len(failed)} chapter(s) could not be retrieved: {', '.join(failed[:5])}")
    print(f"[OK] Done. ZIP saved to: {zip_path}", flush=True)


if __name__ == "__main__":
    main()
