"""One navigation bar, on every page.

Three views of one system, and a person checking something will want all three
within a click: the live floor, the health summary, and the records underneath
both. Kept here rather than copied into each page so a fourth view cannot
quietly appear on two of them and not the third.

The current page is marked rather than un-linked. A link that silently does
nothing is worse than one that reloads.
"""

#: Every page, in the order a person moves through them: what is happening,
#: whether it is healthy, and what was written down.
PAGES = (
    ("/", "Live floor"),
    ("/dashboard", "Line status"),
    ("/tables", "Records"),
)

CSS = """
 .nav { display:flex; gap:2px; align-items:center; }
 .nav a { display:inline-block; padding:5px 13px; border-radius:7px;
          text-decoration:none; font-size:13px; font-weight:600;
          color:#9aa3b8; border:1px solid transparent; }
 .nav a:hover { color:#e8eaf0; background:rgba(255,255,255,.05); }
 .nav a.here { color:#e8eaf0; background:rgba(127,178,255,.14);
               border-color:rgba(127,178,255,.35); }
"""


def bar(current):
    """The links, with `current` marked. `current` is a path from PAGES."""
    links = []
    for href, label in PAGES:
        here = ' class="here"' if href == current else ""
        links.append('<a href="%s"%s>%s</a>' % (href, here, label))
    return '<nav class="nav">%s</nav>' % "".join(links)
