#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin

import requests
import yaml
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GreekNewsMonitor/1.0)"}
DEFAULT_KEYWORDS = [
    "Marfin",
    "Μαρφίν",
    "υπόθεση Marfin",
    "εμπρησμός Marfin",
    "Marfin συλλήψεις",
]

def load_sources(path="src/sources.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]

def normalize_url(url):
    return (url or "").strip()

def dedupe(items):
    seen = set()
    out = []
    for item in items:
        key = (item["source"], item["title"].strip(), item["url"].strip())
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

def parse_rss(xml_text, source_name, keyword):
    soup = BeautifulSoup(xml_text, "xml")
    rows = []
    for item in soup.find_all("item"):
        title = (item.title.text or "").strip() if item.title else ""
        link = (item.link.text or "").strip() if item.link else ""
        pub = (item.pubDate.text or "").strip() if item.pubDate else ""
        hay = f"{title} {link}".lower()
        if title and keyword.lower() in hay:
            rows.append({
                "source": source_name,
                "keyword": keyword,
                "title": title,
                "url": normalize_url(link),
                "published": pub,
            })
    return rows

def parse_html(html, source_name, keyword, base_url):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.select("a[href]"):
        title = a.get_text(" ", strip=True)
        href = a.get("href", "")
        if not title:
            continue
        url = urljoin(base_url, href)
        hay = f"{title} {url}".lower()
        if keyword.lower() in hay:
            rows.append({
                "source": source_name,
                "keyword": keyword,
                "title": title,
                "url": normalize_url(url),
                "published": "",
            })
    return rows

def collect_for_source(src, keywords):
    rows = []
    for keyword in keywords:
        for rss_url in src.get("rss", []):
            try:
                r = requests.get(rss_url, headers=HEADERS, timeout=20)
                if r.ok:
                    rows.extend(parse_rss(r.text, src["name"], keyword))
            except Exception:
                pass

        for sp in src.get("search_paths", []):
            try:
                url = src["base_url"].rstrip("/") + sp.format(query=quote_plus(keyword))
                r = requests.get(url, headers=HEADERS, timeout=20)
                if r.ok:
                    rows.extend(parse_html(r.text, src["name"], keyword, src["base_url"]))
            except Exception:
                pass

        time.sleep(0.5)
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="src/sources.yaml")
    parser.add_argument("--out", default="docs/articles.json")
    parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
    args = parser.parse_args()

    sources = load_sources(args.sources)
    articles = []

    for src in sources:
        articles.extend(collect_for_source(src, args.keywords))

    articles = dedupe(articles)
    articles.sort(key=lambda x: (x.get("published", ""), x["title"]), reverse=True)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "keywords": args.keywords,
        "articles": articles,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(articles)} articles to {args.out}")

if __name__ == "__main__":
    main()