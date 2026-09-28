# liuuuxy.github.io

Personal academic website of Xinyuan Liu. Plain static HTML generated from
JSON by `build.py` (Python standard library only — no npm, no dependencies),
served by GitHub Pages from this repository.

Layout follows the LENS Lab house style
([Som Sagar](https://somsagar07.github.io/), [Aditya Taparia](https://aditya-taparia.github.io/)),
itself adapted from [Jon Barron's template](https://github.com/jonbarron/jonbarron.github.io).

## Editing

Edit the sources, never the generated HTML:

| File | Contents |
|------|----------|
| `data/site.json` | Name, tagline, links, SEO description, research focus, service |
| `data/publications.json` | Every paper, newest first (single source of truth) |
| `data/news.json` | News items, newest first |
| `data/experience.json` | Experience rows |
| `pages/intro.html` | Biography prose |
| `assets/style.css`, `assets/main.js` | Styling and behaviour |

Then regenerate:

```sh
python3 build.py           # write the generated files
python3 build.py --check   # exit non-zero if anything is out of date
```

`build.py` refuses to build on inconsistent data: missing fields, images or
videos that do not exist, papers or news out of date order, your name missing
from an author list, or a link to a paper page that is hidden or has no page.

### Generated — do not edit by hand

`index.html` · `papers/**` · `404.html` · `llms.txt` · `sitemap.xml` · `robots.txt`

When a paper is renamed, hidden or loses its page, the build deletes its old
`papers/<slug>/` directory. Directories under `papers/` that the build did not
create are left alone.

## Adding a publication

Add an object to `data/publications.json`, keeping the list newest first by
`sort_key`. Required fields come first:

```jsonc
{
  "slug": "url-slug",                  // detail page at /papers/url-slug/
  "title": "...",
  "short_title": "Short name",         // breadcrumb and previous/next links
  "authors": ["...", "Xinyuan Liu", "..."],   // exact order; your name is bolded
  "venue": "Full venue name",          // citation metadata
  "venue_display": "Full venue name, 2027",   // the italic line under the authors
  "venue_short": "ICML 2027",          // kept for reference; not currently shown
  "venue_type": "conference",          // conference | workshop | journal | preprint
  "year": "2027",
  "sort_key": "2027-07-01",
  "category": "conference",            // conference -> "Conferences" tab
                                       // preprint   -> "Preprints & Workshops" tab

  "show": true,                        // false: keep the entry but render it nowhere
  "page": true,                        // false: no detail page
  "equal_contribution": ["..."],       // marks these authors with *
  "note_html": "Abridged version at ...",     // extra line under the venue
  "description": "About 30 words for the homepage listing.",
  "summary": "Longer text for the detail page when there is no abstract.",
  "abstract": "The authors' abstract; shown on the detail page as Abstract.",
  "tldr": "One sentence for llms.txt and the page's meta description.",
  "image": "assets/papers/foo.jpg",    // thumbnail, ~560 px wide (PNG, GIF or JPEG)
  "image_alt": "What the thumbnail shows.",
  "og_image": "assets/papers/foo-og.jpg",     // social preview, ideally 1200x630
  "og_image_alt": "What the social preview shows.",
  "figures": [                         // detail-page figures, one or two across
    { "src": "assets/papers/foo-full.jpg", "alt": "...", "caption": "Figure 1. ..." },
    { "video": "assets/demos/foo.mp4", "video_webm": "assets/demos/foo.webm",
      "poster": "assets/demos/foo-poster.jpg", "alt": "...", "caption": "..." }
  ],
  "arxiv_id": "2701.00000",
  "links": { "arxiv": "...", "pdf": "...", "openreview": "...", "project": "...",
             "code": "...", "video": "...", "demo": "..." },
  "link_labels": { "project": "ICML poster" },  // rename any button
  "award": "Oral",                     // rendered in red after the venue
  "bib_type": "inproceedings",         // or "article"; omit for no BibTeX
  "bib_venue": "Venue name for BibTeX",
  "bib_protect": ["Kelvinlet"],        // extra words to keep capitalised
  "bibtex": "@inproceedings{...}"      // optional; replaces the generated entry
}
```

Detail pages need a `description` or an `abstract`. Generated BibTeX keeps
acronyms such as LLM and MaxSAT capitalised automatically.

## Other content

- `assets/xinyuan-liu-cv.pdf` is the CV linked from every page; replace the
  file to update it.
- `assets/demos/` holds the robot demo clips (WebM with MP4 fallback) cut from
  the videos in [physical-agentic-ai](https://github.com/Liuuuxy/physical-agentic-ai).
- `blog/` and the dated folders (`2020/`, `2021/`, `archives/`, `categories/`,
  `tags/`, `dist/`, `css/`, `js/`) are the 2020–2021 Hexo blog. Its pages still
  load at their old URLs but are no longer linked or listed in `sitemap.xml`.
