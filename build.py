#!/usr/bin/env python3
"""Assemble the static site from `src/` page bodies plus the shared partials.

Every page ends up as a plain .html file with no client-side rendering, so the
output directory can be served by anything. Run `python3 build.py` after editing
anything in `src/` or the `_*.part` files, then commit the generated HTML.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
# The site is mounted as a submodule of mylesieong.github.io under products/flexi,
# so it never sits at the origin root. SITE is used for canonical and Open Graph
# URLs and the sitemap; in-page links go through the `{root}` placeholder instead.
SITE = "https://mylesieong.github.io/products/flexi"

HEADER = (ROOT / "_header.part").read_text()
FOOTER = (ROOT / "_footer.part").read_text()
CTA = (ROOT / "_cta.part").read_text()

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="theme-color" content="#FF5985">

<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Flexi Stretch">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{site}/assets/img/app-icon.png">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{site}/assets/img/app-icon.png">

<link rel="icon" href="{{root}}assets/img/app-icon.png" sizes="any">
<link rel="apple-touch-icon" href="{{root}}assets/img/app-icon.png">
<link rel="stylesheet" href="{{root}}css/style.css">

<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
{header}
<main id="main">
{body}
</main>
{footer}
</body>
</html>
"""


def article_jsonld(page):
    """Article + Breadcrumb + (optional) FAQ + (optional) HowTo, as one @graph."""
    graph = [
        {
            "@type": "Article",
            "@id": page["url"] + "#article",
            "headline": page["headline"],
            "description": page["description"],
            "inLanguage": "en-US",
            "datePublished": page["published"],
            "dateModified": page["modified"],
            "mainEntityOfPage": {"@type": "WebPage", "@id": page["url"]},
            "author": {"@type": "Organization", "name": "Flexi Stretch", "url": SITE + "/"},
            "publisher": {
                "@type": "Organization",
                "name": "Flexi Stretch",
                "url": SITE + "/",
                "logo": {"@type": "ImageObject", "url": SITE + "/assets/img/app-icon.png"},
            },
            "image": SITE + "/assets/img/app-icon.png",
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Guides", "item": SITE + "/guides/"},
                {"@type": "ListItem", "position": 3, "name": page["headline"], "item": page["url"]},
            ],
        },
    ]
    if page.get("faq"):
        graph.append({
            "@type": "FAQPage",
            "@id": page["url"] + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in page["faq"]
            ],
        })
    if page.get("howto"):
        graph.append({
            "@type": "HowTo",
            "@id": page["url"] + "#howto",
            "name": page["howto"]["name"],
            "description": page["description"],
            "totalTime": page["howto"]["time"],
            "supply": [], "tool": [],
            "step": [
                {"@type": "HowToStep", "position": i + 1, "name": n, "text": t}
                for i, (n, t) in enumerate(page["howto"]["steps"])
            ],
        })
    return {"@context": "https://schema.org", "@graph": graph}


def build():
    pages = json.loads((ROOT / "src" / "pages.json").read_text())
    written = []

    for page in pages:
        # `canonical` lets a page live at /dir/index.html while advertising the
        # pretty /dir/ form that every internal link actually uses.
        page["url"] = SITE + page.get("canonical", page["path"])
        body = (ROOT / "src" / page["body"]).read_text()
        if page.get("cta", True):
            body = body.replace("<!--CTA-->", CTA)
        jsonld = page.get("jsonld_raw")
        if jsonld:
            jsonld = json.loads((ROOT / "src" / jsonld).read_text())
        else:
            jsonld = article_jsonld(page)

        out = ROOT / page["path"].lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        # The site is served from a sub-path, so no link may start at the origin
        # root. Templates write `{root}`; it resolves to the way back to the site
        # root from wherever this page lands.
        root = "../" * page["path"].lstrip("/").count("/")
        out.write_text(PAGE.format(
            title=page["title"],
            description=page["description"],
            url=page["url"],
            site=SITE,
            og_type=page.get("og_type", "article"),
            jsonld=json.dumps(jsonld, indent=2, ensure_ascii=False),
            header=HEADER,
            body=body,
            footer=FOOTER,
        ).replace("{root}", root))
        written.append((page.get("canonical", page["path"]), page.get("modified", "2026-08-20"), page.get("priority", "0.7")))

    # index.html is hand-maintained (it is the only page with a bespoke layout),
    # so it is listed in the sitemap without being regenerated here.
    urls = [("/", "2026-08-20", "1.0")] + written
    entries = "\n".join(
        f"  <url>\n    <loc>{SITE}{p}</loc>\n    <lastmod>{m}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n    <priority>{pr}</priority>\n  </url>"
        for p, m, pr in urls
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n"
    )

    print(f"built {len(written)} page(s) + sitemap.xml")


if __name__ == "__main__":
    build()
