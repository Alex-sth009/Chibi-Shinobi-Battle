"""
stages.py - Battle backgrounds and platforms
============================================
Every stage is painted with code (no image files) once at load time and then
reused each frame. Platforms are one-way: jump up through them, hold Up+Down
to drop back down.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import math
import random

import pygame

from settings import GROUND_Y, SCREEN_H, SCREEN_W

STAGES = [
    {"id": "forest", "name": "Hidden Forest", "ambient": "leaf",
     "platforms": [(110, 365, 200), (650, 365, 200), (380, 270, 200)]},
    {"id": "village", "name": "Dusk Village", "ambient": "petal",
     "platforms": [(60, 360, 230), (670, 360, 230), (370, 262, 220)]},
    {"id": "falls", "name": "Twin Falls", "ambient": "mist",
     "platforms": [(40, 350, 180), (740, 350, 180), (400, 300, 160)]},
    {"id": "desert", "name": "Sand Canyon", "ambient": "sand",
     "platforms": [(180, 370, 160), (620, 370, 160), (400, 280, 160)]},
    {"id": "volcano", "name": "Volcano Rim", "ambient": "ember", "locked": True, "price": 250,
     "platforms": [(90, 360, 190), (680, 360, 190), (385, 265, 190)]},
]


def gradient(surf, top, bottom, rect=None):
    """Fill a surface with a smooth top-to-bottom colour fade (used for skies)."""
    rect = rect or surf.get_rect()
    for y in range(rect.height):
        k = y / max(1, rect.height - 1)
        col = [int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]
        pygame.draw.line(surf, col, (rect.x, rect.y + y), (rect.right, rect.y + y))


def _mountains(s, rng, color, base, amp, step=60):
    """Draw a jagged mountain silhouette across the background."""
    pts = [(0, SCREEN_H)]
    x = 0
    while x <= SCREEN_W + step:
        pts.append((x, base - rng.randint(0, amp)))
        x += step
    pts.append((SCREEN_W, SCREEN_H))
    pygame.draw.polygon(s, color, pts)


def paint_forest(s, rng):
    """Hidden Forest: blue sky, mountains, trees and a grassy floor."""
    gradient(s, (110, 180, 240), (215, 238, 250))
    _mountains(s, rng, (140, 170, 190), 300, 110, 90)
    _mountains(s, rng, (90, 140, 110), 380, 60, 50)
    for i in range(14):
        x = rng.randint(-20, SCREEN_W)
        h = rng.randint(160, 280)
        pygame.draw.rect(s, (90, 60, 40), (x, GROUND_Y - h, 18, h))
        for _ in range(4):
            pygame.draw.circle(s, rng.choice([(40, 110, 60), (50, 130, 70), (35, 95, 55)]),
                               (x + 9 + rng.randint(-35, 35), GROUND_Y - h + rng.randint(-20, 30)), rng.randint(30, 48))
    pygame.draw.rect(s, (85, 150, 65), (0, GROUND_Y, SCREEN_W, 14))
    pygame.draw.rect(s, (120, 90, 60), (0, GROUND_Y + 14, SCREEN_W, SCREEN_H))
    for i in range(0, SCREEN_W, 14):
        pygame.draw.line(s, (60, 125, 50), (i, GROUND_Y), (i + 5, GROUND_Y - 8), 2)
    return (150, 105, 65), (110, 75, 45)


def paint_village(s, rng):
    """Dusk Village: sunset sky, rooftops with lit windows and paper lanterns."""
    gradient(s, (80, 60, 130), (250, 160, 100))
    pygame.draw.circle(s, (255, 220, 150), (720, 200), 60)
    _mountains(s, rng, (110, 80, 120), 330, 80, 80)
    x = -30
    while x < SCREEN_W:
        w = rng.randint(90, 150)
        h = rng.randint(80, 150)
        top = GROUND_Y - h
        pygame.draw.rect(s, rng.choice([(170, 130, 100), (190, 150, 110), (150, 115, 90)]), (x, top, w, h))
        pygame.draw.polygon(s, (70, 45, 50), [(x - 14, top), (x + w + 14, top), (x + w - 8, top - 26), (x + 8, top - 26)])
        for wx in range(x + 14, x + w - 20, 32):
            pygame.draw.rect(s, (255, 210, 120), (wx, top + 22, 16, 18))
        pygame.draw.circle(s, (230, 60, 50), (x + w // 2, top + 6), 6)
        x += w + rng.randint(10, 30)
    pygame.draw.rect(s, (140, 125, 115), (0, GROUND_Y, SCREEN_W, SCREEN_H))
    for i in range(0, SCREEN_W, 40):
        pygame.draw.line(s, (110, 100, 95), (i, GROUND_Y), (i, SCREEN_H), 2)
    pygame.draw.line(s, (100, 90, 85), (0, GROUND_Y), (SCREEN_W, GROUND_Y), 3)
    return (130, 80, 55), (90, 55, 40)


def paint_falls(s, rng):
    """Twin Falls: grey cliffs either side with a waterfall in the middle."""
    gradient(s, (140, 195, 235), (220, 240, 250))
    pygame.draw.polygon(s, (120, 120, 130), [(0, 80), (260, 140), (300, SCREEN_H), (0, SCREEN_H)])
    pygame.draw.polygon(s, (120, 120, 130), [(SCREEN_W, 80), (SCREEN_W - 260, 140), (SCREEN_W - 300, SCREEN_H), (SCREEN_W, SCREEN_H)])
    pygame.draw.polygon(s, (95, 95, 105), [(0, 200), (180, 230), (220, SCREEN_H), (0, SCREEN_H)])
    pygame.draw.polygon(s, (95, 95, 105), [(SCREEN_W, 200), (SCREEN_W - 180, 230), (SCREEN_W - 220, SCREEN_H), (SCREEN_W, SCREEN_H)])
    pygame.draw.rect(s, (150, 200, 240), (300, 120, 360, GROUND_Y - 120))
    pygame.draw.rect(s, (120, 170, 220), (0, GROUND_Y - 10, SCREEN_W, 30))
    pygame.draw.rect(s, (110, 105, 100), (0, GROUND_Y, SCREEN_W, SCREEN_H))
    for i in range(30):
        pygame.draw.circle(s, (130, 125, 120), (rng.randint(0, SCREEN_W), rng.randint(GROUND_Y + 10, SCREEN_H)), rng.randint(4, 12))
    return (125, 120, 120), (85, 80, 85)


def paint_desert(s, rng):
    """Sand Canyon: hot sky, dunes and rock mesas."""
    gradient(s, (240, 170, 100), (250, 220, 160))
    pygame.draw.circle(s, (255, 245, 200), (200, 120), 45)
    for i in range(4):
        pygame.draw.ellipse(s, (220, 170, 110), (rng.randint(-200, SCREEN_W), 330 + i * 20, 600, 200))
    for x in (120, 700):
        pygame.draw.polygon(s, (180, 110, 70), [(x, GROUND_Y), (x + 20, 230), (x + 140, 220), (x + 170, GROUND_Y)])
    pygame.draw.rect(s, (230, 190, 120), (0, GROUND_Y, SCREEN_W, SCREEN_H))
    for i in range(60):
        pygame.draw.circle(s, (210, 170, 100), (rng.randint(0, SCREEN_W), rng.randint(GROUND_Y + 4, SCREEN_H)), 2)
    return (200, 150, 90), (150, 100, 60)


def paint_volcano(s, rng):
    """Volcano Rim: dark red sky, a smoking crater and lava cracks (shop unlock)."""
    gradient(s, (40, 15, 20), (170, 60, 30))
    pygame.draw.polygon(s, (50, 30, 30), [(200, GROUND_Y), (430, 150), (530, 150), (780, GROUND_Y)])
    pygame.draw.polygon(s, (255, 120, 30), [(440, 150), (520, 150), (500, 175), (460, 175)])
    _mountains(s, rng, (70, 35, 30), 400, 60, 70)
    pygame.draw.rect(s, (60, 40, 35), (0, GROUND_Y, SCREEN_W, SCREEN_H))
    for i in range(10):
        x = rng.randint(0, SCREEN_W)
        pygame.draw.line(s, (255, 110, 30), (x, GROUND_Y + 6), (x + rng.randint(-40, 40), SCREEN_H), 3)
    return (80, 60, 55), (50, 35, 30)


PAINTERS = {"forest": paint_forest, "village": paint_village, "falls": paint_falls,
            "desert": paint_desert, "volcano": paint_volcano}


def build_stage(defn):
    """Paint a stage once and return its background image plus platform rectangles."""
    rng = random.Random(defn["id"])
    bg = pygame.Surface((SCREEN_W, SCREEN_H))
    top_col, side_col = PAINTERS[defn["id"]](bg, rng)
    rects = []
    for (x, y, w) in defn["platforms"]:
        r = pygame.Rect(x, y, w, 12)
        rects.append(r)
        pygame.draw.rect(bg, side_col, (x, y, w, 14), border_radius=3)
        pygame.draw.rect(bg, top_col, (x, y, w, 7), border_radius=3)
        for px in range(x + 20, x + w, 34):
            pygame.draw.line(bg, side_col, (px, y + 1), (px, y + 12), 1)
        pygame.draw.rect(bg, side_col, (x + 12, y + 14, 6, 8))
        pygame.draw.rect(bg, side_col, (x + w - 18, y + 14, 6, 8))
    return {"id": defn["id"], "name": defn["name"], "bg": bg, "platforms": rects, "ambient": defn["ambient"]}


def draw_ambient(surf, stage, t):
    """Animated weather drawn every frame: leaves, petals, mist, sand or embers."""
    kind = stage["ambient"]
    if kind == "mist":
        for i in range(10):
            y = (120 + (t * 260 + i * 37) % (GROUND_Y - 120))
            pygame.draw.line(surf, (220, 240, 255), (310 + i * 34, y), (310 + i * 34, y + 30), 2)
        return
    colors = {"leaf": (70, 150, 60), "petal": (255, 180, 200), "sand": (230, 200, 140), "ember": (255, 140, 40)}
    col = colors.get(kind, (255, 255, 255))
    for i in range(18):
        sp = 30 + (i * 13) % 40
        x = (i * 97 + t * sp * (1 if kind != "sand" else 6)) % (SCREEN_W + 40) - 20
        if kind == "ember":
            y = SCREEN_H - ((i * 53 + t * sp * 1.5) % SCREEN_H)
        else:
            y = (i * 61 + t * sp) % SCREEN_H
        x += math.sin(t * 2 + i) * 12
        if kind == "sand":
            pygame.draw.circle(surf, col, (int(x), int(y)), 1)
        else:
            pygame.draw.ellipse(surf, col, (int(x), int(y), 6, 3))
