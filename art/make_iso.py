"""Isometric pixel cats.

Cats are modelled as 3D ellipsoids and sphere-chains, ray-cast from an
orthographic isometric camera (45° yaw, 30° pitch), lit from the top-left,
and quantised onto hue-shifted colour ramps with coloured outlines.
"""
import colorsys, math
from PIL import Image, ImageDraw, ImageFont

# ---------------- vector helpers ----------------
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    l = math.sqrt(dot(a, a)) or 1
    return (a[0] / l, a[1] / l, a[2] / l)

# ---------------- camera ----------------
YAW, PITCH = math.radians(45), math.radians(30)
V = (math.sin(YAW) * math.cos(PITCH), math.sin(PITCH), math.cos(YAW) * math.cos(PITCH))  # toward viewer
F = mul(V, -1)
RIGHT = norm((math.cos(YAW), 0, -math.sin(YAW)))
UP = norm(cross(RIGHT, F))
if UP[1] < 0:
    UP = mul(UP, -1)
LIGHT = norm(add(add(mul(RIGHT, -0.55), mul(UP, 0.7)), mul(V, 0.45)))
PIX = 0.62
TURN = math.radians(12)   # cat turned this much toward the camera
def roty(a, ang):
    c, s_ = math.cos(ang), math.sin(ang)
    return (a[0] * c + a[2] * s_, a[1], -a[0] * s_ + a[2] * c)
          # world units per pixel (smaller = bigger sprite)

# ---------------- colour ramps ----------------
def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def ramp(base):
    r, g, b = hex2rgb(base)
    shadow, hi = (0.20, 0.15, 0.32), (1.0, 0.97, 0.88)
    def mix(a, c, k): return tuple(a[i] + (c[i] - a[i]) * k for i in range(3))
    steps = [mix((r, g, b), shadow, 0.50), mix((r, g, b), shadow, 0.24), (r, g, b),
             mix((r, g, b), hi, 0.22), mix((r, g, b), hi, 0.42)]
    return [tuple(int(v * 255) for v in c) + (255,) for c in steps]

# ---------------- primitives ----------------
class Ell:
    def __init__(self, c, r, tag, t=0.0):
        self.c, self.r, self.tag, self.t = c, r, tag, t
    def hit(self, o, d):
        oc = sub(o, self.c)
        o2 = (oc[0] / self.r[0], oc[1] / self.r[1], oc[2] / self.r[2])
        d2 = (d[0] / self.r[0], d[1] / self.r[1], d[2] / self.r[2])
        a, b, c = dot(d2, d2), 2 * dot(o2, d2), dot(o2, o2) - 1
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        t = (-b - math.sqrt(disc)) / (2 * a)
        if t < 0:
            return None
        p = add(o, mul(d, t))
        q = sub(p, self.c)
        n = norm((q[0] / self.r[0] ** 2, q[1] / self.r[1] ** 2, q[2] / self.r[2] ** 2))
        return t, p, n

def chain(pts, r0, r1, tag, steps=10):
    out, segs = [], len(pts) - 1
    total = segs * steps
    for i in range(segs):
        for k in range(steps + (1 if i == segs - 1 else 0)):
            u = k / steps
            idx = i * steps + k
            tt = idx / total
            p = tuple(pts[i][j] + (pts[i + 1][j] - pts[i][j]) * u for j in range(3))
            r = r0 + (r1 - r0) * tt
            out.append(Ell(p, (r, r, r), tag, tt))
    return out

class Box:
    def __init__(self, lo, hi):
        self.lo, self.hi, self.tag = lo, hi, 'block'
    def hit(self, o, d):
        tmin, tmax, nrm = -1e9, 1e9, None
        for i in range(3):
            if abs(d[i]) < 1e-9:
                if not (self.lo[i] <= o[i] <= self.hi[i]):
                    return None
                continue
            t1, t2 = (self.lo[i] - o[i]) / d[i], (self.hi[i] - o[i]) / d[i]
            n1 = [0, 0, 0]; n1[i] = -1 if t1 < t2 else 1
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 > tmin:
                tmin, nrm = t1, tuple(n1)
            tmax = min(tmax, t2)
        if tmin > tmax or tmin < 0:
            return None
        return tmin, add(o, mul(d, tmin)), nrm

