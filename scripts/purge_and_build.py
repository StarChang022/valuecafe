#!/usr/bin/env python3
"""
ValueCafe CSS Optimization Pipeline
====================================
Steps:
  1. Scan all HTML & JS files to collect every token that could be a CSS selector
  2. Parse style.css rule-by-rule, drop rules whose selectors are entirely unused
  3. Append app.css (custom styles) to the purged style CSS
  4. Minify the merged result -> style.min.css
  5. Remove css/app.min.css references from all HTML files
  6. Print a before/after size report

Safety rules applied
---------------------
* Element selectors (div, span, a, p, h1-h6, header, footer, nav, ...) are always kept
* Any selector containing a token found in HTML/JS is kept
* Any selector containing :root, :before, :after, ::, [data-, @keyframes, @font-face,
  @charset, @layer is always kept
* Safelist: explicit extra patterns you know are added dynamically by Canvas JS

Usage:
    python3 scripts/purge_and_build.py [--dry-run]
"""

import os
import re
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# SAFELIST - patterns to ALWAYS keep (regex, matched against the full selector)
# Add any JS-generated classes / data-* driven variants you know Canvas uses
# ---------------------------------------------------------------------------
SAFELIST_PATTERNS = [
    r":root",
    r"::?before",
    r"::?after",
    r"::?placeholder",
    r"::?selection",
    r"::?webkit",
    r"\[data-",
    r"@",
    r"\.dark",
    r"\.device-",
    r"\.rtl",
    r"\.sticky-header",
    r"\.has-plugin",
    r"\.menu-open",
    r"\.mega-menu",
    r"\.sub-menu",
    r"\.dropdown",
    r"\.collapsing",
    r"\.collapse",
    r"\.fade",
    r"\.show",
    r"\.hide",
    r"\.hidden",
    r"\.visible",
    r"\.active",
    r"\.disabled",
    r"\.open",
    r"\.no-",
    r"\.is-",
    r"\.has-",
    r"\.was-",
    r"\.needs-",
    r"\.form-",
    r"\.input-",
    r"\.btn",
    r"\.nav",
    r"\.page-",
    r"\.slider-",
    r"\.swiper",
    r"\.owl-",
    r"\.modal",
    r"\.tooltip",
    r"\.popover",
    r"\.offcanvas",
    r"\.toast",
    r"\.alert",
    r"\.badge",
    r"\.spinner",
    r"\.progress",
    r"\.accordion",
    r"\.carousel",
    r"\.tab-",
    r"\.nav-tab",
    r"\.scroll",
    r"\.loading",
    r"\.preloader",
    r"\.overlay",
    r"\.not-found",
    r"html\b",
    r"\bbody\b",
    r"\ba\b",
    r"\bp\b",
    r"\bul\b",
    r"\bol\b",
    r"\bli\b",
    r"\bimg\b",
    r"\bsvg\b",
    r"\biframe\b",
    r"\bvideo\b",
    r"\baudio\b",
    r"\btable\b",
    r"\bthead\b",
    r"\btbody\b",
    r"\btr\b",
    r"\btd\b",
    r"\bth\b",
    r"\bform\b",
    r"\binput\b",
    r"\btextarea\b",
    r"\bselect\b",
    r"\blabel\b",
    r"\bbutton\b",
    r"\bfigure\b",
    r"\bfigcaption\b",
    r"\bblockquote\b",
    r"\bpre\b",
    r"\bcode\b",
    r"\bhr\b",
    r"\bh[1-6]\b",
    r"\bstrong\b",
    r"\bem\b",
    r"\bspan\b",
    r"\bdiv\b",
    r"\bsection\b",
    r"\barticle\b",
    r"\baside\b",
    r"\bheader\b",
    r"\bfooter\b",
    r"\bnav\b",
    r"\bmain\b",
    r"\bdl\b",
    r"\bdt\b",
    r"\bdd\b",
    r"\bsmall\b",
    r"\babbr\b",
    r"\bmark\b",
    r"\bsub\b",
    r"\bsup\b",
    r"\bnoscript\b",
    r"\btime\b",
    r"\baddress\b",
    # Bootstrap utilities we always want
    r"\brow\b",
    r"\bcol\b",
    r"col-",
    r"\bcontainer\b",
    r"container-",
    r"\bd-",
    r"\bg-",
    r"\bms-",
    r"\bme-",
    r"\bmt-",
    r"\bmb-",
    r"\bmy-",
    r"\bmx-",
    r"\bps-",
    r"\bpe-",
    r"\bpt-",
    r"\bpb-",
    r"\bpy-",
    r"\bpx-",
    r"\btext-",
    r"\bbg-",
    r"\bborder",
    r"\brounded",
    r"\bw-",
    r"\bh-",
    r"\bflex",
    r"\bjustify-",
    r"\balign-",
    r"\bposition-",
    r"\btop-",
    r"\bend-",
    r"\bstart-",
    r"\boverflow",
    r"\bvisually-",
    r"\bsr-only",
    r"\bfloat-",
    r"\bvr\b",
]

