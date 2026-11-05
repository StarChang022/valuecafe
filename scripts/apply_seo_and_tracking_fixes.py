#!/usr/bin/env python3
"""
scripts/apply_seo_and_tracking_fixes.py
======================================
Automated migration script to resolve:
1. Reinstall GA4 (G-5PTYPV0S9P) + standard non-delayed GTM (GTM-M6FP6CGL) across all HTML files.
2. Fix all og:image paths to absolute https://valuecafe.cc/... URLs.
3. Fix JSON-LD Schema (Article, CollectionPage, ContactPage, WebPage) across all HTML files.
4. Add new Philosophy articles to index.html under #philosophy.
5. Rebuild sitemap.xml with real timestamps, no external CSS, no llms.txt, no PDF, including 3 new articles.
6. Fix llms.txt URLs.
7. Update scripts/optimize_js.py.
"""

import os
import re
import json
import glob
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GA4_GTM_REPLACEMENT = """\t<!-- Google Analytics 4 -->
\t<script async src="https://www.googletagmanager.com/gtag/js?id=G-5PTYPV0S9P"></script>
\t<script>
\t\twindow.dataLayer = window.dataLayer || [];
\t\tfunction gtag(){dataLayer.push(arguments);}
\t\tgtag('js', new Date());

\t\tgtag('config', 'G-5PTYPV0S9P');
\t</script>

\t<!-- Google Tag Manager -->
\t<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
\tnew Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
\tj=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
\t'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
\t})(window,document,'script','dataLayer','GTM-M6FP6CGL');</script>"""

OLD_TRACKING_PATTERN = re.compile(
    r'[ \t]*<!-- Google Tag Manager \(Optimized: Lazy Loaded on User Interaction\) -->\s*<script>.*?</script>',
    re.DOTALL
)

OG_IMAGE_PATTERN = re.compile(
    r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE
)

JSONLD_PATTERN = re.compile(
    r'[ \t]*<!-- JSON-LD -->\s*<script type=["\']application/ld\+json["\']>.*?</script>',
    re.DOTALL
)

def get_git_dates(rel_path):
    cmd_first = ["git", "-C", ROOT, "log", "--reverse", "--format=%ad", "--date=iso-strict", "--", rel_path]
    cmd_last = ["git", "-C", ROOT, "log", "-n", "1", "--format=%ad", "--date=iso-strict", "--", rel_path]
    try:
        rf = subprocess.check_output(cmd_first).decode().splitlines()
        rl = subprocess.check_output(cmd_last).decode().splitlines()
        first_d = rf[0] if rf else "2026-07-13T00:00:00+08:00"
        last_d = rl[0] if rl else first_d
        return first_d, last_d
    except Exception:
        return "2026-07-13T00:00:00+08:00", "2026-11-05T12:00:00+08:00"

def resolve_absolute_og_image(rel_path, current_og):
    if "general-sharing-image.webp" in current_og:
        if "to-beginners" in rel_path:
            folder = rel_path.replace(".html", "")
            target = f"images/{folder}/cover.webp"
        else:
            target = "images/index/hero.webp"
    elif current_og.startswith("../images/"):
        target = current_og.replace("../", "")
    elif current_og.startswith("images/"):
        target = current_og
    elif current_og.startswith("https://valuecafe.cc/images/"):
        target = current_og.replace("https://valuecafe.cc/", "")
    else:
        target = current_og

    # Validate target exists
    full = os.path.join(ROOT, target)
    if not os.path.exists(full):
        target = "images/index/hero.webp"

    return f"https://valuecafe.cc/{target}"

