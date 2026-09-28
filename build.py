#!/usr/bin/env python3
"""Build the site from data/*.json and pages/*.html.

Standard library only. Edit the sources, never the generated files:

    data/site.json           identity, links, bio metadata, service
    data/publications.json   every paper (single source of truth)
    data/news.json           news items
    data/experience.json     experience rows
    pages/intro.html         biography prose

Generated: index.html, papers/index.html, papers/<slug>/index.html, 404.html,
llms.txt, robots.txt, sitemap.xml. Run `python3 build.py` after any edit;
`python3 build.py --check` exits non-zero if any generated file is stale.
"""

import html
import json
import pathlib
import re
import shutil
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent
GENERATED = {}


# ------------------------------------------------------------------ utils ---

def esc(text):
    return html.escape(str(text), quote=True)


def plain(text):
    """Markup-free text for meta tags, JSON-LD and llms.txt: tags stripped, entities decoded."""
    return html.unescape(re.sub(r"<[^>]+>", "", str(text)))


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def write(relpath, content):
    GENERATED[relpath] = content


def image_size(relpath):
    """(width, height) of a PNG, GIF or JPEG, read from its header."""
    data = (ROOT / relpath).read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + length
    raise ValueError(f"cannot read image size of {relpath}")


def dims(relpath):
    w, h = image_size(relpath)
    return f'width="{w}" height="{h}"'


ICONS = {
    "mail":    '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "cv":      '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "scholar": '<path d="m12 4 10 5-10 5L2 9z"/><path d="M6 11v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5"/>',
    "github":  '<path d="M9 19c-4 1.3-4-2-6-2.5M15 21v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.7 11.7 0 0 0-6.2 0C6.6 2.8 5.6 3.1 5.6 3.1a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.2 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
    "linkedin":'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10v7M8 7v.01M12 17v-4a2 2 0 0 1 4 0v4M12 10v7"/>',
    "pdf":     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "code":    '<path d="m8 6-6 6 6 6"/><path d="m16 6 6 6-6 6"/>',
    "link":    '<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "video":   '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
    "details": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h8"/>',
    "quote":   '<path d="M9 7H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h2v1a3 3 0 0 1-3 3"/><path d="M20 7h-4a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h2v1a3 3 0 0 1-3 3"/>',
    "copy":    '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "sun":     '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon":    '<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z"/>',
}


def icon(name, cls=""):
    extra = f' class="{cls}"' if cls else ""
    return (f'<svg{extra} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
            f'{ICONS[name]}</svg>')


def btn(label, href, icon_name, kind="btn-publication", external=True):
    rel = ' target="_blank" rel="noopener"' if external else ""
    return f'<a class="btn {kind}" href="{esc(href)}"{rel}>{icon(icon_name)} {esc(label)}</a>'


# ------------------------------------------------------- publication bits ---

def authors_html(pub, me):
    marks = set(pub.get("equal_contribution", []))
    out = []
    for name in pub["authors"]:
        # Non-breaking inside a name, so a long list never splits "Xinyuan / Liu".
        label = esc(name).replace(" ", "&nbsp;") + ("*" if name in marks else "")
        out.append(f"<strong>{label}</strong>" if name == me else label)
    return ", ".join(out)


def authors_plain(pub):
    marks = set(pub.get("equal_contribution", []))
    return ", ".join(n + ("*" if n in marks else "") for n in pub["authors"])


def equal_note(pubs):
    return " * denotes equal contribution." if any(p.get("equal_contribution") for p in pubs) else ""


def bib_escape(text):
    return re.sub(r"(?<!\\)([&%_#$])", r"\\\1", text)


def bib_title(title):
    # Protect acronyms and mixed-case words ("LLM", "MaxSAT", "AI") so bibliography
    # styles that lowercase titles keep them as written.
    return re.sub(r"\b([A-Za-z]*[A-Z][A-Za-z]*[A-Z][A-Za-z]*)\b", r"{\1}", bib_escape(title))


