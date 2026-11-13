#!/usr/bin/env python3
"""Refresh the three numbers in the homepage stats row (YouTube subscribers, episodes & shorts, Instagram followers).

    python3 scripts/update_stats.py            # update index.html in place
    python3 scripts/update_stats.py --dry-run  # only print what it found

YouTube: reads the public channel page (no login, no API key). Instagram: official Graph API, only if INSTAGRAM_USER_ID and
INSTAGRAM_TOKEN are set; otherwise the Instagram number stays as it is.
If a source fails or returns an implausible number, that stat keeps its current value; nothing is ever blanked.
Run every 2 days by .github/workflows/update-stats.yml.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
YT = "https://www.youtube.com/channel/UCouniEJHJulndxq3Rakon7Q/videos"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def parse_count(s):
    """'7.22K' -> 7220, '1,790' -> 1790, '1.2M' -> 1200000"""
    s = s.replace(",", "").strip()
    mult = {"K": 1e3, "M": 1e6}.get(s[-1:].upper(), 1)
    return int(round(float(s.rstrip("KMkm")) * mult))


def short(n):
    """7220 -> '7.2K+' ; 1790 -> '1.8K+' ; 850 -> '850+'"""
    if n >= 1000:
        return f"{n / 1000:.1f}K+".replace(".0K", "K")
    return f"{n}+"


def youtube():
    html = get(YT)
    subs = re.search(r'"content":"([\d.,]+[KM]?) subscribers"', html)
    vids = set(re.findall(r'"content":"([\d,]+) videos"|(?<![\d,.])([\d,]{2,}) videos', html))
    vids = {a or b for a, b in vids}
    return (parse_count(subs.group(1)) if subs else None), vids


def instagram():
    """Official Instagram Graph API. Needs two values (GitHub secrets in the workflow):
    INSTAGRAM_USER_ID and INSTAGRAM_TOKEN (a long-lived token of a Business/Creator account). Without them: skipped.
    Instagram blocks automated page reading, so the public profile page is deliberately not scraped."""
    uid, token = os.environ.get("INSTAGRAM_USER_ID"), os.environ.get("INSTAGRAM_TOKEN")
    if not (uid and token):
        return None
    url = f"https://graph.facebook.com/v21.0/{uid}?fields=followers_count&access_token={token}"
    return json.loads(get(url)).get("followers_count")


def current(text, label):
    m = re.search(r'<b>([^<]*)</b><span>' + re.escape(label) + r'</span>', text)
    return m.group(1) if m else None


def num_of(shown):
    m = re.match(r"([\d.,]+)(K?)", shown or "")
    return parse_count(m.group(1) + m.group(2)) if m else None


def main(dry):
    text = INDEX.read_text()
    found = {}
    try:
        subs, vids = youtube()
        if subs:
            found["YouTube Subscribers"] = short(subs)
        old = num_of(current(text, "Episodes &amp; Shorts"))
        if len(vids) == 1:
            found["Episodes &amp; Shorts"] = str(parse_count(next(iter(vids))))
        else:
            print("videos count ambiguous or missing:", vids)
    except Exception as ex:
        print("YouTube fetch failed:", ex)
    try:
        ig = instagram()
        if ig:
            found["Instagram Community"] = short(ig)
        else:
            print("Instagram: no API token set - keeping current value")
    except Exception as ex:
        print("Instagram fetch failed:", ex, "- keeping current value")

    changed = False
    for label, new in found.items():
        old = current(text, label)
        if old is None:
            print(f"! stat row '{label}' not found in index.html")
            continue
        o, n = num_of(old), num_of(new)
        if o and n and (n < o * 0.5 or n > o * 3):
            print(f"! {label}: {old} -> {new} looks implausible, skipped")
            continue
        print(f"{label}: {old} -> {new}")
        if new != old:
            text = text.replace(f"<b>{old}</b><span>{label}</span>", f"<b>{new}</b><span>{label}</span>")
            changed = True
    if changed and not dry:
        INDEX.write_text(text)
        print("index.html updated")
    elif not changed:
        print("no change")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
