"""Render every sprite the room prototype needs and write assets.js.

World units: one floor tile = 12. Camera is the same 2:1 isometric camera as
make_iso.py. Each sprite records the screen offset of its anchor (an object's
min corner, or a cat's feet) so the game can place it exactly.
"""
import base64, io, json, math
from multiprocessing import Pool
from PIL import Image
from make_iso import (add, sub, mul, dot, norm, roty, ramp, Box, Ell, chain, model, material,
                      PALETTES, V, F, RIGHT, UP, LIGHT)

PIX = 0.4            # world units per screen pixel
T = 12
OUT = (30, 20, 38, 255)


def proj(p):
    return dot(p, RIGHT) / PIX, -dot(p, UP) / PIX


def lvl_from(lam):
    return 0 if lam < 0.15 else 1 if lam < 0.38 else 2 if lam < 0.72 else 3


# ---------------- generic renderer ----------------
def render(hitters, lo, hi, shade, outline=True, edges=True):
    xs, ys = [], []
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            for cz in (lo[2], hi[2]):
                sx, sy = proj((cx, cy, cz))
                xs.append(sx); ys.append(sy)
    minx, miny = math.floor(min(xs)) - 2, math.floor(min(ys)) - 2
    w, h = math.ceil(max(xs)) - minx + 2, math.ceil(max(ys)) - miny + 2
    buf = [[None] * w for _ in range(h)]
    for j in range(h):
        for i in range(w):
            sx, sy = minx + i + 0.5, miny + j + 0.5
            o = add(add(mul(RIGHT, sx * PIX), mul(UP, -sy * PIX)), mul(V, 400))
            best = None
            for k, hit in enumerate(hitters):
                r = hit(o, F, sx, sy)
                if r and (best is None or r[0] < best[0]):
                    best = (r[0], r[1], r[2], k)
            buf[j][i] = best
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for j in range(h):
        for i in range(w):
            b = buf[j][i]
            if b:
                px[i, j] = shade(b[2], b[1], max(0.0, dot(b[1], LIGHT)))
    if outline:
        out = im.copy()
        op = out.load()
        for j in range(h):
            for i in range(w):
                b = buf[j][i]
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ii, jj = i + di, j + dj
                    if not (0 <= ii < w and 0 <= jj < h):
                        continue
                    nb = buf[jj][ii]
                    if not nb:
                        continue
                    if b is None or (edges and nb[3] != b[3] and nb[0] < b[0] - 1.2):
                        op[i, j] = OUT
                        break
        im = out
    bb = im.getbbox()
    im = im.crop(bb)
    return im, minx + bb[0], miny + bb[1]


def box_hitter(lo, hi, tag):
    bx = Box(lo, hi)
    def hit(o, d, sx, sy):
        r = bx.hit(o, d)
        if not r:
            return None
        t, p, n = r
        return t, n, (tag, sub(p, lo), n)
    return hit


# ---------------- block sprites ----------------
PAL = {k: ramp(v) for k, v in dict(
    crate='#bf7f45', stone='#8c8fa6', moss='#7a9a62', fence='#a0704a', iron='#4b5468',
    plate_off='#c9473d', plate_on='#5cae5a', btn_off='#d6533f', btn_on='#62c26a',
    fish='#8fb6d2', fishbelly='#e4eef2', floor_a='#55708f', floor_b='#4b6584',
    wall='#c8b088', door='#22192e', metal='#d4ad45',
    tile_a='#b86d4e', tile_b='#a65f45', wall2='#9fb89c', water='#3f8fb5', pit='#6e4a3e',
    cupboard='#7d5139', basket='#b98a52',
    dbody='#f1ebe0', dpatch='#9a6338', dsnout='#f8f3ea', dnose='#2a2230', deye='#1e1a26',
    shelfwood='#9c6a43', washer='#e6e3dc', glass='#4f7395', rim='#aab0b8', panel='#c9ced6',
    boiler='#e9e1cc', copper='#c27a45', hoover='#3f4450', hoovertop='#666f80', bumper='#2a2d35',
    pad_off='#4677c4', pad_on='#7fd9f0', plank_a='#b5845a', plank_b='#a87a53',
    wall3='#c9c2e2', wall3b='#bbb3d8', dado='#8f6a52',
    towel0='#e9a0a8', towel1='#9fc7e0', towel2='#f2d27a', towel3='#b7d8a8', towel4='#f3efe6', towel5='#c7a6d8').items()}


def shade_block(info, n, lam):
    tag, p, nn = info
    L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
    if tag == 'crate':
        a, b = [p[i] for i in range(3) if abs(nn[i]) < 0.5]
        if min(a, b) < 1.1 or max(a, b) > T - 1.1:
            return PAL['crate'][max(0, L - 2)]
        if abs(a - b) < 0.9 or abs(a + b - T) < 0.9:
            return PAL['crate'][max(0, L - 1)]
        return PAL['crate'][L]
    if tag == 'crate_sunk':
        tag, p = 'crate', (p[0], p[1] + 9, p[2])
        a, b = [p[i] for i in range(3) if abs(nn[i]) < 0.5]
        if nn[1] < 0.5:
            return PAL['crate'][max(0, L - 2)]
        if min(a, b) < 1.1 or max(a, b) > T - 1.1:
            return PAL['crate'][max(0, L - 2)]
        if abs(a - b) < 0.9 or abs(a + b - T) < 0.9:
            return PAL['crate'][max(0, L - 1)]
        return PAL['crate'][max(0, L - 1)]
    if tag == 'shelf':
        if nn[0] > 0.5:                                   # open front, facing into the room
            z, y = p[2], p[1]
            if z < 1.2 or z > 22.8 or y < 1.0 or y > 28.8 or abs(y - 10) < 0.6 or abs(y - 20) < 0.6:
                return PAL['shelfwood'][max(0, L - (0 if y > 28.8 or abs(y - 10) < 0.6 or abs(y - 20) < 0.6 else 1))]
            row = 0 if y < 10 else 1 if y < 20 else 2
            base = [1.0, 10.6, 20.6][row]
            for j, (z0, z1) in enumerate(((2.5, 10.5), (12.8, 21.0))):
                hgt = [5.5, 7.0, 4.5, 6.2, 5.0, 6.6][(row * 2 + j) % 6]
                if z0 <= z <= z1 and y <= base + hgt:
                    col = 'towel%d' % ((row * 2 + j * 3) % 6)
                    fold = (y - base) % 1.6 < 0.35
                    return PAL[col][max(0, (2 if not fold else 1))]
            return PAL['shelfwood'][0]                    # shadowy back of the shelf
        if nn[1] > 0.5:
            return PAL['shelfwood'][3]
        return PAL['shelfwood'][max(0, L - (1 if int(p[1] * 1.2) % 5 == 0 else 0))]
    if tag == 'washer':
        if nn[0] > 0.5:
            z, y = p[2], p[1]
            r = math.hypot(z - 6, y - 7)
            if r < 3.3:
                return PAL['glass'][3] if (z - 6) - (y - 7) > 1.6 and r > 1.8 else PAL['glass'][1]
            if r < 4.3:
                return PAL['rim'][L]
            if y > 13.2:
                if math.hypot(z - 9, y - 14.6) < 0.9:
                    return PAL['bumper'][1]
                return PAL['panel'][L]
            if y < 0.8:
                return PAL['rim'][max(0, L - 1)]
        if nn[1] > 0.5:
            return PAL['washer'][4]
        return PAL['washer'][L]
    if tag == 'cupboard':
        if nn[1] > 0.5:
            return PAL['cupboard'][3]
        a, b = [p[i] for i in range(3) if abs(nn[i]) < 0.5]   # a: x or y, b: y or z
        along, up = (b, a) if abs(nn[0]) > 0.5 else (a, b)
        if abs(nn[0]) > 0.5:
            along, up = p[2], p[1]
        else:
            along, up = p[0], p[1]
        if along < 0.8 or along > T - 0.8 or up < 1.2 or abs(up - 22) < 0.5 or up > 32.8:
            return PAL['cupboard'][max(0, L - 2)]
        if abs(nn[0]) > 0.5 and abs(along - 6) < 0.45 and up < 22:
            return PAL['cupboard'][max(0, L - 2)]                     # double doors
        if abs(nn[0]) > 0.5 and abs(along - 7.6) < 0.7 and abs(up - 13) < 0.8:
            return PAL['metal'][3]                                    # knob
        return PAL['cupboard'][L]
    if tag == 'stone':
        a, b = [p[i] % T for i in range(3) if abs(nn[i]) < 0.5]
        if min(a, b) < 0.9 or max(a, b) > T - 0.9:
            return PAL['stone'][max(0, L - 1)]
        if nn[1] > 0.5 and ((int(a * 1.3) * 7 + int(b * 1.3) * 3) % 13 == 0):
            return PAL['moss'][L]
        return PAL['stone'][L]
    if tag == 'fence':
        along = p[0] if abs(nn[2]) > 0.5 else p[2]
        if nn[1] > 0.5:
            return PAL['fence'][3]
        return PAL['fence'][max(0, L - 1)] if along % 4 < 0.7 else PAL['fence'][L]
    if tag in PAL:
        return PAL[tag][L]
    return (255, 0, 255, 255)


