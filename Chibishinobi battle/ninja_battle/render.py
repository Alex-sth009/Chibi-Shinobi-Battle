"""
render.py - All the drawing: chibi ninjas, effects and HUD
==========================================================
The fighters are drawn from shapes (circles, polygons, lines) and posed by
angles, so no sprite art is required. Optional sprite sheets can be dropped
into assets/sprites/<character id>/<state>.png to replace the drawn chibis.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import math
import os
import random

import pygame

from settings import (ASSET_DIR, CHAKRA_COLOR, GROUND_Y, MAX_CHAKRA, MAX_HP, P1_COLOR, P2_COLOR,
                      SCREEN_H, SCREEN_W, WHITE)

_fonts = {}
RS = 1.3   # render scale of fighters on the battlefield (bigger = larger chibis)


def font(size, bold=True):
    """Cached font lookup (creating fonts every frame would be slow)."""
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _fonts[key]


def text(surf, msg, size, color, pos, center=False, shadow=True, right=False, bold=True):
    """Draw text with a drop shadow, aligned left, right or centred."""
    f = font(size, bold)
    img = f.render(str(msg), True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    if shadow:
        sh = f.render(str(msg), True, (0, 0, 0))
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def outline_text(surf, msg, size, color, pos, outline=(0, 0, 0)):
    """Draw text with a thick black outline - used for big impact messages."""
    f = font(size)
    base = f.render(msg, True, color)
    ol = f.render(msg, True, outline)
    r = base.get_rect(center=pos)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
        surf.blit(ol, (r.x + dx, r.y + dy))
    surf.blit(base, r)


def darker(c, k=0.7):
    """Return a darker version of a colour, for shading."""
    return tuple(max(0, int(v * k)) for v in c[:3])


# ======================================================================
#  Optional sprite sheets
# ======================================================================
class SpriteBank:
    """Optional sprite-sheet support: if assets/sprites/<id>/<state>.png exists it
    is used instead of the drawn chibi. Sheets are horizontal strips of square
    frames facing right.
    """
    def __init__(self):
        self.cache = {}

    def _load(self, cid, state):
        key = (cid, state)
        if key in self.cache:
            return self.cache[key]
        path = os.path.join(ASSET_DIR, "sprites", cid, state + ".png")
        frames = None
        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path).convert_alpha()
                fh = sheet.get_height()
                n = max(1, sheet.get_width() // fh)
                frames = [sheet.subsurface((i * fh, 0, fh, fh)).copy() for i in range(n)]
            except pygame.error:
                frames = None
        self.cache[key] = frames
        return frames

    def frame(self, cid, state, t):
        """Pick the animation frame for this moment in time."""
        frames = self._load(cid, state) or self._load(cid, "idle")
        if not frames:
            return None
        return frames[int(t * 10) % len(frames)]


SPRITES = SpriteBank()


# ======================================================================
#  Procedural chibi
# ======================================================================
def _limb(s, start, angle, length, color, width, end_color=None, end_r=3):
    """Draw one arm or leg as a thick line at the given angle (0 = straight down,
    90 = pointing forwards), with a hand or foot at the end.
    """
    a = math.radians(angle)
    ex = start[0] + math.sin(a) * length
    ey = start[1] + math.cos(a) * length
    pygame.draw.line(s, color, start, (ex, ey), width)
    pygame.draw.circle(s, color, (int(start[0]), int(start[1])), width // 2)
    if end_color:
        pygame.draw.circle(s, end_color, (int(ex), int(ey)), end_r)
    return ex, ey


def _hair(s, pal, hx, hy, r, t):
    """Draw the character's hairstyle: messy, spiky, swept, bob, long or topknot."""
    hair = pal["hair"]
    style = pal.get("hair_style", "short")
    dark = darker(hair, 0.75)
    if style == "long":
        pygame.draw.polygon(s, dark, [(hx - r + 2, hy - 4), (hx + 2, hy - 6), (hx - 2, hy + 34), (hx - r - 6, hy + 30)])
    if style == "bob":
        pygame.draw.polygon(s, dark, [(hx - r - 2, hy - 2), (hx + 4, hy - 2), (hx + 2, hy + 14), (hx - r - 3, hy + 13)])
    # cap
    pygame.draw.circle(s, hair, (int(hx - 1), int(hy - 2)), r + 1)
    if style == "messy":
        for i in range(7):
            a = math.radians(150 + i * 32)
            rr = r + (8 if i % 2 == 0 else 4)
            b1 = math.radians(150 + i * 32 - 16)
            b2 = math.radians(150 + i * 32 + 16)
            pygame.draw.polygon(s, hair, [(hx + math.cos(b1) * (r - 2), hy + math.sin(b1) * (r - 2)),
                                          (hx + math.cos(a) * rr, hy + math.sin(a) * rr),
                                          (hx + math.cos(b2) * (r - 2), hy + math.sin(b2) * (r - 2))])
    elif style == "spiky":
        for i in range(5):
            a = math.radians(190 + i * 30)
            b1, b2 = a - 0.25, a + 0.25
            pygame.draw.polygon(s, hair, [(hx + math.cos(b1) * r, hy + math.sin(b1) * r),
                                          (hx + math.cos(a) * (r + 10), hy + math.sin(a) * (r + 10)),
                                          (hx + math.cos(b2) * r, hy + math.sin(b2) * r)])
    elif style == "swept":
        pygame.draw.polygon(s, hair, [(hx + 8, hy - r), (hx - r - 14, hy - 8), (hx - r + 2, hy + 4)])
        pygame.draw.polygon(s, hair, [(hx, hy - r + 2), (hx - r - 10, hy + 6), (hx - r + 4, hy + 10)])
    elif style == "topknot":
        pygame.draw.circle(s, hair, (int(hx - 2), int(hy - r - 5)), 7)
        pygame.draw.circle(s, dark, (int(hx - 2), int(hy - r - 5)), 7, 2)


