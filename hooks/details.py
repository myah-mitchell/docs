"""Render Markdown inside <details> blocks.

Pages use plain <details> so they read the same on GitHub. Python-Markdown
leaves HTML blocks alone unless they carry a markdown attribute, which
md_in_html honours, so add it at build time instead of in the source.
"""

import re

DETAILS = re.compile(r"^<details>$", re.MULTILINE)


def on_page_markdown(markdown, **kwargs):
    return DETAILS.sub('<details markdown="1">', markdown)