# ---------------- cat models (X = forward, Y = up, Z = side) ----------------
def model(kind):
    if kind == 'ginger':      # slim, leggy, tail up
        body = Ell((0, 10, 0), (10, 4.6, 4.4), 'body')
        head = Ell((12, 15.5, 0), (5.2, 4.8, 5.4), 'head')
        legs_y, leg_r, paw_r = 8, 1.35, 1.6
        leg_x = (-6.5, 6.5)
        tail = chain([(-9, 11, 0), (-12.5, 14, 0), (-13.5, 20, 0), (-12, 24, 0)], 1.4, 1.1, 'tail')
        muz = Ell((16.3, 13.8, 0), (1.9, 1.6, 2.5), 'muzzle')
        ears = [(11.5, 19, 2.8), (11.5, 19, -2.8)]
        ear_tip = 4.4
        eye = dict(az=0.5, el=0.12, aw=0.23, eh=0.28)
        b_rz = 4.4
    elif kind == 'smoke':     # medium build, sleek, tail low
        body = Ell((0, 10, 0), (10.5, 5.0, 4.8), 'body')
        head = Ell((12.5, 15.5, 0), (5.4, 5.0, 5.6), 'head')
        legs_y, leg_r, paw_r = 8, 1.45, 1.7
        leg_x = (-6.8, 6.8)
        tail = chain([(-9.5, 10.5, 0), (-13, 9, 0), (-15.5, 10, 0), (-16.5, 14, 0)], 1.5, 1.1, 'tail')
        muz = Ell((17, 13.8, 0), (1.9, 1.6, 2.6), 'muzzle')
        ears = [(12, 19, 2.9), (12, 19, -2.9)]
        ear_tip = 4.2
        eye = dict(az=0.5, el=0.12, aw=0.23, eh=0.28)
        b_rz = 4.8
    else:                     # old Tom: round, low, stubby, droopy tail
        body = Ell((0, 8.6, 0), (11, 7.0, 7.0), 'body')
        head = Ell((12.5, 13.5, 0), (5.8, 5.2, 6.2), 'head')
        legs_y, leg_r, paw_r = 4.5, 1.8, 2.0
        leg_x = (-6.5, 6.5)
        tail = chain([(-10, 7, 0), (-13.5, 4.5, 0), (-15.5, 2.0, 0), (-17.5, 1.6, 0)], 1.9, 1.7, 'tail')
        muz = Ell((17.3, 11.8, 0), (2.2, 1.9, 3.1), 'muzzle')
        ears = [(12, 17.5, 3.2), (12, 17.5, -3.2)]
        ear_tip = 2.9          # smaller, older ears
        eye = dict(az=0.5, el=0.14, aw=0.24, eh=0.12)   # sleepy half-lids
        b_rz = 7.0
    parts = [body, head, muz]
    nose = Ell(add(muz.c, (muz.r[0] - 0.2, 1.2, 0)), (0.8, 0.6, 0.9), 'nose')
    parts.append(nose)
    for lx in leg_x:
        for lz in (b_rz * 0.55, -b_rz * 0.55):
            parts += chain([(lx, legs_y, lz), (lx + 0.3, paw_r, lz)], leg_r, leg_r, 'leg', steps=8)
            parts.append(Ell((lx + 0.7, paw_r, lz), (paw_r * 1.2, paw_r, paw_r), 'paw'))
    parts += tail
    for ex, ey, ez in ears:
        parts += chain([(ex, ey, ez), (ex + 0.4, ey + ear_tip, ez * 1.15)], 1.9, 0.35, 'ear', steps=10)
    return parts, body, head, muz, eye