def _face(s, pal, hx, hy, r, eyes, mouth, t, eye_glow=None):
    """Draw the face: headband or bandana, eyes (open, blinking, hurt or KO'd),
    mouth and cheek blush.
    """
    pygame.draw.circle(s, pal["skin"], (int(hx + 3), int(hy + 3)), r - 2)
    style = pal.get("hair_style")
    # bangs
    hair = pal["hair"]
    if style in ("messy", "spiky", "bob", "long", "short", "topknot"):
        pygame.draw.polygon(s, hair, [(hx - 4, hy - r + 2), (hx + r, hy - 8), (hx + r - 2, hy - 2), (hx + 6, hy - 6), (hx + 2, hy - 1)])
    # headband / bandana
    if style == "bandana":
        pygame.draw.polygon(s, pal["accent"], [(hx - r, hy - 5), (hx + r, hy - 7), (hx + r - 1, hy - 14), (hx - r + 2, hy - r + 3)])
        pygame.draw.line(s, pal["accent"], (hx - r, hy - 6), (hx - r - 10, hy + 2 + math.sin(t * 8) * 2), 4)
    else:
        pygame.draw.rect(s, pal["accent"], (hx - r + 1, hy - 9, 2 * r - 1, 5))
        pygame.draw.rect(s, (190, 195, 205), (hx + 1, hy - 10, 11, 7), border_radius=2)
        pygame.draw.line(s, (130, 135, 150), (hx + 3, hy - 7), (hx + 10, hy - 7), 1)
        tail_y = hy - 7
        pygame.draw.line(s, pal["accent"], (hx - r + 1, tail_y), (hx - r - 9, tail_y + 4 + math.sin(t * 7) * 3), 3)
        pygame.draw.line(s, pal["accent"], (hx - r + 1, tail_y + 2), (hx - r - 7, tail_y + 10 + math.sin(t * 7 + 1) * 3), 3)
    # eyes
    ex1, ex2, ey = hx + 3, hx + 11, hy + 2
    if eyes == "x":
        for ex in (ex1, ex2):
            pygame.draw.line(s, (40, 40, 40), (ex - 2, ey - 2), (ex + 2, ey + 2), 2)
            pygame.draw.line(s, (40, 40, 40), (ex - 2, ey + 2), (ex + 2, ey - 2), 2)
    elif eyes == "hurt" or eyes == "closed" or (t % 3.4) < 0.1:
        for ex in (ex1, ex2):
            pygame.draw.line(s, (40, 40, 40), (ex - 2, ey), (ex + 2, ey + (1 if eyes == "hurt" else 0)), 2)
    else:
        for ex in (ex1, ex2):
            pygame.draw.ellipse(s, WHITE, (ex - 3, ey - 4, 6, 8))
            pygame.draw.ellipse(s, eye_glow or pal["eye"], (ex - 1, ey - 3, 4, 6))
            pygame.draw.circle(s, WHITE, (ex, ey - 2), 1)
    # mouth
    if mouth == "open":
        pygame.draw.circle(s, (120, 40, 40), (int(hx + 9), int(hy + 10)), 2)
    elif mouth == "smile":
        pygame.draw.lines(s, (90, 45, 45), False, [(hx + 6, hy + 9), (hx + 9, hy + 11), (hx + 12, hy + 9)], 1)
    else:
        pygame.draw.line(s, (90, 50, 50), (hx + 7, hy + 10), (hx + 11, hy + 10), 1)
    pygame.draw.circle(s, (250, 170, 160), (int(hx + 13), int(hy + 7)), 2)


def _outlined(src, color=(22, 18, 30, 240), thickness=2):
    """Cartoon ink outline around a sprite (makes the chibis pop off the stage)."""
    try:
        mask = pygame.mask.from_surface(src)
        ink = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    except (pygame.error, ValueError):
        return src
    p = thickness
    out = pygame.Surface((src.get_width() + p * 2, src.get_height() + p * 2), pygame.SRCALPHA)
    for dx, dy in ((0, p), (p * 2, p), (p, 0), (p, p * 2), (0, 0), (p * 2, 0), (0, p * 2), (p * 2, p * 2)):
        out.blit(ink, (dx, dy))
    out.blit(src, (p, p))
    return out


def draw_chibi(surf, x, y, facing, pal, pose, t=0.0, scale=1.0, alpha=255, flash=False, eye_glow=None,
               outline=True, squash=(1.0, 1.0)):
    """Draws a chibi ninja with feet at (x, y)."""
    size = pal.get("size", 1.0)
    S = pygame.Surface((110, 120), pygame.SRCALPHA)
    fx, fy = 55, 108
    crouch = pose.get("crouch", 0)
    lean = pose.get("lean", 0)
    bob = pose.get("bob", 0)
    bw = 15 * size
    hip = (fx + lean * 0.3, fy - 14 + crouch)
    neck = (fx + lean, fy - 36 * (0.9 + 0.1 * size) + crouch + bob)
    outfit, dark, pants = pal["outfit"], pal["outfit_dark"], pal["pants"]
    skin = pal["skin"]
    sandal = (45, 50, 70)
    shoulder_b = (neck[0] - 3, neck[1] + 5)
    shoulder_f = (neck[0] + 3, neck[1] + 5)

    # back limbs
    _limb(S, shoulder_b, pose.get("back_arm", -15), 12, darker(outfit, 0.8), 5, darker(skin, 0.9), 3)
    _limb(S, (hip[0] - 3, hip[1]), pose.get("back_leg", -6), 13, darker(pants, 0.8), 6, sandal, 3)
    # body
    body = [(neck[0] - bw / 2, neck[1]), (neck[0] + bw / 2, neck[1]), (hip[0] + bw / 2, hip[1] + 2), (hip[0] - bw / 2, hip[1] + 2)]
    pygame.draw.polygon(S, outfit, body)
    shade = [(neck[0], neck[1]), (neck[0] + bw / 2, neck[1]), (hip[0] + bw / 2, hip[1] + 2), (hip[0], hip[1] + 2)]
    pygame.draw.polygon(S, darker(outfit, 0.86), shade)
    if size > 1.1:
        pygame.draw.circle(S, outfit, (int(hip[0] + 2), int(hip[1] - 8)), int(bw * 0.62))
    pygame.draw.polygon(S, dark, [(neck[0] - 3, neck[1]), (neck[0] + 5, neck[1]), (neck[0] + 1, neck[1] + 9)])
    pygame.draw.line(S, pal["accent"], (hip[0] - bw / 2, hip[1] - 3), (hip[0] + bw / 2, hip[1] - 3), 3)
    pygame.draw.rect(S, dark, (hip[0] - bw / 2 - 2, hip[1] - 6, 6, 7), border_radius=2)  # pouch
    # front leg
    _limb(S, (hip[0] + 3, hip[1]), pose.get("front_leg", 6), 13, pants, 6, sandal, 3)
    # head
    r = 15
    hx, hy = neck[0] + 1, neck[1] - 12
    _hair(S, pal, hx, hy, r, t)
    _face(S, pal, hx, hy, r, pose.get("eyes", "open"), pose.get("mouth", "line"), t, eye_glow)
    # front arm
    hand = _limb(S, shoulder_f, pose.get("front_arm", 15), 12, outfit, 5, skin, 3)
    if pose.get("seal"):
        pygame.draw.circle(S, pal.get("chakra", CHAKRA_COLOR), (int(hand[0]), int(hand[1])), 5, 1)

    if facing < 0:
        S = pygame.transform.flip(S, True, False)
    rot = pose.get("rot", 0) * (1 if facing > 0 else -1)
    if rot or scale != 1.0:
        S2 = pygame.transform.rotozoom(S, rot, scale)
    else:
        S2 = S
    sqx, sqy = squash
    if sqx != 1.0 or sqy != 1.0:
        S2 = pygame.transform.smoothscale(S2, (max(1, int(S2.get_width() * sqx)),
                                               max(1, int(S2.get_height() * sqy))))
    if outline:
        S2 = _outlined(S2)
    if flash:
        S2 = S2.copy()
        S2.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)
    if alpha < 255:
        S2 = S2.copy()
        S2.set_alpha(alpha)
    # feet offset from centre, rotated with the sprite
    ox, oy = 0, (fy - 60) * scale * sqy
    th = math.radians(rot)
    rx = ox * math.cos(th) + oy * math.sin(th)
    ry = -ox * math.sin(th) + oy * math.cos(th)
    rect = S2.get_rect(center=(x - rx, y - ry))
    surf.blit(S2, rect)


