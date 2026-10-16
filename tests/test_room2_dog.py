import asyncio
from harness import *
async def body(g):
    await g.pg.evaluate("(() => { const S = __cats.S; S.filled = ['72,72','60,72']; })()")   # bridge already built
    # Moe walks towards the key
    await g.put('ginger', 46, 30)
    await g.select('ginger'); await g.pg.keyboard.down('ArrowLeft')
    modes, minx, shot = [], 99, False
    for i in range(70):
        await g.wait(40)
        m, x, dx = await g.st("[S.dog.mode, S.cats.ginger.x, S.dog.x]")
        if not modes or modes[-1] != m: modes.append(m)
        minx = min(minx, x)
        if m == 'bark' and not shot: await g.shot('dog_bark.png'); shot = True
        if i == 25: await g.pg.keyboard.up('ArrowLeft')
    await g.pg.keyboard.up('ArrowLeft')
    p = await g.pos('ginger')
    print('   dog modes:', ' > '.join(modes), '| Moe closest x', round(minx, 1), 'now', p)
    check('dog wakes, jumps out and chases Moe', modes[:3] == ['sleep', 'wake', 'chase'], modes)
    check('dog bowls Moe back the way she came', p[0] > 30, p)
    check('Moe could not snatch the key in the commotion', await g.st("S.cats.ginger.carry") is None)
    check('dog barks at her', 'bark' in modes)
    ok = await g.until("S.dog.mode === 'sleep' && Math.abs(S.dog.x - 14) < 0.1", 12000)
    check('dog trots back to its basket and goes back to sleep', ok, await g.st("[S.dog.mode, S.dog.x.toFixed(1), S.dog.z.toFixed(1)]"))
    # Joe sneaks in while it sleeps
    await g.put('smoke', 40, 30)
    await g.walk('smoke', '-x', 8.5); await g.walk('smoke', '-z', 30)
    check('Joe sneaks in for the key without waking the dog', await g.st("S.cats.smoke.carry === 'key' && S.dog.mode === 'sleep'"), await g.pos('smoke'))
    # but once Moe wakes it, Joe gets chased too
    await g.put('ginger', 30, 46)
    await g.until("S.dog.mode === 'chase'", 3000)
    await g.put('ginger', 100, 80, select=False)       # Moe is gone; Joe is the nearest cat in its patch
    await g.select('smoke')
    seen = await g.until("S.dog.mode === 'bark'", 4000)
    check('awake dog chases Joe too', seen and await g.st("!!S.cats.smoke.kb"), await g.pos('smoke'))
async def loophole(g):
    # Moe creeps along the back wall to the corner nearest the key: the dog must hear her before she can grab it
    await g.put('ginger', 40, 6)
    await g.walk('ginger', '-x', 5.5); await g.walk('ginger', '+z', 24.5, limit=2000)
    check('Moe cannot sneak the key from the corner', await g.st("S.cats.ginger.carry") is None and await g.st("S.dog.mode !== 'sleep'"), await g.pos('ginger'))

asyncio.run(run(2, body)); asyncio.run(run(2, loophole)); summary()