def material(kind, part, p, n, body, head, muz, eye):
    """Pick a material name for a surface point."""
    tag = part.tag
    if tag == 'nose':
        return 'nose'
    if tag == 'muzzle':
        if kind == 'tom' and (int(p[2] * 2.3) + int(p[1] * 2.1)) % 3 == 0:
            return 'grey'
        return 'light'
    if tag == 'head':
        q = sub(p, head.c)
        az, el = math.atan2(q[2], q[0]), math.asin(max(-1, min(1, q[1] / math.sqrt(dot(q, q)))))
        for s in (1, -1):
            da, de = az - s * eye['az'], el - eye['el']
            if abs(da) < eye['aw'] and abs(de) < eye['eh']:
                if kind == 'tom':
                    return 'pupil'
                return 'pupil' if abs(da) < eye['aw'] * 0.45 else 'iris'
            if kind == 'tom' and abs(da) < eye['aw'] * 1.2 and 0 < de - eye['eh'] < 0.12:
                return 'stripe'                                      # heavy lids
        if q[0] > 0 and q[1] < -0.5:
            return 'light'                                           # cheeks/chin
        # forehead "M"
        if q[1] > 1.6 and q[0] > -1:
            band = math.sin(q[2] * 2.2)
            if kind == 'ginger' and band > 0.35: return 'stripe'
            if kind == 'smoke' and band > 0.7: return 'stripe'
            if kind == 'tom' and band > 0.25: return 'stripe'
        if kind == 'tom' and q[1] > 2.5 and abs(q[2]) > 3.6:
            return 'grey'
        return 'base'
    if tag == 'ear':
        return 'ear' if n[0] > 0.45 and part.t < 0.8 else 'base'
    if tag == 'paw':
        return 'light'
    if tag == 'leg':
        if p[1] < 3.2 and kind != 'tom':
            return 'light'
        if kind in ('ginger', 'tom') and math.sin(p[1] * 1.6) > 0.65:
            return 'stripe'
        return 'base'
    if tag == 'tail':
        if kind == 'ginger' and math.sin(part.t * 24) > 0.25: return 'stripe'
        if kind == 'smoke' and math.sin(part.t * 20) > 0.7: return 'stripe'
        if kind == 'tom' and math.sin(part.t * 14) > 0.15: return 'stripe'
        if kind == 'ginger' and part.t > 0.9: return 'light'
        return 'base'
    if tag == 'body':
        q = sub(p, body.c)
        lx, ly, lz = q[0] / body.r[0], q[1] / body.r[1], q[2] / body.r[2]
        if ly < -0.45 or (lx > 0.72 and ly < 0.35):
            return 'light'
        if kind == 'ginger' and ly > -0.25 and math.sin(lx * 15 + ly * 3) > 0.45:
            return 'stripe'
        if kind == 'smoke' and ly > -0.15 and math.sin(lx * 15 + ly * 3) > 0.78:
            return 'stripe'
        if kind == 'tom' and ly > -0.4:
            if abs(lz) < 0.35 and ly > 0.75:
                return 'stripe'                                      # spine line
            r = math.sqrt((lx + 0.1) ** 2 * 1.6 + (ly + 0.05) ** 2)
            if math.sin(r * 11) > 0.35:
                return 'stripe'                                      # classic swirl
        return 'base'
    return 'base'


PALETTES = {
    'ginger': dict(base='#ee9a4c', stripe='#c25f28', light='#fbe4c6', iris='#7aa83c', pupil='#26202e', nose='#e8798a', ear='#f2a2ad'),
    'smoke':  dict(base='#5a5e6b', stripe='#6c707e', light='#a9adba', iris='#cbdc3e', pupil='#17181f', nose='#b97a86', ear='#a98692'),
    'tom':    dict(base='#a8855d', stripe='#5d4330', light='#ece2ce', iris='#b8902e', pupil='#2a2230', nose='#c47f7a', ear='#c99a90', grey='#d9d4cb'),
}
BLOCK = dict(grass='#7fbf5a', dirt='#9a6a44')