def draw_pup(surf, x, y, facing, t, scale=1.0, running=False, rot=0):
    """Draw the ninja pup companion."""
    S = pygame.Surface((60, 40), pygame.SRCALPHA)
    body, dark = (40, 40, 48), (25, 25, 30)
    leg = math.sin(t * 20) * 5 if running else 0
    for lx, ph in ((18, 1), (38, -1)):
        pygame.draw.line(S, dark, (lx, 26), (lx + leg * ph, 36), 4)
    pygame.draw.ellipse(S, body, (10, 14, 34, 16))
    pygame.draw.line(S, body, (12, 18), (4, 10 + math.sin(t * 12) * 3), 4)
    pygame.draw.circle(S, body, (44, 14), 9)
    pygame.draw.polygon(S, body, [(38, 8), (41, -1), (45, 7)])
    pygame.draw.polygon(S, body, [(44, 7), (49, 0), (50, 9)])
    pygame.draw.ellipse(S, (230, 230, 230), (46, 14, 10, 6))
    pygame.draw.circle(S, (255, 220, 60), (47, 12), 2)
    pygame.draw.circle(S, (0, 0, 0), (55, 15), 2)
    pygame.draw.line(S, (220, 60, 60), (22, 14), (34, 12), 2)  # collar
    if facing < 0:
        S = pygame.transform.flip(S, True, False)
    if scale != 1 or rot:
        S = pygame.transform.rotozoom(S, rot, scale)
    surf.blit(S, S.get_rect(midbottom=(x, y + 2)))


def draw_ball(surf, x, y, r, pal, t, facing):
    """Draw a fighter rolled up as a spinning boulder."""
    cx, cy = int(x), int(y - r)
    pygame.draw.circle(surf, pal["outfit"], (cx, cy), int(r))
    ang = t * 14 * facing
    for i in range(3):
        a = ang + i * math.tau / 3
        pygame.draw.line(surf, pal["outfit_dark"], (cx, cy), (cx + math.cos(a) * r, cy + math.sin(a) * r), max(2, int(r / 6)))
        pygame.draw.circle(surf, pal["hair"], (int(cx + math.cos(a + 1) * r * 0.7), int(cy + math.sin(a + 1) * r * 0.7)), max(3, int(r / 5)))
    pygame.draw.circle(surf, darker(pal["outfit"], 0.6), (cx, cy), int(r), 3)
    for i in range(3):
        pygame.draw.line(surf, (230, 230, 230), (cx - facing * (r + 6 + i * 8), cy - r / 2 + i * r / 2),
                         (cx - facing * (r + 20 + i * 8), cy - r / 2 + i * r / 2), 2)


def draw_drill(surf, x, y, facing, pal, t, scale=1.0, tint=None):
    """Draw the spinning drill used by the fang jutsu."""
    L, W = 64 * scale, 38 * scale
    cy = y - 26 * scale
    col = tint or pal["outfit"]
    tip = (x + facing * L * 0.55, cy)
    back = x - facing * L * 0.45
    pygame.draw.polygon(surf, col, [tip, (back, cy - W / 2), (back, cy + W / 2)])
    for i in range(5):
        k = ((t * 6 + i / 5) % 1.0)
        px = back + facing * L * k
        hw = (W / 2) * (1 - k)
        pygame.draw.line(surf, (240, 240, 240) if i % 2 else darker(col, 0.6), (px, cy - hw), (px + facing * 10 * scale, cy + hw), max(2, int(3 * scale)))
    pygame.draw.circle(surf, pal["hair"], (int(back + facing * 8), int(cy)), int(7 * scale))


