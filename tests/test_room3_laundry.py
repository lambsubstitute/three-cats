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
        pg = await b.new_page(viewport={'width': 1280, 'height': 900})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_TUNNEL' not in m.text else None)

        # --- title screen
        await pg.goto(GAME + '#test')
        await pg.wait_for_timeout(1500)
        print('mode at load:', await pg.evaluate("__cats.mode"), 'title visible:', await pg.evaluate("!document.getElementById('title').hidden"))
        await pg.screenshot(path=SP + 'title.png')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        print('after Enter:', await pg.evaluate("__cats.mode"), await pg.evaluate("__cats.S.room"))

        # --- Room 3
        await pg.goto(GAME + '#room3-test')
        await pg.reload()
        await pg.wait_for_timeout(1200)
        ev = pg.evaluate
        async def st(expr): return await ev(f"(() => {{ const S = __cats.S; return {expr}; }})()")
        async def put(cat, x, z, y=0):
            await ev(f"(() => {{ const c = __cats.S.cats.{cat}; c.x={x}; c.z={z}; c.y={y}; c.vy=0; c.safe=[{x},{y},{z}]; __cats.select('{cat}'); }})()")
        async def pos(cat): return await st(f"[S.cats.{cat}.x, S.cats.{cat}.y, S.cats.{cat}.z].map(v => +v.toFixed(1))")
        async def walk(cat, dirn, target, limit=5000):
            ax = 0 if dirn[1] == 'x' else 2
            sign = 1 if dirn[0] == '+' else -1
            await pg.keyboard.down(KEY[dirn]); t = 0
            while t < limit:
                await pg.wait_for_timeout(25); t += 25
                if ((await pos(cat))[ax] - target) * sign >= 0: break
            await pg.keyboard.up(KEY[dirn]); await pg.wait_for_timeout(60)
            return await pos(cat)
        async def hop(cat, dirn, top, limit=1500):
            # jump while walking, and let go of the arrow as soon as the cat lands on the higher surface
            await pg.keyboard.down(KEY[dirn]); await pg.keyboard.down('Space')
            t = 0; released = False
            while t < limit:
                await pg.wait_for_timeout(20); t += 20
                if t > 120 and not released: await pg.keyboard.up('Space'); released = True
                y, g = await st(f"[S.cats.{cat}.y, S.cats.{cat}.ground]")
                if g and y >= top - 0.6 and t > 150: break
            await pg.keyboard.up(KEY[dirn])
            if not released: await pg.keyboard.up('Space')
            await pg.wait_for_timeout(200)
            return await pos(cat)
        print('room:', await st("S.room"), 'hoover at', await st("S.vac.x.toFixed(1)"))

        # hoover shoos a cat standing in its lane
        hx = await st("S.vac.x"); d = await st("S.vac.dir")
        await put('smoke', hx + d * 25, 54)
        await ev("(() => { __cats.S.cats.smoke.safe = [24, 0, 89]; })()")
        await pg.wait_for_timeout(1200)
        print('Joe after hoover pass:', await pos('smoke'))
        await pg.screenshot(path=SP + 'r3_shoo.png')

        # Mr Mews pushes the right-hand crate north into the hoover's lane (wait until the hoover is on the far left)
        await put('tom', 90, 85)
        for _ in range(80):
            if await st("S.vac.x < 40 && S.vac.dir < 0"): break
            await pg.wait_for_timeout(50)
        print('push crate north ->', await walk('tom', '-z', 60.2), 'crate', await st("JSON.stringify([S.crates[1].x, S.crates[1].z])"))
        mx = 0
        for _ in range(60):
            mx = max(mx, await st("S.vac.x")); await pg.wait_for_timeout(50)
        print('hoover furthest right over 3s:', round(mx, 1), '(crate starts at x=84)')

        # Joe walks onto the lane pad, right of the crate
        await put('smoke', 102, 80)
        print('Joe to pad ->', await walk('smoke', '-z', 54), 'pads', await st("JSON.stringify(S.plates)"))

        # Moe: washing machine, then the shelf with the other pad
        await put('ginger', 18, 41)
        print('Moe onto washer ->', await hop('ginger', '-z', 16))
        print('Moe onto shelf ->', await hop('ginger', '-x', 30))
        print('pads', await st("JSON.stringify(S.plates)"), 'latched', await st("S.latched"))
        await pg.screenshot(path=SP + 'r3_pads.png')

        # cat tower beside the boiler
        await put('tom', 114, 19)
        await put('smoke', 114, 31)
        print('Joe onto Mr Mews ->', await hop('smoke', '-z', 10))
        await put('ginger', 114, 33)
        print('Moe onto Joe ->', await hop('ginger', '-z', 20))
        await pg.screenshot(path=SP + 'r3_tower.png')
        print('Moe onto boiler ->', await hop('ginger', '-z', 44), 'carry', await st("S.cats.ginger.carry"))

        # all out through the back door
        await pg.wait_for_timeout(800)
        for cat in ('ginger', 'smoke', 'tom'):
            await put(cat, 96, 22)
            await walk(cat, '-z', 0, limit=1500)
        await pg.wait_for_timeout(300)
        print('moved on to room 4:', await st("S.room === 3"), 'fish', await st("S.fishTotal"))
        print('progress saved:', await ev("localStorage.getItem('moe-joe-mrmews-save')"))
        await pg.screenshot(path=SP + 'r3_win.png')
        print('errors:', errs)
        await b.close()
asyncio.run(main())
