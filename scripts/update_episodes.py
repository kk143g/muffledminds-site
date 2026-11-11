#!/usr/bin/env python3
"""Sync the website's episode lists with the YouTube channel.

Run weekly by .github/workflows/update-episodes.yml (and by hand with
`python3 scripts/update_episodes.py`; add --no-fetch to only re-render).

1. Reads the channel's public RSS feed and adds any new long-form videos
   (Shorts are skipped) to data/episodes.json.
2. Re-renders the episode cards on the homepage (latest 9) and the tabbed
   archive in episodes/index.html, plus the archive's ItemList JSON-LD.

New series: add an entry to "series" in data/episodes.json with a "match" list
of lowercase title fragments. Videos matching no series go to "podcast".
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "episodes.json"
CHANNEL_ID = "UCouniEJHJulndxq3Rakon7Q"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
SITE = "https://muffledminds.com"
HOME_COUNT = 9
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def get(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0 (muffledminds-site updater)"})
    return urllib.request.urlopen(req, timeout=30)


def is_short(vid):
    """/shorts/<id> answers 200 for Shorts and redirects (3xx) for normal videos."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        r = opener.open(urllib.request.Request(f"https://www.youtube.com/shorts/{vid}", method="HEAD",
                        headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
        return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        return True  # when unsure, don't publish a possible Short


def duration_minutes(vid):
    """Best effort: the watch page carries lengthSeconds. Returns None if unavailable."""
    try:
        page = get(f"https://www.youtube.com/watch?v={vid}").read().decode("utf-8", "ignore")
        m = re.search(r'"lengthSeconds":"(\d+)"', page)
        return round(int(m.group(1)) / 60) if m else None
    except Exception:
        return None


def clean_title(raw):
    parts = [p.strip() for p in raw.split("|")]
    keep = [p for p in parts if p and not re.search(
        r"muffled minds|find your clarity|^(ep|episode|s\d+)\s*[e#]?\s*#?\s*\d+$|^s\d+\s*e\d+$|^e\d+$", p, re.I)]
    return " | ".join(keep) or raw.strip()


def label_for(raw, series_key, series_name, eps):
    m = re.search(r"\bS(\d+)\s*E(\d+)\b", raw, re.I)
    if m:
        return f"SEASON {int(m.group(1))} · EP {int(m.group(2))}"
    m = re.search(r"(?:ep(?:isode)?\.?\s*#?\s*|e)(\d+)\s*$", raw.strip(), re.I)
    n = int(m.group(1)) if m else None
    if series_key == "podcast":
        return f"EP #{n}" if n else "PODCAST"
    if n is None:
        n = 1 + sum(1 for e in eps if e["series"] == series_key)
    return f"{series_name.upper()} #{n:02d}"


def series_for(title, series):
    low = title.lower()
    for s in series:
        if any(f in low for f in s["match"]):
            return s
    return next(s for s in series if s["key"] == "podcast")


def fetch_new(cfg):
    feed = ET.fromstring(get(FEED).read())
    known = {e["id"] for e in cfg["episodes"]}
    added = []
    for entry in feed.findall("a:entry", NS):
        vid = entry.find("yt:videoId", NS).text
        if vid in known:
            continue
        raw = entry.find("a:title", NS).text or ""
        published = entry.find("a:published", NS).text[:10]
        if is_short(vid):
            continue
        s = series_for(raw, cfg["series"])
        ep = {
            "id": vid,
            "title": clean_title(raw),
            "label": label_for(raw, s["key"], s["name"], cfg["episodes"] + added),
            "series": s["key"],
            "date": published,
            "minutes": duration_minutes(vid),
            "guest": "",
            "page": "",
        }
        added.append(ep)
        print("added:", vid, ep["label"], ep["title"])
    cfg["episodes"].extend(added)
    cfg["episodes"].sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return added


def fmt_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d).strftime("%-d %b %Y")


def meta_line(e):
    bits = []
    if e.get("minutes"):
        bits.append(f"{e['minutes']} min")
    if e.get("guest"):
        bits.append(html.escape(e["guest"]))
    bits.append(fmt_date(e["date"]))
    return " &middot; ".join(bits)