def pose_for(f, t):
    """Turn a fighter's current state into limb angles - this is the animation."""
    s = f.state
    at = f.anim_t
    p = {"back_arm": -12, "front_arm": 12, "back_leg": -6, "front_leg": 6, "lean": 0, "crouch": 0, "bob": 0,
         "eyes": "open", "mouth": "line", "rot": 0}
    if s == "idle":
        p["bob"] = math.sin(at * 4) * 1.2
    elif s == "walk":
        sw = math.sin(at * 10)
        p.update(front_leg=28 * sw, back_leg=-28 * sw, front_arm=-22 * sw, back_arm=22 * sw)
    elif s in ("run", "dash"):
        sw = math.sin(at * 17)
        p.update(front_leg=48 * sw, back_leg=-48 * sw, front_arm=-80, back_arm=-70, lean=7)
        if s == "dash":
            p.update(front_arm=92, mouth="open")
    elif s == "jump":
        if f.flip_t > 0:
            p["rot"] = (1 - f.flip_t / 0.45) * 360
            p.update(front_leg=40, back_leg=10, front_arm=-40, back_arm=-60, mouth="open")
            return p
        if f.vy < 0:
            p.update(front_leg=55, back_leg=-15, front_arm=-130, back_arm=-110)
        else:
            p.update(front_leg=25, back_leg=-25, front_arm=70, back_arm=-70)
    elif s == "attack":
        ap = f.attack_pose
        if ap == "punch":
            p.update(front_arm=95, back_arm=-35, lean=3, mouth="open")
        elif ap == "punch2":
            p.update(front_arm=-20, back_arm=95, lean=4, mouth="open", front_leg=20)
        elif ap == "kick":
            p.update(front_leg=95, back_leg=-10, back_arm=-50, front_arm=-30, lean=-4)
        elif ap == "kick2":
            p.update(front_leg=110, back_leg=-20, back_arm=-70, front_arm=-60, lean=-6, mouth="open")
        elif ap == "uppercut":
            p.update(front_arm=170, back_arm=-40, front_leg=-20, back_leg=20, mouth="open")
        elif ap == "palm":
            p.update(front_arm=90, back_arm=80, lean=5, mouth="open", seal=True)
        elif ap == "kick_up":
            p.update(front_leg=165, back_leg=-10, front_arm=-60, back_arm=-40, lean=-8)
        elif ap == "dive":
            p.update(front_leg=60, back_leg=-35, front_arm=-70, back_arm=-50)
    elif s == "air_attack":
        p.update(front_leg=60, back_leg=-35, front_arm=-70, back_arm=-50, mouth="open")
    elif s == "throw":
        p.update(front_arm=100 if f.state_t < 0.1 else 60, back_arm=-40, lean=2)
    elif s == "block":
        p.update(front_arm=115, back_arm=100, crouch=3, lean=-2, eyes="open")
    elif s == "charge":
        p.update(front_arm=55, back_arm=50, crouch=3 + math.sin(at * 20), seal=True, mouth="open")
    elif s == "cast":
        p.update(front_arm=60, back_arm=55, seal=True, bob=math.sin(at * 12))
    elif s == "hurt":
        p.update(lean=-6, front_arm=-50, back_arm=-70, eyes="hurt", mouth="open")
    elif s == "knockdown":
        p.update(eyes="hurt", mouth="open", front_arm=-150, back_arm=-120)
        p["rot"] = 90 if f.on_ground else (at * 900) % 360
    elif s == "ko":
        p.update(eyes="x", mouth="open", front_arm=-150, back_arm=-120)
        p["rot"] = 90 if f.on_ground else (at * 700) % 360
    elif s == "victory":
        p.update(front_arm=170, back_arm=-30, mouth="smile", bob=math.sin(at * 6) * 2)
    elif s in ("spin_kick", "spin"):
        p.update(front_leg=90 if s == "spin_kick" else 10, front_arm=90, back_arm=-90, flip=int(at * 18) % 2)
    elif s == "slam":
        p.update(front_arm=-150, back_arm=150, front_leg=40, back_leg=-40, mouth="open")
    return p


def floor_under(world, x, y):
    return world.floor_below(x, y) if world else GROUND_Y


def draw_fighter(surf, layer, f, t):
    """Draw one fighter with shadow, speed trails, squash-and-stretch and auras."""
    pal = f.char["palette"]
    # ground shadow
    fy = floor_under(f.world, f.x, f.y)
    dist = max(0, fy - f.y)
    sw = max(10, (32 - dist * 0.08) * f.scale * RS * pal.get("size", 1))
    pygame.draw.ellipse(layer, (0, 0, 0, 70), (f.x - sw / 2, fy - 5, sw, 10))

    # pet
    if pal.get("companion") == "pup" and f.pet_out <= 0 and f.hp > 0 and f.state not in ("drill", "bigdrill"):
        py = floor_under(f.world, f.pet_x, f.y)
        draw_pup(surf, f.pet_x, py if abs(py - f.y) < 4 else f.y, f.facing, t, 0.8 * RS, f.state in ("run", "walk"))

    if f.bound > 0:
        pygame.draw.ellipse(layer, (10, 10, 20, 150), (f.x - 30, f.y - 8, 60, 14))

    blink = f.invuln > 0 and int(t * 30) % 2 == 0 and f.state not in ("knockdown", "ko")
    alpha = 110 if blink else 255
    flash = f.hurt_flash > 0 or f.block_flash > 0
    # squash & stretch: stretch while rising, squash on landing
    sq = (1.0, 1.0)
    if f.land_t > 0 and f.on_ground:
        k = f.land_t / 0.14
        sq = (1 + 0.18 * k, 1 - 0.16 * k)
    elif not f.on_ground and f.vy < -250:
        sq = (0.93, 1.1)
    elif not f.on_ground and f.vy > 500:
        sq = (0.95, 1.07)
    eye_glow = (255, 200, 40) if f.has_buff("hawk") else ((230, 230, 255) if f.has_buff("sight") else None)
    s = f.state

    if s == "ball":
        for i in (2, 1):
            draw_ball(layer, f.x - f.facing * 16 * i, f.y, 22 * f.scale * pal.get("size", 1) * (1 - 0.08 * i),
                      pal, t, f.facing)
        draw_ball(surf, f.x, f.y, 22 * f.scale * pal.get("size", 1), pal, t, f.facing)
    elif s in ("drill", "bigdrill"):
        draw_drill(surf, f.x, f.y, f.facing, pal, t, f.scale * RS)
        if s == "bigdrill":
            draw_drill(surf, f.x - f.facing * 20, f.y + 10, f.facing, pal, t + 0.3, f.scale * RS * 0.8, (60, 60, 70))
    elif s == "top":
        wob = math.sin(t * 40) * 10
        draw_chibi(surf, f.x, f.y, f.facing if int(t * 16) % 2 else -f.facing, pal,
                   {"front_arm": 90, "back_arm": -90, "front_leg": 10, "back_leg": -10, "rot": wob, "mouth": "open"},
                   t, f.scale * RS, alpha, flash)
        for i in range(3):
            rr = pygame.Rect(0, 0, 70 * f.scale, 20 * f.scale)
            rr.center = (f.x, f.y - (10 + i * 25) * f.scale)
            pygame.draw.arc(surf, (240, 240, 240), rr, (t * 10 + i) % math.tau, (t * 10 + i) % math.tau + 2, 2)
    else:
        frame = SPRITES.frame(f.char["id"], s, f.anim_t)
        if frame is not None:
            h = int(80 * f.scale * RS * pal.get("size", 1))
            img = pygame.transform.smoothscale(frame, (h, h))
            if f.facing < 0:
                img = pygame.transform.flip(img, True, False)
            if alpha < 255:
                img.set_alpha(alpha)
            surf.blit(img, img.get_rect(midbottom=(f.x, f.y)))
        else:
            p = pose_for(f, t)
            facing = -f.facing if p.get("flip") else f.facing
            y = f.y - (10 if p["rot"] == 90 else 0)
            # speed trails
            if abs(f.vx) > 260 and f.hp > 0 and s not in ("knockdown", "ko"):
                for i in (2, 1):
                    draw_chibi(layer, f.x - f.facing * 13 * i, y, facing, pal, p, t, f.scale * RS,
                               int(70 / i), False, eye_glow, outline=False, squash=sq)
            draw_chibi(surf, f.x, y, facing, pal, p, t, f.scale * RS, alpha, flash, eye_glow, squash=sq)

    # auras
    col = pal.get("chakra", CHAKRA_COLOR)
    if s == "charge":
        for i in range(6):
            a = t * 6 + i
            h = 50 + math.sin(a * 3) * 10
            pts = [(f.x - 22 + i * 9, f.y), (f.x - 18 + i * 9 + math.sin(a) * 5, f.y - h), (f.x - 14 + i * 9, f.y)]
            pygame.draw.polygon(layer, (*col, 90), pts)
    if f.has_buff("focus") or f.has_buff("gate"):
        c2 = (255, 90, 60, 80)
        for i in range(4):
            yy = f.y - 10 - ((t * 120 + i * 15) % 60)
            pygame.draw.line(layer, c2, (f.x - 16 + i * 10, yy), (f.x - 16 + i * 10, yy - 12), 3)
    if f.has_buff("meditate"):
        pygame.draw.circle(layer, (200, 200, 255, 60), (int(f.x), int(f.y - 30)), 34, 3)


