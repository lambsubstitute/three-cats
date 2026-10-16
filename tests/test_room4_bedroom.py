import asyncio
from harness import *

async def body(g):
    check('room 4 loaded', await g.st("S.room") == 3)
    # shortcut checks: Mr Mews can't jump onto the landing or the pouffe-free wardrobe; Moe can't reach the wardrobe top from the floor
    await g.put('tom', 70, 31)
    p = await g.hop('tom', '-z', 20, limit=1200)
    check('Mr Mews cannot jump onto the landing from the floor', p[1] < 1, p)
    await g.put('ginger', 18, 36)
    p = await g.hop('ginger', '-x', 46, limit=1200)
    check('Moe cannot reach the wardrobe top from the floor', p[1] < 40, p)
    check('...and has no fish', await g.st("S.cats.ginger.carry") is None)

    # Mr Mews pushes the pouffe (48..60, 60..72) to the wardrobe: west along z 66, then north, then west again
    await g.put('tom', 66, 66); await g.put('ginger', 100, 84, select=False)
    await g.walk('tom', '-x', 42)                       # pouffe ends at x ~24
    await g.put('tom', 30, 79)
    await g.walk('tom', '-z', 42.2)                     # pouffe z 60 -> ~30
    await g.put('tom', 42, 36)
    await g.walk('tom', '-x', 30.2)                     # pouffe x -> ~12
    pf = await g.st("[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))")
    check('pouffe pushed against the wardrobe', pf[0] <= 12.5 and 24 <= pf[1] <= 40, pf)
    # Moe hops onto the pouffe, then bounces onto the wardrobe
    await g.put('tom', 60, 80, select=False)
    await g.put('ginger', pf[0] + 6, pf[1] + 17.5)
    p = await g.leap('ginger', '-z', pf[1] + 6)
    check('Moe gets onto the pouffe', abs(p[1] - 5) < 0.7, p)
    p = await g.leap('ginger', '-x', 6)
    check('Moe bounces off the pouffe onto the wardrobe', p[1] > 45, p)
    check('Moe has the fish', await g.st("S.cats.ginger.carry") == 'fish')
    await g.shot('r4_fish.png')

    # pull the pouffe back out (Shift) and push it against the landing's front face (z = 24) at x 60..72
    await g.put('ginger', 100, 84, select=False)
    await g.put('tom', pf[0] + 18, pf[1] + 6)
    await g.walk('tom', '+x', 72, shift=True)           # pull it east
    pf = await g.st("[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))")
    check('Mr Mews pulls the pouffe back out with Shift', pf[0] > 40, pf)
    await g.put('tom', pf[0] - 6 - 0.5 + 0, pf[1] + 6)
    # line up: push it east to x 60, then north to z 24
    await g.put('tom', pf[0] - 6.2, pf[1] + 6)
    await g.walk('tom', '+x', 60 - 6 + 0.2 + (60 - pf[0]) )
    pf = await g.st("[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))")
    await g.put('tom', pf[0] + 6, pf[1] + 12 + 6.2)
    await g.walk('tom', '-z', 24 + 12 + 6.5)
    pf = await g.st("[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))")
    check('pouffe against the landing', pf[1] <= 24.6 and 56 <= pf[0] <= 108, pf)
    # Mr Mews: onto the pouffe, then bounce onto the landing
    await g.put('tom', pf[0] + 6, pf[1] + 12 + 6.5)
    p = await g.leap('tom', '-z', pf[1] + 6.5)
    check('Mr Mews hops onto the pouffe', abs(p[1] - 5) < 0.7, p)
    p = await g.leap('tom', '-z', 18)
    check('Mr Mews bounces onto the landing', abs(p[1] - 20) < 0.7, p)
    await g.walk('tom', '-z', 12)
    await g.walk('tom', '-x', 70)
    check('plate latched by Mr Mews', await g.until("S.latched", 2000))
    # Joe up via Mr Mews? he's on the landing now; use the pouffe instead
    await g.put('smoke', pf[0] + 2, pf[1] + 12 + 4)
    p = await g.leap('smoke', '-z', pf[1] + 6)
    p = await g.leap('smoke', '-z', 19)
    check('Joe bounces up to the landing (or onto Mr Mews there)', p[1] >= 19.5, p)
    await g.put('ginger', 100, 30)
    p = await g.hop('ginger', '-z', 20)
    check('Moe jumps onto the landing unaided', abs(p[1] - 20) < 0.7, p)
    await g.until("S.gate > 0.95", 3000)
    await g.shot('r4_landing.png')
    for cat in ('ginger', 'smoke', 'tom'):
        await g.put(cat, 96, 14, y=20)
        await g.walk(cat, '-z', 0, limit=1500)
    await g.wait(400)
    check('all out of room 4 -> room 5', await g.st("S.room") == 4, await g.st("S.room"))

asyncio.run(run(4, body)); summary()
