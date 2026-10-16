"""Bundle the game into one self-contained page.

Inlines the rendered sprites (art/assets.js) into the game code (src/game.html)
and writes index.html, which runs straight from the file system or any web host.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
template = (ROOT / 'src' / 'game.html').read_text(encoding='utf-8')
assets = (ROOT / 'art' / 'assets.js').read_text(encoding='utf-8')
if '/*ASSETS*/' not in template:
    raise SystemExit('src/game.html is missing the /*ASSETS*/ placeholder')
page = '<!doctype html>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' \
       + template.replace('/*ASSETS*/', assets)
(ROOT / 'index.html').write_text(page, encoding='utf-8')
print(f'wrote index.html ({len(page) // 1024} KB)')
