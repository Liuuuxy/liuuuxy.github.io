# liuuuxy.github.io

Personal academic website of Xinyuan Liu, built on
[Jon Barron's website template](https://github.com/jonbarron/jonbarron_website).

## Editing

Everything is in `index.html`; edit it directly. `stylesheet.css` is Jon
Barron's original stylesheet, unmodified.

To add a paper, copy one of the `<tr>...</tr>` rows in the Research table and
fill it in. A thumbnail is optional: put the image in `assets/papers/` and
reference it with `width="160"`. For a thumbnail that plays a video on hover,
copy the Physical Agentic AI row, which uses Barron's `one` / `two` pattern
(give each row's script functions a unique name).

Each paper's BibTeX sits in the row itself, in a `<div class="bib">` right
after the links: the "bibtex" link shows or hides it, and "copy" puts it on the
clipboard. When copying a row, give the new `div` a unique `id` and use that id
in both `onclick` calls.

| Path | Contents |
|------|----------|
| `assets/profile.jpg` | Profile photo (square, shown as a circle) |
| `assets/xinyuan-liu-cv.pdf` | CV; replace the file to update it |
| `assets/papers/` | Paper thumbnails and the hover clip |

## Other content

`blog/` and the dated folders (`2020/`, `2021/`, `archives/`, `categories/`,
`tags/`, `dist/`, `css/`, `js/`, `images/`) are the 2020–2021 Hexo blog. Its
pages still load at their old URLs but are not linked from the homepage.
