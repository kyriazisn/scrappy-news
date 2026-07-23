#!/usr/bin/env python3
import argparse
import hashlib
import sqlite3
import time
from datetime import datetime
from urllib.parse import quote_plus, urljoin

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarfinMonitor/1.0)"}
DEFAULT_KEYWORDS = ["Marfin", "Μαρφίν", "υπόθεση Marfin", "εμπρησμός Marfin", "Marfin συλλήψεις"]


def load_sources(path="sources.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def init_db(db_path="news.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            source TEXT,
            keyword TEXT,
            title TEXT,
            url TEXT,
            published TEXT,
            fetched_at TEXT
        )"""
    )
    conn.commit()
    return conn


def article_id(source, title, url):
    return hashlib.sha256(f"{source}|{title}|{url}".encode("utf-8")).hexdigest()


def save_rows(conn, rows):
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        rid = article_id(r["source"], r["title"], r["url"])
        try:
            cur.execute(
                "INSERT INTO articles VALUES (?,?,?,?,?,?,?)",
                (
                    rid,
                    r["source"],
                    r["keyword"],
                    r["title"],
                    r["url"],
                    r.get("published", ""),
                    r["fetched_at"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


def parse_rss(xml_text, source_name, keyword):
    soup = BeautifulSoup(xml_text, "xml")
    rows = []
    for item in soup.find_all("item"):
        title = (item.title.text or "").strip() if item.title else ""
        link = (item.link.text or "").strip() if item.link else ""
        pub = (item.pubDate.text or "").strip() if item.pubDate else ""
        hay = f"{title} {link}".lower()
        if title and keyword.lower() in hay:
            rows.append(
                {
                    "source": source_name,
                    "keyword": keyword,
                    "title": title,
                    "url": link,
                    "published": pub,
                }
            )
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
            rows.append(
                {
                    "source": source_name,
                    "keyword": keyword,
                    "title": title,
                    "url": url,
                    "published": "",
                }
            )
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
    ap.add_argument("--db", default="news.db")
    ap.add_argument("--csv", default="results.csv")
    ap.add_argument("--sources", default="sources.yaml")
    args = ap.parse_args()

    sources = load_sources(args.sources)
    conn = init_db(args.db)
    all_rows = []

    for src in sources:
        all_rows.extend(collect_for_source(src, args.keywords))

    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    for r in all_rows:
        r["fetched_at"] = now

    if all_rows:
        df = pd.DataFrame(all_rows).drop_duplicates(subset=["source", "title", "url"])
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")
        inserted = save_rows(conn, df.to_dict("records"))
        print(f"Found {len(df)} rows, inserted {inserted}, saved to {args.csv}")
    else:
        pd.DataFrame(
            columns=["source", "keyword", "title", "url", "published", "fetched_at"]
        ).to_csv(args.csv, index=False, encoding="utf-8-sig")
        print("No rows found; empty CSV created")


if __name__ == "__main__":
    main()