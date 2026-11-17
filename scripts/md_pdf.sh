#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Markdown → PDF avec les figures SVG : pandoc (HTML autonome) puis Chrome sans écran.
#   scripts/md_pdf.sh docs/RAPPORT_TECHNIQUE.md      → docs/RAPPORT_TECHNIQUE.pdf
# Outils de rédaction seulement (pas des dépendances de Salubri) : pandoc (GPL-2.0+), Chrome ou Chromium.
set -euo pipefail
src="$1"; out="${src%.md}.pdf"; dir="$(cd "$(dirname "$src")" && pwd)"
chrome="$(command -v google-chrome || command -v chromium || command -v chromium-browser)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
css="$tmp/style.css"
cat > "$css" <<'CSS'
body{font-family:"DejaVu Sans",Arial,sans-serif;font-size:10.5pt;line-height:1.45;max-width:none;margin:0}
h1{font-size:20pt;color:#1d4e3f;border-bottom:3px solid #1d4e3f;padding-bottom:4px}
h2{font-size:14pt;color:#1d4e3f;margin-top:18pt}h3{font-size:12pt}
table{border-collapse:collapse;width:100%;font-size:8.5pt;margin:6pt 0;page-break-inside:auto}
th,td{border:1px solid #bbb;padding:3px 5px;vertical-align:top}th{background:#e6efe9}
tr{page-break-inside:avoid}img{max-width:100%}code{font-size:9pt;background:#f3f3f3}
blockquote{border-left:4px solid #c9a227;background:#fbf6e6;margin:8pt 0;padding:4pt 10pt}
@page{size:A4;margin:16mm 14mm}
CSS
(cd "$dir" && pandoc "$(basename "$src")" -f gfm -t html5 -s --embed-resources --metadata pagetitle="Salubri" \
  --css "$css" -o "$tmp/doc.html")
"$chrome" --headless --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf="$tmp/doc.pdf" "file://$tmp/doc.html" 2>/dev/null
mv "$tmp/doc.pdf" "$out"
echo "$out"
