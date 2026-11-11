#!/usr/bin/env python3
"""Build one episode detail page from data/episode-pages/<slug>.json.

    python3 scripts/build_episode_page.py find-your-clarity-05

Writes episodes/<slug>.html, sets "page" for that video in data/episodes.json,
re-renders the episode lists (homepage + archive) and adds the page to sitemap.xml.
The JSON holds everything on the page: description, guest, chapters, transcript,
topics, takeaways and FAQ (see data/episode-pages/find-your-clarity-05.json).
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://muffledminds.com"
e = html.escape

ICON = {  # topic chip icons (Font Awesome free)
    "mindset": "lightbulb", "mental": "brain", "business": "briefcase", "comedy": "face-laugh-beam",
    "society": "people-group", "affairs": "newspaper", "education": "graduation-cap", "sports": "futbol",
    "stories": "hand-holding-heart", "psychology": "brain", "relationships": "heart", "power": "chess-king",
    "ai": "robot", "parenting": "children", "career": "user-tie", "health": "heart-pulse", "default": "comments",
}


def mmss(sec):
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def iso_dur(sec):
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s and not h else "")


def long_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d).strftime("%-d %B %Y")


def heading_label(d, ser):
    """Top-of-page label, e.g. 'SERIES: FIND YOUR CLARITY · EPISODE: 05' or 'PODCAST · SEASON 2 · EPISODE: 03'."""
    if d.get("heading_label"):
        return d["heading_label"], d.get("breadcrumb_label", d["heading_label"])
    lab = d["label"]
    season = re.search(r"SEASON\s+(\d+)", lab, re.I)
    num = re.search(r"(?:#|EP\s*#?\s*|EPISODE\s*#?\s*)(\d+)", lab, re.I)
    ep = f"EPISODE: {int(num.group(1)):02d}" if num else ""
    if ser["key"] == "podcast":
        head = ["PODCAST"] + ([f"SEASON {int(season.group(1))}"] if season else [])
    else:
        head = [f"SERIES: {ser['name'].upper()}"]
    parts = head + ([ep] if ep else [])
    crumb = " · ".join([ser["name"]] + ([f"Season {int(season.group(1))}"] if season else []) + ([f"Episode {int(num.group(1)):02d}"] if num else []))
    return " · ".join(parts), crumb


SECTIONS = [("about", "About This Episode"), ("discuss", "We discuss"), ("takeaways", "Key Takeaways"),
            ("chapters", "Chapters"), ("guest", "About The Guest"), ("transcript", "Full Transcript"),
            ("faq", "Frequently Asked Questions")]


def topic_chip(t):
    icon = ICON.get(t.get("icon", "default"), ICON["default"])
    return f'<span class="topic-tag"><i class="fa-solid fa-{icon}"></i> {e(t["label"])}</span>'


def related_cards(cfg, vid, series, n=3):
    """Other episodes from the same series/playlist, newest first (same cards as the episode lists)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import update_episodes
    mine = [x for x in cfg["episodes"] if x["series"] == series and x["id"] != vid][:n]
    return "".join(update_episodes.card(x, "") for x in mine)


def more_heading(cfg, series_key):
    ser = next(s for s in cfg["series"] if s["key"] == series_key)
    if ser["key"] == "podcast":
        return "More From Muffled Minds Podcast", "Browse All Podcast Episodes"
    return (f'More From Muffled Minds <span class="gold">Series: {e(ser["name"])}</span>',
            f'Browse All {e(ser["name"])} Episodes')


def refresh_related(cfg):
    """Rewrite the 'Keep Listening' block of every episode page: series-aware heading, same-series cards."""
    pat = re.compile(
        r'(<div class="eyebrow">Keep Listening</div>\s*<h2>)(.*?)(</h2>\s*</div>\s*<div class="ep-grid">\n)(.*?)'
        r'(    </div>\n    <div class="view-all">\n      <a href=")([^"]*)(" class="btn btn-outline"><i class="fa-solid fa-list"></i> )(.*?)(</a>)', re.S)
    n = 0
    for ep in cfg["episodes"]:
        if not ep.get("page"):
            continue
        path = ROOT / "episodes" / ep["page"]
        if not path.exists():
            continue
        title, btn = more_heading(cfg, ep["series"])
        cards = related_cards(cfg, ep["id"], ep["series"])
        text = path.read_text()
        new, k = pat.subn(lambda m: m.group(1) + title + m.group(3) + cards + m.group(5)
                          + f"index.html#{ep['series']}" + m.group(7) + btn + m.group(9), text, count=1)
        if k and new != text:
            path.write_text(new)
            n += 1
    return n


