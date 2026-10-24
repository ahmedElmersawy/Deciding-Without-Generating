#!/usr/bin/env bash
# Build a marked-up PDF (deletions struck out in red, additions underlined in blue) between
# two versions of the paper source in main/. Each file is diffed on its own rather than with
# --flatten: flattening puts the abstract inside \twocolumn[...], which latexdiff can only
# swap whole, so abstract changes would go unmarked. Tabulars are diffed as whole blocks (old
# struck, new shown): marking up inside them breaks rules such as \cmidrule.
#
# Usage: bash scripts/paper_diff.sh [OLD_REF] [OUT_PDF]
#   OLD_REF  git ref of the old version (default: paper-baseline-2026-10-23)
#   OUT_PDF  output path (default: main/main_diff.pdf)
# The new version is the working tree's main/. Needs latexdiff and ulem.sty.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
old_ref=${1:-paper-baseline-2026-10-23}
out=${2:-main/main_diff.pdf}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/old"
git archive "$old_ref" main | tar -x -C "$work/old"
cp -r main "$work/new"
cd "$work/new"
rm -f ./*.aux ./*.bbl ./*.blg ./*.log ./*.out

for f in main.tex sections/*.tex; do
  if [ -f "$work/old/main/$f" ]; then
    latexdiff --config="PICTUREENV=(?:picture|DIFnomarkup|tabular)[\w\d*@]*" "$work/old/main/$f" "$f" > "$f.diff" 2>/dev/null
    mv "$f.diff" "$f"
  fi
done

pdflatex -interaction=nonstopmode -halt-on-error main >/dev/null
bibtex main >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main >/dev/null
cd - >/dev/null
cp "$work/new/main.pdf" "$out"
echo "$out"
