# docs

Source for [Documentation, How-Tos, and Ramblings](https://myah-mitchell.github.io/docs/), built with [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). Pages live in `content/`, text that several pages include lives in `snippets/`, and the navigation is in `mkdocs.yml`.

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

A page about one of the fleet's tools goes in `content/tools/<tool>/`. The primer is `index.md`, and each how-to is a file beside it. Add a new term to `content/tools/glossary.md`, in alphabetical order. See [Tool pages](content/standards/markdown-style-guide.md#tool-pages) for both shapes.

A diagram is a `mermaid` code block in the page. See [Diagrams](content/standards/markdown-style-guide.md#diagrams) for when an SVG is used instead.

A post goes in `content/blog/posts/` and needs front matter with a `date`, which the blog plugin reads.

## Versions

`requirements.txt` pins MkDocs to 1.6. MkDocs 2.0 drops the plugin and theme system this site depends on, so do not upgrade past 1.x without planning a migration.

## License

Copyright (C) 2026 Myah Mitchell. Everything in this repo, the published pages and their code snippets included, is licensed under [Creative Commons Attribution-ShareAlike 4.0 International](LICENSE). You can copy, adapt, and republish it, commercially too, as long as you credit Myah Mitchell with a link to <https://myah-mitchell.github.io/docs/>, say what you changed, and release your version under the same license.