def draw_summon(surf, layer, sm, t):
    """Draw a shadow clone, drill clone or ninja pup."""
    pal = sm.palette
    if sm.kind == "pup":
        draw_pup(surf, sm.x, sm.y, sm.facing, t, sm.scale * RS, sm.state in ("run", "dive"),
                 rot=(-30 if sm.state == "dive" else 0))
        return
    if sm.kind == "clone_drill" or sm.state == "drill":
        draw_drill(surf, sm.x, sm.y, sm.facing, pal, t, sm.scale * RS)
        return
    poses = {
        "run": {"front_leg": 48 * math.sin(sm.t * 17), "back_leg": -48 * math.sin(sm.t * 17), "front_arm": -80, "back_arm": -70, "lean": 7},
        "punch": {"front_arm": 95, "back_arm": -35, "lean": 3, "mouth": "open"},
        "throw": {"front_arm": 100, "back_arm": -40},
        "idle": {"front_arm": 10, "back_arm": -10},
        "kick_up": {"front_leg": 165, "back_leg": -10, "front_arm": -60, "back_arm": -40, "lean": -8},
        "grab": {"front_arm": 95, "back_arm": 90, "lean": 3, "mouth": "open"},
        "dive": {"front_leg": 40, "back_leg": -20, "front_arm": 100, "back_arm": 90, "rot": -40, "mouth": "open"},
    }
    p = {"back_arm": -12, "front_arm": 12, "back_leg": -6, "front_leg": 6, "lean": 0, "crouch": 0, "bob": 0,
         "eyes": "open", "mouth": "line", "rot": 0}
    p.update(poses.get(sm.state, {}))
    draw_chibi(surf, sm.x, sm.y, sm.facing, pal, p, t, sm.scale * RS, 225)


def _star(surf, cx, cy, r, angle, color, inner=0.35, points=4):
    """Draw a pointed star shape (shuriken blades)."""
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = angle + i * math.pi / points
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(surf, color, pts)


def draw_kunai(surf, x, y, ang, scale=1.0, tag=False):
    """Draw a kunai knife rotated to match its flight direction."""
    c, s_ = math.cos(ang), math.sin(ang)

    def P(dx, dy):
        return (x + (dx * c - dy * s_) * scale, y + (dx * s_ + dy * c) * scale)
    pygame.draw.polygon(surf, (70, 75, 90), [P(12, 0), P(0, -4), P(-2, 0), P(0, 4)])
    pygame.draw.line(surf, (110, 70, 40), P(-2, 0), P(-9, 0), 3)
    pygame.draw.circle(surf, (70, 75, 90), [int(v) for v in P(-12, 0)], int(3 * scale), 1)
    if tag:
        pygame.draw.polygon(surf, (245, 240, 220), [P(-4, -2), P(-10, -2), P(-10, 8), P(-4, 8)])
        pygame.draw.line(surf, (220, 40, 40), P(-7, -1), P(-7, 7), 1)


