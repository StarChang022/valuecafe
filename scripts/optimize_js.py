#!/usr/bin/env python3
"""
ValueCafe JavaScript & Tracking Optimization Pipeline
=====================================================
Optimizations applied:
  1. Tracking (GA4 + GTM):
     - Eliminates duplicate GA4 loading (G-5PTYPV0S9P was loaded twice: directly and via GTM).
     - Delays GTM loading until user interaction (touchstart, scroll, mousemove, click, keydown)
       or 3.5s timeout, preventing 457 KiB of unused JS from blocking FCP/LCP/TBT during PageSpeed audits.
  2. 1st Party JS (Canvas Modular Loading):
     - Replaces heavy all-in-one bundle (plugins.min.js [738KB] + functions.bundle.js [308KB])
       with Canvas's native dynamic modular loader (functions.js [~37KB, ~10KB gzip]).
     - Automatically configures cnvsOptions (jsFolder, cssFolder) based on file depth.
     - Modules and plugins (e.g. menus, gototop, carousel) are loaded on-demand only when needed.

Usage:
    python3 scripts/optimize_js.py [--dry-run]
"""

import os
import re
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY_RUN = "--dry-run" in sys.argv

GA_GTM_PATTERN = re.compile(
    r'[ \t]*<!-- Google Analytics 4 -->\s*'
    r'<script async src="https://www\.googletagmanager\.com/gtag/js\?id=G-5PTYPV0S9P"></script>\s*'
    r'<script>.*?'
    r'gtag\([\'"]config[\'"],\s*[\'"]G-5PTYPV0S9P[\'"]\);\s*'
    r'</script>\s*'
    r'<!-- Google Tag Manager -->\s*'
    r'<script>\(function\s*\(w,\s*d,\s*s,\s*l,\s*i\).*?GTM-M6FP6CGL.*?</script>',
    re.DOTALL
)

OPTIMIZED_GTM_TEMPLATE = """\t<!-- Google Tag Manager (Optimized: Lazy Loaded on User Interaction) -->
\t<script>
\t\twindow.dataLayer = window.dataLayer || [];
\t\t(function () {
\t\t\tvar gtmLoaded = false;
\t\t\tfunction loadGTM() {
\t\t\t\tif (gtmLoaded) return;
\t\t\t\tgtmLoaded = true;
\t\t\t\twindow.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
\t\t\t\tvar f = document.getElementsByTagName('script')[0],
\t\t\t\t\tj = document.createElement('script');
\t\t\t\tj.async = true;
\t\t\t\tj.src = 'https://www.googletagmanager.com/gtm.js?id=GTM-M6FP6CGL';
\t\t\t\tf.parentNode.insertBefore(j, f);
\t\t\t\t['touchstart', 'scroll', 'mousemove', 'click', 'keydown'].forEach(function (e) {
\t\t\t\t\twindow.removeEventListener(e, loadGTM, { passive: true });
\t\t\t\t});
\t\t\t}
\t\t\t['touchstart', 'scroll', 'mousemove', 'click', 'keydown'].forEach(function (e) {
\t\t\t\twindow.addEventListener(e, loadGTM, { passive: true, once: true });
\t\t\t});
\t\t\tsetTimeout(loadGTM, 3500);
\t\t})();
\t</script>"""

JS_BUNDLE_PATTERN = re.compile(
    r'[ \t]*<!-- JavaScripts -->\s*'
    r'<script defer src="(?:\.\./)?js/plugins\.min\.js"></script>\s*'
    r'<script defer src="(?:\.\./)?js/functions\.bundle\.js"></script>',
    re.DOTALL
)

def get_optimized_js_template(depth):
    prefix = "../" if depth > 0 else ""
    js_folder = f"{prefix}js/"
    css_folder = f"{prefix}css/"
    js_src = f"{prefix}js/functions.js"

    return f"""\t<!-- JavaScripts -->
\t<script>
\t\tvar cnvsOptions = {{
\t\t\tjsFolder: '{js_folder}',
\t\t\tcssFolder: '{css_folder}'
\t\t}};
\t</script>
\t<script defer src="{js_src}"></script>"""

def main():
    os.chdir(ROOT)
    html_files = sorted(glob.glob("**/*.html", recursive=True))
    print(f"Found {len(html_files)} HTML files in {ROOT}")
    if DRY_RUN:
        print("[DRY RUN MODE] No files will be modified.\n")

    ga_updated = 0
    js_updated = 0

    for rel_path in html_files:
        with open(rel_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = content
        depth = rel_path.count(os.sep)

        # 1. Replace GA4 + GTM
        if GA_GTM_PATTERN.search(new_content):
            new_content = GA_GTM_PATTERN.sub(OPTIMIZED_GTM_TEMPLATE, new_content, count=1)
            ga_updated += 1
        else:
            print(f"  [WARN] GA+GTM pattern not found in: {rel_path}")

        # 2. Replace JS Bundle
        if JS_BUNDLE_PATTERN.search(new_content):
            optimized_js = get_optimized_js_template(depth)
            new_content = JS_BUNDLE_PATTERN.sub(optimized_js, new_content, count=1)
            js_updated += 1
        else:
            print(f"  [WARN] JS Bundle pattern not found in: {rel_path}")

        if not DRY_RUN and new_content != content:
            with open(rel_path, "w", encoding="utf-8") as f:
                f.write(new_content)

    print("\n==========================================")
    print("Optimization Summary:")
    print(f"  Total HTML files processed: {len(html_files)}")
    print(f"  Tracking (GA+GTM) updated:  {ga_updated}/{len(html_files)}")
    print(f"  Canvas Modular JS updated:  {js_updated}/{len(html_files)}")
    print("==========================================")
    if DRY_RUN:
        print("Run without --dry-run to apply changes.")

if __name__ == "__main__":
    main()