def block_sprite(size, tag):
    return render([box_hitter((0, 0, 0), size, tag)], (0, 0, 0), size, shade_block)


def gate_sprite():
    # portcullis running along z (sits in the left wall's doorway)
    hs = []
    for k in range(7):
        z0 = 1 + k * 3.6
        hs.append(box_hitter((0, 0, z0), (2, 30, z0 + 1.4), 'iron'))
    hs.append(box_hitter((0, 26, 0), (2.4, 30, 24), 'iron'))
    hs.append(box_hitter((0.2, 12, 0), (2.2, 14, 24), 'iron'))
    return render(hs, (0, 0, 0), (2.4, 30, 24), shade_block, edges=False)


def fish_sprite():
    parts = [Ell((0, 4, 0), (4.2, 2.2, 1.3), 'fish'),
             Ell((0.3, 3.4, 0), (3.2, 1.2, 1.25), 'fishbelly'),
             Ell((-4.6, 4.8, 0), (1.4, 1.5, 0.6), 'fish'),
             Ell((-4.6, 3.2, 0), (1.4, 1.5, 0.6), 'fish')]
    def hit(o, d, sx, sy):
        best = None
        for e in parts:
            r = e.hit(o, d)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[2], (e.tag, None, None))
        return best
    def shade(info, n, lam):
        return PAL[info[0]][min(4, lvl_from(lam) + 1)]
    im, ox, oy = render([hit], (-6, 1, -2), (5, 7, 2), shade)
    # eye
    return im, ox, oy


# ---------------- cats ----------------
CAT_SCALE = 0.5
CAT_RAMPS = {k: {m: ramp(c) for m, c in pal.items()} for k, pal in PALETTES.items()}


def cat_hitter(kind, ang, phase, pose='walk', item=None):
    parts, body, head, muz, eye = model(kind)
    legs = [p for p in parts if p.tag in ('leg', 'paw')]
    hip = max(p.c[1] for p in legs if p.tag == 'leg')
    if pose == 'pull':
        # front paws reach forward onto the crate, body leans back on the hind legs
        for p in legs:
            if p.c[0] > 0:
                k = max(0.0, min(1.0, 1 - p.c[1] / hip)) if p.tag == 'leg' else 1.0
                p.c = (p.c[0] + 9.0 * k, p.c[1] + 5.0 * k, p.c[2])
        for p in parts:
            if p.tag not in ('leg', 'paw'):
                p.c = (p.c[0] - 1.8, p.c[1] - 0.6, p.c[2])
    if phase is not None:
        for p in legs:
            front, side = p.c[0] > 0, p.c[2] > 0
            if pose == 'pull' and front:
                continue
            pair = 0 if front == side else math.pi
            off = 2.6 * math.sin(phase + pair)
            k = max(0.0, min(1.0, 1 - p.c[1] / hip)) if p.tag == 'leg' else 1.0
            lift = max(0.0, math.cos(phase + pair)) * 0.9 * k
            p.c = (p.c[0] + off * k, p.c[1] + lift, p.c[2])
        bob = 0.35 * abs(math.sin(phase))
        for p in parts:
            if p.tag not in ('leg', 'paw'):
                p.c = (p.c[0], p.c[1] + bob, p.c[2])
    if item == 'key':
        mx, my = muz.c[0] + muz.r[0] * 0.55 + 0.3, muz.c[1] - muz.r[1] * 0.55
        ring = [Ell((mx, my + 1.3 * math.cos(t), -3.4 + 1.3 * math.sin(t)), (0.55, 0.55, 0.55), 'key')
                for t in [i * math.pi / 4 for i in range(8)]]
        parts = parts + ring + [Ell((mx, my, 0.4), (0.5, 0.5, 2.8), 'key'),
                                Ell((mx, my - 0.8, 2.5), (0.45, 0.8, 0.4), 'key'),
                                Ell((mx, my - 0.7, 1.4), (0.45, 0.6, 0.35), 'key')]
    if item == 'fish':
        # fish held crossways in the mouth, head to one side and tail to the other
        mx, my = muz.c[0] + muz.r[0] * 0.55 + 0.4, muz.c[1] - muz.r[1] * 0.6
        parts = parts + [Ell((mx, my, 0.6), (1.5, 1.7, 3.6), 'fish'),
                         Ell((mx - 0.2, my - 0.6, 0.6), (1.35, 0.8, 3.0), 'fishbelly'),
                         Ell((mx, my + 0.9, -3.7), (0.55, 1.3, 1.1), 'fish'),
                         Ell((mx, my - 0.9, -3.7), (0.55, 1.3, 1.1), 'fish')]
    s = CAT_SCALE
    circles = []
    for p in parts:
        w = roty(mul(p.c, s), -ang)
        cx, cy = proj(w)
        circles.append((p, cx, cy, max(p.r) * s / PIX + 1.5))

    def hit(o, d, sx, sy):
        ol, dl = mul(roty(o, ang), 1 / s), roty(d, ang)
        best = None
        for p, cx, cy, r in circles:
            if abs(sx - cx) > r or abs(sy - cy) > r:
                continue
            h = p.hit(ol, dl)
            if h and (best is None or h[0] < best[0]):
                best = (h[0], h[1], h[2], p)
        if not best:
            return None
        t, pl, nl, p = best
        if p.tag in ('fish', 'fishbelly'):
            return t * s, roty(nl, -ang), ('fishmat', p.tag)
        if p.tag == 'key':
            return t * s, roty(nl, -ang), ('fishmat', 'metal')
        mat = material(kind, p, pl, nl, body, head, muz, eye)
        return t * s, roty(nl, -ang), (kind, mat)
    return hit


def shade_cat(info, n, lam):
    kind, mat = info
    l = lvl_from(lam)
    if kind == 'fishmat':
        return PAL[mat][min(4, l + 1)]
    if lam > 0.93 and mat in ('base', 'light'):
        l = 4
    if mat in ('pupil', 'iris', 'nose'):
        l = 2
    return CAT_RAMPS[kind][mat][l]