def build_jsonld(rel_path, content, abs_og_image, first_date, last_date):
    # Extract current meta
    name_m = re.search(r'<title>(.*?)</title>', content, re.S)
    raw_title = name_m.group(1).strip() if name_m else "ValueCafe"
    
    desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content="([^"]*)"', content, re.S)
    if not desc_m:
        desc_m = re.search(r"<meta\s+name=[\"']description[\"']\s+content='([^']*)'", content, re.S)
    desc = desc_m.group(1).strip() if desc_m else ""

    canonical = "https://valuecafe.cc" if rel_path == "index.html" else f"https://valuecafe.cc/{rel_path}"

    # Determine Page Type
    hub_pages = {
        "financial-ratios.html", "intrinsic-value.html", "legendary.html",
        "news.html", "philosophy.html"
    }
    
    publisher_obj = {
        "@type": "Organization",
        "name": "ValueCafe",
        "logo": {
            "@type": "ImageObject",
            "url": "https://valuecafe.cc/images/logo.svg"
        }
    }

    if rel_path == "index.html":
        data = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": raw_title,
            "description": desc,
            "url": canonical,
            "publisher": publisher_obj,
            "inLanguage": "en-US"
        }
    elif rel_path in hub_pages:
        data = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": raw_title,
            "description": desc,
            "url": canonical,
            "publisher": publisher_obj,
            "inLanguage": "en-US"
        }
    elif rel_path == "contact.html":
        data = {
            "@context": "https://schema.org",
            "@type": "ContactPage",
            "name": raw_title,
            "description": desc,
            "url": canonical,
            "publisher": publisher_obj,
            "inLanguage": "en-US"
        }
    elif rel_path in ["privacy.html", "terms.html", "worldview.html", "404.html"]:
        data = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": raw_title,
            "description": desc,
            "url": canonical,
            "publisher": publisher_obj,
            "inLanguage": "en-US"
        }
    else:
        # Article schema
        # For news articles, check if explicit datetime tag exists
        time_m = re.search(r'<time\s+datetime=["\'](\d{4}-\d{2}-\d{2})["\']', content)
        if time_m:
            pub_date = f"{time_m.group(1)}T00:00:00+08:00"
        else:
            pub_date = first_date

        data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": raw_title,
            "description": desc,
            "image": abs_og_image,
            "datePublished": pub_date,
            "dateModified": last_date,
            "author": {
                "@type": "Person",
                "name": "STARChang",
                "url": "https://valuecafe.cc/contact.html"
            },
            "publisher": publisher_obj,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": canonical
            },
            "inLanguage": "en-US"
        }

    # Format JSON-LD with tabs
    raw_json = json.dumps(data, indent=2, ensure_ascii=False)
    # indent with tabs
    tabbed_lines = []
    for line in raw_json.splitlines():
        tabbed_lines.append("\t" + line.replace("  ", "\t"))
    tabbed_json = "\n".join(tabbed_lines)

    return f"\t<!-- JSON-LD -->\n\t<script type=\"application/ld+json\">\n{tabbed_json}\n\t</script>"

def update_index_philosophy(content):
    if "buy-and-hold-dynamic-rebalancing.html" in content:
        return content

    target = """\t\t\t\t\t<div class="column column-list">
\t\t\t\t\t\t<a href="philosophy/investment-moat.html">"""

    replacement = """\t\t\t\t\t<div class="column column-list">
\t\t\t\t\t\t<a href="philosophy/buy-and-hold-dynamic-rebalancing.html">
\t\t\t\t\t\t\t<div class="cards border-horizontal">
\t\t\t\t\t\t\t\t<div class="image">
\t\t\t\t\t\t\t\t\t<img src="images/philosophy/buy-and-hold-dynamic-rebalancing/cover.webp" alt="Buy and Hold vs Dynamic Rebalancing" loading="lazy" decoding="async">
\t\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t\t\t<div class="column">
\t\t\t\t\t\t\t\t\t<h3>Buy and Hold vs Dynamic Rebalancing</h3>
\t\t\t\t\t\t\t\t\t<p>Long-term holding is the natural byproduct of owning outstanding businesses, never a rigid dogma.</p>
\t\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t</a>
\t\t\t\t\t\t<a href="philosophy/mr-market-emotional-discipline.html">
\t\t\t\t\t\t\t<div class="cards border-horizontal">
\t\t\t\t\t\t\t\t<div class="image">
\t\t\t\t\t\t\t\t\t<img src="images/philosophy/mr-market-emotional-discipline/cover.webp" alt="Mr. Market's Emotions" loading="lazy" decoding="async">
\t\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t\t\t<div class="column">
\t\t\t\t\t\t\t\t\t<h3>Mr. Market's Emotions</h3>
\t\t\t\t\t\t\t\t\t<p>Mr. Market knocks on your door every day with a quote. His job is to provide liquidity and discounts, not to guide your decisions. Learn to look past short-term price fluctuations and make market panic your best friend.</p>
\t\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t</a>
\t\t\t\t\t\t<a href="philosophy/investment-moat.html">"""

    if target in content:
        return content.replace(target, replacement, 1)
    else:
        print("[WARN] Target for index philosophy not matched exactly.")
        return content