def build(slug):
    d = json.loads((ROOT / "data" / "episode-pages" / f"{slug}.json").read_text())
    cfg = json.loads((ROOT / "data" / "episodes.json").read_text())
    vid, url = d["id"], f"{SITE}/episodes/{slug}.html"
    ser = next(s for s in cfg["series"] if s["key"] == d["series"])
    playlist = ser.get("playlist") or "https://youtube.com/@muffledminds"
    yt = f"https://www.youtube.com/watch?v={vid}"
    title, seo_desc = d["title"], d["seo_description"]
    mins = round(d["duration"] / 60)
    guest = d["guest"]
    head_label, crumb_label = heading_label(d, ser)
    more_title, more_btn = more_heading(cfg, d["series"])
    jump = "\n".join(f'      <a href="#{k}">{e(v)}</a>' for k, v in SECTIONS)

    # ---- JSON-LD -----------------------------------------------------------
    transcript_text = " ".join(p["text"] for p in d["transcript"])
    clips = [{"@type": "Clip", "name": c["title"], "startOffset": int(c["start"]),
              "endOffset": int(c["end"]), "url": f"{yt}&t={int(c['start'])}s"} for c in d["chapters"]]
    ld = [
        {"@context": "https://schema.org", "@type": "PodcastEpisode", "url": url, "name": title,
         "datePublished": d["date"], "description": seo_desc, "timeRequired": iso_dur(d["duration"]),
         "keywords": ", ".join(d["keywords"]),
         "associatedMedia": {"@type": "MediaObject", "contentUrl": yt},
         "partOfSeries": {"@type": "PodcastSeries", "name": "Muffled Minds", "url": SITE + "/"},
         "actor": {"@type": "Person", "name": guest["name"], "jobTitle": guest["role"]}},
        {"@context": "https://schema.org", "@type": "VideoObject", "name": title, "description": seo_desc,
         "thumbnailUrl": f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg", "uploadDate": d["date"],
         "duration": iso_dur(d["duration"]), "embedUrl": f"https://www.youtube.com/embed/{vid}", "contentUrl": yt,
         "inLanguage": "ur", "transcript": transcript_text, "hasPart": clips},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Episodes", "item": SITE + "/episodes/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
            for q in d["faq"]]},
    ]
    ld_html = "\n".join(f'<script type="application/ld+json">\n{json.dumps(x, indent=2, ensure_ascii=False)}\n</script>' for x in ld)

    # ---- body pieces ---------------------------------------------------------
    chapters = "\n".join(
        f'        <li><a href="{yt}&amp;t={int(c["start"])}s" data-seek="{int(c["start"])}" target="_blank" rel="noopener">'
        f'<span class="ch-time">{mmss(c["start"])}</span><span class="ch-title">{e(c["title"])}</span></a></li>'
        for c in d["chapters"])
    discuss = "\n".join(f"        <li>{e(x)}</li>" for x in d["we_discuss"])
    takeaways = "\n".join(f"        <li>{e(x)}</li>" for x in d["takeaways"])
    summary = "\n".join(f"      <p>{e(p)}</p>" for p in d["summary"])
    topics = "\n      ".join(topic_chip(t) for t in d["topics"])
    faq = "\n".join(
        f'      <details class="faq-item"><summary>{e(q["q"])}</summary><p>{e(q["a"])}</p></details>' for q in d["faq"])
    def tr_html(items):
        return "\n".join(
            f'          <p><a class="ts" href="{yt}&amp;t={int(p["start"])}s" data-seek="{int(p["start"])}" target="_blank" rel="noopener">{mmss(p["start"])}</a> {e(p["text"])}</p>'
            for p in items)
    if d.get("transcript_en"):
        transcript_block = (
            '        <div class="tr-tabs" role="tablist" aria-label="Transcript language">\n'
            '          <button type="button" class="tr-tab is-active" role="tab" id="tr-tab-ur" aria-controls="tr-ur" aria-selected="true" data-tr="ur">Roman Urdu <span>as spoken in the video</span></button>\n'
            '          <button type="button" class="tr-tab" role="tab" id="tr-tab-en" aria-controls="tr-en" aria-selected="false" data-tr="en">English</button>\n'
            '        </div>\n'
            f'        <div class="tr-panel" role="tabpanel" id="tr-ur" aria-labelledby="tr-tab-ur" lang="ur-Latn">\n{tr_html(d["transcript"])}\n        </div>\n'
            f'        <div class="tr-panel" role="tabpanel" id="tr-en" aria-labelledby="tr-tab-en" lang="en" hidden>\n{tr_html(d["transcript_en"])}\n        </div>')
    else:
        transcript_block = f'        <div class="tr-panel">\n{tr_html(d["transcript"])}\n        </div>'
    glinks = "".join(
        f'<a href="{e(l["url"])}" target="_blank" rel="noopener" class="btn btn-outline"><i class="fa-solid fa-link"></i> {e(l["label"])}</a>'
        for l in guest.get("links", []))
    bio = "\n".join(f"        <p>{e(p)}</p>" for p in guest["bio"])

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(d["seo_title"])}</title>
<meta name="description" content="{e(seo_desc)}">
<meta name="keywords" content="{e(", ".join(d["keywords"]))}">
<meta name="robots" content="index, follow, max-image-preview:large, max-video-preview:-1">
<link rel="canonical" href="{url}">