DIRS = 8
FRAMES = [None, 0, math.pi / 2, math.pi, 3 * math.pi / 2]   # idle + 4 walk frames


def columns(kind):
    cols = [('walk', ph) for ph in FRAMES]
    if kind == 'tom':
        cols += [('pull', ph) for ph in FRAMES[1:]]
    return cols


def cat_job(args):
    kind, d, f = args
    cols = columns(kind)
    pose, ph = cols[f % len(cols)]
    item = [None, 'fish', 'key'][f // len(cols)]
    ang = d * 2 * math.pi / DIRS
    R = 13
    im, ox, oy = render([cat_hitter(kind, ang, ph, pose, item)], (-R, 0, -R), (R, 16, R), shade_cat, edges=True)
    return kind, d, f, im, ox, oy


def b64(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


# ---------------- background (floor + back walls) ----------------
ROOM = 8 * T
DOOR = (60, 84)


def background():
    hs = [box_hitter((0, -4, 0), (ROOM, 0, ROOM), 'floor'),
          box_hitter((-4, -4, -4), (0, 44, ROOM), 'wallL'),
          box_hitter((-4, -4, -4), (ROOM, 44, 0), 'wallR'),
          box_hitter((-1, 0, DOOR[0]), (0.3, 32, DOOR[1]), 'door')]

    def shade(info, n, lam):
        tag, p, nn = info
        L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
        if tag == 'floor':
            if nn[1] < 0.5:
                return PAL['floor_b'][0]
            tx, tz = int(p[0] // T), int(p[2] // T)
            key = 'floor_a' if (tx + tz) % 2 == 0 else 'floor_b'
            edge = p[0] % T < 0.7 or p[2] % T < 0.7
            return PAL[key][max(0, L - (1 if edge else 0))]
        if tag == 'door':
            return PAL['door'][1]
        # walls: brick courses; top cap lighter
        if nn[1] > 0.5:
            return PAL['wall'][4]
        along = p[2] if tag == 'wallL' else p[0]
        row = int(p[1] // 5)
        mortar = p[1] % 5 < 0.8 or (along + (6 if row % 2 else 0)) % 12 < 0.8
        return PAL['wall'][max(0, L - (1 if mortar else 0))]
    return render(hs, (-4, -4, -4), (ROOM, 44, ROOM), shade, edges=True)


def ell_sprite(parts, lo, hi, shade_tag):
    def hit(o, d, sx, sy):
        best = None
        for e in parts:
            r = e.hit(o, d)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[2], (e.tag, sub(r[1], e.c), e))
        return best
    return render([hit], lo, hi, shade_tag)


class CylV:
    """Upright cylinder for orthographic rays (side + top cap)."""
    def __init__(self, cx, cz, r, y0, y1, tag):
        self.cx, self.cz, self.r, self.y0, self.y1, self.tag = cx, cz, r, y0, y1, tag
    def hit(self, o, d):
        best = None
        if abs(d[1]) > 1e-9:
            t = (self.y1 - o[1]) / d[1]
            if t > 0:
                px_, pz_ = o[0] + d[0] * t - self.cx, o[2] + d[2] * t - self.cz
                if px_ * px_ + pz_ * pz_ <= self.r * self.r:
                    best = (t, (o[0] + d[0] * t, self.y1, o[2] + d[2] * t), (0.0, 1.0, 0.0))
        ox, oz = o[0] - self.cx, o[2] - self.cz
        a2 = d[0] ** 2 + d[2] ** 2
        b2 = 2 * (ox * d[0] + oz * d[2])
        c2 = ox * ox + oz * oz - self.r ** 2
        disc = b2 * b2 - 4 * a2 * c2
        if a2 > 1e-12 and disc >= 0:
            t = (-b2 - math.sqrt(disc)) / (2 * a2)
            if t > 0:
                y = o[1] + d[1] * t
                if self.y0 <= y <= self.y1 and (best is None or t < best[0]):
                    p = (o[0] + d[0] * t, y, o[2] + d[2] * t)
                    best = (t, p, norm((p[0] - self.cx, 0, p[2] - self.cz)))
        return best


def boiler_sprite():
    body = CylV(6, 6, 5.8, 0, 44, 'boiler')
    parts = [body, CylV(6, 6, 6.1, 2, 3.6, 'copper'), CylV(6, 6, 6.1, 38.5, 40, 'copper'),
             Ell((6, 44, 6), (5.8, 1.4, 5.8), 'boiler'), Ell((6, 45.6, 6), (1.2, 0.8, 1.2), 'copper')]
    def hit(o, d, sx, sy):
        best = None
        for e in parts:
            r = e.hit(o, d)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[2], (e.tag, r[1]))
        return best
    def shade(info, n, lam):
        tag, p = info
        l = lvl_from(lam)
        if tag == 'boiler' and n[1] < 0.5:
            ang = math.atan2(p[2] - 6, p[0] - 6)
            # little round gauge on the side facing the room
            if abs(ang - 0.78) < 0.22 and abs(p[1] - 26) < 1.4:
                return PAL['rim'][3] if abs(ang - 0.78) < 0.12 and abs(p[1] - 26) < 0.8 else PAL['bumper'][1]
            if int(p[1]) % 9 == 0:
                return PAL['boiler'][max(0, l - 1)]
        return PAL[tag][min(4, l + (1 if tag == 'boiler' and l < 3 else 0))]
    return render([hit], (0, 0, 0), (12, 47, 12), shade)


def hoover_sprite():
    parts = [CylV(0, 0, 7, 0, 2.6, 'hoover'), Ell((0, 2.6, 0), (6.3, 0.9, 6.3), 'hoovertop'),
             Ell((0, 3.5, 0), (1.7, 0.45, 1.7), 'rim')]
    def hit(o, d, sx, sy):
        best = None
        for e in parts:
            r = e.hit(o, d)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[2], (e.tag, r[1]))
        return best
    def shade(info, n, lam):
        tag, p = info
        l = lvl_from(lam)
        if tag == 'hoover' and n[1] < 0.5 and p[1] < 1.3:
            return PAL['bumper'][max(0, l - 1)]
        return PAL[tag][min(4, l + 1)]
    return render([hit], (-7.5, 0, -7.5), (7.5, 4.5, 7.5), shade)


def gate_x_sprite():
    hs = []
    for k in range(7):
        x0 = 1 + k * 3.6
        hs.append(box_hitter((x0, 0, 0), (x0 + 1.4, 30, 2), 'iron'))
    hs.append(box_hitter((0, 26, 0), (24, 30, 2.4), 'iron'))
    hs.append(box_hitter((0, 12, 0.2), (24, 14, 2.2), 'iron'))
    return render(hs, (0, 0, 0), (24, 30, 2.4), shade_block, edges=False)


ROOM3 = (10 * T, 8 * T)
DOOR3 = (84, 108)


def background3():
    X, Z = ROOM3
    hs = [box_hitter((0, -4, 0), (X, 0, Z), 'floor'),
          box_hitter((-4, -4, -4), (0, 44, Z), 'wallL'),
          box_hitter((-4, -4, -4), (X, 44, 0), 'wallR'),
          box_hitter((DOOR3[0], 0, -1), (DOOR3[1], 32, 0.3), 'door')]

    def shade(info, n, lam):
        tag, p, nn = info
        L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
        if tag == 'floor':
            if nn[1] < 0.5:
                return PAL['plank_b'][0]
            band = int(p[2] // 4)
            key = 'plank_a' if band % 2 == 0 else 'plank_b'
            seam = p[2] % 4 < 0.45 or (p[0] + band * 7) % 24 < 0.45
            grain = (int(p[0] * 0.7 + band * 3) % 11 == 0)
            return PAL[key][max(0, L - (1 if seam else 0) - (1 if grain and not seam else 0) + 0)]
        if tag == 'door':
            return PAL['door'][1]
        if nn[1] > 0.5:
            return PAL['wall3'][4]
        along = p[2] if tag == 'wallL' else p[0]
        y = p[1] + 4
        if 13 <= y < 15:
            return PAL['dado'][L]
        if y < 13:
            return PAL['plank_b'][max(0, L - (1 if along % 12 < 0.6 else 0))]
        return PAL['wall3' if along % 6 < 3 else 'wall3b'][L]
    return render(hs, (-4, -4, -4), (X, 44, Z), shade, edges=True)


def key_sprite():
    parts = [Ell((-2.6 + 1.5 * math.cos(t), 0.6, 1.5 * math.sin(t)), (0.6, 0.6, 0.6), 'metal')
             for t in [i * math.pi / 4 for i in range(8)]]
    parts += [Ell((0.8, 0.6, 0), (2.8, 0.5, 0.5), 'metal'),
              Ell((2.8, 0.6, 0.9), (0.45, 0.45, 0.8), 'metal'),
              Ell((1.7, 0.6, 0.8), (0.4, 0.45, 0.6), 'metal')]
    return ell_sprite(parts, (-5, 0, -3), (4, 2, 3), lambda info, n, lam: PAL['metal'][min(4, lvl_from(lam) + 1)])


DOG_SCALE = 0.75


def dog_sprite(awake, empty=False):
    hy = 9.0 if awake else 4.8
    hz = 0.0 if awake else 1.0
    P = [Ell((0.5, 2.2, 0), (15, 3.4, 9.5), 'basket'),
         Ell((-1, 5.3, 0), (8.5, 4.0, 4.8), 'dbody'),
         Ell((8.3, hy, hz), (4.0, 3.5, 3.8), 'dhead'),
         Ell((11.9, hy - 0.9, hz), (2.4, 1.7, 2.0), 'dsnout'),
         Ell((14.1, hy - 0.4, hz), (0.8, 0.6, 0.8), 'dnose'),
         Ell((7.6, hy + 0.6, hz + 3.6), (2.3, 3.0, 0.9), 'dear'),
         Ell((7.6, hy + 0.6, hz - 3.6), (2.3, 3.0, 0.9), 'dear'),
         Ell((10.5, 4.2, -2.6), (3.0, 1.2, 1.4), 'dbody'),
         Ell((10.2, 4.2, 2.8), (3.0, 1.2, 1.4), 'dbody')]
    tail = [(-9, 5, 2), (-8, 4.5, 5.5), (-3, 4.2, 7)] if not awake else [(-9, 6, 0), (-12, 9, 0), (-12.5, 12, 0)]
    P += chain(tail, 1.5, 0.9, 'dbody', steps=6)
    head = P[2]
    if empty:
        P = [P[0]]                                   # just the basket, for when the dog is out of it
    s = DOG_SCALE

    def hit(o, d, sx, sy):
        ol, dl = mul(o, 1 / s), d
        best = None
        for e in P:
            r = e.hit(ol, dl)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[1], r[2], e)
        if not best:
            return None
        t, p, n, e = best
        mat = e.tag
        if mat == 'dhead':
            q = sub(p, head.c)
            az = math.atan2(q[2], q[0]); el = math.asin(max(-1, min(1, q[1] / math.sqrt(dot(q, q)))))
            mat = 'dbody'
            for sgn in (1, -1):
                if abs(az - sgn * 0.5) < 0.2 and abs(el - 0.2) < (0.2 if awake else 0.06):
                    mat = 'deye'
            if mat == 'dbody' and q[2] > 0.6 and q[1] > -0.5:
                mat = 'dpatch'                                   # patch over one eye
        elif mat == 'dear':
            mat = 'dpatch'
        elif mat == 'dbody' and e is P[1]:
            q = sub(p, e.c)
            if q[0] < -1.5 and q[1] > 1.0 and q[2] > -2.5:
                mat = 'dpatch'                                   # saddle patch
        elif mat == 'basket':
            if n[1] > 0.6 and dot(sub(p, e.c), (1, 0, 0)) ** 2 / 169 + (p[2] - e.c[2]) ** 2 / 64 < 0.55:
                mat = 'cushion'
        return t * s, n, (mat, p)

    def shade(info, n, lam):
        mat, p = info
        l = lvl_from(lam)
        if mat == 'basket':
            weave = (int(p[1] * 1.6) + int((p[0] + p[2]) * 0.8)) % 2
            return PAL['basket'][max(0, min(4, l - weave))]
        if mat == 'cushion':
            return PAL['plate_off'][max(0, l - 1)]
        if mat in ('deye', 'dnose'):
            return PAL[mat][1]
        if mat == 'dhead':
            mat = 'dbody'
        return PAL[mat][min(4, l + (1 if mat in ('dbody', 'dsnout') and l < 3 else 0))]
    return render([hit], (-13, 0, -8), (12, 12, 8), shade)


def dog_run_hitter(ang, phase):
    """Standalone Jack Russell for chasing, facing +x like the cats; phase None = standing."""
    tz = 0 if phase is None else math.sin(phase * 2) * 1.4
    P = [Ell((0, 8, 0), (8, 3.8, 4.0), 'dbody'),
         Ell((5.5, 7.6, 0), (3.6, 3.6, 3.6), 'dbody'),
         Ell((9.6, 12, 0), (3.7, 3.4, 3.4), 'dhead'),
         Ell((13, 11.1, 0), (2.2, 1.5, 1.7), 'dsnout'),
         Ell((15, 11.6, 0), (0.75, 0.6, 0.75), 'dnose'),
         Ell((8.4, 14.0, 2.7), (1.7, 2.3, 0.8), 'dear'),
         Ell((8.4, 14.0, -2.7), (1.7, 2.3, 0.8), 'dear')]
    body, head = P[0], P[2]
    for hx_, hz_ in ((5.5, 2.4), (5.5, -2.4), (-5.5, 2.4), (-5.5, -2.4)):
        off, lift = 0.0, 0.0
        if phase is not None:
            pair = 0 if (hx_ > 0) == (hz_ > 0) else math.pi
            off = 3.2 * math.sin(phase + pair)
            lift = max(0.0, math.cos(phase + pair)) * 1.4
        P += chain([(hx_, 6.5, hz_), (hx_ + off, 1.2 + lift, hz_)], 1.3, 1.2, 'dleg', steps=6)
        P.append(Ell((hx_ + off + 0.6, 1.0 + lift, hz_), (1.5, 1.0, 1.25), 'dleg'))
    P += chain([(-7.5, 9.5, 0), (-9.5, 12, tz), (-10.2, 14.5, tz * 1.5)], 1.1, 0.7, 'dtail', steps=5)
    if phase is not None:
        bob = 0.5 * abs(math.sin(phase))
        for e in P:
            if e.tag not in ('dleg',):
                e.c = (e.c[0], e.c[1] + bob, e.c[2])
    s = DOG_SCALE

    def hit(o, d, sx, sy):
        ol, dl = mul(roty(o, ang), 1 / s), roty(d, ang)
        best = None
        for e in P:
            r = e.hit(ol, dl)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[1], r[2], e)
        if not best:
            return None
        t, p, n, e = best
        mat = e.tag
        if mat == 'dhead':
            q = sub(p, head.c)
            az = math.atan2(q[2], q[0]); el = math.asin(max(-1, min(1, q[1] / math.sqrt(dot(q, q)))))
            mat = 'dbody'
            for sgn in (1, -1):
                if abs(az - sgn * 0.55) < 0.2 and abs(el - 0.2) < 0.2:
                    mat = 'deye'
            if mat == 'dbody' and q[2] > 0.6 and q[1] > -0.5:
                mat = 'dpatch'
        elif mat == 'dear':
            mat = 'dpatch'
        elif mat == 'dtail':
            mat = 'dpatch' if e.c[1] > 13 else 'dbody'
        elif mat == 'dleg':
            mat = 'dbody'
        elif mat == 'dbody' and e is body:
            q = sub(p, e.c)
            if q[0] < -1.5 and q[1] > 0.8 and q[2] > -2.8:
                mat = 'dpatch'
        return t * s, roty(n, -ang), (mat, p)

    def shade(info, n, lam):
        mat, p = info
        l = lvl_from(lam)
        if mat in ('deye', 'dnose'):
            return PAL[mat][1]
        return PAL[mat][min(4, l + (1 if mat in ('dbody', 'dsnout') and l < 3 else 0))]
    return hit, shade