def bibtex(pub):
    if pub.get("bibtex"):
        return pub["bibtex"]
    last = lambda n: n.split()[-1]
    names = " and ".join(f"{last(n)}, {' '.join(n.split()[:-1])}" for n in pub["authors"])
    first = re.sub(r"[^a-z]", "", last(pub["authors"][0]).lower())
    word = re.sub(r"[^a-z]", "", pub["title"].split(":")[0].split()[0].lower())
    title = bib_title(pub["title"])
    for word_ in pub.get("bib_protect", []):
        title = title.replace(word_, "{" + word_ + "}")
    field = "journal" if pub["bib_type"] == "article" else "booktitle"
    return (f"@{pub['bib_type']}{{{first}{pub['year']}{word},\n"
            f"    title={{{title}}},\n"
            f"    author={{{bib_escape(names)}}},\n"
            f"    {field}={{{bib_escape(pub['bib_venue'])}}},\n"
            f"    year={{{pub['year']}}}\n}}")


LINK_ORDER = [
    ("arxiv", "arXiv", "pdf"), ("pdf", "PDF", "pdf"), ("openreview", "OpenReview", "link"),
    ("project", "Project page", "link"), ("code", "Code", "code"), ("video", "Video", "video"),
    ("demo", "Hardware demos", "video"),
]


def pub_links(pub, prefix, with_details=True, with_bibtex=True):
    links, labels = pub.get("links", {}), pub.get("link_labels", {})
    parts = [btn(labels.get(k, label), links[k], ico) for k, label, ico in LINK_ORDER if links.get(k)]
    if with_details and pub.get("page", True):
        parts.append(btn("Details", f"{prefix}papers/{pub['slug']}/", "details", external=False))
    if with_bibtex and pub.get("bib_type"):
        bid = f"bib-{pub['slug']}"
        parts.append(f'<button type="button" class="btn btn-publication" data-bibtex-toggle="{bid}" '
                     f'aria-expanded="false" aria-controls="{bid}">{icon("quote")} BibTeX</button>')
    return parts


def venue_html(pub):
    out = esc(pub["venue_display"])
    if pub.get("award"):
        out += f' &middot; <span class="pub-award">{esc(pub["award"])}</span>'
    return out


def paper_url(site, pub):
    if pub.get("page", True):
        return f"{site['url']}/papers/{pub['slug']}/"
    links = pub.get("links", {})
    return links.get("arxiv") or links.get("openreview") or site["url"] + "/#publications"


# ------------------------------------------------------------ page chrome ---

# Loaded without blocking render: where Google is unreachable the page still
# appears at once in the fallback font instead of waiting for a timeout.
FONT_URL = ("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;"
            "0,9..40,700;1,9..40,400&amp;display=swap")

THEME_INIT = """<script>
// Before first paint: the theme class goes on <html> (the :root colour aliases
// resolve their var() references against that element) so a dark device never
// sees a light flash, and .js lets CSS collapse BibTeX only when it can be opened.
(function () {
  var d = document.documentElement, s = null;
  d.classList.add('js');
  try { s = localStorage.getItem('theme'); } catch (e) {}
  if (s === 'dark' || (s === null && window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    d.classList.add('dark');
  }
})();
</script>"""


def head(site, *, title, description, url_path, prefix, og_type="profile", og_image=None, og_alt=None,
         extra="", ld=(), canonical=True, robots="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"):
    url = site["url"] + "/" + url_path
    image_path = og_image or site["og_image"]
    image = site["url"] + "/" + image_path
    image_alt = og_alt or site["og_image_alt"]
    iw, ih = image_size(image_path)
    desc = esc(plain(description))
    ttl = esc(plain(title))
    ld_html = "".join(
        f'\n<script type="application/ld+json">\n{json.dumps(obj, indent=2, ensure_ascii=False)}\n</script>'
        for obj in ld)
    url_tags = (f'<link rel="canonical" href="{esc(url)}">\n<meta property="og:url" content="{esc(url)}">\n'
                if canonical else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ttl}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{esc(site['name'])}">