def draw_projectile(surf, layer, p, t):
    """Draw a flying weapon or jutsu with its motion trail."""
    ang = math.atan2(p.vy, p.vx)
    if p.kind in ("kunai", "tagkunai", "shuriken", "star", "bigshuriken"):
        tl = 26 if p.kind != "bigshuriken" else 40
        col = (200, 225, 255, 90) if p.kind != "star" else (120, 200, 255, 120)
        pygame.draw.line(layer, col, (p.x, p.y), (p.x - p.vx * 0.035, p.y - p.vy * 0.035),
                         4 if p.kind == "bigshuriken" else 3)
        pygame.draw.line(layer, (255, 255, 255, 40), (p.x, p.y),
                         (p.x - p.vx * 0.06, p.y - p.vy * 0.06), 2)
    if p.kind == "kunai":
        draw_kunai(surf, p.x, p.y, ang)
    elif p.kind == "tagkunai":
        draw_kunai(surf, p.x, p.y, ang, 1.2, tag=True)
    elif p.kind in ("shuriken", "star"):
        if p.kind == "star":
            pygame.draw.circle(layer, (120, 200, 255, 90), (int(p.x), int(p.y)), 11)
        _star(surf, p.x, p.y, 9, math.radians(p.angle), (90, 95, 110))
        pygame.draw.circle(surf, (30, 30, 40), (int(p.x), int(p.y)), 2)
    elif p.kind == "bigshuriken":
        _star(surf, p.x, p.y, 24, math.radians(p.angle), (80, 85, 100), 0.3)
        _star(surf, p.x, p.y, 16, math.radians(p.angle), (120, 125, 140), 0.3)
        pygame.draw.circle(surf, (30, 30, 40), (int(p.x), int(p.y)), 5)
    elif p.kind in ("fire", "bigfire"):
        r = p.w / 2
        fl = math.sin(t * 40 + p.x) * r * 0.1
        pygame.draw.circle(layer, (255, 120, 20, 110), (int(p.x), int(p.y)), int(r * 1.3 + fl))
        pygame.draw.circle(surf, (255, 110, 30), (int(p.x), int(p.y)), int(r + fl))
        pygame.draw.circle(surf, (255, 200, 60), (int(p.x + p.vx * 0.01), int(p.y)), int(r * 0.6))
        pygame.draw.circle(surf, (255, 250, 200), (int(p.x + p.vx * 0.015), int(p.y)), int(r * 0.3))
    elif p.kind == "shadow":
        pygame.draw.ellipse(layer, (10, 10, 20, 200), (p.x - p.w / 2, p.y - 4, p.w, 10))
        pygame.draw.line(layer, (10, 10, 20, 150), (p.owner.x, p.owner.y - 2), (p.x, p.y), 5)


