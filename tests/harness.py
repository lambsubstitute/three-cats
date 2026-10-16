"""Shared helpers for driving the game in headless Chromium with real key presses."""
import asyncio, json
from playwright.async_api import async_playwright
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
GAME = (ROOT / 'index.html').as_uri()
SP = str(ROOT / 'tests' / 'shots') + '/'
Path(SP).mkdir(exist_ok=True)
KEY = {'+x': 'ArrowRight', '-x': 'ArrowLeft', '+z': 'ArrowDown', '-z': 'ArrowUp'}
AX = {'x': 0, 'y': 1, 'z': 2}
RESULTS = []

def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + (('  [' + str(detail) + ']') if detail != '' else ''))

class Game:
    def __init__(self, pg): self.pg = pg; self.errs = []
    async def st(self, expr): return await self.pg.evaluate(f"(() => {{ const S = __cats.S; return {expr}; }})()")
    async def pos(self, cat): return await self.st(f"[S.cats.{cat}.x, S.cats.{cat}.y, S.cats.{cat}.z].map(v => +v.toFixed(2))")
    async def put(self, cat, x, z, y=0, select=True):
        await self.pg.evaluate(f"(() => {{ const c = __cats.S.cats.{cat}; c.x={x}; c.z={z}; c.y={y}; c.vy=0; c.safe=[{x},{y},{z}]; {'__cats.select(' + repr(cat) + ');' if select else ''} }})()")
        await self.pg.wait_for_timeout(60)
    async def select(self, cat):
        await self.pg.evaluate(f"__cats.select('{cat}')"); await self.pg.wait_for_timeout(40)
    async def wait(self, ms): await self.pg.wait_for_timeout(ms)
    async def walk(self, cat, dirn, target, limit=6000, shift=False):
        """Hold an arrow until the cat's coordinate passes target (or it stops moving)."""
        await self.select(cat)
        ax = AX[dirn[1]]; sign = 1 if dirn[0] == '+' else -1
        if shift: await self.pg.keyboard.down('ShiftLeft')
        await self.pg.keyboard.down(KEY[dirn])
        t = 0; last = None; still = 0
        while t < limit:
            await self.pg.wait_for_timeout(25); t += 25
            v = (await self.pos(cat))[ax]
            if (v - target) * sign >= 0: break
            if last is not None and abs(v - last) < 1e-4:
                still += 1
                if still > 24: break
            else: still = 0
            last = v
        await self.pg.keyboard.up(KEY[dirn])
        if shift: await self.pg.keyboard.up('ShiftLeft')
        await self.pg.wait_for_timeout(80)
        return await self.pos(cat)
    async def hop(self, cat, dirn, top, limit=1600):
        """Jump while walking; let go of the arrow as soon as the cat lands at or above `top`."""
        await self.select(cat)
        await self.pg.keyboard.down(KEY[dirn]); await self.pg.keyboard.down('Space')
        t = 0; released = False
        while t < limit:
            await self.pg.wait_for_timeout(20); t += 20
            if t > 120 and not released: await self.pg.keyboard.up('Space'); released = True
            y, g = await self.st(f"[S.cats.{cat}.y, S.cats.{cat}.ground]")
            if g and y >= top - 0.6 and t > 160: break
        await self.pg.keyboard.up(KEY[dirn])
        if not released: await self.pg.keyboard.up('Space')
        await self.pg.wait_for_timeout(200)
        return await self.pos(cat)
    async def leap(self, cat, dirn, stop_at, limit=2500):
        """Jump while walking: let go of Space right after take-off and of the arrow once
        the cat's coordinate passes stop_at, then wait for it to land."""
        await self.select(cat)
        ax = AX[dirn[1]]; sign = 1 if dirn[0] == '+' else -1
        await self.pg.keyboard.down(KEY[dirn]); await self.pg.keyboard.down('Space')
        t = 0; space = True; arrow = True; airborne = False
        while t < limit:
            await self.pg.wait_for_timeout(15); t += 15
            x, y, z, g = await self.st(f"[S.cats.{cat}.x, S.cats.{cat}.y, S.cats.{cat}.z, S.cats.{cat}.ground]")
            if not g: airborne = True
            if space and airborne: await self.pg.keyboard.up('Space'); space = False
            if arrow and ([x, y, z][ax] - stop_at) * sign >= 0: await self.pg.keyboard.up(KEY[dirn]); arrow = False
            if airborne and g and not arrow: break
            if airborne and g and arrow and t > 200:
                # landed before reaching the stop point (e.g. blocked): stop here
                break
        if space: await self.pg.keyboard.up('Space')
        if arrow: await self.pg.keyboard.up(KEY[dirn])
        await self.pg.wait_for_timeout(120)
        return await self.pos(cat)
    async def jump_in_place(self, cat, ms=900):
        await self.select(cat)
        await self.pg.keyboard.down('Space'); await self.pg.wait_for_timeout(100); await self.pg.keyboard.up('Space')
        peak = 0; t = 0
        while t < ms:
            await self.pg.wait_for_timeout(20); t += 20
            peak = max(peak, (await self.pos(cat))[1])
        return peak
    async def until(self, expr, limit=8000):
        t = 0
        while t < limit:
            if await self.st(expr): return True
            await self.pg.wait_for_timeout(50); t += 50
        return False
    async def shot(self, name): await self.pg.screenshot(path=SP + name)

async def run(room, body, viewport=(1280, 900)):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
        g = Game(pg)
        pg.on('pageerror', lambda e: g.errs.append(str(e)))
        await pg.goto(f'{GAME}#room{room}-test')
        await pg.reload(); await pg.wait_for_timeout(1300)
        await body(g)
        check(f'room {room}: no script errors', not g.errs, g.errs[:3])
        await b.close()

def summary():
    bad = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed' + ('' if not bad else '; failing: ' + ', '.join(bad)))