<meta name="generator" content="build.py">
<meta name="robots" content="{robots}">
{url_tags}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{ttl}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{esc(image)}">
<meta property="og:image:alt" content="{esc(image_alt)}">
<meta property="og:image:width" content="{iw}">
<meta property="og:image:height" content="{ih}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ttl}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{esc(image)}">
<meta name="twitter:image:alt" content="{esc(image_alt)}">
<meta name="theme-color" content="#F7F9FC" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#12161B" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONT_URL}" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="{FONT_URL}" rel="stylesheet"></noscript>
<link rel="stylesheet" href="{prefix}assets/style.css">
<link rel="icon" href="{prefix}assets/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">
{THEME_INIT}{extra}{ld_html}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<button id="theme-toggle" type="button" aria-label="Dark mode" aria-pressed="false" title="Toggle dark/light mode">{icon("moon", "icon-moon")}{icon("sun", "icon-sun")}</button>
"""


def footer(site, prefix):
    home = prefix or "./"
    return f"""<footer class="site-footer page">
<nav class="footer-links" aria-label="Site"><a href="{home}">{esc(site['name'])}</a> &middot; <a href="{prefix}papers/">Publications</a> &middot; <a href="{prefix}{esc(site['cv'])}">CV</a></nav>
<p>&copy; {esc(site['copyright_year'])} {esc(site['name'])} &middot; <a href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></p>
<p class="credit">Website design adapted from <a href="https://github.com/jonbarron/jonbarron.github.io" target="_blank" rel="noopener">Jon Barron</a>.</p>
</footer>
<script src="{prefix}assets/main.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------ structured ---

def person_ld(site, pubs):
    aff = {"@type": "CollegeOrUniversity", "name": site["affiliation"]["name"], "url": site["affiliation"]["url"]}
    if site["affiliation"].get("department"):
        aff["department"] = {"@type": "Organization", "name": site["affiliation"]["department"]}
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": site["url"] + "/#website", "url": site["url"] + "/",
             "name": site["name"], "inLanguage": "en",
             "publisher": {"@id": site["url"] + "/#person"}},
            {"@type": "Person", "@id": site["url"] + "/#person", "name": site["name"],
             "url": site["url"] + "/", "email": "mailto:" + site["email"],
             "image": site["url"] + "/" + site["profile_image"],
             "jobTitle": "PhD Student in Computer Science",
             "description": plain(site["description"]),
             "knowsAbout": site["research_focus"],
             "affiliation": aff,
             "alumniOf": [{"@type": "CollegeOrUniversity", "name": a} for a in site["alumni_of"]],
             "sameAs": site["same_as"]},
            {"@type": "ItemList", "@id": site["url"] + "/#publications", "name": "Publications",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": p["title"],
                                  "url": paper_url(site, p)} for i, p in enumerate(pubs)]},
        ],
    }


def article_ld(site, pub):
    obj = {
        "@context": "https://schema.org", "@type": "ScholarlyArticle",
        "@id": paper_url(site, pub) + "#article",
        "name": pub["title"], "headline": pub["title"], "url": paper_url(site, pub),
        "datePublished": pub["year"], "inLanguage": "en",
        "author": [{"@type": "Person", "name": a} for a in pub["authors"]],
    }
    # "abstract" only for the authors' own abstract; the site's summaries go in "description".
    if pub.get("abstract"):
        obj["abstract"] = plain(pub["abstract"])
    if pub.get("description"):
        obj["description"] = plain(pub["description"])
    if pub["venue_type"] in ("conference", "workshop"):
        obj["publication"] = {"@type": "PublicationEvent", "name": pub["venue"]}
    image = pub.get("og_image") or pub.get("image")
    if image:
        obj["image"] = site["url"] + "/" + image
    if pub.get("arxiv_id"):
        obj["identifier"] = "arXiv:" + pub["arxiv_id"]
        obj["sameAs"] = "https://arxiv.org/abs/" + pub["arxiv_id"]
    return obj


def citation_meta(pub):
    rows = [f'<meta name="citation_title" content="{esc(pub["title"])}">']
    rows += [f'<meta name="citation_author" content="{esc(a)}">' for a in pub["authors"]]
    rows.append(f'<meta name="citation_publication_date" content="{esc(pub["year"])}">')
    if pub["venue_type"] in ("conference", "workshop"):
        rows.append(f'<meta name="citation_conference_title" content="{esc(pub["venue"])}">')
    if pub.get("arxiv_id"):
        rows.append(f'<meta name="citation_arxiv_id" content="{esc(pub["arxiv_id"])}">')
        rows.append(f'<meta name="citation_pdf_url" content="https://arxiv.org/pdf/{esc(pub["arxiv_id"])}">')
    return "\n" + "\n".join(rows)


