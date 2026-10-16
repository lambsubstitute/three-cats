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
        await pg.goto(GAME + '#room2-test')
        await pg.wait_for_timeout(700)
        ev = pg.evaluate
        async def st(expr): return await ev(f"(() => {{ const S = __cats.S; return {expr}; }})()")
        async def pos(cat='tom'): return await st(f"[S.cats.{cat}.x, S.cats.{cat}.z]")
        async def walk(dirn, target, cat='tom', limit=6000, extra=None):
            ax = 0 if dirn[1] == 'x' else 1
            sign = 1 if dirn[0] == '+' else -1
            await pg.keyboard.down(KEY[dirn])
            t = 0; last = None; still = 0
            while t < limit:
                await pg.wait_for_timeout(25); t += 25
                v = (await pos(cat))[ax]
                if (v - target) * sign >= 0: break
                if last is not None and abs(v - last) < 1e-4:
                    still += 1
                    if still > 20: break
                else: still = 0
                last = v
            await pg.keyboard.up(KEY[dirn])
            await pg.wait_for_timeout(60)
            return await pos(cat)
        # park Moe and Joe out of the way, select Mr Mews
        await ev("(() => { const S = __cats.S; Object.assign(S.cats.ginger, {x: 112, z: 6, safe:[112,0,6]}); Object.assign(S.cats.smoke, {x: 116, z: 16, safe:[116,0,16]}); __cats.select('tom'); })()")
        print('start', await pos())
        # crate C (84,72): get to z ~81 (deliberately off-centre), push west
        print(await walk('-z', 81))
        print('push C ->', await walk('-x', 0, limit=2500), 'filled', await st("JSON.stringify(S.filled)"))
        async def place(x, z):
            await ev(f"(() => {{ const c = __cats.S.cats.tom; c.x={x}; c.z={z}; c.y=0; c.vy=0; c.safe=[{x},0,{z}]; }})()")
        # crate B (96,48): stand on its north side and push it south into row 72 with the keys
        await place(101, 40)
        print('push B south ->', await walk('+z', 66.0), 'B', await st("JSON.stringify([S.crates[1].x, S.crates[1].z])"))
        # stand on its east side, off-centre (row centre is 78, use 82), and push it west with the keys
        await place(114, 82)
        print('push B west ->', await walk('-x', 0, limit=5000), 'filled', await st("JSON.stringify(S.filled)"), 'crates', await st("JSON.stringify(S.crates.map(c=>[+c.x.toFixed(1),+c.z.toFixed(1),c.sunk]))"))
        await pg.screenshot(path=SP + 'bridge_built.png')
        # Mr Mews walks the bridge from slightly off-centre
        print('walk bridge ->', await walk('-x', 40, limit=5000))
        print('bridge goal done:', await st("document.querySelectorAll('#goals li')[0].classList.contains('done')"))
        await pg.screenshot(path=SP + 'bridge_crossed.png')
        print('errors:', errs)
        await b.close()
asyncio.run(main())