def draw_fx(surf, layer, fx, t):
    """Draw one visual effect. Each `kind` has its own look."""
    k = fx.progress
    kind = fx.kind
    if kind == "ring":
        r = int(10 + fx.kw.get("radius", 60) * k)
        col = fx.kw.get("color", (255, 255, 255))
        pygame.draw.ellipse(layer, (*col, int(200 * (1 - k))), (fx.x - r, fx.y - r * 0.3, r * 2, r * 0.6), 4)
    elif kind in ("burst", "burst_aura"):
        col = fx.kw.get("color", (255, 120, 80))
        r = int(10 + 50 * k)
        pygame.draw.circle(layer, (*col, int(160 * (1 - k))), (int(fx.x), int(fx.y)), r, 4)
        for i in range(8):
            a = i * math.pi / 4 + k
            pygame.draw.line(layer, (*col, int(200 * (1 - k))), (fx.x + math.cos(a) * r * 0.6, fx.y + math.sin(a) * r * 0.6),
                             (fx.x + math.cos(a) * r * 1.2, fx.y + math.sin(a) * r * 1.2), 3)
    elif kind == "lightning":
        for _ in range(4):
            pts = [(fx.x, fx.y)]
            for _ in range(5):
                pts.append((pts[-1][0] + random.uniform(-14, 14), pts[-1][1] + random.uniform(-14, 14)))
            pygame.draw.lines(surf, random.choice([(200, 230, 255), (120, 180, 255), WHITE]), False, pts, 2)
        pygame.draw.circle(layer, (150, 200, 255, 120), (int(fx.x), int(fx.y)), 14)
    elif kind in ("orb_charge", "orb_blast"):
        big = kind == "orb_blast"
        r = int((10 + 12 * k) if not big else (24 + 50 * k))
        a = 255 if not big else int(220 * (1 - k))
        pygame.draw.circle(layer, (100, 170, 255, min(200, a)), (int(fx.x), int(fx.y)), r)
        pygame.draw.circle(layer, (220, 240, 255, min(230, a)), (int(fx.x), int(fx.y)), max(2, r // 2))
        for i in range(3):
            aa = t * 14 + i * 2.1
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (int(fx.x), int(fx.y))
            pygame.draw.arc(layer, (255, 255, 255, min(230, a)), rect, aa, aa + 1.6, 2)
    elif kind in ("fist_glow", "palm_glow"):
        col = (120, 255, 150) if kind == "fist_glow" else (170, 210, 255)
        r = int(8 + 6 * math.sin(t * 30))
        pygame.draw.circle(layer, (*col, 150), (int(fx.x), int(fx.y)), r + 6)
        pygame.draw.circle(layer, (255, 255, 255, 180), (int(fx.x), int(fx.y)), max(2, r - 2))
    elif kind == "dome":
        r = 52
        pygame.draw.circle(layer, (150, 210, 255, 60), (int(fx.x), int(fx.y)), r)
        for i in range(4):
            aa = t * 16 + i * 1.57
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (int(fx.x), int(fx.y))
            pygame.draw.arc(layer, (230, 245, 255, 200), rect, aa, aa + 1.0, 3)
    elif kind == "shadow_link":
        o, tg = fx.kw["owner"], fx.kw["target"]
        pygame.draw.line(layer, (10, 10, 20, 190), (o.x, o.y - 2), (tg.x, tg.y - 2), 7)
        pygame.draw.ellipse(layer, (10, 10, 20, 190), (tg.x - 26, tg.y - 7, 52, 12))
    elif kind == "strangle":
        for i in range(5):
            yy = fx.y - 8 - i * 11
            w = 30 + math.sin(t * 10 + i) * 4
            pygame.draw.ellipse(layer, (10, 10, 20, 200), (fx.x - w / 2, yy - 4, w, 8), 3)
    elif kind == "heal":
        for i in range(6):
            a = t * 5 + i
            yy = fx.y - ((t * 60 + i * 12) % 60)
            pygame.draw.circle(layer, (120, 255, 150, 150), (int(fx.x + math.cos(a) * 18), int(yy)), 4)
        pygame.draw.circle(layer, (120, 255, 150, 50), (int(fx.x), int(fx.y - 28)), 32)
    elif kind == "explosion":
        r = int(12 + 60 * k)
        pygame.draw.circle(layer, (255, 140, 30, int(230 * (1 - k))), (int(fx.x), int(fx.y)), r)
        pygame.draw.circle(layer, (255, 230, 120, int(230 * (1 - k))), (int(fx.x), int(fx.y)), max(2, r // 2))
    elif kind == "impact":
        col = fx.kw.get("color", (255, 230, 160))
        small = fx.kw.get("small")
        n = 4 if small else 6
        R = (16 if small else 34) * (0.5 + k)
        a = int(235 * (1 - k))
        for i in range(n):
            ang = i * math.tau / n + fx.x * 0.01
            x2, y2 = fx.x + math.cos(ang) * R, fx.y + math.sin(ang) * R
            pygame.draw.line(layer, (*col, a), (fx.x, fx.y), (x2, y2), 3 if small else 4)
        pygame.draw.circle(layer, (255, 255, 255, a), (int(fx.x), int(fx.y)), int(R * 0.45))
        if not small:
            pygame.draw.circle(layer, (*col, a), (int(fx.x), int(fx.y)), int(R * 0.9), 3)
    elif kind == "crack":
        rng = random.Random(int(fx.x))
        for i in range(6):
            x = fx.x
            y = fx.y
            for _ in range(4):
                nx = x + rng.uniform(15, 30) * (1 if i % 2 else -1)
                ny = y + rng.uniform(-4, 8)
                pygame.draw.line(layer, (40, 30, 20, int(255 * (1 - k))), (x, y), (nx, ny), 3)
                x, y = nx, ny
    elif kind == "log":
        a = int(255 * min(1, (1 - k) * 2))
        S = pygame.Surface((24, 50), pygame.SRCALPHA)
        pygame.draw.rect(S, (140, 95, 55, a), (2, 4, 20, 44), border_radius=6)
        pygame.draw.ellipse(S, (190, 150, 100, a), (2, 0, 20, 10))
        pygame.draw.ellipse(S, (110, 75, 40, a), (7, 3, 10, 5), 1)
        surf.blit(S, S.get_rect(midbottom=(fx.x, fx.y)))
    elif kind == "banner":
        a = min(1, (1 - k) * 3)
        if a > 0:
            outline_text(surf, fx.kw["text"], 20, fx.kw.get("color", WHITE), (int(fx.x), int(fx.y - 20 * k)))


def draw_particle(layer, p):
    """Draw one particle (smoke, spark or glow)."""
    k = p.life / p.max_life
    if p.kind == "smoke":
        r = p.size * (1.6 - k * 0.6)
        pygame.draw.circle(layer, (*p.color, int(180 * k)), (int(p.x), int(p.y)), int(r))
    elif p.kind == "spark":
        pygame.draw.line(layer, (*p.color, 255), (p.x, p.y), (p.x - p.vx * 0.03, p.y - p.vy * 0.03), 2)
    elif p.kind == "glow":
        pygame.draw.circle(layer, (*p.color, int(200 * k)), (int(p.x), int(p.y)), max(1, int(p.size * k)))
    else:
        pygame.draw.circle(layer, (*p.color, int(255 * k)), (int(p.x), int(p.y)), max(1, int(p.size * k)))


_vignette = None
_tints = {}

# Gentle colour grade per stage (added to the frame - keep the numbers small!)
STAGE_TINT = {"forest": (4, 12, 6), "village": (16, 4, 14), "falls": (4, 10, 18),
              "desert": (18, 10, 0), "volcano": (22, 4, 0)}


def post_process(surf, world):
    """Soft edge vignette + stage colour grade + impact flash."""
    global _vignette
    if _vignette is None:
        v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        depth = 110
        for i in range(depth):
            k = 1 - i / depth
            a = int(95 * k ** 1.7)
            col = (0, 0, 14, a)
            pygame.draw.line(v, col, (0, i), (SCREEN_W, i))
            pygame.draw.line(v, col, (0, SCREEN_H - 1 - i), (SCREEN_W, SCREEN_H - 1 - i))
            pygame.draw.line(v, col, (i, 0), (i, SCREEN_H))
            pygame.draw.line(v, col, (SCREEN_W - 1 - i, 0), (SCREEN_W - 1 - i, SCREEN_H))
        _vignette = v
    sid = world.stage.get("id")
    if sid not in _tints:
        tint = pygame.Surface((SCREEN_W, SCREEN_H))
        tint.fill(STAGE_TINT.get(sid, (0, 0, 0)))
        _tints[sid] = tint
    surf.blit(_tints[sid], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    surf.blit(_vignette, (0, 0))
    if getattr(world, "flash", 0) > 0:
        fl = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fl.fill((255, 240, 210, int(120 * min(1.0, world.flash / 0.12))))
        surf.blit(fl, (0, 0))


def draw_world(surf, layer, world, t):
    """Draw a whole battle in the right order: ground effects, summons, fighters,
    projectiles, effects, particles and floating text.
    """
    layer.fill((0, 0, 0, 0))
    for pr in world.projectiles:
        if pr.kind == "shadow":
            draw_projectile(surf, layer, pr, t)
    for fx in world.fx:
        if fx.kind in ("shadow_link", "ring", "crack", "log"):
            draw_fx(surf, layer, fx, t)
    surf.blit(layer, (0, 0))
    layer.fill((0, 0, 0, 0))
    for sm in world.summons:
        draw_summon(surf, layer, sm, t)
    order = sorted(world.fighters, key=lambda f: 1 if f.move or f.state == "attack" else 0)
    for f in order:
        draw_fighter(surf, layer, f, t)
        if f.hp > 0:
            col = P1_COLOR if f.team == 1 else P2_COLOR
            top = (f.rect().top - 6) if f.state in ("ball", "top", "slam", "drill", "bigdrill") else f.y - 80 * RS * f.char["palette"].get("size", 1)
            pygame.draw.polygon(surf, col, [(f.x - 5, top - 8), (f.x + 5, top - 8), (f.x, top)])
            text(surf, f.label, 11, col, (f.x, top - 16), center=True)
    for pr in world.projectiles:
        if pr.kind != "shadow":
            draw_projectile(surf, layer, pr, t)
    for fx in world.fx:
        if fx.kind not in ("shadow_link", "ring", "crack", "log", "banner"):
            draw_fx(surf, layer, fx, t)
    for p in world.particles:
        draw_particle(layer, p)
    surf.blit(layer, (0, 0))
    for fx in world.fx:
        if fx.kind == "banner":
            draw_fx(surf, layer, fx, t)
    for ft in world.texts:
        a = ft.life / ft.max_life
        if a > 0.05:
            outline_text(surf, ft.text, ft.size, ft.color, (int(ft.x), int(ft.y)))


# ======================================================================
#  HUD
# ======================================================================
def draw_kunai_icon(surf, x, y):
    """Small kunai icon for the HUD counter."""
    draw_kunai(surf, x, y, -0.6, 1.1)


def draw_shuriken_icon(surf, x, y, t=0):
    """Small spinning shuriken icon for the HUD counter."""
    _star(surf, x, y, 8, t, (150, 155, 170))
    pygame.draw.circle(surf, (30, 30, 40), (x, y), 2)


def draw_scroll_icon(surf, x, y):
    """Small ninja-scroll icon for the HUD counter."""
    pygame.draw.rect(surf, (240, 225, 180), (x - 9, y - 6, 18, 12))
    pygame.draw.rect(surf, (200, 60, 50), (x - 11, y - 7, 4, 14), border_radius=2)
    pygame.draw.rect(surf, (200, 60, 50), (x + 7, y - 7, 4, 14), border_radius=2)
    pygame.draw.line(surf, (120, 90, 60), (x - 4, y - 2), (x + 4, y - 2), 1)
    pygame.draw.line(surf, (120, 90, 60), (x - 4, y + 2), (x + 3, y + 2), 1)


def _bar(surf, x, y, w, h, frac, color, back_frac=None, right=False):
    """Draw one HUD bar; `back_frac` is the yellow 'damage taken' trail."""
    pygame.draw.rect(surf, (15, 15, 22), (x - 2, y - 2, w + 4, h + 4), border_radius=4)
    pygame.draw.rect(surf, (50, 50, 60), (x, y, w, h), border_radius=3)
    if back_frac is not None and back_frac > frac:
        bw = int(w * back_frac)
        pygame.draw.rect(surf, (255, 220, 120), (x + (w - bw if right else 0), y, bw, h), border_radius=3)
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        pygame.draw.rect(surf, color, (x + (w - fw if right else 0), y, fw, h), border_radius=3)
        pygame.draw.rect(surf, tuple(min(255, c + 60) for c in color), (x + (w - fw if right else 0), y, fw, max(2, h // 3)), border_radius=3)


BUFF_NAMES = {"hawk": ("HAWK EYE", (255, 200, 60)), "sight": ("TRUE SIGHT", (170, 210, 255)),
              "meditate": ("MEDITATE", (200, 200, 255)), "focus": ("WILD FOCUS", (255, 130, 90)),
              "gate": ("GATE", (255, 90, 90))}


def draw_player_hud(surf, f, left, t, wins=0):
    """Top of the screen: portrait, name, health bar, chakra bar, buffs, round wins."""
    pal = f.char["palette"]
    col = P1_COLOR if left else P2_COLOR
    px = 12 if left else SCREEN_W - 58
    pygame.draw.rect(surf, (15, 15, 22), (px - 2, 8, 50, 50), border_radius=8)
    pygame.draw.rect(surf, col, (px, 10, 46, 46), border_radius=7)
    clip = surf.get_clip()
    surf.set_clip(pygame.Rect(px + 2, 12, 42, 42))
    draw_chibi(surf, px + 23, 92, 1 if left else -1, pal, {"eyes": "open", "mouth": "line"}, t, 1.25)
    surf.set_clip(clip)
    bx = 66 if left else SCREEN_W - 66 - 330
    name_pos = (bx, 4) if left else (bx + 330, 4)
    text(surf, f.char["name"], 14, WHITE, name_pos, right=not left)
    _bar(surf, bx, 22, 330, 16, f.hp / MAX_HP, (230, 60, 60) if f.hp > 30 else (255, 40, 40), f.hp_display / MAX_HP, right=not left)
    text(surf, f"{int(f.hp)}", 12, WHITE, (bx + 6, 23) if left else (bx + 324, 23), right=not left)
    _bar(surf, bx + (0 if left else 110), 43, 220, 9, f.chakra / MAX_CHAKRA, CHAKRA_COLOR, right=not left)
    text(surf, f"CHAKRA {int(f.chakra)}", 10, (200, 225, 255), (bx + 226, 42) if left else (bx + 104, 42), right=not left, shadow=True)
    # buffs
    x = bx if left else bx + 330
    for b, tl in f.buffs.items():
        name, bc = BUFF_NAMES.get(b, (b.upper(), WHITE))
        label = f"{name} {int(tl) + 1}"
        img = font(10).render(label, True, (20, 20, 20))
        w = img.get_width() + 10
        rx = x if left else x - w
        pygame.draw.rect(surf, bc, (rx, 57, w, 14), border_radius=6)
        surf.blit(img, (rx + 5, 58))
        x = x + w + 4 if left else x - w - 4
    # round wins
    for i in range(2):
        cx = (bx + 300 - i * 16) if left else (bx + 30 + i * 16)
        pygame.draw.circle(surf, (15, 15, 22), (cx, 64 if not f.buffs else 78), 6)
        if i < wins:
            pygame.draw.circle(surf, (255, 210, 60), (cx, 64 if not f.buffs else 78), 4)


def draw_inventory(surf, fighters, t):
    """Kunai / shuriken / scroll counters (bottom-left)."""
    h = 24 * len(fighters) + 8
    box = pygame.Surface((300, h), pygame.SRCALPHA)
    box.fill((10, 10, 20, 150))
    surf.blit(box, (8, SCREEN_H - h - 6))
    for i, f in enumerate(fighters):
        y = SCREEN_H - h + 4 + i * 24
        col = P1_COLOR if f.team == 1 else P2_COLOR
        text(surf, f.label, 13, col, (16, y + 2))
        draw_kunai_icon(surf, 66, y + 12)
        text(surf, f"x{f.kunai}", 13, WHITE, (80, y + 3))
        draw_shuriken_icon(surf, 136, y + 11, t * 3)
        text(surf, f"x{f.shuriken}", 13, WHITE, (148, y + 3))
        draw_scroll_icon(surf, 212, y + 11)
        text(surf, f"x{f.scrolls}", 13, WHITE, (226, y + 3))