# ------------------------------------------------------------- homepage ---

def pub_card(site, pub, prefix):
    thumb = ""
    if pub.get("image"):
        target = (f"{prefix}papers/{pub['slug']}/" if pub.get("page", True)
                  else pub.get("links", {}).get("arxiv"))
        img = (f'<img src="{prefix}{esc(pub["image"])}" alt="{esc(pub["image_alt"])}" {dims(pub["image"])} '
               f'loading="lazy" decoding="async">')
        thumb = f'<a href="{esc(target)}" tabindex="-1" aria-hidden="true">{img}</a>' if target else img
    title = esc(pub["title"])
    if pub.get("page", True):
        title = f'<a href="{prefix}papers/{pub["slug"]}/">{title}</a>'
    elif pub.get("links", {}).get("arxiv"):
        title = f'<a href="{esc(pub["links"]["arxiv"])}" target="_blank" rel="noopener">{title}</a>'
    note = f'<div class="pub-note">{pub["note_html"]}</div>' if pub.get("note_html") else ""
    desc = f'<div class="description">{pub["description"]}</div>' if pub.get("description") else ""
    links = pub_links(pub, prefix)
    links_html = f'<div class="pub-links">{"".join(links)}</div>' if links else ""
    bib = f'<div id="bib-{pub["slug"]}" class="bibtex"><pre>{esc(bibtex(pub))}</pre></div>' if pub.get("bib_type") else ""
    return f"""<li class="pub-item" data-category="{pub['category']}">
<div class="pub-thumb">{thumb}</div>
<div class="pub-body">
<h3 class="pub-title">{title}</h3>
<div class="pub-authors">{authors_html(pub, site['name'])}</div>
<div class="pub-venue">{venue_html(pub)}</div>
{note}{desc}{links_html}{bib}
</div>
</li>"""


def build_index(site, pubs, news, experience, intro):
    prefix = ""
    n_conf = sum(p["category"] == "conference" for p in pubs)
    n_pre = len(pubs) - n_conf
    conf_label = "Conferences &amp; Journals" if any(p["venue_type"] == "journal" for p in pubs) else "Conferences"
    link_row = "".join(
        f'<a class="btn" href="{esc(l["href"])}"'
        + (' target="_blank" rel="noopener"' if l.get("external") else "")
        + f'>{icon(l["icon"])} {esc(l["label"])}</a>'
        + ('<span class="link-break" aria-hidden="true"></span>' if i == 2 else "")
        for i, l in enumerate(site["links"]))
    # Separators are their own elements so narrow screens can drop them and stack the segments.
    tagline = '<span class="sep" aria-hidden="true"> &middot; </span>'.join(
        f'<span class="seg">{esc(t)}</span>' for t in site["tagline"])
    news_rows = "\n".join(
        f'<tr><td class="news-date-cell"><span class="news-date">{esc(n["date"])}</span></td><td>{n["html"]}</td></tr>'
        for n in news)
    exp_rows = "\n".join(
        f'<tr><td class="exp-where"><a class="exp-org" href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["org"])}</a>'
        f'<br><span class="exp-when">{esc(e["when"])}</span></td>'
        f'<td><span class="exp-role">{esc(e["role"])}</span>{", " + esc(e["detail"]) if e.get("detail") else ""}. {e["html"]}</td></tr>'
        for e in experience)
    cards = "\n".join(pub_card(site, p, prefix) for p in pubs)
    service = "\n".join(
        f'<p class="service-line"><span class="service-label">{esc(s["label"])}</span> {esc(s["venues"])}</p>'
        for s in site["service"])

    page = head(site, title=site["title"], description=site["description"], url_path="",
                prefix=prefix, ld=[person_ld(site, pubs)])
    page += f"""
<main id="main" class="page">

  <section class="intro-grid">
    <div class="intro-text">
      <h1 class="h-name">{esc(site['name'])}</h1>
      <p class="h-tagline">{tagline}</p>
{intro.rstrip()}
    </div>
    <img class="intro-photo" src="{esc(site['profile_image'])}" alt="{esc(site['profile_image_alt'])}" {dims(site['profile_image'])} fetchpriority="high">
    <nav class="link-row" aria-label="Contact and profiles">{link_row}</nav>
  </section>

  <section class="home-section" aria-labelledby="news-heading">
    <h2 class="h-section" id="news-heading">News</h2>
    <div class="news-box" tabindex="0" role="region" aria-label="News items (scrollable)">
      <table class="news-table">
        <tbody>
{news_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section class="home-section" id="publications" aria-labelledby="research-heading">
    <h2 class="h-section" id="research-heading">Research</h2>
    <p class="section-note">See my <a href="{esc(site['cv'])}">CV</a> and <a href="{esc(site['scholar'])}" target="_blank" rel="noopener">Google Scholar</a>.{equal_note(pubs)}</p>
    <div class="tab-navigation" role="tablist" aria-label="Filter publications">
      <a class="tab-button active" role="tab" id="tab-all" href="#all" data-tab="all" aria-selected="true" aria-controls="pub-panel" tabindex="0">All <span class="pub-tab-count">({len(pubs)})</span></a>
      <a class="tab-button" role="tab" id="tab-conferences" href="#conferences" data-tab="conferences" aria-selected="false" aria-controls="pub-panel" tabindex="-1">{conf_label} <span class="pub-tab-count">({n_conf})</span></a>
      <a class="tab-button" role="tab" id="tab-preprints" href="#preprints" data-tab="preprints" aria-selected="false" aria-controls="pub-panel" tabindex="-1">Preprints<span class="tab-long"> &amp; Workshops</span> <span class="pub-tab-count">({n_pre})</span></a>
    </div>
    <div id="pub-panel">
      <ol class="pub-list" id="pub-list" data-filter="all">
{cards}
      </ol>
    </div>
  </section>

  <section class="home-section" aria-labelledby="experience-heading">
    <h2 class="h-section" id="experience-heading">Experience</h2>
    <table class="exp-table">
      <tbody>
{exp_rows}
      </tbody>
    </table>
  </section>

  <section class="home-section" aria-labelledby="service-heading">
    <h2 class="h-section" id="service-heading">Service</h2>
{service}
  </section>

</main>
"""
    page += footer(site, prefix)
    write("index.html", page)