SAFELIST_RE = [re.compile(p, re.IGNORECASE) for p in SAFELIST_PATTERNS]


# ---------------------------------------------------------------------------
# STEP 1: Collect all tokens from HTML & JS
# ---------------------------------------------------------------------------

def collect_tokens():
    """Return a set of all class names, IDs, element names found in HTML & JS."""
    tokens = set()

    html_files = glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True)
    js_files = [
        os.path.join(ROOT, "js", "functions.js"),
        os.path.join(ROOT, "js", "functions.bundle.js"),
    ]
    source_files = html_files + [f for f in js_files if os.path.exists(f)]

    for filepath in source_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        # class="..." - capture individual class names
        for m in re.finditer(r'class=["\']([^"\']+)["\']', content):
            for cls in m.group(1).split():
                tokens.add(cls)

        # id="..."
        for m in re.finditer(r'\bid=["\']([^"\']+)["\']', content):
            tokens.add(m.group(1))

        # data-* values
        for m in re.finditer(r'data-[a-z\-]+=["\']([^"\']+)["\']', content):
            for val in m.group(1).split():
                tokens.add(val)

        # JS: addClass / classList.add patterns
        for m in re.finditer(
            r'(?:addClass|classList\.(?:add|remove|toggle|contains))\s*\(\s*[\'"]([^\'"]+)[\'"]',
            content
        ):
            for cls in m.group(1).split():
                tokens.add(cls)

        # JS: $(".xxx") querySelector style strings
        for m in re.finditer(r'["\']([a-zA-Z0-9\s\-#.:\[\]>~+*,_]+)["\']', content):
            for part in re.split(r'[\s,>+~]', m.group(1)):
                part = part.strip()
                if part.startswith(".") or part.startswith("#"):
                    tokens.add(part.lstrip(".#"))
                elif part and re.match(r'^[a-zA-Z][a-zA-Z0-9\-_]*$', part):
                    tokens.add(part)

    print(f"  Collected {len(tokens):,} unique tokens from {len(source_files)} source files")
    return tokens


# ---------------------------------------------------------------------------
# STEP 2: Parse style.css and keep/drop rule blocks
# ---------------------------------------------------------------------------

def should_keep_rule(selector_block, tokens):
    """Return True if this rule block should be kept."""
    stripped = selector_block.strip()
    if stripped.startswith("@"):
        return True

    for pattern in SAFELIST_RE:
        if pattern.search(selector_block):
            return True

    cleaned = re.sub(r'::[a-zA-Z\-]+', '', selector_block)
    cleaned = re.sub(r':[a-zA-Z\-]+(\([^)]*\))?', '', cleaned)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'[>+~]', ' ', cleaned)
    cleaned = re.sub(r'[{}()\'\"@;:!]', ' ', cleaned)

    for m in re.finditer(r'\.([a-zA-Z][a-zA-Z0-9_\-]*)', cleaned):
        if m.group(1) in tokens:
            return True

    for m in re.finditer(r'#([a-zA-Z][a-zA-Z0-9_\-]*)', cleaned):
        if m.group(1) in tokens:
            return True

    for m in re.finditer(r'\b([a-zA-Z][a-zA-Z0-9]*)\b', cleaned):
        if m.group(1) in tokens:
            return True

    return False


def purge_css(css_content, tokens):
    """
    Walk through CSS content, keeping rules whose selectors are used.
    Handles nested @media / @supports blocks correctly.
    Returns (purged_css, kept_count, dropped_count).
    """
    result = []
    kept = 0
    dropped = 0

    i = 0
    length = len(css_content)

    while i < length:
        while i < length and css_content[i] in ' \t\r\n':
            i += 1
        if i >= length:
            break

        if css_content[i] == '@':
            j = i
            while j < length and css_content[j] not in '{;':
                j += 1

            if j >= length:
                result.append(css_content[i:])
                break

            if css_content[j] == ';':
                result.append(css_content[i:j+1])
                kept += 1
                i = j + 1
                continue

            at_header = css_content[i:j+1]
            i = j + 1

            depth = 1
            block_start = i
            while i < length and depth > 0:
                if css_content[i] == '{':
                    depth += 1
                elif css_content[i] == '}':
                    depth -= 1
                i += 1
            block_content = css_content[block_start:i-1]

            at_keyword = at_header.split()[0].lower()

            if at_keyword in (
                '@keyframes', '@-webkit-keyframes', '@-moz-keyframes',
                '@font-face', '@charset', '@import', '@layer', '@property',
                '@counter-style'
            ):
                result.append(at_header + block_content + "}")
                kept += 1
            else:
                inner_purged, k, d = purge_css(block_content, tokens)
                kept += k
                dropped += d
                inner_stripped = inner_purged.strip()
                if inner_stripped:
                    result.append(at_header + inner_purged + "}")
            continue

        j = i
        while j < length and css_content[j] != '{':
            j += 1

        if j >= length:
            break

        selector = css_content[i:j]
        i = j + 1

        depth = 1
        body_start = i
        while i < length and depth > 0:
            if css_content[i] == '{':
                depth += 1
            elif css_content[i] == '}':
                depth -= 1
            i += 1
        body = css_content[body_start:i-1]

        if should_keep_rule(selector, tokens):
            result.append(selector + "{" + body + "}")
            kept += 1
        else:
            dropped += 1

    return "".join(result), kept, dropped