<meta property="og:type" content="video.episode">
<meta property="og:site_name" content="Muffled Minds">
<meta property="og:title" content="{e(d["seo_title"])}">
<meta property="og:description" content="{e(seo_desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://img.youtube.com/vi/{vid}/maxresdefault.jpg">
<meta property="video:release_date" content="{d["date"]}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(d["seo_title"])}">
<meta name="twitter:description" content="{e(seo_desc)}">
<meta name="twitter:image" content="https://img.youtube.com/vi/{vid}/maxresdefault.jpg">

<meta name="theme-color" content="#050505">
<link rel="icon" type="image/png" href="../assets/favicon.png">
<link rel="apple-touch-icon" href="../assets/icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<link rel="stylesheet" href="../css/style.css">

{ld_html}
</head>
<body>

<header>
  <div class="nav">
    <a href="../index.html" class="brand">
      <img src="../assets/icon.png" alt="Muffled Minds logo">
      <span>MUFFLED MINDS</span>
    </a>
    <nav class="nav-links">
      <a href="../index.html#about">About</a>
      <a href="../index.html#topics">Topics</a>
      <a href="../index.html#episodes">Episodes</a>
      <a href="../index.html#guests">Guests</a>
      <a href="../index.html#community">Community</a>
      <a href="../index.html#contact">Contact</a>
      <a href="https://youtube.com/@muffledminds" target="_blank" rel="noopener" class="nav-cta">Watch on YouTube</a>
    </nav>
    <button class="menu-toggle" aria-label="Toggle menu"><span></span><span></span><span></span></button>
  </div>
</header>

<section class="ep-detail">
  <div class="wrap">
    <div class="breadcrumb"><a href="../index.html">Home</a> / <a href="index.html">Episodes</a> / {e(crumb_label)}</div>
    <div class="ep-num">{e(head_label)}</div>
    <h1>{e(title)}</h1>
    <div class="ep-detail-meta"><span><i class="fa-regular fa-calendar"></i> {long_date(d["date"])}</span><span><i class="fa-regular fa-clock"></i> {mins} min</span><span><i class="fa-solid fa-user"></i> {e(guest["name"])}</span><span><i class="fa-brands fa-youtube"></i> {e(ser["name"])}</span></div>

    <div class="video-embed">
      <iframe id="ep-player" src="https://www.youtube.com/embed/{vid}?enablejsapi=1&amp;rel=0" title="{e(title)}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe>
    </div>

    <div class="hero-ctas" style="justify-content:flex-start;">
      <a href="{yt}" target="_blank" rel="noopener" class="btn btn-primary"><i class="fa-brands fa-youtube"></i> Watch on YouTube</a>
      <a href="{playlist}" target="_blank" rel="noopener" class="btn btn-outline"><i class="fa-solid fa-list-ul"></i> Full {e(ser["name"])} playlist</a>
      <a href="index.html" class="btn btn-outline"><i class="fa-solid fa-list"></i> All Episodes</a>
    </div>

    <nav class="ep-jump" aria-label="Jump to a section">
{jump}
    </nav>

    <div class="ep-block" id="about">
      <h2>About This Episode</h2>
{summary}
      <h3 id="discuss">We discuss</h3>
      <ul class="ep-list">
{discuss}
      </ul>
    </div>

    <div class="ep-block" id="takeaways">
      <h2>Key Takeaways</h2>
      <ul class="ep-list">
{takeaways}
      </ul>
    </div>

    <div class="ep-block" id="chapters">
      <h2>Chapters</h2>
      <ol class="ep-chapters">
{chapters}
      </ol>
    </div>

    <div class="ep-block" id="guest">
      <h2>About The Guest</h2>
      <div class="guest-card">
        <div>
          <div class="guest-name">{e(guest["name"])}</div>
          <div class="guest-role">{e(guest["role"])}</div>
{bio}
          <div class="hero-ctas" style="justify-content:flex-start;margin-top:14px;">{glinks}</div>
        </div>
      </div>
    </div>

    <div class="ep-block" id="transcript">
      <h2>Full Transcript</h2>
      <p class="ep-note">{e(d["transcript_note"])}</p>
      <details class="transcript">
        <summary><i class="fa-solid fa-chevron-down"></i> Read the full transcript</summary>
        <div class="transcript-body">
{transcript_block}
        </div>
      </details>
    </div>

    <div class="ep-block" id="faq">
      <h2>Frequently Asked Questions</h2>
{faq}
    </div>
  </div>