# ----------------------------------------------------------- paper pages ---

def figure_html(f, prefix):
    if f.get("video"):
        sources = "".join(f'<source src="{prefix}{esc(f[k])}" type="{t}">'
                          for k, t in (("video_webm", "video/webm"), ("video", "video/mp4")) if f.get(k))
        media = (f'<video poster="{prefix}{esc(f["poster"])}" {dims(f["poster"])} autoplay muted loop playsinline '
                 f'controls preload="metadata" aria-label="{esc(f["alt"])}">{sources}</video>')
    else:
        media = f'<img src="{prefix}{esc(f["src"])}" alt="{esc(f["alt"])}" {dims(f["src"])} decoding="async">'
    cap = f'<figcaption>{f["caption"]}</figcaption>' if f.get("caption") else ""
    return f'<figure class="paper-figure">{media}{cap}</figure>'


def build_paper(site, pub, prev_pub, next_pub):
    prefix = "../../"
    slug = pub["slug"]
    figs = pub.get("figures") or ([{"src": pub["image"], "alt": pub["image_alt"]}] if pub.get("image") else [])
    figure = (f'<div class="paper-figures paper-figures-{len(figs)}">{"".join(figure_html(f, prefix) for f in figs)}</div>'
              if figs else "")
    if pub.get("abstract"):
        body_title, body = "Abstract", pub["abstract"]
    else:
        body_title, body = "Summary", pub.get("summary") or pub.get("description")
    body_html = f'<section class="paper-section"><h2>{body_title}</h2><p>{body}</p></section>' if body else ""
    note = f'<p class="pub-note">{pub["note_html"]}</p>' if pub.get("note_html") else ""
    equal = '<p class="paper-meta paper-equal">* Equal contribution.</p>' if pub.get("equal_contribution") else ""
    links = pub_links(pub, prefix, with_details=False, with_bibtex=False)
    bib = ""
    if pub.get("bib_type"):
        bib_id = f"bibtex-{slug}"
        bib = f"""<section class="paper-section">
      <h2>BibTeX</h2>
      <pre class="paper-bibtex" id="{bib_id}">{esc(bibtex(pub))}</pre>
      <button type="button" class="btn btn-publication" data-copy-target="{bib_id}">{icon("copy")} <span aria-live="polite">Copy BibTeX</span></button>
    </section>"""
    nav = []
    if prev_pub:
        nav.append(f'<a href="../{prev_pub["slug"]}/">&larr; {esc(prev_pub["short_title"])}</a>')
    nav.append('<a href="../">All publications</a>')
    if next_pub:
        nav.append(f'<a href="../{next_pub["slug"]}/">{esc(next_pub["short_title"])} &rarr;</a>')
    breadcrumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": site["name"], "item": site["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Publications", "item": site["url"] + "/papers/"},
            {"@type": "ListItem", "position": 3, "name": pub["title"], "item": paper_url(site, pub)},
        ]}
    og = pub.get("og_image") or pub.get("image")
    page = head(site, title=f"{pub['title']} — {site['name']}",
                description=pub.get("tldr") or pub.get("description") or pub.get("abstract"),
                url_path=f"papers/{slug}/", prefix=prefix, og_type="article", og_image=og,
                og_alt=(pub.get("og_image_alt") or pub.get("image_alt")) if og else None,
                extra=citation_meta(pub), ld=[article_ld(site, pub), breadcrumb_ld])
    page += f"""
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="{prefix}">{esc(site['name'])}</a> &rsaquo; <a href="../">Publications</a> &rsaquo; <span aria-current="page">{esc(pub['short_title'])}</span>
  </nav>
  <article>
    <header class="paper-header">
      <h1 class="paper-title">{esc(pub['title'])}</h1>
      <p class="paper-authors">{authors_html(pub, site['name'])}</p>
      {equal}
      <p class="paper-meta">{venue_html(pub)}</p>
      {note}
      <div class="pub-links">{"".join(links)}</div>
    </header>
    {figure}
    {body_html}
    {bib}
  </article>
  <nav class="footer-nav" aria-label="Publication navigation">{" &middot; ".join(nav)}</nav>
</main>
"""
    page += footer(site, prefix)
    write(f"papers/{slug}/index.html", page)


