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

`build.py` refuses to build if the data is inconsistent (missing fields,
images that do not exist, papers out of date order, your name missing from an
author list).

### Generated — do not edit by hand

`index.html` · `papers/**` · `404.html` · `llms.txt` · `sitemap.xml` · `robots.txt`

## Adding a publication

Add an object to `data/publications.json`, keeping the list newest first by
`sort_key`:

```jsonc
{
  "slug": "url-slug",                 // detail page at /papers/url-slug/
  "title": "...",
  "authors": ["...", "Xinyuan Liu", "..."],   // exact order; your name is bolded
  "equal_contribution": ["..."],     // optional; marks names with *
  "venue": "Full venue name",
  "venue_display": "Full venue name, 2027",    // the italic line under the authors
  "venue_short": "ICML 2027",        // breadcrumb and prev/next links
  "venue_type": "conference",        // conference | workshop | journal | preprint
  "year": "2027",
  "sort_key": "2027-07-01",
  "category": "conference",          // conference -> "Conferences & Journals" tab
                                     // preprint   -> "Preprints & Workshops" tab
  "page": true,                      // false: no detail page (e.g. under review)
  "image": "assets/papers/foo.jpg",  // optional ~360px-wide thumbnail
  "figure": "assets/papers/foo-full.jpg",      // optional larger figure for the detail page
  "image_alt": "What the figure shows.",
  "note_html": "Abridged version at ...",      // optional extra line
  "description": "One or two sentences for the listing.",
  "abstract": "Optional; shown on the detail page instead of the description.",
  "tldr": "One sentence for llms.txt and the page's meta description.",
  "arxiv_id": "2701.00000",
  "links": { "arxiv": "...", "pdf": "...", "openreview": "...", "code": "...",
             "project": "...", "video": "...", "demo": "..." },
  "award": "Oral",                   // optional; rendered in red
  "bib_type": "inproceedings",       // or "article"; omit for no BibTeX
  "bib_venue": "Venue name for BibTeX",
  "bibtex": "@inproceedings{...}"    // optional; overrides the generated entry
}
```

## Other content

- `blog/` and the dated folders (`2020/`, `2021/`, `archives/`, `categories/`,
  `tags/`, `dist/`, `css/`, `js/`) are the 2020–2021 Hexo blog, kept so its old
  URLs keep working. `data/legacy-sitemap.json` keeps them in the sitemap.
- `assets/xinyuan-liu-cv.pdf` is the CV linked from the site; replace the file
  to update it.
