import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
GAME = (ROOT / 'index.html').as_uri()
SP = str(ROOT / 'tests' / 'shots') + '/'
Path(SP).mkdir(exist_ok=True)
KEY = {'+x': 'ArrowRight', '-x': 'ArrowLeft', '+z': 'ArrowDown', '-z': 'ArrowUp'}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(GAME + '#test')
        await pg.wait_for_timeout(1200)
        await pg.evaluate("localStorage.clear()")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        ev = pg.evaluate
        async def st(expr): return await ev(f"(() => {{ const S = __cats.S; return {expr}; }})()")
        async def put(cat, x, z, y=0):
            await ev(f"(() => {{ const c = __cats.S.cats.{cat}; c.x={x}; c.z={z}; c.y={y}; c.vy=0; c.safe=[{x},{y},{z}]; __cats.select('{cat}'); }})()")
        async def walk(cat, dirn, ms):
            await pg.keyboard.down(KEY[dirn]); await pg.wait_for_timeout(ms); await pg.keyboard.up(KEY[dirn]); await pg.wait_for_timeout(80)
        print('room', await st("S.room"), 'mode', await ev("__cats.mode"))
        # Mr Mews onto the red plate, Joe presses the button behind the fence
        await put('tom', 18, 66); await walk('tom', '-z', 300)
        await put('smoke', 86, 32); await walk('smoke', '-z', 700)
        print('plate', await st("S.plate"), 'button', await st("S.button"))
        # fish: Moe off Mr Mews's back onto the ledge
        await put('tom', 30, 12); await put('ginger', 31, 12, 10)
        await pg.keyboard.down('Space'); await pg.keyboard.down('ArrowLeft'); await pg.wait_for_timeout(120)
        await pg.keyboard.up('Space'); await pg.wait_for_timeout(450); await pg.keyboard.up('ArrowLeft'); await pg.wait_for_timeout(300)
        print('Moe carries', await st("S.cats.ginger.carry"))
        # the plate needs holding: put a crate on it instead of Mr Mews, then everyone leaves
        await ev("(() => { const S = __cats.S; Object.assign(S.crates[1], {x: 12, z: 48, y: 0}); })()")
        await pg.wait_for_timeout(1500)
        print('gate', await st("S.gate.toFixed(2)"))
        for cat in ('ginger', 'smoke', 'tom'):
            await put(cat, 12, 72); await walk(cat, '-x', 600)
        await pg.wait_for_timeout(400)
        print('now in room', await st("S.room"), 'fish', await st("S.fishTotal"), 'save', await ev("localStorage.getItem('moe-joe-mrmews-save')"))
        # reload: title should offer Continue in the Scullery
        await pg.goto(GAME); await pg.wait_for_timeout(1200)
        print('continue button:', await ev("document.getElementById('continueBtn').hidden ? 'hidden' : document.getElementById('continueBtn').textContent"))
        await pg.screenshot(path=SP + 'title_continue.png')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(500)
        print('after Enter, header:', await ev("document.getElementById('roomName').textContent"))
        print('errors:', errs)
        await b.close()
asyncio.run(main())