def build_papers_index(site, pubs):
    prefix = "../"
    rows = []
    for p in pubs:
        title = esc(p["title"])
        if p.get("page", True):
            title = f'<a href="{p["slug"]}/">{title}</a>'
        rows.append(f"""<li class="pub-item" data-category="{p['category']}">
<div class="pub-body">
<h2 class="pub-title">{title}</h2>
<div class="pub-authors">{authors_html(p, site['name'])}</div>
<div class="pub-venue">{venue_html(p)}</div>
</div>
</li>""")
    page = head(site, title=f"Publications — {site['name']}",
                description=f"All publications by {site['name']}, newest first, each with a summary and citation.",
                url_path="papers/", prefix=prefix)
    page += f"""
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="{prefix}">{esc(site['name'])}</a> &rsaquo; <span aria-current="page">Publications</span></nav>
  <h1 class="h-name page-heading">Publications</h1>
  <p class="section-note">All {len(pubs)} publications, newest first; each links to a page with its summary and citation. See also <a href="{esc(site['scholar'])}" target="_blank" rel="noopener">Google Scholar</a>.{equal_note(pubs)}</p>
  <ol class="pub-list pub-list-compact">
{chr(10).join(rows)}
  </ol>
</main>
"""
    page += footer(site, prefix)
    write("papers/index.html", page)


def build_404(site):
    # GitHub Pages serves this body at every missing URL, so asset paths are
    # absolute and there is no canonical URL to claim.
    page = head(site, title=f"Page not found — {site['name']}", description="This page does not exist.",
                url_path="404.html", prefix="/", canonical=False, robots="noindex")
    page += f"""
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">{esc(site['name'])}</a></nav>
  <h1 class="h-name page-heading">Page not found</h1>
  <p class="section-note">The page you were looking for doesn&rsquo;t exist. Try the <a href="/">homepage</a> or the <a href="/papers/">publication list</a>.</p>
</main>
"""
    page += footer(site, "/")
    write("404.html", page)


# ------------------------------------------------------------ text files ---

