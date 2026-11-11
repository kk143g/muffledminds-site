#!/usr/bin/env python3
"""SEO check for one episode page. Run after publishing a page:

    python3 scripts/seo_check.py find-your-clarity-05

Checks the live page on muffledminds.com (falls back to the local file with --local) for: HTTP status, title and
description length, one H1, canonical, Open Graph, JSON-LD validity and required fields, thumbnail availability,
sitemap entry, internal links from the archive / homepage / sibling episodes, and image alt text.
Prints PASS / WARN / FAIL lines and exits 1 if anything FAILs.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://muffledminds.com"
results = []


def rec(level, msg):
    results.append(level)
    print(f"{level:5} {msg}")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (muffledminds seo check)"})
    r = urllib.request.urlopen(req, timeout=30)
    return r.status, r.read().decode("utf-8", "ignore")


def status(url, method="HEAD"):
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=30).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main(slug, local=False):
    url = f"{SITE}/episodes/{slug}.html"
    if local:
        html = (ROOT / "episodes" / f"{slug}.html").read_text()
        rec("INFO", f"checking local file episodes/{slug}.html")
    else:
        code, html = fetch(url) if status(url) == 200 else (status(url), "")
        if code != 200:
            rec("FAIL", f"{url} returns {code} (not live yet? GitHub Pages can take several minutes)")
            return
        rec("PASS", f"live page returns 200: {url}")

    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
    rec("PASS" if 30 <= len(title) <= 70 else "WARN", f"title is {len(title)} chars (aim 30-70): {title}")
    desc = re.search(r'<meta name="description" content="(.*?)">', html, re.S)
    if not desc:
        rec("FAIL", "no meta description")
    else:
        n = len(desc.group(1))
        rec("PASS" if 70 <= n <= 160 else "WARN", f"meta description is {n} chars (aim 70-160)")
    rec("PASS" if len(re.findall(r"<h1[ >]", html)) == 1 else "FAIL", "exactly one H1")
    canon = re.search(r'<link rel="canonical" href="(.*?)"', html)
    rec("PASS" if canon and canon.group(1) == url else "FAIL", f"canonical = {canon.group(1) if canon else None}")
    for p in ("og:title", "og:description", "og:image", "og:url"):
        rec("PASS" if f'property="{p}"' in html else "FAIL", f"{p} present")
    rec("PASS" if 'name="robots" content="index' in html else "FAIL", "robots allows indexing")

    # JSON-LD
    need = {"PodcastEpisode": ["name", "datePublished", "description", "url"],
            "VideoObject": ["name", "description", "thumbnailUrl", "uploadDate", "embedUrl"],
            "BreadcrumbList": ["itemListElement"], "FAQPage": ["mainEntity"]}
    found = {}
    for m in re.finditer(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S):
        try:
            d = json.loads(m.group(1))
            found[d["@type"]] = d
        except Exception as ex:
            rec("FAIL", f"invalid JSON-LD block: {ex}")
    for t, keys in need.items():
        d = found.get(t)
        if not d:
            rec("FAIL", f"JSON-LD {t} missing")
            continue
        miss = [k for k in keys if not d.get(k)]
        rec("FAIL" if miss else "PASS", f"JSON-LD {t}" + (f" missing {miss}" if miss else " complete"))
    v = found.get("VideoObject", {})
    if v:
        rec("PASS" if v.get("transcript") else "WARN", "VideoObject has transcript")
        rec("PASS" if v.get("hasPart") else "WARN", f"VideoObject has {len(v.get('hasPart', []))} chapter clips (key moments)")
        th = status(v.get("thumbnailUrl", ""))
        rec("PASS" if th == 200 else "FAIL", f"thumbnail {v.get('thumbnailUrl')} returns {th}")

    # images and links
    imgs = re.findall(r"<img [^>]*>", html)
    noalt = [i for i in imgs if "alt=" not in i]
    rec("PASS" if not noalt else "WARN", f"{len(imgs)} images, {len(noalt)} without alt text")

    # sitemap + internal links
    sm = (ROOT / "sitemap.xml").read_text()
    rec("PASS" if url in sm else "FAIL", "listed in sitemap.xml")
    page = f"{slug}.html"
    for name, path, needle in (("archive page", "episodes/index.html", page), ("homepage", "index.html", f"episodes/{page}")):
        t = (ROOT / path).read_text()
        rec("PASS" if needle in t else "WARN", f"linked from the {name}")
    cfg = json.loads((ROOT / "data" / "episodes.json").read_text())
    me = next((e for e in cfg["episodes"] if e.get("page") == page), None)
    sib = [e for e in cfg["episodes"] if me and e["series"] == me["series"] and e.get("page") and e["page"] != page]
    linking = [e["page"] for e in sib if page in (ROOT / "episodes" / e["page"]).read_text()]
    rec("PASS" if linking or not sib else "WARN", f"linked from {len(linking)} sibling episode page(s)")

    fails = results.count("FAIL")
    print(f"\n{results.count('PASS')} pass, {results.count('WARN')} warn, {fails} fail")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1], local="--local" in sys.argv)
