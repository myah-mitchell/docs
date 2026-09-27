# docs

Source for [Documentation, How-Tos, and Ramblings](https://myah-mitchell.github.io/docs/), built with [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). Pages live in `content/`, and the navigation is in `mkdocs.yml`.

Every page follows the [Markdown style guide](content/standards/markdown-style-guide.md).

## Preview locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/mkdocs serve
```

Open `http://127.0.0.1:8000/docs/`. The page reloads on save.

Before pushing, run the same checks CI does:

```bash
.venv/bin/mkdocs build --strict
npx markdownlint-cli2 "**/*.md" "#.venv" "#site"
```

`--strict` fails on any broken link or anchor.

## Publishing

Every push to `main` builds the site and deploys it to GitHub Pages through `.github/workflows/pages.yml`. The repo's *Settings > Pages > Source* must be set to **GitHub Actions**.

## Adding a page

1. Create the page under the right section in `content/`, with a kebab-case filename.
2. Add it to `nav` in `mkdocs.yml`. Pages missing from `nav` still build, but nobody can find them.
3. Put images in an `img/` folder beside the page that uses them.

A post goes in `content/blog/posts/` and needs front matter with a `date`, which the blog plugin reads.

## Versions

`requirements.txt` pins MkDocs to 1.6. MkDocs 2.0 drops the plugin and theme system this site depends on, so do not upgrade past 1.x without planning a migration.