DOG_FRAMES = [None, 0, math.pi / 2, math.pi, 3 * math.pi / 2]


def dog_job(args):
    d, f = args
    hit, shade = dog_run_hitter(d * 2 * math.pi / DIRS, DOG_FRAMES[f])
    R = 14
    im, ox, oy = render([hit], (-R, 0, -R), (R, 15, R), shade, edges=True)
    return d, f, im, ox, oy


ROOM2 = (10 * T, 8 * T)
CHAN = (60, 84)
DOOR2 = (66, 90)


def background2():
    X, Z = ROOM2
    hs = [box_hitter((0, -4, 0), (CHAN[0], 0, Z), 'floor'),
          box_hitter((CHAN[1], -4, 0), (X, 0, Z), 'floor'),
          box_hitter((CHAN[0], -16, 0), (CHAN[1], -3, Z), 'water'),
          box_hitter((CHAN[0] - 4, -16, -4), (CHAN[1], -4, 0), 'pit'),
          box_hitter((-4, -4, -4), (0, 44, Z), 'wallL'),
          box_hitter((-4, -4, -4), (X, 44, 0), 'wallR'),
          box_hitter((-1, 0, DOOR2[0]), (0.3, 32, DOOR2[1]), 'door')]

    def shade(info, n, lam):
        tag, p, nn = info
        L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
        if tag == 'floor':
            if nn[1] < 0.5:
                return PAL['pit'][max(0, L - 1)]
            tx, tz = int(p[0] // T), int(p[2] // T)
            key = 'tile_a' if (tx + tz) % 2 == 0 else 'tile_b'
            edge = p[0] % T < 0.7 or p[2] % T < 0.7
            return PAL[key][max(0, L - (1 if edge else 0))]
        if tag == 'water':
            if nn[1] < 0.5:
                return PAL['water'][0]
            ripple = (p[0] * 0.9 + math.sin(p[2] * 0.45) * 2.5) % 7 < 0.7
            return PAL['water'][3 if ripple else 2]
        if tag == 'pit':
            return PAL['pit'][max(0, L - 1)]
        if tag == 'door':
            return PAL['door'][1]
        if nn[1] > 0.5:
            return PAL['wall2'][4]
        along = p[2] if tag == 'wallL' else p[0]
        grout = p[1] % 6 < 0.7 or along % 6 < 0.7
        if p[1] < 6:
            return PAL['wall2'][max(0, L - 2)] if grout else PAL['wall2'][max(0, L - 1)]   # darker skirting row
        return PAL['wall2'][max(0, L - (1 if grout else 0))]
    return render(hs, (-4, -16, -4), (X, 44, Z), shade, edges=True)


# ======================= rooms 4-8 =======================
PAL.update({k: ramp(v) for k, v in dict(
    carpet='#6f9c9b', carpet2='#5d8a8a', paper='#e3c9c1', paper2='#d6b6ad', skirt='#efe8de',
    wood2='#8a5a3c', wood3='#a0724c', duvet0='#f0c4c8', duvet1='#bcd7ea', duvet2='#f3dfa2', duvet3='#c9e2c3', pillow='#f4f1ea',
    pouffe='#d9a441', flag='#77736d', flag2='#6a6661', brick='#7d4a3c', brick2='#6c3f33', mortar='#4a3b37', coal='#1c1a1d', coalhi='#3a3638',
    bottle='#2f4a3a', barrel='#8b5a35', hoop='#4b4b55',
    lino_a='#e9e4d8', lino_b='#3c4a5c', ktile='#efe6cf', ktile2='#7fae8f', worktop='#d9cdb5', steel='#b9c0c8', cab='#6f9a86', fridge='#e4ece6',
    wool='#e58fb0', wool2='#c9608a',
    deck='#c9a26b', deck2='#b88f5a', glass2='#bfe0e8', frame='#f2f2ee', gallery='#9b6b45', terracotta='#c4673f', leaf='#5f9c4a', leaf2='#4a7f3a',
    liftmetal='#9aa3ad', hazard='#e6c23a',
    attic='#7d5a3d', attic2='#6d4e35', beam='#5a3f2b', insul='#c9b48a', cardboard='#c49a6c', tape='#e3cf9e', trunk='#6b4a32').items()})


class Floor:
    """Floor slab with optional square holes (coal pits) that show their inner walls."""
    def __init__(self, X, Z, holes=(), depth=12, thick=4):
        self.X, self.Z, self.holes, self.depth, self.thick = X, Z, set(holes), depth, thick

    def hit(self, o, d):
        X, Z = self.X, self.Z
        t = -o[1] / d[1]
        p = (o[0] + d[0] * t, 0.0, o[2] + d[2] * t)
        if 0 <= p[0] < X and 0 <= p[2] < Z:
            cx, cz = int(p[0] // T), int(p[2] // T)
            if (cx, cz) not in self.holes:
                return t, p, (0.0, 1.0, 0.0), 'top'
            for _ in range(24):
                x0, z0 = cx * T, cz * T
                tx = (x0 - o[0]) / d[0]
                tz = (z0 - o[2]) / d[2]
                tb = (-self.depth - o[1]) / d[1]
                tm = min(tx, tz, tb)
                q = (o[0] + d[0] * tm, o[1] + d[1] * tm, o[2] + d[2] * tm)
                if tm == tb:
                    return tm, q, (0.0, 1.0, 0.0), 'pitbottom'
                if tm == tx:
                    if (cx - 1, cz) in self.holes:
                        cx -= 1
                        continue
                    return tm, q, (1.0, 0.0, 0.0), 'pitwall'
                if (cx, cz - 1) in self.holes:
                    cz -= 1
                    continue
                return tm, q, (0.0, 0.0, 1.0), 'pitwall'
            return None
        best = None
        tX = (X - o[0]) / d[0]
        q = (o[0] + d[0] * tX, o[1] + d[1] * tX, o[2] + d[2] * tX)
        if -self.thick <= q[1] <= 0 and 0 <= q[2] <= Z:
            best = (tX, q, (1.0, 0.0, 0.0), 'edge')
        tZ = (Z - o[2]) / d[2]
        q = (o[0] + d[0] * tZ, o[1] + d[1] * tZ, o[2] + d[2] * tZ)
        if -self.thick <= q[1] <= 0 and 0 <= q[0] <= X and (best is None or tZ < best[0]):
            best = (tZ, q, (0.0, 0.0, 1.0), 'edge')
        return best


def room_background(X, Z, wall_h, door, floor_fn, wall_fn, cap, edge, holes=()):
    """door = (wall, a, b, y0, y1) with wall 'left' (runs along z) or 'back' (runs along x)."""
    fl = Floor(X, Z, holes)
    wall, a, b, y0, y1 = door

    def floor_hit(o, d, sx, sy):
        r = fl.hit(o, d)
        if not r:
            return None
        t, p, n, tag = r
        return t, n, ('floor:' + tag, p, n)
    hs = [floor_hit,
          box_hitter((-4, -4, -4), (0, wall_h, Z), 'wallL'),
          box_hitter((-4, -4, -4), (X, wall_h, 0), 'wallR'),
          box_hitter((-1, y0, a), (0.3, y1, b), 'door') if wall == 'left' else box_hitter((a, y0, -1), (b, y1, 0.3), 'door')]

    def shade(info, n, lam):
        tag, p, nn = info
        L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
        if tag == 'floor:top':
            return floor_fn(p, L)
        if tag == 'floor:edge':
            return PAL[edge][0]
        if tag == 'floor:pitwall':
            return PAL['coalhi'][0] if p[1] > -3 else PAL['coal'][1]
        if tag == 'floor:pitbottom':
            lump = (int(p[0] * 0.9) * 7 + int(p[2] * 0.9) * 13) % 5 == 0
            return PAL['coalhi'][1] if lump else PAL['coal'][0]
        if tag == 'door':
            return PAL['door'][1]
        if nn[1] > 0.5:
            return PAL[cap][4]
        along = p[2] if tag == 'wallL' else p[0]
        return wall_fn(along, p[1] - 4, L)
    return render(hs, (-4, -16, -4), (X, wall_h, Z), shade, edges=True)


# ---- room styles
def bedroom_floor(p, L):
    x, z = p[0], p[2]
    if (int(x // 3) + int(z // 3)) % 2 == 0 and (x % 12 < 1.2 or z % 12 < 1.2):
        return PAL['carpet2'][L]
    return PAL['carpet'][L]


def bedroom_wall(along, y, L):
    if y < 4:
        return PAL['skirt'][max(0, L - (1 if y > 3.4 else 0))]
    dot = (int(along) % 6 == 3) and (int(y) % 6 == 3) or (int(along + 3) % 6 == 3 and int(y + 3) % 6 == 3)
    return PAL['paper2'][L] if dot else PAL['paper'][L]


def cellar_floor(p, L):
    x, z = p[0], p[2]
    row = int(z // 8)
    off = 5 if row % 2 else 0
    seam = z % 8 < 0.6 or (x + off) % 11 < 0.6
    k = 'flag2' if (int((x + off) // 11) + row) % 3 == 0 else 'flag'
    return PAL[k][max(0, L - (1 if seam else 0))]


def cellar_wall(along, y, L):
    row = int(y // 3)
    mortar = y % 3 < 0.6 or (along + (3 if row % 2 else 0)) % 7 < 0.6
    if mortar:
        return PAL['mortar'][L]
    return PAL['brick2' if (int((along + (3 if row % 2 else 0)) // 7) + row) % 4 == 0 else 'brick'][L]


def kitchen_floor(p, L):
    k = 'lino_a' if (int(p[0] // 6) + int(p[2] // 6)) % 2 == 0 else 'lino_b'
    return PAL[k][L]


def kitchen_wall(along, y, L):
    if 12 <= y < 15:
        return PAL['ktile2'][max(0, L - (1 if along % 3 < 0.4 else 0))]
    grout = y % 4 < 0.4 or along % 4 < 0.4
    return PAL['ktile'][max(0, L - (1 if grout else 0))]


def conservatory_floor(p, L):
    x, z = p[0], p[2]
    # herringbone-ish: alternate plank direction in 6-unit cells
    cell = (int(x // 6) + int(z // 6)) % 2
    u = z if cell else x
    seam = u % 2 < 0.35 or (x % 6 < 0.35 if cell else z % 6 < 0.35)
    return PAL['deck2' if cell else 'deck'][max(0, L - (1 if seam else 0))]


def conservatory_wall(along, y, L):
    if y < 8:
        return PAL['frame'][max(0, L - (1 if y > 7.2 or y < 0.8 else 0))]
    if along % 12 < 1.0 or y % 16 < 1.0:
        return PAL['frame'][L]
    shine = (along - y * 0.6) % 24 < 2.5
    return PAL['glass2'][min(4, L + (1 if shine else 0))]


def attic_floor(p, L):
    x, z = p[0], p[2]
    band = int(x // 5)
    seam = x % 5 < 0.5 or (z + band * 9) % 30 < 0.5
    knot = (int(z * 0.8 + band * 5) % 17 == 0) and x % 5 > 2
    return PAL['attic2' if band % 2 else 'attic'][max(0, L - (1 if seam or knot else 0))]


def attic_wall(along, y, L):
    if along % 24 < 2.2:
        return PAL['beam'][L]
    if y > 30:
        return PAL['beam'][max(0, L - 1)] if y < 32.5 else PAL['insul'][max(0, L - (1 if int(along * 1.3 + y) % 5 == 0 else 0))]
    return PAL['attic'][max(0, L - (1 if along % 6 < 0.5 else 0))]


# ---- props
def shade_props(info, n, lam):
    tag, p, nn = info
    L = 1 if lam < 0.35 else 2 if lam < 0.7 else 3
    top, fx, fz = nn[1] > 0.5, nn[0] > 0.5, nn[2] > 0.5
    if tag == 'landing':
        if top:
            edge = p[0] < 1.5 or p[2] > 22.5 or p[0] > 58.5
            return PAL['carpet2' if edge else 'carpet'][L]
        u = p[0] if fz else p[2]
        if p[1] > 18.6:
            return PAL['wood3'][min(4, L + 1)]
        if p[1] < 1.4:
            return PAL['wood2'][max(0, L - 1)]
        return PAL['wood3'][max(0, L - (1 if u % 10 < 0.6 else 0))]
    if tag == 'wardrobe':
        if top:
            return PAL['wood2'][3]
        if p[1] > 43.5:
            return PAL['wood3'][L]
        if p[1] < 2:
            return PAL['wood2'][max(0, L - 1)]
        if fx:
            z, y = p[2], p[1]
            if abs(z - 12) < 0.4:
                return PAL['wood2'][0]
            if (abs(z - 10.5) < 0.6 or abs(z - 13.5) < 0.6) and abs(y - 24) < 0.8:
                return PAL['metal'][3]
            inset = (1.6 < (z % 12) < 10.4) and 4 < y < 41
            border = inset and ((z % 12) < 2.2 or (z % 12) > 9.8 or y < 4.6 or y > 40.4)
            return PAL['wood2'][max(0, L - 1)] if border else PAL['wood2'][L]
        return PAL['wood2'][L]
    if tag == 'bed':
        if top:
            z, x = p[2], p[0]
            if z < 7 and 2 < x < 22:
                return PAL['pillow'][L]
            if z < 8:
                return PAL['duvet1'][L]
            c = 'duvet%d' % ((int(x // 6) + int((z - 8) // 7)) % 4)
            seam = x % 6 < 0.45 or (z - 8) % 7 < 0.45
            return PAL[c][max(0, L - (1 if seam else 0))]
        if p[1] < 4:
            return PAL['wood2'][L]
        c = 'duvet%d' % ((int((p[0] if fz else p[2]) // 6)) % 4)
        return PAL[c][max(0, L - 1)]
    if tag == 'winerack':
        if top:
            return PAL['barrel'][3]
        if fz:
            x, y = p[0], p[1]
            if x < 1.2 or x > 22.8 or y < 1.2 or y > 34.8:
                return PAL['barrel'][L]
            cx, cy = (x - 1.2) % 3.6, (y - 1.2) % 3.6
            r = math.hypot(cx - 1.8, cy - 1.8)
            if r < 1.25:
                filled = (int((x - 1.2) // 3.6) * 3 + int((y - 1.2) // 3.6) * 5) % 7 != 0
                if filled:
                    return PAL['bottle'][3] if (cx - 1.8) + (cy - 1.8) < -0.9 else PAL['bottle'][1]
                return PAL['coal'][0]
            return PAL['barrel'][max(0, L - 1)]
        return PAL['barrel'][max(0, L - (1 if p[1] % 3.6 < 0.5 else 0))]
    if tag == 'counter' or tag == 'island':
        if top:
            if tag == 'counter' and 18 < p[0] < 30 and 2 < p[2] < 10:
                return PAL['steel'][1 if (2.8 < p[2] < 9.2 and 18.8 < p[0] < 29.2) else 3]
            return PAL['worktop'][L]
        if p[1] > 16.5:
            return PAL['worktop'][max(0, L - 1)]
        if p[1] < 1.5:
            return PAL['cab'][0]
        u = p[0] if fz else p[2]
        if u % 12 < 0.5:
            return PAL['cab'][max(0, L - 1)]
        if abs(u % 12 - 9.5) < 0.5 and 11 < p[1] < 14:
            return PAL['metal'][3]
        return PAL['cab'][L]
    if tag == 'fridge':
        if top:
            return PAL['fridge'][2]
        if fz:
            if abs(p[1] - 26) < 0.4:
                return PAL['rim'][1]
            if abs(p[0] - 9.5) < 0.5 and (20 < p[1] < 25 or 28 < p[1] < 34):
                return PAL['steel'][3]
        return PAL['fridge'][L]
    if tag == 'gallery':
        if top:
            return PAL['deck'][max(0, L - (1 if p[2] % 3 < 0.4 else 0))]
        u = p[0] if fz else p[2]
        if p[1] > 27:
            return PAL['gallery'][min(4, L + 1)] if p[1] > 28.6 else PAL['gallery'][max(0, L - 1)]
        if u % 24 < 1.4:
            return PAL['wood2'][L]
        return PAL['gallery'][max(0, L - (1 if u % 3 < 0.35 else 0))]
    if tag == 'plantshelf':
        if top:
            return PAL['wood3'][3]
        u = p[0] if fz else p[2]
        y = p[1]
        if u < 0.9 or u > 11.1 or y % 11 < 0.9 or y > 43:
            return PAL['wood3'][L]
        level = int(y // 11)
        base = level * 11 + 0.9
        pot_c = 3 + (level % 2) * 6
        if abs(u - pot_c) < 2.2 and y < base + 4:
            return PAL['terracotta'][L]
        if abs(u - pot_c) < 3.0 and base + 4 <= y < base + 8.5:
            return PAL['leaf' if int(u * 2 + y) % 3 else 'leaf2'][L]
        return PAL['wood2'][0]
    if tag == 'liftslab':
        if top:
            stripe = p[0] < 1 or p[0] > 11 or p[2] < 1 or p[2] > 11
            return PAL['hazard' if stripe and int((p[0] + p[2]) // 1.5) % 2 else 'liftmetal'][L if not stripe else 2]
        u = p[0] if fz else p[2]
        return PAL['hazard' if int((u + p[1] * 2) // 1.5) % 2 else 'bumper'][2]
    if tag == 'loft':
        if top:
            return PAL['attic'][max(0, L - (1 if p[2] % 5 < 0.5 else 0))]
        u = p[0] if fz else p[2]
        if p[1] > 17.5:
            return PAL['beam'][L]
        return PAL['attic2'][max(0, L - (1 if u % 5 < 0.5 else 0))]
    if tag == 'boxes':
        y = p[1]
        if top:
            return PAL['tape'][L] if abs(p[0] - 6) < 1 else PAL['cardboard'][L]
        u = p[0] if fz else p[2]
        if y % 13.33 < 0.6:
            return PAL['cardboard'][0]
        if abs(u - 6) < 1 and y % 13.33 > 9:
            return PAL['tape'][L]
        return PAL['cardboard'][L]
    if tag == 'trunk':
        u = p[0] if fz else p[2]
        if top:
            return PAL['trunk'][3] if not (abs(p[0] - 5) < 0.8 or abs(p[0] - 19) < 0.8) else PAL['metal'][2]
        if abs(u - 5) < 0.8 or abs(u - 19) < 0.8 or abs(p[1] - 10.5) < 0.5:
            return PAL['metal'][L]
        return PAL['trunk'][L]
    return shade_block(info, n, lam)


def prop_sprite(size, tag):
    return render([box_hitter((0, 0, 0), size, tag)], (0, 0, 0), size, shade_props)


def round_sprite(parts, lo, hi, shade_fn):
    def hit(o, d, sx, sy):
        best = None
        for e in parts:
            r = e.hit(o, d)
            if r and (best is None or r[0] < best[0]):
                best = (r[0], r[2], (e.tag, r[1], e))
        return best
    return render([hit], lo, hi, shade_fn)


def pouffe_sprite():
    parts = [CylV(6, 6, 5.8, 0, 4.2, 'pouffe'), Ell((6, 4.2, 6), (5.8, 1.0, 5.8), 'pouffetop')]
    def shade(info, n, lam):
        tag, p, e = info
        l = lvl_from(lam)
        if tag == 'pouffetop':
            r = math.hypot(p[0] - 6, p[2] - 6)
            ang = math.atan2(p[2] - 6, p[0] - 6)
            if r < 0.8:
                return PAL['wood2'][2]
            if r > 1.5 and abs(((ang * 8 / math.pi) % 2) - 1) < 0.18:
                return PAL['pouffe'][max(0, l)]
            return PAL['pouffe'][min(4, l + 1)]
        if p[1] < 0.8:
            return PAL['wood2'][1]
        ang = math.atan2(p[2] - 6, p[0] - 6)
        return PAL['pouffe'][max(0, l - (1 if abs(((ang * 6 / math.pi) % 2) - 1) < 0.12 else 0))]
    return round_sprite(parts, (0, 0, 0), (12, 6, 12), shade)


def barrel_sprite():
    parts = [CylV(6, 6, 5.7, 0, 14, 'barrel')]
    def shade(info, n, lam):
        tag, p, e = info
        l = lvl_from(lam)
        if n[1] > 0.5:
            r = math.hypot(p[0] - 6, p[2] - 6)
            return PAL['hoop'][2] if r > 5.0 else PAL['barrel'][max(0, l - (1 if int(p[0]) % 3 == 0 else 0))]
        if abs(p[1] - 2.5) < 0.7 or abs(p[1] - 11.5) < 0.7:
            return PAL['hoop'][l]
        ang = math.atan2(p[2] - 6, p[0] - 6)
        stave = abs(((ang * 7 / math.pi) % 2) - 1) < 0.1
        return PAL['barrel'][max(0, l - (1 if stave else 0))]
    return round_sprite(parts, (0, 0, 0), (12, 14, 12), shade)


def pot_sprite():
    parts = [CylV(6, 6, 4.6, 0, 8, 'terracotta'),
             Ell((6, 12, 6), (5.5, 5, 5.5), 'leaf'), Ell((4, 16, 5), (3.8, 4.2, 3.8), 'leaf2'),
             Ell((8, 15, 8), (3.6, 4.4, 3.6), 'leaf'), Ell((6, 19.5, 6), (2.8, 3.2, 2.8), 'leaf2')]
    def shade(info, n, lam):
        tag, p, e = info
        l = lvl_from(lam)
        if tag == 'terracotta':
            return PAL['terracotta'][max(0, l - (1 if p[1] > 6.8 else 0))]
        speck = (int(p[0] * 2.1) + int(p[1] * 1.7) + int(p[2] * 2.3)) % 4 == 0
        return PAL[tag][max(0, min(4, l - (1 if speck else 0)))]
    return round_sprite(parts, (0, 0, 0), (12, 23, 12), shade)


def wool_frames(nf=4):
    out = []
    for f in range(nf):
        ph = f * math.pi / 2 / nf * 2
        parts = [Ell((0, 4, 0), (4, 4, 4), 'wool')]
        def shade(info, n, lam, ph=ph):
            tag, p, e = info
            l = lvl_from(lam)
            q = (p[0], p[1] - 4, p[2])
            a = math.atan2(q[1], q[0]) + ph
            b = math.atan2(q[1], q[2]) - ph * 0.7
            s1 = abs(math.sin(a * 3 + q[2] * 0.5)) < 0.22
            s2 = abs(math.sin(b * 3 + q[0] * 0.5)) < 0.18
            if s1 or s2:
                return PAL['wool2'][max(0, l)]
            return PAL['wool'][min(4, l + 1)]
        out.append(round_sprite(parts, (-4.5, 0, -4.5), (4.5, 8.5, 4.5), shade))
    return out


if __name__ == '__main__':
    assets = {'pix': PIX, 'right': RIGHT, 'up': UP, 'sprites': {}, 'cats': {}}

    def put(name, res):
        im, ox, oy = res
        assets['sprites'][name] = dict(src=b64(im), ox=ox, oy=oy, w=im.width, h=im.height)

    put('bg1', background())
    put('bg2', background2())
    put('cupboard', block_sprite((T, 34, T), 'cupboard'))
    put('crate_sunk', block_sprite((T, 3, T), 'crate_sunk'))
    put('key', key_sprite())
    put('bg3', background3())
    put('shelf', block_sprite((T, 30, 2 * T), 'shelf'))
    put('washer', block_sprite((T, 16, T), 'washer'))
    put('boiler', boiler_sprite())
    put('hoover', hoover_sprite())
    put('pad_off', block_sprite((T, 1.2, T), 'pad_off'))
    put('pad_on', block_sprite((T, 0.5, T), 'pad_on'))
    put('gate_x', gate_x_sprite())
    # rooms 4-8
    put('bg4', room_background(120, 96, 56, ('back', 84, 108, 20, 48), bedroom_floor, bedroom_wall, 'paper', 'carpet2'))
    put('bg5', room_background(96, 96, 44, ('left', 12, 36, 0, 32), cellar_floor, cellar_wall, 'brick', 'flag2',
                               holes=[(5, 0), (3, 1), (5, 1), (1, 2), (2, 2), (3, 2), (7, 2), (1, 3), (3, 3), (4, 3), (5, 3), (7, 3),
                                      (1, 4), (5, 4), (1, 5), (2, 5), (3, 5), (5, 5), (6, 5), (3, 6), (3, 7)]))
    put('bg6', room_background(120, 96, 44, ('back', 12, 36, 0, 32), kitchen_floor, kitchen_wall, 'ktile', 'lino_b'))
    put('bg7', room_background(120, 96, 58, ('back', 84, 108, 30, 54), conservatory_floor, conservatory_wall, 'frame', 'deck2'))
    put('bg8', room_background(120, 96, 56, ('left', 12, 36, 20, 48), attic_floor, attic_wall, 'beam', 'attic2'))
    put('landing', prop_sprite((60, 20, 24), 'landing'))
    put('wardrobe', prop_sprite((12, 46, 24), 'wardrobe'))
    put('bed', prop_sprite((24, 10, 36), 'bed'))
    put('pouffe', pouffe_sprite())
    put('winerack', prop_sprite((24, 36, 12), 'winerack'))
    put('barrel', barrel_sprite())
    put('counter', prop_sprite((48, 18, 12), 'counter'))
    put('fridge', prop_sprite((12, 40, 12), 'fridge'))
    put('island', prop_sprite((24, 18, 24), 'island'))
    for i, fr in enumerate(wool_frames()):
        put('wool%d' % i, fr)
    put('gallery', prop_sprite((120, 30, 24), 'gallery'))
    put('plantshelf', prop_sprite((12, 44, 12), 'plantshelf'))
    put('pot', pot_sprite())
    put('liftslab', prop_sprite((12, 1.5, 12), 'liftslab'))
    put('loft', prop_sprite((36, 20, 48), 'loft'))
    put('boxes', prop_sprite((12, 40, 12), 'boxes'))
    put('trunk', prop_sprite((24, 12, 12), 'trunk'))
    put('dog_sleep', dog_sprite(False))
    put('dog_awake', dog_sprite(True))
    put('dog_basket', dog_sprite(False, empty=True))
    put('crate', block_sprite((T, T, T), 'crate'))
    put('ledge', block_sprite((2 * T, 3 * T, 2 * T), 'stone'))
    put('plate_off', block_sprite((T, 1.2, T), 'plate_off'))
    put('plate_on', block_sprite((T, 0.5, T), 'plate_on'))
    put('btn_off', block_sprite((6, 2.5, 6), 'btn_off'))
    put('btn_on', block_sprite((6, 1, 6), 'btn_on'))
    put('fence_x12', block_sprite((T, 30, 2), 'fence'))
    put('fence_x6', block_sprite((6, 30, 2), 'fence'))
    put('fence_z12', block_sprite((2, 30, T), 'fence'))
    put('gate', gate_sprite())
    put('fish', fish_sprite())

    jobs = [(k, d, f) for k in ('ginger', 'smoke', 'tom') for d in range(DIRS) for f in range(3 * len(columns(k)))]
    with Pool() as pool:
        res = pool.map(cat_job, jobs)
    for kind in ('ginger', 'smoke', 'tom'):
        mine = [r for r in res if r[0] == kind]
        x0 = min(r[4] for r in mine); y0 = min(r[5] for r in mine)
        x1 = max(r[4] + r[3].width for r in mine); y1 = max(r[5] + r[3].height for r in mine)
        cw, ch = x1 - x0, y1 - y0
        sheet = Image.new('RGBA', (cw * 3 * len(columns(kind)), ch * DIRS), (0, 0, 0, 0))
        for _, d, f, im, ox, oy in mine:
            sheet.paste(im, (f * cw + ox - x0, d * ch + oy - y0))
        sheet.save(f'sheet_{kind}.png')
        assets['cats'][kind] = dict(src=b64(sheet), ox=x0, oy=y0, w=cw, h=ch, frames=len(columns(kind)), dirs=DIRS)

    with Pool() as pool:
        dres = pool.map(dog_job, [(d, f) for d in range(DIRS) for f in range(len(DOG_FRAMES))])
    x0 = min(r[3] for r in dres); y0 = min(r[4] for r in dres)
    x1 = max(r[3] + r[2].width for r in dres); y1 = max(r[4] + r[2].height for r in dres)
    cw, ch = x1 - x0, y1 - y0
    sheet = Image.new('RGBA', (cw * len(DOG_FRAMES), ch * DIRS), (0, 0, 0, 0))
    for d, f, im, ox, oy in dres:
        sheet.paste(im, (f * cw + ox - x0, d * ch + oy - y0))
    sheet.save('sheet_dog.png')
    assets['dog'] = dict(src=b64(sheet), ox=x0, oy=y0, w=cw, h=ch, frames=len(DOG_FRAMES), dirs=DIRS)

    with open('assets.js', 'w') as fh:
        fh.write('const ASSETS = ' + json.dumps(assets) + ';\n')
    print('ok', sum(len(v['src']) for v in assets['sprites'].values()) + sum(len(v['src']) for v in assets['cats'].values()))