def card(e, prefix):
    local = e.get("page")
    href = f"{prefix}{local}" if local else f"https://www.youtube.com/watch?v={e['id']}"
    ext = "" if local else ' target="_blank" rel="noopener"'
    t = html.escape(e["title"])
    return (
        f'      <a class="ep-card" href="{href}"{ext}>\n'
        f'        <div class="ep-thumb"><img src="https://img.youtube.com/vi/{e["id"]}/hqdefault.jpg" alt="{t} thumbnail" loading="lazy">'
        f'<span class="play"><i class="fa-solid fa-circle-play"></i></span></div>\n'
        f'        <div class="ep-body">\n'
        f'          <div class="ep-num">{html.escape(e["label"])}</div>\n'
        f'          <h3>{t}</h3>\n'
        f'          <div class="ep-meta">{meta_line(e)}</div>\n'
        f'        </div>\n'
        f'      </a>\n'
    )


def replace_block(text, name, body):
    pat = re.compile(rf"(<!-- {name}:START -->\n).*?(<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        sys.exit(f"marker {name} missing")
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def tabs_html(cfg, prefix, limit, archive):
    """Series tabs + one card grid per series. Archive: all cards (JS pages them 9 at a time)."""
    eps = cfg["episodes"]
    tabs, panels = [], []
    for i, s in enumerate(cfg["series"]):
        mine = [e for e in eps if e["series"] == s["key"]]
        if not mine and s["key"] != "podcast":
            continue
        k = s["key"]
        on = i == 0
        shown = mine if limit is None else mine[:limit]
        tabs.append(
            f'      <button class="ep-tab{" is-active" if on else ""}" role="tab" id="{"" if archive else "h-"}tab-{k}" aria-controls="{"" if archive else "h-"}panel-{k}" '
            f'aria-selected="{"true" if on else "false"}" data-tab="{k}">{html.escape(s["name"])} <span>{len(mine)}</span></button>\n')
        more = ('      <div class="view-all ep-more-wrap" hidden><button type="button" class="btn btn-outline ep-more">'
                '<i class="fa-solid fa-chevron-down"></i> Show more episodes</button></div>\n') if archive else ""
        panels.append(
            f'    <div class="ep-panel" role="tabpanel" id="{"" if archive else "h-"}panel-{k}" aria-labelledby="{"" if archive else "h-"}tab-{k}" data-panel="{k}"{"" if on else " hidden"}>\n'
            f'      <div class="ep-grid{" ep-grid-3" if archive else ""}">\n' + "".join(card(e, prefix) for e in shown) + '      </div>\n'
            + more + '    </div>\n')
    cls = "ep-tabs ep-tabs-top" if archive else "ep-tabs"
    return (f'    <div class="{cls}" role="tablist" aria-label="Episode series"{" data-hash" if archive else ""}>\n'
            + "".join(tabs) + '    </div>\n' + "".join(panels))


def render(cfg):
    eps = cfg["episodes"]

    home = ROOT / "index.html"
    home.write_text(replace_block(home.read_text(), "HOME-EPISODES",
                                  tabs_html(cfg, "episodes/", limit=HOME_COUNT, archive=False)))

    body = tabs_html(cfg, "", limit=None, archive=True)
    arch = ROOT / "episodes" / "index.html"
    text = replace_block(arch.read_text(), "EPISODES", body)

    items = []
    for n, e in enumerate(eps, 1):
        url = f"{SITE}/episodes/{e['page']}" if e.get("page") else f"https://www.youtube.com/watch?v={e['id']}"
        items.append({"@type": "ListItem", "position": n, "url": url, "name": e["title"]})
    ld = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": "Muffled Minds Podcast Episodes",
                     "itemListElement": items}, indent=2, ensure_ascii=False)
    text = replace_block(text, "EPISODES-LD", f'<script type="application/ld+json">\n{ld}\n</script>\n')
    arch.write_text(text)


def main():
    cfg = json.loads(DATA.read_text())
    if "--no-fetch" not in sys.argv:
        fetch_new(cfg)
    DATA.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    render(cfg)
    print(f"{len(cfg['episodes'])} episodes")


if __name__ == "__main__":
    main()
