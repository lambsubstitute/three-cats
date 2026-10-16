import asyncio
from harness import *
BALL = "[S.balls[0].x, S.balls[0].z].map(v => +v.toFixed(1))"

async def body(g):
    check('room 6 loaded', await g.st("S.room") == 5)
    # a cat on the pad opens the gate, but it shuts again once the cat steps off
    await g.put('smoke', 18, 66); await g.wait(1500)
    check('a cat on the pad lifts the gate', await g.st("S.gate > 0.9"))
    await g.walk('smoke', '+z', 84); await g.wait(1500)
    check('gate drops again when the cat steps off', await g.st("S.gate < 0.1"))
    # rolling with no stopper: west along its row it runs to the wall, missing the pad
    await g.put('tom', 56, 92, select=False); await g.put('smoke', 112, 30, select=False)
    await g.put('ginger', 112, 78)
    await g.walk('ginger', '-x', 100, limit=800)
    await g.until("!S.balls[0].vx && !S.balls[0].vz", 4000)
    b = await g.st(BALL)
    check('ball rolls until it hits the wall', b[0] < 5, b)
    check('...and the pad is not pressed', not await g.st("S.plates[0]"))
    # reset the ball to its start
    await g.pg.evaluate("(() => { const b = __cats.S.balls[0]; b.x = 102; b.z = 78; })()")
    # solution: Joe stands as a stopper at (102, 58.5); Moe nudges the ball north from the south
    await g.put('smoke', 102, 58.5, select=False)
    await g.put('ginger', 102, 88)
    await g.walk('ginger', '-z', 84, limit=800)
    await g.until("!S.balls[0].vx && !S.balls[0].vz", 4000)
    b = await g.st(BALL)
    check("ball stops against Joe in the pad's row", abs(b[1] - 66) < 0.6, b)
    # Mr Mews as the second stopper at (8, 66); Moe nudges the ball west from the east
    await g.put('smoke', 112, 30, select=False)
    await g.put('tom', 8, 66, select=False)
    await g.put('ginger', 112, 66)
    await g.walk('ginger', '-x', 108, limit=800)
    await g.until("!S.balls[0].vx && !S.balls[0].vz", 5000)
    b = await g.st(BALL)
    check('ball stops against Mr Mews on the pad', abs(b[0] - 18) < 0.6 and abs(b[1] - 66) < 0.6, b)
    await g.walk('tom', '+z', 86)
    await g.wait(1500)
    check('pad held by the ball, gate open', await g.st("S.plates[0] && S.gate > 0.9"))
    await g.shot('r6_ball.png')
    # fish: Moe from the floor can't reach the fridge top; from the worktop she can
    await g.put('ginger', 102, 18)
    peak = await g.jump_in_place('ginger')
    check('Moe cannot reach the fridge top from the floor', await g.st("S.cats.ginger.carry") is None, round(peak, 1))
    await g.put('ginger', 88, 18)
    p = await g.leap('ginger', '-z', 7)
    check('Moe jumps onto the worktop', abs(p[1] - 18) < 0.7, p)
    p = await g.leap('ginger', '+x', 101)
    check('Moe jumps from the worktop onto the fridge', abs(p[1] - 40) < 0.7, p)
    check('Moe has the fish', await g.st("S.cats.ginger.carry") == 'fish')
    for cat in ('ginger', 'smoke', 'tom'):
        await g.put(cat, 24, 20)
        await g.walk(cat, '-z', 0, limit=1500)
    await g.wait(300)
    check('all out of room 6 -> room 7', await g.st("S.room") == 6, await g.st("S.room"))

asyncio.run(run(6, body)); summary()
