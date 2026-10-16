import asyncio
from harness import *
CR = "[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))"

async def body(g):
    check('room 7 loaded, door open', await g.st("S.room === 6 && S.gate === 1"))
    await g.put('ginger', 40, 31)
    p = await g.leap('ginger', '-z', 18)
    check('Moe cannot jump onto the gallery from the floor', p[1] < 1, p)
    await g.put('ginger', 24, 86)
    # the crate is wedged in the corner: pushing it does nothing
    await g.put('tom', 102, 90)
    await g.walk('tom', '+x', 110, limit=900)
    check('the cornered crate will not budge when pushed', await g.st(CR) == [108, 84], await g.st(CR))
    # pull it west, then north (Shift)
    await g.put('tom', 101.9, 90)
    await g.walk('tom', '-x', 84, shift=True)
    c = await g.st(CR)
    check('Mr Mews pulls the crate out of the corner', c[0] < 96, c)
    await g.put('tom', c[0] + 6, c[1] - 6.1)
    await g.walk('tom', '-z', 30.5, shift=True)
    c = await g.st(CR)
    check('...and pulls it north towards the gallery', c[1] < 40, c)
    await g.put('tom', c[0] + 6, c[1] + 18.2)
    await g.walk('tom', '-z', 24 + 12 + 6.4)
    c = await g.st(CR)
    check('crate pushed against the gallery', c[1] <= 24.6, c)

    # lift: Mr Mews on it, Joe on his back, then Moe steps onto the pad
    await g.put('tom', 54, 30, select=False)
    await g.put('smoke', 54, 44)
    p = await g.leap('smoke', '-z', 31)
    check('Joe hops onto Mr Mews on the lift', abs(p[1] - 10) < 0.7, p)
    await g.put('ginger', 102, 66)
    await g.walk('ginger', '-z', 54)
    check('Moe on the pad: lift goes up with both riders', await g.until("S.lift.y >= 29.9", 6000), await g.st("[S.lift.y, S.cats.tom.y, S.cats.smoke.y]"))
    check('...Mr Mews and Joe carried up', await g.st("Math.abs(S.cats.tom.y - 30) < 0.7 && Math.abs(S.cats.smoke.y - 40) < 0.7"), await g.st("[S.cats.tom.y, S.cats.smoke.y]"))
    await g.shot('r7_lift.png')
    await g.walk('tom', '-z', 14)
    await g.walk('smoke', '-z', 14)
    check('Mr Mews and Joe step off onto the gallery', await g.st("Math.abs(S.cats.tom.y - 30) < 0.7 && Math.abs(S.cats.smoke.y - 30) < 0.7"), await g.st("[S.cats.tom.y, S.cats.smoke.y]"))
    await g.walk('smoke', '-z', 4); await g.walk('smoke', '+x', 116); await g.walk('tom', '+x', 114)   # wait at the far end, out of Moe's way
    # Moe leaves the pad; lift sinks
    await g.walk('ginger', '+z', 70)
    check('lift sinks when the pad is released', await g.until("S.lift.y < 0.1", 6000))
    # Moe: crate, then gallery
    c = await g.st(CR)
    await g.put('ginger', c[0] + 6, c[1] + 18)
    p = await g.leap('ginger', '-z', c[1] + 7)
    check('Moe hops onto the crate', abs(p[1] - 12) < 0.7, p)
    p = await g.leap('ginger', '-z', 18)
    check('Moe jumps from the crate up to the gallery', abs(p[1] - 30) < 0.7, p)
    # fish on the plant shelf
    await g.walk('ginger', '-x', 6)
    p = await g.leap('ginger', '+z', 30)
    check('Moe jumps from the gallery onto the plant shelf', abs(p[1] - 44) < 0.7, p)
    check('Moe has the fish', await g.st("S.cats.ginger.carry") == 'fish')
    await g.walk('ginger', '-z', 18)                 # back down onto the gallery
    # everyone along the gallery to the door
    for cat in ('smoke', 'tom', 'ginger'):
        await g.walk(cat, '-x' if (await g.pos(cat))[0] > 96 else '+x', 96); await g.walk(cat, '-z', 0, limit=1500)
    await g.wait(300)
    check('all out of room 7 -> room 8', await g.st("S.room") == 7, await g.st("S.room"))

asyncio.run(run(7, body)); summary()