def build_llms_txt(site, pubs, news):
    lines = [f"# {site['name']}", "", f"> {plain(site['description'])}", f"> Contact: {site['email']}", "",
             "## Research focus", ""]
    lines += [f"- {r}" for r in site["research_focus"]]
    lines += ["", "## Pages", "",
              f"- [Homepage]({site['url']}/): biography, news, publications, experience, service",
              f"- [Publications]({site['url']}/papers/): all {len(pubs)} publications, each with a summary and BibTeX",
              f"- [CV]({site['url']}/{site['cv']}): curriculum vitae (PDF)", "", "## Profiles", ""]
    lines += [f"- {l['label']}: {l['href']}" for l in site["links"] if l.get("external")]
    lines += ["", "## Publications", ""]
    for p in pubs:
        summary = f" {plain(p['tldr'])}" if p.get("tldr") else ""
        lines.append(f"- [{p['title']}]({paper_url(site, p)}) — {plain(p['venue_display'])}.{summary} "
                     f"Authors: {authors_plain(p)}.")
    if any(p.get("equal_contribution") for p in pubs):
        lines += ["", "(* denotes equal contribution.)"]
    lines += ["", "## Recent news", ""]
    lines += [f"- {n['date']}: {plain(n['html'])}" for n in news]
    lines += ["", "## Service", ""]
    lines += [f"- {s['label']} {s['venues']}" for s in site["service"]]
    write("llms.txt", "\n".join(lines) + "\n")


