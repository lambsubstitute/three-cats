import asyncio
from harness import *
CR = "[S.crates[1].x, S.crates[1].z].map(v => +v.toFixed(1))"
async def body(g):
    for label, strip in (('fresh game', False), ('game carried over from the last version (crates with no kind)', True)):
        await g.pg.evaluate("location.reload()"); await g.wait(1300)
        if strip:
            await g.pg.evaluate("(() => { for (const c of __cats.S.crates) { delete c.kind; delete c.h; } })()")
        await g.put('ginger', 80, 86, select=False); await g.put('smoke', 90, 86, select=False)
        # Mr Mews pushes the crate at (36,48) west along its row onto the red plate at (12..24, 48..60)
        await g.put('tom', 54, 54)
        await g.walk('tom', '-x', 30.5)
        c = await g.st(CR)
        await g.wait(300)
        check(f'{label}: crate pushed onto the plate', 11 <= c[0] <= 14, c)
        await g.walk('tom', '+x', 60); await g.wait(300)
        check(f'{label}: plate stays down under the crate after Mr Mews leaves', await g.st("S.plate"))
asyncio.run(run(1, body)); summary()
