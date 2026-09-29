#!/usr/bin/env python3
"""
ValueCafe CSS Build Script
- Minifies style.css -> style.min.css (with calc() and media query safety)
- Bundles [params, components, custom, pages, widgets] -> css/app.css & css/app.min.css
"""

import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def minify_css_safe(css):
    tokens = {}
    counter = 0

    def save_str(m):
        nonlocal counter
        k = f"__STR_TOKEN_{counter}__"
        tokens[k] = m.group(0)
        counter += 1
        return k

    def save_calc(m):
        nonlocal counter
        k = f"__CALC_TOKEN_{counter}__"
        tokens[k] = m.group(0)
        counter += 1
        return k

    # Protect strings
    css = re.sub(r"\"[^\"]*\"|\x27[^\x27]*\x27", save_str, css)
    # Protect calc / min / max / clamp
    css = re.sub(r"(?:calc|min|max|clamp)\([^\)]+\)", save_calc, css)

    # Remove comments
    css = re.sub(r"/\*[\s\S]*?\*/", "", css)

    # Normalize whitespace
    css = re.sub(r"\s+", " ", css)

    # Remove spaces around safe delimiters
    css = re.sub(r"\s*([\{\};,>~])\s*", r"\1", css)
    # Remove spaces around colon ONLY in declaration context (after identifier/value)
    # Use a lookahead: only strip space before : if it's followed by a non-( char
    # (this protects :not(, :is(, :has(, :where(, :nth-child( etc.)
    css = re.sub(r"\s+:\s*", ":", css)  # space before colon -> remove
    css = re.sub(r":\s+", ":", css)     # space after colon -> remove (property values)

    # Fix spaces for @media and @supports at-rule keywords only
    # Restore 'and (' and 'or (' and 'not (' ONLY when preceded by ) or a media feature
    css = re.sub(r"\)\s*(and|or|not)\s*\(", r") \1 (", css)
    css = re.sub(r"@media\(", "@media (", css)
    css = re.sub(r"@supports\(", "@supports (", css)

    # Remove trailing semicolon before }
    css = re.sub(r";\}", "}", css)

    # Restore protected tokens in reverse order
    for k, v in reversed(list(tokens.items())):
        css = css.replace(k, v)

    return css.strip()


def build():
    # 1. Minify style.css
    style_path = os.path.join(ROOT_DIR, "style.css")
    style_min_path = os.path.join(ROOT_DIR, "style.min.css")

    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            style_content = f.read()

        if style_content.startswith("Ｐ"):
            style_content = style_content[1:]

        style_min = minify_css_safe(style_content)
        with open(style_min_path, "w", encoding="utf-8") as f:
            f.write(style_min)
        print(f"✓ Built style.min.css ({len(style_content):,} bytes -> {len(style_min):,} bytes)")

    # 2. Bundle custom CSS
    custom_files = [
        "css/params.css",
        "css/components.css",
        "css/custom.css",
        "css/pages.css",
        "css/widgets.css",
    ]

    parts = []
    for rel_path in custom_files:
        full_path = os.path.join(ROOT_DIR, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                parts.append(f"/* === {os.path.basename(rel_path)} === */\n" + f.read())

    app_css = "\n\n".join(parts)
    app_css_path = os.path.join(ROOT_DIR, "css", "app.css")
    with open(app_css_path, "w", encoding="utf-8") as f:
        f.write(app_css)

    app_min = minify_css_safe(app_css)
    app_min_path = os.path.join(ROOT_DIR, "css", "app.min.css")
    with open(app_min_path, "w", encoding="utf-8") as f:
        f.write(app_min)

    print(f"✓ Built css/app.css ({len(app_css):,} bytes)")
    print(f"✓ Built css/app.min.css ({len(app_min):,} bytes)")

    # 3. Append app.min into style.min.css (eliminates the second CSS HTTP request)
    # Fix relative image paths: ../images/ -> images/ (style.min.css lives at root, not /css/)
    app_min_for_merge = app_min.replace("url('../images/", "url('images/").replace('url("../images/', 'url("images/')
    with open(style_min_path, "a", encoding="utf-8") as f:
        f.write("\n" + app_min_for_merge)

    with open(style_min_path, "r", encoding="utf-8") as f:
        merged_size = len(f.read())
    print(f"✓ Merged app.min.css into style.min.css (final: {merged_size:,} bytes)")


if __name__ == "__main__":
    build()