def generate_sitemap(html_files):
    urls = []
    for f in html_files:
        rel = os.path.relpath(f, ROOT)
        if rel == "404.html":
            continue
        first_d, last_d = get_git_dates(rel)
        url = "https://valuecafe.cc/" if rel == "index.html" else f"https://valuecafe.cc/{rel}"
        urls.append((url, rel, last_d))

    # Sort order: index first, then others
    def sort_key(item):
        u, r, d = item
        if r == "index.html":
            return "000"
        return r

    urls.sort(key=sort_key)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url, rel, last_d in urls:
        lines.append('  <url>')
        lines.append(f'    <loc>{url}</loc>')
        lines.append(f'    <lastmod>{last_d}</lastmod>')
        lines.append('  </url>')
    lines.append('</urlset>\n')

    return "\n".join(lines)

def update_optimize_js_py():
    path = os.path.join(ROOT, "scripts", "optimize_js.py")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    # Update GA_GTM_PATTERN and OPTIMIZED_GTM_TEMPLATE so it doesn't revert tracking
    new_opt_template = '''OPTIMIZED_GTM_TEMPLATE = """\t<!-- Google Analytics 4 -->
\t<script async src="https://www.googletagmanager.com/gtag/js?id=G-5PTYPV0S9P"></script>
\t<script>
\t\twindow.dataLayer = window.dataLayer || [];
\t\tfunction gtag(){dataLayer.push(arguments);}
\t\tgtag('js', new Date());

\t\tgtag('config', 'G-5PTYPV0S9P');
\t</script>

\t<!-- Google Tag Manager -->
\t<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
\tnew Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
\tj=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
\t'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
\t})(window,document,'script','dataLayer','GTM-M6FP6CGL');</script>"""'''

    if "OPTIMIZED_GTM_TEMPLATE = " in c:
        c = re.sub(r'OPTIMIZED_GTM_TEMPLATE = """.*?"""', new_opt_template, c, flags=re.DOTALL)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Updated scripts/optimize_js.py template.")

def update_llms_txt():
    path = os.path.join(ROOT, "llms.txt")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    c = c.replace("https://valuecafe.cc/to-beginners", "https://valuecafe.cc/to-beginners/pick-great-companies.html")
    c = c.replace("https://valuecafe.cc/statements", "https://valuecafe.cc/statements/balance-sheet.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated llms.txt links.")

def main():
    html_files = sorted(glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True))
    print(f"Processing {len(html_files)} HTML files...")

    updated_count = 0
    for f in html_files:
        rel = os.path.relpath(f, ROOT)
        with open(f, "r", encoding="utf-8") as fp:
            content = fp.read()

        first_d, last_d = get_git_dates(rel)

        # 1. Update Tracking
        if OLD_TRACKING_PATTERN.search(content):
            content = OLD_TRACKING_PATTERN.sub(GA4_GTM_REPLACEMENT, content, count=1)

        # 2. Update og:image
        og_m = OG_IMAGE_PATTERN.search(content)
        abs_og = "https://valuecafe.cc/images/index/hero.webp"
        if og_m:
            abs_og = resolve_absolute_og_image(rel, og_m.group(1))
            new_og_tag = f'<meta property="og:image" content="{abs_og}">'
            content = OG_IMAGE_PATTERN.sub(new_og_tag, content, count=1)

        # 3. Update JSON-LD
        new_jsonld = build_jsonld(rel, content, abs_og, first_d, last_d)
        if JSONLD_PATTERN.search(content):
            content = JSONLD_PATTERN.sub(new_jsonld, content, count=1)

        # 4. If index.html, add Philosophy cards
        if rel == "index.html":
            content = update_index_philosophy(content)

        with open(f, "w", encoding="utf-8") as fp:
            fp.write(content)
        updated_count += 1

    print(f"Successfully updated {updated_count} HTML files.")

    # 5. Rebuild sitemap.xml
    sitemap_content = generate_sitemap(html_files)
    sitemap_path = os.path.join(ROOT, "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as fp:
        fp.write(sitemap_content)
    print("Successfully rebuilt sitemap.xml.")

    # 6. Update llms.txt
    update_llms_txt()

    # 7. Update scripts/optimize_js.py
    update_optimize_js_py()

    print("All tasks finished successfully.")

if __name__ == "__main__":
    main()