def render(kind, size=(96, 84)):
    pal = PALETTES[kind]
    ramps = {k: ramp(v) for k, v in {**pal, **BLOCK}.items()}
    parts, body, head, muz, eye = model(kind)
    block = Box((-20, -5, -11), (21, 0, 11))
    cat_shadow = (body.c[0] + 2, body.r[0] + 4, body.r[2] + 2.5)

    Wd, Ht = size
    centre = (0, 6, 0)
    buf = [[None] * Wd for _ in range(Ht)]
    for j in range(Ht):
        for i in range(Wd):
            u, v = (i - Wd / 2 + 0.5) * PIX, (Ht / 2 - j - 0.5) * PIX
            o = add(add(add(centre, mul(RIGHT, u)), mul(UP, v)), mul(V, 200))
            best = None
            oc, dc = roty(o, TURN), roty(F, TURN)       # ray in cat space
            for part in parts:
                h = part.hit(oc, dc)
                if h and (best is None or h[0] < best[0]):
                    best = (h[0], h[1], roty(h[2], -TURN), part)
            h = block.hit(o, F)
            if h and (best is None or h[0] < best[0]):
                best = (h[0], h[1], h[2], block)
            if not best:
                continue
            t, p, n, part = best
            lam = max(0.0, dot(n, LIGHT))
            if part is block:
                if n[1] > 0.5:
                    mat = 'grass'
                    lvl = 3 if lam > 0.5 else 2
                    # cat's shadow on the grass
                    pc = roty(p, TURN)
                    sx = (pc[0] - cat_shadow[0]) / cat_shadow[1]
                    sz = pc[2] / cat_shadow[2]
                    if sx * sx + sz * sz < 1:
                        lvl -= 2
                    elif (int(p[0] * 1.7) * 7 + int(p[2] * 1.7) * 13) % 11 == 0:
                        lvl += 1                                      # grass flecks
                else:
                    mat = 'grass' if p[1] > -1.3 else 'dirt'
                    lvl = 2 if lam > 0.35 else 1
                    if mat == 'dirt' and (int(p[0] * 1.3) * 5 + int(p[1] * 1.3) * 3 + int(p[2] * 1.3) * 7) % 9 == 0:
                        lvl -= 1
                buf[j][i] = dict(mat=mat, lvl=max(0, min(4, lvl)), t=t, cat=False, tag='block')
                continue
            mat = material(kind, part, p, n, body, head, muz, eye)
            lvl = 0 if lam < 0.15 else 1 if lam < 0.38 else 2 if lam < 0.72 else 3
            if lam > 0.93 and mat in ('base', 'light'):
                lvl = 4
            buf[j][i] = dict(mat=mat, lvl=lvl, t=t, cat=True, tag=part.tag)

    # internal contour lines where one part sits well in front of another
    for j in range(Ht):
        for i in range(Wd):
            c = buf[j][i]
            if not c or not c['cat']:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < Wd and 0 <= jj < Ht and buf[jj][ii] and buf[jj][ii]['cat']:
                    if c['t'] - buf[jj][ii]['t'] > 2.2 and c['mat'] not in ('pupil', 'iris'):
                        c['lvl'] = 0
                        break

    im = Image.new("RGBA", (Wd, Ht), (0, 0, 0, 0))
    px = im.load()
    for j in range(Ht):
        for i in range(Wd):
            c = buf[j][i]
            if c:
                col = ramps[c['mat']][c['lvl']]
                if c['mat'] in ('pupil', 'iris', 'nose'):
                    col = ramps[c['mat']][2] if c['lvl'] > 0 else ramps[c['mat']][1]
                px[i, j] = col

    # eye catchlights: top-left pixel of each eye blob
    seen = set()
    for j in range(Ht):
        for i in range(Wd):
            c = buf[j][i]
            if c and c['mat'] in ('pupil', 'iris') and kind != 'tom' and (i, j) not in seen:
                stack, blob = [(i, j)], []
                while stack:
                    a, b = stack.pop()
                    if (a, b) in seen or not (0 <= a < Wd and 0 <= b < Ht):
                        continue
                    cc = buf[b][a]
                    if not cc or cc['mat'] not in ('pupil', 'iris'):
                        continue
                    seen.add((a, b)); blob.append((a, b))
                    stack += [(a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)]
                a, b = min(blob, key=lambda q: (q[1], q[0]))
                px[a, b] = (255, 255, 255, 255)

    # coloured outlines: around the cat (over grass too) and around the block
    out = im.copy()
    op = out.load()
    for j in range(Ht):
        for i in range(Wd):
            c = buf[j][i]
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if not (0 <= ii < Wd and 0 <= jj < Ht):
                    continue
                nb = buf[jj][ii]
                if nb and nb['cat'] and (c is None or not c['cat']):
                    r, g, b, _ = ramps['base'][0]
                    op[i, j] = (int(r * 0.5), int(g * 0.45), int(b * 0.55), 255)
                    break
                if nb and not nb['cat'] and c is None:
                    r, g, b, _ = ramps[nb['mat']][0]
                    op[i, j] = (int(r * 0.55), int(g * 0.55), int(b * 0.6), 255)
                    break
    bbox = out.getbbox()
    return out.crop((bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1))


if __name__ == '__main__':
    S = 6
    names = [('ginger', 'Ginger'), ('smoke', 'Smoke'), ('tom', 'Old Tom')]
    sprites = []
    for k, label in names:
        im = render(k)
        im.save(f"{k}_iso_1x.png")
        sprites.append((im, label))
    cw = max(s.width for s, _ in sprites) * S
    ch = max(s.height for s, _ in sprites) * S
    sheet = Image.new("RGBA", (3 * cw + 4 * 24, ch + 70), (214, 228, 238, 255))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except Exception:
        f = ImageFont.load_default()
    for i, (im, label) in enumerate(sprites):
        big = im.resize((im.width * S, im.height * S), Image.NEAREST)
        x = 24 + i * (cw + 24)
        sheet.alpha_composite(big, (x + (cw - big.width) // 2, 10 + ch - big.height))
        d.text((x + cw // 2, ch + 42), label, fill=(55, 60, 70), font=f, anchor="mm")
    sheet.save("cat_lineup_iso.png")