# ---------------------------------------------------------------------------
# STEP 3: Minify CSS
# ---------------------------------------------------------------------------

def minify_css_safe(css):
    saved_tokens = {}
    counter = 0

    def save_str(m):
        nonlocal counter
        k = f"__STR_TOKEN_{counter}__"
        saved_tokens[k] = m.group(0)
        counter += 1
        return k

    def save_calc(m):
        nonlocal counter
        k = f"__CALC_TOKEN_{counter}__"
        saved_tokens[k] = m.group(0)
        counter += 1
        return k

    css = re.sub(r'"[^"]*"|\'[^\']*\'', save_str, css)
    css = re.sub(r'(?:calc|min|max|clamp)\([^)]+\)', save_calc, css)
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};,>~])\s*', r'\1', css)
    css = re.sub(r'\s+:\s*', ':', css)
    css = re.sub(r':\s+', ':', css)
    css = re.sub(r'\)\s*(and|or|not)\s*\(', r') \1 (', css)
    css = re.sub(r'@media\(', '@media (', css)
    css = re.sub(r'@supports\(', '@supports (', css)
    css = re.sub(r';}', '}', css)

    for k, v in reversed(list(saved_tokens.items())):
        css = css.replace(k, v)

    return css.strip()


# ---------------------------------------------------------------------------
# STEP 4: Remove app.min.css references from all HTML files
# ---------------------------------------------------------------------------

APP_CSS_LINK_RE = re.compile(
    r'\t?<link[^>]+href=["\'][^"\']*app\.min\.css[^"\']*["\'][^>]*>\n?',
    re.IGNORECASE
)


def remove_app_css_from_html(filepath):
    """Remove all <link> tags pointing to app.min.css. Return True if changed."""
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    cleaned = APP_CSS_LINK_RE.sub('', original)

    if cleaned == original:
        return False

    if not DRY_RUN:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cleaned)
    return True


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("ValueCafe CSS Optimization Pipeline")
    if DRY_RUN:
        print("  WARNING: DRY-RUN mode - no files will be written")
    print("=" * 60)

    print("\n[Step 1] Scanning HTML & JS for used tokens...")
    tokens = collect_tokens()

    print("\n[Step 2] Purging unused rules from style.css...")
    style_path = os.path.join(ROOT, "style.css")
    with open(style_path, "r", encoding="utf-8") as f:
        style_raw = f.read()
    original_size = len(style_raw.encode("utf-8"))

    if style_raw and ord(style_raw[0]) > 127:
        style_raw = style_raw[1:]

    purged_css, kept, dropped = purge_css(style_raw, tokens)
    print(f"  Kept {kept:,} rules, dropped {dropped:,} rules")

    print("\n[Step 3] Merging css/app.css into purged style...")
    app_css_path = os.path.join(ROOT, "css", "app.css")
    with open(app_css_path, "r", encoding="utf-8") as f:
        app_css = f.read()
    merged_css = purged_css + "\n\n/* === app.css (ValueCafe custom) === */\n" + app_css

    print("\n[Step 4] Minifying merged CSS...")
    minified = minify_css_safe(merged_css)
    final_size = len(minified.encode("utf-8"))

    style_min_path = os.path.join(ROOT, "style.min.css")
    if not DRY_RUN:
        with open(style_min_path, "w", encoding="utf-8") as f:
            f.write(minified)

    reduction_pct = 100 * (1 - final_size / original_size)
    print(f"  style.min.css: {original_size/1024:.1f} KiB -> {final_size/1024:.1f} KiB ({reduction_pct:.1f}% smaller)")

    print("\n[Step 5] Removing app.min.css references from HTML files...")
    html_files = glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True)
    changed_count = 0
    for html_path in html_files:
        if remove_app_css_from_html(html_path):
            rel = os.path.relpath(html_path, ROOT)
            print(f"  Updated: {rel}")
            changed_count += 1

    print(f"\n  {changed_count} HTML file(s) updated")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  style.min.css size : {original_size/1024:.1f} KiB  ->  {final_size/1024:.1f} KiB")
    print(f"  Size reduction     : {reduction_pct:.1f}%")
    print(f"  Kept rules         : {kept:,}")
    print(f"  Dropped rules      : {dropped:,}")
    print(f"  HTML files updated : {changed_count}")
    if DRY_RUN:
        print("\n  DRY-RUN - no files were modified. Remove --dry-run to apply.")
    else:
        print("\n  Done! Deploy the new style.min.css to see the improvement.")
    print("=" * 60)


if __name__ == "__main__":
    main()