def build_sitemap(site, pubs):
    urls = [(site["url"] + "/", "1.0"), (site["url"] + "/papers/", "0.8")]
    urls += [(f"{site['url']}/papers/{p['slug']}/", "0.8") for p in pubs if p.get("page", True)]
    body = "\n".join(f"  <url>\n    <loc>{esc(u)}</loc>\n    <lastmod>{site['updated']}</lastmod>\n    <priority>{pr}</priority>\n  </url>"
                     for u, pr in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n')


def build_robots(site):
    blocks = "\n\n".join(f"User-agent: {a}\nAllow: /" for a in ["*"] + site["llm_user_agents"])
    write("robots.txt", "# Everyone, including AI and LLM crawlers, may index this site.\n\n"
          f"{blocks}\n\nSitemap: {site['url']}/sitemap.xml\n")


# ------------------------------------------------------------ validation ---

def validate(site, all_pubs, news, experience, intro):
    errors = []
    slugs = [p.get("slug") for p in all_pubs]
    if len(set(slugs)) != len(slugs):
        errors.append("duplicate publication slugs")
    required = ("slug", "title", "short_title", "authors", "venue", "venue_display", "venue_short",
                "venue_type", "year", "sort_key", "category")
    for p in all_pubs:
        missing = [k for k in required if k not in p]
        if missing:
            errors.append(f"{p.get('slug', '?')}: missing {', '.join(missing)}")
            continue
        if p["category"] not in ("conference", "preprint"):
            errors.append(f"{p['slug']}: category must be conference or preprint")
        if site["name"] not in p["authors"]:
            errors.append(f"{p['slug']}: {site['name']} not in author list")
        for name in p.get("equal_contribution", []):
            if name not in p["authors"]:
                errors.append(f"{p['slug']}: equal_contribution names a non-author {name}")
        paths = ([p["image"]] if p.get("image") else []) + ([p["og_image"]] if p.get("og_image") else [])
        for f in p.get("figures", []):
            if not (f.get("src") or f.get("video")):
                errors.append(f"{p['slug']}: a figure has neither src nor video")
            paths += [f[k] for k in ("src", "video", "video_webm", "poster") if f.get(k)]
            if not f.get("alt"):
                errors.append(f"{p['slug']}: a figure has no alt text")
            if f.get("video") and not f.get("poster"):
                errors.append(f"{p['slug']}: video figure without a poster")
        for path in paths:
            if not (ROOT / path).exists():
                errors.append(f"{p['slug']}: {path} does not exist")
            elif not path.endswith((".mp4", ".webm")):
                try:
                    image_size(path)
                except (ValueError, struct.error, IndexError):
                    errors.append(f"{p['slug']}: unsupported image format {path} (use PNG, GIF or JPEG)")
        if p.get("image") and not p.get("image_alt"):
            errors.append(f"{p['slug']}: image without image_alt")
        if p.get("page", True) and p.get("show", True) and not (p.get("description") or p.get("abstract")):
            errors.append(f"{p['slug']}: has a detail page but no description or abstract")
        if p.get("bib_type") and not (p.get("bibtex") or p.get("bib_venue")):
            errors.append(f"{p['slug']}: bib_type set without bib_venue or bibtex")
    keys = [p.get("sort_key", "") for p in all_pubs]
    if keys != sorted(keys, reverse=True):
        errors.append("publications.json is not ordered newest first by sort_key")

    linkable = {p["slug"] for p in all_pubs if p.get("show", True) and p.get("page", True)}
    for i, n in enumerate(news):
        for k in ("date", "sort_key", "html"):
            if k not in n:
                errors.append(f"news[{i}]: missing {k}")
    texts = [(f"news[{i}]", n.get("html", "")) for i, n in enumerate(news)] + [("pages/intro.html", intro)]
    texts += [(f"experience[{i}]", e.get("html", "")) for i, e in enumerate(experience)]
    texts += [(f"{p.get('slug')}.{k}", p.get(k, "")) for p in all_pubs
              for k in ("note_html", "description", "summary", "abstract")]
    texts += [(f"{p.get('slug')}.figures", f.get("caption", "")) for p in all_pubs for f in p.get("figures", [])]
    for where, text in texts:
        for slug in re.findall(r'href=["\'](?:https?://liuuuxy\.github\.io)?/?(?:\.\./)*papers/([^/"\'#?]+)', text):
            if slug not in linkable:
                errors.append(f"{where}: links to papers/{slug}/, which is hidden or has no page")
    keys = [n.get("sort_key", "") for n in news]
    if keys != sorted(keys, reverse=True):
        errors.append("news.json is not ordered newest first by sort_key")
    for i, e in enumerate(experience):
        for k in ("org", "url", "when", "role", "html"):
            if k not in e:
                errors.append(f"experience[{i}]: missing {k}")
    for path in (site["profile_image"], site["cv"], site["og_image"]):
        if not (ROOT / path).exists():
            errors.append(f"site.json references missing file {path}")
    if errors:
        sys.exit("build.py: data errors:\n  " + "\n  ".join(errors))


# ------------------------------------------------------------------ main ---

def main():
    site = load("site.json")
    all_pubs = load("publications.json")
    news = load("news.json")
    experience = load("experience.json")
    intro = (ROOT / "pages" / "intro.html").read_text(encoding="utf-8")
    validate(site, all_pubs, news, experience, intro)
    pubs = [p for p in all_pubs if p.get("show", True)]

    build_index(site, pubs, news, experience, intro)
    paged = [p for p in pubs if p.get("page", True)]
    for i, p in enumerate(paged):
        build_paper(site, p, paged[i - 1] if i > 0 else None, paged[i + 1] if i + 1 < len(paged) else None)
    build_papers_index(site, pubs)
    build_404(site)
    build_llms_txt(site, pubs, news)
    build_sitemap(site, pubs)
    build_robots(site)

    check = "--check" in sys.argv
    stale = []
    for rel, content in GENERATED.items():
        path = ROOT / rel
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    # Pages for papers that were renamed, hidden or lost their page.
    live = {p["slug"] for p in paged}
    for d in sorted((ROOT / "papers").iterdir()):
        if not d.is_dir() or d.name in live:
            continue
        page = d / "index.html"
        generated = ([x.name for x in d.iterdir()] == ["index.html"]
                     and '<meta name="generator" content="build.py">' in page.read_text(encoding="utf-8"))
        if not generated:
            print(f"build.py: warning: papers/{d.name}/ is not a paper page; leaving it alone")
            continue
        stale.append(f"papers/{d.name}/ (orphaned)")
        if not check:
            shutil.rmtree(d)
    if check:
        if stale:
            sys.exit("build.py --check: out of date: " + ", ".join(stale))
        print(f"build.py --check: {len(GENERATED)} files up to date")
    else:
        print(f"build.py: {len(stale)} of {len(GENERATED)} outputs changed" + (f" ({', '.join(stale)})" if stale else ""))


if __name__ == "__main__":
    main()
