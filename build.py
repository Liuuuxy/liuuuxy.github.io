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
`python3 build.py --check` fails if the generated files are out of date.
"""

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
GENERATED = {}


# ------------------------------------------------------------------ utils ---

def esc(text):
    return html.escape(str(text), quote=True)


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def write(relpath, content):
    GENERATED[relpath] = content


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)


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


def authors_html(pub, me):
    marks = set(pub.get("equal_contribution", []))
    out = []
    for name in pub["authors"]:
        # Non-breaking inside a name, so a long author list never splits "Xinyuan / Liu".
        label = esc(name).replace(" ", "&nbsp;") + ("*" if name in marks else "")
        out.append(f"<strong>{label}</strong>" if name == me else label)
    return ", ".join(out)


def authors_plain(pub):
    return ", ".join(pub["authors"])


def bibtex(pub):
    if pub.get("bibtex"):
        return pub["bibtex"]
    last = lambda n: n.split()[-1]
    names = " and ".join(f"{last(n)}, {' '.join(n.split()[:-1])}" for n in pub["authors"])
    first = re.sub(r"[^a-z]", "", last(pub["authors"][0]).lower())
    word = re.sub(r"[^a-z]", "", pub["title"].split(":")[0].split()[0].lower())
    key = f"{first}{pub['year']}{word}"
    if pub["bib_type"] == "article":
        where = f"    journal={{{pub['bib_venue']}}},\n"
    else:
        where = f"    booktitle={{{pub['bib_venue']}}},\n"
    return (f"@{pub['bib_type']}{{{key},\n"
            f"    title={{{pub['title']}}},\n"
            f"    author={{{names}}},\n"
            f"{where}"
            f"    year={{{pub['year']}}}\n}}")


def pub_links(pub, prefix, with_details=True, with_bibtex=True):
    links = pub.get("links", {})
    order = [
        ("arxiv", "arXiv", "pdf"), ("pdf", "PDF", "pdf"), ("openreview", "OpenReview", "link"),
        ("project", "Project page", "link"), ("code", "Code", "code"), ("video", "Video", "video"),
        ("demo", "Hardware demos", "video"), ("extended", "Extended version", "pdf"),
    ]
    labels = pub.get("link_labels", {})
    parts = [btn(labels.get(k, label), links[k], ico) for k, label, ico in order if links.get(k)]
    if with_details and pub.get("page", True):
        parts.append(btn("Details", f"{prefix}papers/{pub['slug']}/", "details", external=False))
    if with_bibtex and pub.get("bib_type"):
        bid = f"bib-{pub['slug']}"
        parts.append(f'<button type="button" class="btn btn-publication" data-bibtex-toggle="{bid}" '
                     f'aria-expanded="false" aria-controls="{bid}">{icon("quote")} BibTeX</button>')
    return parts


# ------------------------------------------------------------ page chrome ---

THEME_INIT = """<script>
// Before first paint, so a dark device never sees a light flash. The class
// goes on <html>: the :root colour aliases resolve their var() references
// against that element, so a class on <body> would leave them light.
(function () {
  var s = null;
  try { s = localStorage.getItem('theme'); } catch (e) {}
  if (s === 'dark' || (s === null && window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  }
})();
</script>"""


def head(site, *, title, description, url_path, prefix, og_type="profile", og_image=None,
         extra="", ld=()):
    url = site["url"] + "/" + url_path
    image = site["url"] + "/" + (og_image or site["og_image"])
    ld_html = "".join(
        f'\n<script type="application/ld+json">\n{json.dumps(obj, indent=2, ensure_ascii=False)}\n</script>'
        for obj in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(site['name'])}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(image)}">
<meta name="theme-color" content="#F7F9FC" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#12161B" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700;1,9..40,400&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}assets/style.css">
<link rel="icon" href="{prefix}assets/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">
{THEME_INIT}{extra}{ld_html}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<button id="theme-toggle" type="button" aria-label="Toggle dark mode" title="Toggle dark/light mode">{icon("moon", "icon-moon")}{icon("sun", "icon-sun")}</button>
"""


def footer(site, prefix):
    return f"""<footer class="site-footer page">
<nav class="footer-links" aria-label="Site"><a href="{prefix or './'}">{esc(site['name'])}</a> &middot; <a href="{prefix}papers/">Publications</a> &middot; <a href="{prefix}{esc(site['cv'])}">CV</a></nav>
<p>&copy; {esc(site['copyright_year'])} {esc(site['name'])} &middot; <a href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></p>
<p class="credit">Website design adapted from <a href="https://github.com/jonbarron/jonbarron.github.io" target="_blank" rel="noopener">Jon Barron</a>.</p>
</footer>
<script src="{prefix}assets/main.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------ structured ---

def person_ld(site, pubs):
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
             "description": site["description"],
             "knowsAbout": site["research_focus"],
             "affiliation": {"@type": "CollegeOrUniversity", "name": site["affiliation"]["name"],
                             "url": site["affiliation"]["url"]},
             "alumniOf": [{"@type": "CollegeOrUniversity", "name": a} for a in site["alumni_of"]],
             "sameAs": site["same_as"]},
            {"@type": "ItemList", "@id": site["url"] + "/#publications", "name": "Publications",
             "itemListElement": [
                 {"@type": "ListItem", "position": i + 1, "name": p["title"],
                  "url": paper_url(site, p)}
                 for i, p in enumerate(pubs)]},
        ],
    }


def paper_url(site, pub):
    if pub.get("page", True):
        return f"{site['url']}/papers/{pub['slug']}/"
    links = pub.get("links", {})
    return links.get("arxiv") or links.get("openreview") or site["url"] + "/#publications"


def article_ld(site, pub):
    obj = {
        "@context": "https://schema.org", "@type": "ScholarlyArticle",
        "@id": paper_url(site, pub) + "#article",
        "name": pub["title"], "headline": pub["title"], "url": paper_url(site, pub),
        "datePublished": pub["year"], "inLanguage": "en",
        "author": [{"@type": "Person", "name": a} for a in pub["authors"]],
        "isPartOf": {"@type": "PublicationIssue", "name": pub["venue"]},
    }
    if pub.get("abstract") or pub.get("description"):
        obj["abstract"] = strip_tags(pub.get("abstract") or pub["description"])
    if pub.get("image"):
        obj["image"] = site["url"] + "/" + pub["image"]
    if pub.get("arxiv_id"):
        obj["identifier"] = "arXiv:" + pub["arxiv_id"]
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

def venue_html(pub):
    out = esc(pub["venue_display"])
    if pub.get("award"):
        out += f' &middot; <span class="pub-award">{esc(pub["award"])}</span>'
    return out


def pub_card(site, pub, prefix, index):
    thumb = ""
    if pub.get("image"):
        loading = 'fetchpriority="high"' if index == 0 else 'loading="lazy"'
        target = f"{prefix}papers/{pub['slug']}/" if pub.get("page", True) else pub["links"].get("arxiv", "#")
        w, h = pub.get("image_size", [178, 100])
        thumb = (f'<a href="{esc(target)}" tabindex="-1" aria-hidden="true">'
                 f'<img src="{prefix}{esc(pub["image"])}" alt="{esc(pub["image_alt"])}" '
                 f'width="{w}" height="{h}" {loading} decoding="async"></a>')
    title = esc(pub["title"])
    if pub.get("page", True):
        title = f'<a href="{prefix}papers/{pub["slug"]}/">{title}</a>'
    elif pub.get("links", {}).get("arxiv"):
        title = f'<a href="{esc(pub["links"]["arxiv"])}" target="_blank" rel="noopener">{title}</a>'
    note = f'<div class="pub-note">{pub["note_html"]}</div>' if pub.get("note_html") else ""
    desc = f'<div class="description">{pub["description"]}</div>' if pub.get("description") else ""
    links = pub_links(pub, prefix)
    links_html = f'<div class="pub-links">{"".join(links)}</div>' if links else ""
    bib = ""
    if pub.get("bib_type"):
        bib = f'<div id="bib-{pub["slug"]}" class="bibtex"><pre>{esc(bibtex(pub))}</pre></div>'
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
    conf_label = "Conferences &amp; Journals" if any(p["venue_type"] == "journal" for p in pubs) else "Conferences"
    n_pre = len(pubs) - n_conf
    link_row = "".join(
        f'<a class="btn" href="{esc(l["href"])}"'
        + (' target="_blank" rel="noopener"' if l.get("external") else "")
        + f'>{icon(l["icon"])} {esc(l["label"])}</a>'
        + ('<span class="link-break" aria-hidden="true"></span>' if i == 2 else "")
        for i, l in enumerate(site["links"]))
    news_rows = "\n".join(
        f'<tr><td class="news-date-cell"><span class="news-date">{esc(n["date"])}</span></td><td>{n["html"]}</td></tr>'
        for n in news)
    exp_rows = "\n".join(
        f'<tr><td class="exp-where"><a class="exp-org" href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["org"])}</a>'
        f'<br><span class="exp-when">{esc(e["when"])}</span></td>'
        f'<td><span class="exp-role">{esc(e["role"])}.</span> {e["html"]}</td></tr>'
        for e in experience)
    cards = "\n".join(pub_card(site, p, prefix, i) for i, p in enumerate(pubs))
    equal_note = " * denotes equal contribution." if any(p.get("equal_contribution") for p in pubs) else ""
    service = " &middot; ".join(
        f'<span class="service-label">{esc(s["label"])}</span> {esc(s["venues"])}' for s in site["service"])

    page = head(site, title=site["title"], description=site["description"], url_path="",
                prefix=prefix, ld=[person_ld(site, pubs)])
    page += f"""
<main id="main" class="page">

  <section class="intro-grid">
    <div class="intro-text">
      <h1 class="h-name">{esc(site['name'])}</h1>
      <p class="h-tagline">{esc(site['tagline'])}</p>
{intro.rstrip()}
    </div>
    <img class="intro-photo" src="{esc(site['profile_image'])}" alt="{esc(site['name'])}" width="320" height="400" fetchpriority="high">
    <nav class="link-row" aria-label="Contact and profiles">{link_row}</nav>
  </section>

  <section class="home-section" aria-labelledby="news-heading">
    <h2 class="h-section" id="news-heading">News</h2>
    <div class="news-box" tabindex="0" role="region" aria-label="News">
      <table class="news-table">
        <tbody>
{news_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section class="home-section" id="publications" aria-labelledby="research-heading">
    <h2 class="h-section" id="research-heading">Research</h2>
    <p class="section-note">See my <a href="{esc(site['cv'])}">CV</a> and <a href="{esc(site['scholar'])}" target="_blank" rel="noopener">Google Scholar</a>.{equal_note}</p>
    <div class="tab-navigation" role="tablist" aria-label="Filter publications">
      <a class="tab-button active" role="tab" id="tab-all" href="#all" data-tab="all" aria-selected="true" aria-controls="pub-list" tabindex="0">All <span class="pub-tab-count">({len(pubs)})</span></a>
      <a class="tab-button" role="tab" id="tab-conferences" href="#conferences" data-tab="conferences" aria-selected="false" aria-controls="pub-list" tabindex="-1">{conf_label} <span class="pub-tab-count">({n_conf})</span></a>
      <a class="tab-button" role="tab" id="tab-preprints" href="#preprints" data-tab="preprints" aria-selected="false" aria-controls="pub-list" tabindex="-1">Preprints &amp; Workshops <span class="pub-tab-count">({n_pre})</span></a>
    </div>
    <ol class="pub-list" id="pub-list" data-filter="all" role="tabpanel" aria-labelledby="tab-all">
{cards}
    </ol>
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
    <p class="service-line">{service}</p>
  </section>

</main>
"""
    page += footer(site, prefix)
    write("index.html", page)


# ----------------------------------------------------------- paper pages ---

def build_paper(site, pub, prev_pub, next_pub):
    prefix = "../../"
    slug = pub["slug"]
    figs = pub.get("figures") or ([{"src": pub["image"], "alt": pub["image_alt"]}] if pub.get("image") else [])
    figure = ""
    if figs:
        items = "".join(
            f'<figure class="paper-figure"><img src="{prefix}{esc(f["src"])}" alt="{esc(f["alt"])}" decoding="async">'
            + (f'<figcaption>{f["caption"]}</figcaption>' if f.get("caption") else "") + '</figure>'
            for f in figs)
        figure = f'<div class="paper-figures paper-figures-{len(figs)}">{items}</div>' 
    summary = pub.get("abstract") or pub.get("description")
    summary_html = (f'<section class="paper-section"><h2>{"Abstract" if pub.get("abstract") else "Summary"}</h2>'
                    f'<p>{summary}</p></section>') if summary else ""
    note = f'<p class="paper-meta">{pub["note_html"]}</p>' if pub.get("note_html") else ""
    links = pub_links(pub, prefix, with_details=False, with_bibtex=False)
    bib_id = f"bibtex-{slug}"
    bib = ""
    if pub.get("bib_type"):
        bib = f"""<section class="paper-section">
      <h2>BibTeX</h2>
      <pre class="paper-bibtex" id="{bib_id}">{esc(bibtex(pub))}</pre>
      <button type="button" class="btn btn-publication" data-copy-target="{bib_id}">{icon("copy")} <span>Copy BibTeX</span></button>
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
    page = head(site, title=f"{pub['title']} — {site['name']}", description=strip_tags(pub.get("tldr") or pub["description"]),
                url_path=f"papers/{slug}/", prefix=prefix, og_type="article", og_image=pub.get("image"),
                extra=citation_meta(pub), ld=[article_ld(site, pub), breadcrumb_ld])
    page += f"""
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="{prefix}">{esc(site['name'])}</a> &rsaquo; <a href="../">Publications</a> &rsaquo; <span>{esc(pub['venue_short'])}</span>
  </nav>
  <article>
    <header class="paper-header">
      <h1 class="paper-title">{esc(pub['title'])}</h1>
      <p class="paper-authors">{authors_html(pub, site['name'])}</p>
      <p class="paper-meta">{venue_html(pub)}</p>
      {note}
      <div class="pub-links">{"".join(links)}</div>
    </header>
    {figure}
    {summary_html}
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
<h3 class="pub-title">{title}</h3>
<div class="pub-authors">{authors_html(p, site['name'])}</div>
<div class="pub-venue">{venue_html(p)}</div>
</div>
</li>""")
    page = head(site, title=f"Publications — {site['name']}",
                description=f"All publications by {site['name']}, newest first.",
                url_path="papers/", prefix=prefix)
    page += f"""
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="{prefix}">{esc(site['name'])}</a> &rsaquo; <span>Publications</span></nav>
  <h1 class="h-name page-heading">Publications</h1>
  <p class="section-note">{len(pubs)} papers, newest first. See also <a href="{esc(site['scholar'])}" target="_blank" rel="noopener">Google Scholar</a>.</p>
  <ol class="pub-list pub-list-compact">
{chr(10).join(rows)}
  </ol>
</main>
"""
    page += footer(site, prefix)
    write("papers/index.html", page)


def build_404(site):
    page = head(site, title=f"Page not found — {site['name']}", description="This page does not exist.",
                url_path="404.html", prefix="/")
    page = page.replace('<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">',
                        '<meta name="robots" content="noindex">')
    page += f"""
<main id="main" class="page">
  <h1 class="h-name page-heading">Page not found</h1>
  <p class="section-note">The page you were looking for doesn&rsquo;t exist. Try the <a href="/">homepage</a> or the <a href="/papers/">publication list</a>.</p>
</main>
"""
    page += footer(site, "/")
    write("404.html", page)


# ------------------------------------------------------------ text files ---

def build_llms_txt(site, pubs):
    lines = [f"# {site['name']}", "", f"> {site['description']}", f"> Contact: {site['email']}", "",
             "## Research focus", ""]
    lines += [f"- {r}" for r in site["research_focus"]]
    lines += ["", "## Pages", "",
              f"- [Homepage]({site['url']}/): biography, news, publications, experience",
              f"- [Publications]({site['url']}/papers/): all {len(pubs)} papers",
              f"- [CV]({site['url']}/{site['cv']}): curriculum vitae (PDF)",
              f"- [Google Scholar]({site['scholar']})", "", "## Publications", ""]
    for p in pubs:
        venue = p["venue_display"]
        desc = f" {strip_tags(p['tldr'])}" if p.get("tldr") else ""
        lines.append(f"- [{p['title']}]({paper_url(site, p)}) — {strip_tags(venue)}.{desc} Authors: {authors_plain(p)}.")
    lines += ["", "## Service", ""]
    lines += [f"- {s['label']} {s['venues']}" for s in site["service"]]
    write("llms.txt", "\n".join(lines) + "\n")


def build_sitemap(site, pubs):
    urls = [(site["url"] + "/", site["updated"], "1.0"), (site["url"] + "/papers/", site["updated"], "0.8")]
    urls += [(f"{site['url']}/papers/{p['slug']}/", site["updated"], "0.8") for p in pubs if p.get("page", True)]
    body = "\n".join(f"  <url>\n    <loc>{esc(u)}</loc>\n    <lastmod>{m}</lastmod>\n    <priority>{pr}</priority>\n  </url>"
                     for u, m, pr in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n')


def build_robots(site):
    agents = ["*"] + site["llm_user_agents"]
    blocks = "\n\n".join(f"User-agent: {a}\nAllow: /" for a in agents)
    write("robots.txt", "# Everyone, including AI and LLM crawlers, may index this site.\n\n"
          f"{blocks}\n\nSitemap: {site['url']}/sitemap.xml\n")


# ------------------------------------------------------------ validation ---

def validate(site, pubs, news, experience):
    errors = []
    slugs = [p["slug"] for p in pubs]
    if len(set(slugs)) != len(slugs):
        errors.append("duplicate publication slugs")
    for p in pubs:
        for key in ("slug", "title", "authors", "venue", "venue_display", "venue_short", "venue_type", "year",
                    "sort_key", "category"):
            if key not in p:
                errors.append(f"{p.get('slug', '?')}: missing {key}")
        if p.get("category") not in ("conference", "preprint"):
            errors.append(f"{p['slug']}: category must be conference or preprint")
        if site["name"] not in p.get("authors", []):
            errors.append(f"{p['slug']}: {site['name']} not in author list")
        if "short_title" not in p:
            errors.append(f"{p['slug']}: missing short_title")
        paths = [p["image"]] if p.get("image") else []
        paths += [f["src"] for f in p.get("figures", [])]
        for path in paths:
            if not (ROOT / path).exists():
                errors.append(f"{p['slug']}: image {path} does not exist")
        for f in p.get("figures", []):
            if not f.get("alt"):
                errors.append(f"{p['slug']}: figure {f['src']} has no alt text")
        if p.get("page", True) and not (p.get("description") or p.get("abstract")):
            errors.append(f"{p['slug']}: has a detail page but no description or abstract")
        if p.get("image") and not p.get("image_alt"):
            errors.append(f"{p['slug']}: image without image_alt")
        for name in p.get("equal_contribution", []):
            if name not in p["authors"]:
                errors.append(f"{p['slug']}: equal_contribution names a non-author {name}")
    if [p["sort_key"] for p in pubs] != sorted((p["sort_key"] for p in pubs), reverse=True):
        errors.append("publications.json is not ordered newest first by sort_key")
    if [n["sort_key"] for n in news] != sorted((n["sort_key"] for n in news), reverse=True):
        errors.append("news.json is not ordered newest first by sort_key")
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
    validate(site, all_pubs, news, experience)
    pubs = [p for p in all_pubs if p.get("show", True)]

    build_index(site, pubs, news, experience, intro)
    paged = [p for p in pubs if p.get("page", True)]
    for i, p in enumerate(paged):
        build_paper(site, p, paged[i - 1] if i > 0 else None, paged[i + 1] if i + 1 < len(paged) else None)
    build_papers_index(site, pubs)
    build_404(site)
    build_llms_txt(site, pubs)
    build_sitemap(site, pubs)
    build_robots(site)

    stale = []
    for rel, content in GENERATED.items():
        path = ROOT / rel
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(rel)
            if "--check" not in sys.argv:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    if "--check" in sys.argv:
        if stale:
            sys.exit("build.py --check: out of date: " + ", ".join(stale))
        print(f"build.py --check: {len(GENERATED)} files up to date")
    else:
        print(f"build.py: wrote {len(stale)} of {len(GENERATED)} files" + (f" ({', '.join(stale)})" if stale else ""))


if __name__ == "__main__":
    main()