</section>

<section id="topics" class="alt">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">Topics Discussed</div>
      <h2>What This Episode <span class="gold">Covers</span></h2>
      <p>Find Your Clarity takes one big question and works through it. Here is what this conversation touches on.</p>
    </div>
    <div class="topic-tags">
      {topics}
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <div class="section-head">
      <div class="eyebrow">Keep Listening</div>
      <h2>{more_title}</h2>
    </div>
    <div class="ep-grid">
{related_cards(cfg, vid, d["series"])}    </div>
    <div class="view-all">
      <a href="index.html#{d["series"]}" class="btn btn-outline"><i class="fa-solid fa-list"></i> {more_btn}</a>
    </div>
  </div>
</section>

<footer>
  <div class="foot-brand">
    <img src="../assets/icon.png" alt="Muffled Minds">
    MUFFLED MINDS
  </div>
  <div class="foot-links">
    <a href="https://youtube.com/@muffledminds" target="_blank" rel="noopener">YouTube</a>
    <a href="https://www.instagram.com/muffled.minds" target="_blank" rel="noopener">Instagram</a>
    <a href="https://www.facebook.com/muffledmindsofficial" target="_blank" rel="noopener">Facebook</a>
    <a href="https://www.tiktok.com/@muffled.minds" target="_blank" rel="noopener">TikTok</a>
    <a href="https://x.com/muffled_minds" target="_blank" rel="noopener">X</a>
    <a href="https://www.linkedin.com/company/145323402" target="_blank" rel="noopener">LinkedIn</a>
    <a href="https://podcasts.apple.com/us/podcast/muffled-minds/id1838959441" target="_blank" rel="noopener">Apple Podcasts</a>
    <a href="https://open.spotify.com/show/2SM3ZEF0dohVdkWgbwpjap" target="_blank" rel="noopener">Spotify</a>
    <a href="https://www.podchaser.com/podcasts/muffled-minds-6209711" target="_blank" rel="noopener">Podchaser</a>
    <a href="mailto:contact@muffledminds.com">contact@muffledminds.com</a>
  </div>
  <p>&copy; <span class="year"></span> Muffled Minds. Find your clarity.</p>
</footer>

<script src="../js/script.js"></script>
<script src="../js/episode-player.js"></script>
</body>
</html>
'''
    (ROOT / "episodes" / f"{slug}.html").write_text(page)

    # link the episode lists to the new page, re-render them, add to the sitemap
    for ep in cfg["episodes"]:
        if ep["id"] == vid:
            ep["page"] = f"{slug}.html"
    (ROOT / "data" / "episodes.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    sm = ROOT / "sitemap.xml"
    text = sm.read_text()
    if url not in text:
        entry = (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{d['date']}</lastmod>\n"
                 f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n")
        sm.write_text(text.replace("</urlset>", entry + "</urlset>"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import update_episodes
    update_episodes.render(cfg)
    print("related blocks refreshed on", refresh_related(cfg), "pages")
    print("built", f"episodes/{slug}.html")


if __name__ == "__main__":
    build(sys.argv[1])
