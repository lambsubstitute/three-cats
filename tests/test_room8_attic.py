import asyncio
from harness import *

async def body(g):
    check('room 8 loaded', await g.st("S.room") == 7)
    await g.put('tom', 48, 80, select=False)       # Mr Mews shuffles back so Joe can pass along the front
    # Moe near the dog wakes it and gets chased back
    await g.put('ginger', 100, 66)
    await g.walk('ginger', '+z', 76, limit=1200)
    check('Moe wakes the dog and is chased off', await g.st("S.dog.awake > 0"), await g.pos('ginger'))
    await g.put('ginger', 8, 84)
    await g.until("S.dog.mode === 'sleep'", 15000)
    # Joe sneaks round the north side of the dog to the key, then back
    # route: along the front, up between the crate and the dog, east between the dog and the hoover lane, down to the key
    await g.walk('smoke', '+x', 75.5); await g.put('smoke', 76, 90); await g.walk('smoke', '-z', 72); await g.walk('smoke', '+x', 110); await g.walk('smoke', '+z', 90)
    check('Joe picks up the key without waking the dog', await g.st("S.cats.smoke.carry === 'key' && S.dog.awake === 0"), await g.pos('smoke'))
    await g.walk('smoke', '-z', 72); await g.walk('smoke', '-x', 76); await g.walk('smoke', '+z', 90); await g.walk('smoke', '-x', 12)

    # Mr Mews pushes the crate into the hoover's lane when the hoover is on the right, confining it there
    await g.put('tom', 66, 88)
    await g.until("S.vac.x > 85 && S.vac.dir > 0", 8000)
    await g.walk('tom', '-z', 62)
    check('pushing the crate does not wake the dog', await g.st("S.dog.awake === 0"))
    c = await g.st("[S.crates[1].x, S.crates[1].z].map(v => +v.toFixed(1))")
    check('crate pushed into the hoover lane', c[1] < 54, c)
    lo = 999
    for _ in range(80):
        lo = min(lo, await g.st("S.vac.x")); await g.wait(50)
    check('hoover now stays right of the crate', lo > 72 + 6.5, round(lo, 1))
    # Mr Mews pushes the pouffe north against the loft
    await g.put('tom', 30, 88)
    await g.walk('tom', '-z', 66.3)
    pf = await g.st("[S.crates[0].x, S.crates[0].z].map(v => +v.toFixed(1))")
    check('pouffe against the loft', pf[1] <= 48.6, pf)

    # Mr Mews and Joe cross the lane on the clear (left) side and make a tower at the boxes; Moe climbs it for the fish
    await g.put('tom', 50, 80); await g.walk('tom', '-z', 30); await g.walk('tom', '+x', 114); await g.walk('tom', '-z', 19)
    await g.put('smoke', 50, 80); await g.walk('smoke', '-z', 30); await g.walk('smoke', '+x', 114); await g.walk('smoke', '-z', 31)
    t = await g.pos('tom')
    check('Mr Mews crossed the lane and reached the boxes', t[0] > 112 and t[2] < 20, t)
    p = await g.leap('smoke', '-z', t[2] + 1)
    check('Joe climbs onto Mr Mews', abs(p[1] - 10) < 0.7, p)
    await g.put('ginger', 50, 80); await g.walk('ginger', '-z', 34); await g.walk('ginger', '+x', 114)
    p = await g.leap('ginger', '-z', t[2] + 1)
    check('Moe climbs onto Joe', abs(p[1] - 20) < 0.7, p)
    p = await g.leap('ginger', '-z', 6)
    check('Moe jumps from the tower onto the boxes', abs(p[1] - 40) < 0.7, p)
    check('Moe has the fish', await g.st("S.cats.ginger.carry") == 'fish')
    await g.shot('r8_tower.png')
    # Moe can't do it from a crate or from Mr Mews alone (shortcut checks done by height: 12+28 = 40, 10+28 = 38 < 40 top)

    # everyone back to the loft: Moe jumps, Mr Mews and Joe bounce off the pouffe
    await g.walk('ginger', '+z', 20)
    await g.walk('ginger', '-x', 44); await g.walk('ginger', '+z', 42)
    p = await g.leap('ginger', '-x', 30)
    check('Moe jumps up onto the loft', abs(p[1] - 20) < 0.7, p)
    await g.walk('ginger', '-z', 40); await g.walk('ginger', '-x', 8)       # step back from the edge, clear of the door
    await g.walk('smoke', '+z', 34)
    await g.walk('tom', '+z', 30); await g.walk('tom', '-x', 42); await g.walk('tom', '+z', 66.5); await g.walk('tom', '-x', 30)
    p = await g.leap('tom', '-z', 55)
    check('Mr Mews hops onto the pouffe', abs(p[1] - 5) < 0.7, p)
    p = await g.leap('tom', '-z', 40)
    check('Mr Mews bounces onto the loft', abs(p[1] - 20) < 0.7, p)
    await g.walk('tom', '-z', 8)                    # tuck into the back corner of the loft
    await g.walk('smoke', '-x', 42); await g.walk('smoke', '+z', 66); await g.walk('smoke', '-x', 30)
    p = await g.leap('smoke', '-z', 55)
    p = await g.leap('smoke', '-z', 42)
    check('Joe bounces onto the loft', abs(p[1] - 20) < 0.7, p)
    await g.walk('smoke', '-z', 24); await g.walk('smoke', '-x', 0, limit=2500)
    check('Joe unlocks the gate with the key', await g.st("S.unlocked"))
    await g.until("S.gate > 0.95", 3000)
    await g.shot('r8_loft.png')
    for cat in ('smoke', 'ginger', 'tom'):
        if await g.st(f"S.cats.{cat}.out"): continue
        z = (await g.pos(cat))[2]
        a = await g.walk(cat, '-z' if z > 24 else '+z', 24); b = await g.walk(cat, '-x', 0, limit=2500)
        print('   exit', cat, 'from z', z, '->', a, '->', b, 'active', await g.st("S.active"))
    await g.wait(400)
    check('all out: game won', await g.st("S.won"), await g.st("[S.room, S.won]"))
    check('win screen shows', await g.pg.evaluate("!document.getElementById('win').hidden"))
    await g.shot('r8_win.png')

asyncio.run(run(8, body)); summary()
