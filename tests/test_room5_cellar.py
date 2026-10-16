import asyncio
from harness import *

async def body(g):
    check('room 5 loaded, dark', await g.st("S.room === 4 && !S.lights"))
    await g.shot('r5_dark.png')
    # Joe can't reach the light cord
    await g.put('smoke', 78, 18)
    peak = await g.jump_in_place('smoke')
    check('Joe cannot reach the light cord', not await g.st("S.lights"), round(peak, 1))
    await g.put('smoke', 66, 78)
    # Mr Mews walks into a coal hole and gets sent back
    await g.put('tom', 78, 64)          # tile (6,5) is a pit just north of here
    await g.wait(200)
    p = await g.walk('tom', '-z', 50, limit=1500)
    check('Mr Mews falls into a coal hole and is sent back', p[2] > 60, p)
    await g.put('tom', 84, 88)

    # Moe walks the safe path to the cord using only the arrow keys: (6,6) -> (7,6) -> (7,4) -> (6,4) -> (6,1)
    await g.put('ginger', 78, 78)
    await g.walk('ginger', '+x', 90); await g.walk('ginger', '-z', 54); await g.walk('ginger', '-x', 78); await g.walk('ginger', '-z', 18)
    p = await g.pos('ginger')
    check('Moe reaches the cord without falling in', abs(p[0] - 78) < 2.5 and abs(p[2] - 18) < 2.5, p)
    await g.jump_in_place('ginger')
    check('Moe pulls the light cord', await g.st("S.lights"))
    await g.wait(1200)
    check('gate opens with the lights', await g.until("S.gate > 0.95", 3000))
    await g.shot('r5_lit.png')

    # Moe: (6,1) -> (6,2) -> (4,2) -> (4,0) -> (3,0), then barrel, then wine rack
    await g.walk('ginger', '+z', 30); await g.walk('ginger', '-x', 54); await g.walk('ginger', '-z', 6); await g.walk('ginger', '-x', 41.5)
    p = await g.leap('ginger', '-x', 31)
    check('Moe hops onto the barrel', abs(p[1] - 14) < 0.7, p)
    p = await g.leap('ginger', '-x', 13)
    check('Moe jumps from the barrel onto the wine rack', abs(p[1] - 36) < 0.7, p)
    check('Moe has the fish', await g.st("S.cats.ginger.carry") == 'fish')

    # Mr Mews: (7,7) -> (4,7) -> (4,4) -> (2,4), push the crate into hole (2,2), then on to the door
    await g.walk('tom', '-x', 54); await g.walk('tom', '-z', 54.4)
    await g.put('tom', 54, 54.3, select=False)      # line up on the row centre before heading west
    await g.walk('tom', '-x', 30)
    p = await g.pos('tom')
    check('Mr Mews reaches the crate without falling in', abs(p[0] - 30) < 1.5 and abs(p[2] - 54) < 1.5, p)
    await g.walk('tom', '-z', 40)
    check('crate drops into the hole and plugs it', await g.st("S.filled.includes('24,24')"), await g.st("JSON.stringify(S.filled)"))
    await g.walk('tom', '-z', 18); await g.walk('tom', '-x', 0, limit=3000)
    check('Mr Mews walks over the plugged hole and out', await g.st("S.cats.tom.out"))
    # Joe follows the same route; Moe jumps down and leaves
    await g.put('smoke', 90, 88)
    await g.walk('smoke', '-x', 54); await g.walk('smoke', '-z', 54); await g.walk('smoke', '-x', 30); await g.walk('smoke', '-z', 18); await g.walk('smoke', '-x', 0, limit=3000)
    check('Joe out', await g.st("S.cats.smoke.out"))
    await g.walk('ginger', '+z', 18)       # step off the rack (falls to the floor at (1,1))
    await g.walk('ginger', '-x', 0, limit=3000)
    await g.wait(300)
    check('all out of room 5 -> room 6', await g.st("S.room") == 5, await g.st("S.room"))

async def alt(g):
    await g.put('ginger', 66, 90, select=False); await g.put('smoke', 90, 90, select=False)
    await g.pg.evaluate("(() => { __cats.S.lights = true; })()")
    await g.put('tom', 50, 42)                      # east of the crate, in row 3 (hole (3,3) is under... use row 4 overlap instead)
    await g.put('tom', 48.5, 52.8)                  # in row 4 but overlapping the crate's row, as in the slip
    await g.walk('tom', '-x', 30.5)
    check('slip: crate shoved west into hole (1,3)', await g.st("S.filled.includes('12,36')"), await g.st("JSON.stringify(S.filled)"))
    await g.put('tom', 30, 42)
    await g.walk('tom', '-x', 6); await g.walk('tom', '-z', 24); await g.walk('tom', '-x', 0, limit=2500)
    p = await g.pos('tom')
    check('...and Mr Mews still reaches the door that way', p[0] < 8.5 and 14 < p[2] < 34, p)

asyncio.run(run(5, body)); asyncio.run(run(5, alt)); summary()
