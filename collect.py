#!/usr/bin/env python3
"""Collects current headlines for the Holosplash AR mug (AR_curved's NewsTicker) into news.json.

One region per audience, picked on the phone by the visitor's IP country (the same GeoJS lookup as the weather);
everyone else gets the fallback region. Run by .github/workflows/news.yml every 30 minutes; the phone reads
https://raw.githubusercontent.com/holosplash/ar-news/main/news.json (CORS *, 5-minute cache).

Standard library only. A feed that fails keeps its previous headlines, so one outage never blanks a region.
news.json is only rewritten when the headlines change.

    python3 collect.py            update news.json
    python3 collect.py --print    show what would be written, write nothing
"""
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).with_name("news.json")
PER_REGION = 12
FALLBACK = "en"

REGIONS = [
    # id, source shown on the mug, language (for "x min ago"), countries, feed, titles to drop
    {"id": "de", "source": "tagesschau", "lang": "de", "countries": ["DE", "AT", "LI", "LU"],
     "feed": "https://www.tagesschau.de/index~rss2.xml",
     "skip": r"^(tagesschau|tagesthemen|nachtmagazin)\b.*\d|^Liveblog|^Wetter"},
    {"id": "ch", "source": "SRF News", "lang": "de", "countries": ["CH"],
     "feed": "https://www.srf.ch/news/bnf/rss/1646", "skip": None},
    {"id": "it", "source": "ANSA", "lang": "it", "countries": ["IT", "SM", "VA"],
     "feed": "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml", "skip": None},
    {"id": "en", "source": "BBC News", "lang": "en", "countries": [],
     "feed": "https://feeds.bbci.co.uk/news/world/rss.xml", "skip": r"^(Watch|Listen|In pictures)\b"},
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "holosplash-ar-news/1.0 (+https://holosplash.com)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", "", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def iso(pub_date):
    try:
        dt = email.utils.parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return ""


def headlines(region):
    root = ET.fromstring(fetch(region["feed"]))
    skip = re.compile(region["skip"], re.I) if region["skip"] else None
    items, seen = [], set()
    for it in root.iter("item"):
        title, url = clean(it.findtext("title")), (it.findtext("link") or "").strip()
        if not title or not url.startswith("http") or title in seen or (skip and skip.search(title)):
            continue
        seen.add(title)
        items.append({"title": title, "url": url, "time": iso(it.findtext("pubDate"))})
    items.sort(key=lambda i: i["time"], reverse=True)   # some feeds are not in date order
    return items[:PER_REGION]


def main():
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"version": 0, "regions": []}
    old = {r["id"]: r for r in previous.get("regions", [])}

    regions, failed = [], []
    for spec in REGIONS:
        entry = {k: spec[k] for k in ("id", "source", "lang", "countries")}
        try:
            entry["items"] = headlines(spec)
            if not entry["items"]:
                raise ValueError("no items")
        except Exception as e:  # keep what we had
            failed.append(f"{spec['id']}: {e}")
            entry["items"] = old.get(spec["id"], {}).get("items", [])
        regions.append(entry)

    changed = [r["items"] for r in regions] != [old.get(r["id"], {}).get("items") for r in regions]
    out = {
        "version": previous.get("version", 0) + (1 if changed else 0),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if changed else previous.get("updated", ""),
        "fallback": FALLBACK,
        "regions": regions,
    }

    for r in regions:
        print(f"{r['id']}: {len(r['items'])} headlines" + (f" — newest: {r['items'][0]['title'][:70]}" if r["items"] else ""))
    for f in failed:
        print("FAILED", f, file=sys.stderr)

    if "--print" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=2)[:1500])
    elif changed:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"news.json v{out['version']} written")
    else:
        print("no change")
    return 1 if len(failed) == len(REGIONS) else 0


if __name__ == "__main__":
    sys.exit(main())
