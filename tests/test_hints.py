"""The side panel shows objectives, not solutions: Room 1 is a full tutorial,
later rooms list what's new and offer a two-step hint per goal."""
import asyncio
from harness import *

TEXTS = "[...document.querySelectorAll('#goals .gtext')].map(e => e.textContent)"


async def room1(g):
    pg = g.pg
    check('Room 1 has no hint buttons (it is the tutorial)', await pg.locator('#goals .clue-btn').count() == 0)
    check('Room 1 has no "new" box', await pg.locator('#rules').is_hidden())
    first = (await pg.evaluate(TEXTS))[0]
    check('Room 1 goal still explains how', 'Mr Mews' in first, first)


async def room2(g):
    pg = g.pg
    check('Room 2 shows the "new in this room" box', await pg.locator('#rules').is_visible())
    rules = await pg.locator('#rules p').all_text_contents()
    check('...with the water and dog rules', len(rules) == 2 and 'water' in rules[0] and 'Dogs' in rules[1], rules)
    texts = await pg.evaluate(TEXTS)
    check('goals are objectives only', texts[0] == 'Get across the water.' and 'Joe' not in texts[1], texts)
    btns = pg.locator('#goals .clue-btn')
    check('hint buttons on the first three goals, none on the last', await btns.count() == 3)

    li = pg.locator('#goals li').nth(1)
    clue, btn = li.locator('.clue'), li.locator('.clue-btn')
    check('hint starts closed', await clue.is_hidden())
    await btn.click()
    t1 = await clue.text_content()
    check('first press gives a nudge, not the answer', await clue.is_visible() and 'Joe' not in t1, t1)
    check('button now offers the full answer', await btn.text_content() == 'Show me how')
    check('mouse click gives the keys back to the game', await pg.evaluate("document.activeElement.id") == 'screen')
    await btn.click()
    t2 = await clue.text_content()
    check('second press shows the full answer', 'Joe' in t2, t2)
    check('...and the button goes away', await btn.is_hidden())

    # still revealed after a restart, and the game keys still work
    await pg.keyboard.press('KeyR'); await g.wait(200)
    check('hint stays open after restarting the room', 'Joe' in (await pg.locator('#goals li').nth(1).locator('.clue').text_content()))
    cat = await g.st("S.active")
    p0 = await g.pos(cat)
    for k in ('ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft'):
        await pg.keyboard.down(k); await g.wait(250); await pg.keyboard.up(k)
        if await g.pos(cat) != p0: break
    check('arrow keys still drive the cat', await g.pos(cat) != p0)

    # keyboard: Enter on the button keeps focus there for the next press
    li0 = pg.locator('#goals li').nth(0)
    await li0.locator('.clue-btn').focus()
    await pg.keyboard.press('Enter')
    check('keyboard press keeps focus on the hint button', await pg.evaluate("document.activeElement.className") == 'clue-btn')
    check('...and shows the nudge', await li0.locator('.clue').is_visible())


async def room6(g):
    rules = await g.pg.locator('#rules p').all_text_contents()
    check('Room 6 explains the wool ball', any('wool' in r for r in rules), rules)


async def room8(g):
    check('Room 8 has nothing new, so no box', await g.pg.locator('#rules').is_hidden())


async def main():
    await run(1, room1)
    await run(2, room2)
    await run(6, room6)
    await run(8, room8)
    summary()

asyncio.run(main())
