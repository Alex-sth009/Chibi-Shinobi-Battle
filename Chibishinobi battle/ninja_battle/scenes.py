"""
scenes.py - Menus, selection screens, battle and results
========================================================
The game is a simple state machine: one Scene is active at a time and each
Scene knows how to update itself and draw itself. Scenes swap by calling
game.change(NextScene(game)).

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

import history
import render
from ai import AIController
from characters import DUMMY, ROSTER, get_char
from controls import NullController
from fighter import Fighter
from settings import (ACTION_LABELS, ACTIONS, CHAKRA_CHARGE_RATE, DEFAULT_KEYS, DIFFICULTIES,
                      GROUND_Y, MAX_HP, P1_COLOR,
                      P2_COLOR, ROUND_TIME, ROUNDS_TO_WIN, SCREEN_H, SCREEN_W, UI_ACCENT, UI_DARK,
                      UI_PANEL, WHITE, AUTHOR, VERSION, save_save)
from stages import STAGES, build_stage, draw_ambient, gradient
from world import World

_bg_cache = {}


def menu_bg(surf, t):
    """Shared animated background for all the menu screens."""
    if "menu" not in _bg_cache:
        s = pygame.Surface((SCREEN_W, SCREEN_H))
        gradient(s, (30, 20, 60), (200, 90, 50))
        pygame.draw.circle(s, (255, 210, 140), (SCREEN_W - 170, 170), 90)
        rng = random.Random(3)
        pts = [(0, SCREEN_H)]
        for x in range(0, SCREEN_W + 60, 60):
            pts.append((x, 380 - rng.randint(0, 90)))
        pts.append((SCREEN_W, SCREEN_H))
        pygame.draw.polygon(s, (50, 30, 60), pts)
        pygame.draw.rect(s, (30, 20, 35), (0, 470, SCREEN_W, 80))
        _bg_cache["menu"] = s
    surf.blit(_bg_cache["menu"], (0, 0))
    for i in range(14):
        x = (i * 83 + t * (20 + i * 3)) % (SCREEN_W + 20) - 10
        y = (i * 47 + t * 25) % SCREEN_H
        pygame.draw.ellipse(surf, (255, 180, 200), (int(x), int(y), 6, 3))


def wrap(msg, size, width):
    """Split a long sentence into lines that fit inside a given width."""
    f = render.font(size, False)
    words, lines, cur = msg.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.size(test)[0] > width:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def nav(*ctrls):
    """Merge menu input from controllers -> set of 'up','down','left','right','ok','back'."""
    out = set()
    for c in ctrls:
        if c.p("up"):
            out.add("up")
        if c.p("down"):
            out.add("down")
        if c.p("left"):
            out.add("left")
        if c.p("right"):
            out.add("right")
        if c.p("attack"):
            out.add("ok")
        if c.p("throw"):
            out.add("back")
    return out


def is_unlocked(game, item):
    """Has this character or stage been bought in the Shop?"""
    return not item.get("locked") or item["id"] in game.save["unlocked"]


class Scene:
    """Base class for every screen. A scene updates itself and draws itself;
    the Game object keeps exactly one scene active at a time.
    """
    def __init__(self, game):
        self.game = game
        self.t = 0.0

    def handle_event(self, e):
        return False

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        pass

    def keys_ok(self):
        return self.game.enter_pressed

    def menu_input(self):
        """Menu commands from either player, plus the Enter key."""
        n = nav(self.game.c1, self.game.c2)
        if self.game.enter_pressed:
            n.add("ok")
        return n


# ======================================================================
class MainMenu(Scene):
    """Title screen with the mode list (Story/War/Game/Community are placeholders)."""
    ITEMS = [
        ("Story Mode", False, "Progress through the ninja world in a story/RPG mode or do unique missions to gain characters and maps!"),
        ("War Mode", False, "Attack other villages and defend your own while fighting alongside other ninjas!"),
        ("Battle Mode", True, "Battle your friends side by side with your unlocked characters (2 players)."),
        ("Versus Mode", True, "Battle the computer with your favourite characters."),
        ("Survival Mode", True, "Fight through mass amounts of enemies, earn coins and set a new highscore!"),
        ("Option Mode", True, "Set enemy difficulty, configure keys, and choose MP3 or MIDI music."),
        ("Training Mode", True, "Train your skills against a training dummy (infinite chakra)."),
        ("Game Mode", False, "Play exciting minigames without quitting the game!"),
        ("Shop Mode", True, "Unlock characters and stages using coins earned in Survival Mode!"),
        ("Community", False, "Visit the community website."),
        ("How to Play", True, "Controls, jutsu inputs and tips."),
        ("Quit", True, "Exit the game."),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.sel = 2
        self.popup = 0.0
        self.demo = [random.choice(ROSTER[:7]), random.choice(ROSTER[:7])]

    def update(self, dt):
        super().update(dt)
        self.popup = max(0.0, self.popup - dt)
        n = self.menu_input()
        if "up" in n:
            self.sel = (self.sel - 1) % len(self.ITEMS)
            self.game.audio.play("select")
        if "down" in n:
            self.sel = (self.sel + 1) % len(self.ITEMS)
            self.game.audio.play("select")
        if "ok" in n:
            name, avail, _ = self.ITEMS[self.sel]
            if not avail:
                self.popup = 1.6
                self.game.audio.play("block")
                return
            self.game.audio.play("confirm")
            g = self.game
            if name == "Battle Mode":
                g.change(StageSelect(g, "battle"))
            elif name == "Versus Mode":
                g.change(StageSelect(g, "versus"))
            elif name == "Survival Mode":
                g.change(StageSelect(g, "survival"))
            elif name == "Training Mode":
                g.change(StageSelect(g, "training"))
            elif name == "Option Mode":
                g.change(OptionsScene(g))
            elif name == "Shop Mode":
                g.change(ShopScene(g))
            elif name == "How to Play":
                g.change(HowToPlay(g))
            elif name == "Quit":
                g.running = False

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, "SHINOBI CLASH", 54, (255, 160, 40), (SCREEN_W // 2, 50))
        render.text(surf, "Chibi Ninja Battle", 18, (255, 230, 200), (SCREEN_W // 2, 92), center=True)
        # author credit - this game is the work of the author named in settings.py
        render.text(surf, f"An original game created by {AUTHOR}  -  v{VERSION}", 12, (255, 200, 150),
                    (SCREEN_W // 2, SCREEN_H - 84), center=True, bold=False)
        # demo chibis
        for i, ch in enumerate(self.demo):
            x = 120 if i == 0 else SCREEN_W - 120
            pose = {"front_arm": 170 if int(self.t) % 4 == i * 2 else 12, "back_arm": -12, "bob": math.sin(self.t * 4 + i) * 2,
                    "mouth": "smile"}
            render.draw_chibi(surf, x, 460, 1 if i == 0 else -1, ch["palette"], pose, self.t, 2.2)
        y0 = 118
        for i, (name, avail, _) in enumerate(self.ITEMS):
            y = y0 + i * 27
            selected = i == self.sel
            rect = pygame.Rect(SCREEN_W // 2 - 150, y, 300, 24)
            pygame.draw.rect(surf, UI_ACCENT if selected else (25, 25, 40), rect, border_radius=8)
            label = name + ("" if avail else "  (Unavailable)")
            col = (20, 20, 20) if selected else (WHITE if avail else (130, 130, 140))
            render.text(surf, label, 16, col, rect.center, center=True, shadow=not selected)
        desc = self.ITEMS[self.sel][2]
        box = pygame.Rect(150, SCREEN_H - 66, SCREEN_W - 300, 54)
        pygame.draw.rect(surf, (15, 15, 25), box, border_radius=8)
        for i, line in enumerate(wrap(desc, 14, box.w - 20)[:2]):
            render.text(surf, line, 14, WHITE, (box.x + 10, box.y + 8 + i * 20), bold=False)
        render.text(surf, f"Coins: {self.game.save['coins']}   Best survival: {self.game.save['highscore']}",
                    12, (255, 220, 120), (SCREEN_W - 10, 8), right=True)
        render.text(surf, "W/S or Arrows: move   M / Num3 / Enter: confirm   N / Num2: back   Esc: main menu",
                    11, (220, 220, 230), (10, 8), bold=False)
        if self.popup > 0:
            r = pygame.Rect(0, 0, 420, 70)
            r.center = (SCREEN_W // 2, SCREEN_H // 2)
            pygame.draw.rect(surf, (15, 15, 25), r, border_radius=12)
            pygame.draw.rect(surf, UI_ACCENT, r, 3, border_radius=12)
            render.text(surf, "This mode is unavailable in this version.", 16, WHITE, r.center, center=True)


# ======================================================================
class StageSelect(Scene):
    """Choose the battleground. Locked stages show their Shop price."""
    def __init__(self, game, mode):
        super().__init__(game)
        self.mode = mode
        self.sel = 0
        self.thumbs = []
        for s in STAGES:
            st = build_stage(s)
            self.thumbs.append(pygame.transform.smoothscale(st["bg"], (256, 144)))

    def update(self, dt):
        super().update(dt)
        n = self.menu_input()
        cols = 3
        if "left" in n:
            self.sel = (self.sel - 1) % len(STAGES)
        if "right" in n:
            self.sel = (self.sel + 1) % len(STAGES)
        if "up" in n:
            self.sel = (self.sel - cols) % len(STAGES)
        if "down" in n:
            self.sel = (self.sel + cols) % len(STAGES)
        if n & {"left", "right", "up", "down"}:
            self.game.audio.play("select")
        if "back" in n:
            self.game.change(MainMenu(self.game))
        elif "ok" in n:
            st = STAGES[self.sel]
            if not is_unlocked(self.game, st):
                self.game.audio.play("block")
                return
            self.game.audio.play("confirm")
            self.game.change(CharSelect(self.game, self.mode, st))

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, "SELECT STAGE", 36, WHITE, (SCREEN_W // 2, 40))
        for i, st in enumerate(STAGES):
            col, row = i % 3, i // 3
            x = 60 + col * 290
            y = 90 + row * 200
            sel = i == self.sel
            pygame.draw.rect(surf, UI_ACCENT if sel else UI_DARK, (x - 6, y - 6, 268, 186), border_radius=10)
            surf.blit(self.thumbs[i], (x, y))
            locked = not is_unlocked(self.game, st)
            if locked:
                dim = pygame.Surface((256, 144), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 160))
                surf.blit(dim, (x, y))
                render.text(surf, f"LOCKED - {st['price']} coins (Shop)", 14, (255, 200, 120), (x + 128, y + 72), center=True)
            render.text(surf, st["name"], 16, (20, 20, 20) if sel else WHITE, (x + 128, y + 160), center=True, shadow=not sel)
        render.text(surf, "Move: choose   Attack: confirm   Throw: back", 14, WHITE, (SCREEN_W // 2, SCREEN_H - 22), center=True)


# ======================================================================
class CharSelect(Scene):
    """Choose fighters. Each player moves their own cursor with their own keys and
    confirms with attack / cancels with throw. The panel shows stats and the
    full jutsu list with its button combination.
    """
    def __init__(self, game, mode, stage_def):
        super().__init__(game)
        self.mode, self.stage_def = mode, stage_def
        self.cursor = [0, 1]
        self.done = [False, False]
        self.two_players = mode == "battle"
        self.needs_second = mode in ("battle", "versus")
        self.phase = 0          # versus: 0 = pick yourself, 1 = pick CPU
        self.start_timer = -1

    def ctrl_for(self, idx):
        if self.two_players:
            return self.game.c1 if idx == 0 else self.game.c2
        return None

    def _move(self, idx, n):
        if "left" in n:
            self.cursor[idx] = (self.cursor[idx] - 1) % len(ROSTER)
            self.game.audio.play("select")
        if "right" in n:
            self.cursor[idx] = (self.cursor[idx] + 1) % len(ROSTER)
            self.game.audio.play("select")

    def update(self, dt):
        super().update(dt)
        g = self.game
        if self.start_timer >= 0:
            self.start_timer -= dt
            if self.start_timer < 0:
                c1 = ROSTER[self.cursor[0]]
                if self.mode == "training":
                    c2 = DUMMY
                elif self.mode == "survival":
                    c2 = random.choice([c for c in ROSTER if not c.get("locked")])
                else:
                    c2 = ROSTER[self.cursor[1]]
                g.change(BattleScene(g, self.mode, self.stage_def, c1, c2))
            return
        if self.two_players:
            for idx in (0, 1):
                n = nav(self.ctrl_for(idx))
                if idx == 0 and g.enter_pressed:
                    n.add("ok")
                if not self.done[idx]:
                    self._move(idx, n)
                    if "ok" in n and is_unlocked(g, ROSTER[self.cursor[idx]]):
                        self.done[idx] = True
                        g.audio.play("confirm")
                    elif "back" in n:
                        g.change(StageSelect(g, self.mode))
                        return
                elif "back" in n:
                    self.done[idx] = False
            if all(self.done):
                self.start_timer = 0.6
        else:
            n = self.menu_input()
            idx = self.phase
            self._move(idx, n)
            if "ok" in n and is_unlocked(g, ROSTER[self.cursor[idx]]):
                g.audio.play("confirm")
                self.done[idx] = True
                if self.needs_second and self.phase == 0:
                    self.phase = 1
                else:
                    self.start_timer = 0.5
            elif "back" in n:
                if self.phase == 1:
                    self.phase = 0
                    self.done[0] = False
                else:
                    g.change(StageSelect(g, self.mode))

    def draw_panel(self, surf, idx, rect):
        """Draw one player's character information panel."""
        ch = ROSTER[self.cursor[idx]]
        col = P1_COLOR if idx == 0 else P2_COLOR
        pygame.draw.rect(surf, UI_PANEL, rect, border_radius=10)
        pygame.draw.rect(surf, col, rect, 3, border_radius=10)
        who = "PLAYER 1" if idx == 0 else ("PLAYER 2" if self.two_players else "CPU")
        render.text(surf, who + ("  - READY!" if self.done[idx] else ""), 13, col, (rect.x + 10, rect.y + 6))
        render.text(surf, ch["name"], 22, WHITE, (rect.x + 10, rect.y + 22))
        render.text(surf, ch["title"], 13, (255, 210, 140), (rect.x + 10, rect.y + 50), bold=False)
        for i, line in enumerate(wrap(ch["description"], 12, rect.w - 150)[:4]):
            render.text(surf, line, 12, (220, 220, 230), (rect.x + 10, rect.y + 70 + i * 16), bold=False, shadow=False)
        pose = {"front_arm": 12, "back_arm": -12, "bob": math.sin(self.t * 4) * 1.5}
        if self.done[idx]:
            pose = {"front_arm": 170, "back_arm": -30, "mouth": "smile"}
        render.draw_chibi(surf, rect.right - 70, rect.y + 150, 1 if idx == 0 else -1, ch["palette"], pose, self.t, 1.9)
        if ch["palette"].get("companion") == "pup":
            render.draw_pup(surf, rect.right - 120, rect.y + 150, 1, self.t, 1.0)
        stats = [("Strength", ch["strength"], 6), ("Jutsu Power", ch["jutsu_power"], 6), ("Speed", ch["speed"], 10),
                 ("Chakra/sec", round(ch["chakra_gain"] * CHAKRA_CHARGE_RATE, 1), 13),
                 ("Combo", ch["combo"], 6)]
        for i, (nm, v, mx) in enumerate(stats):
            y = rect.y + 140 + i * 15
            render.text(surf, nm, 11, WHITE, (rect.x + 10, y), shadow=False)
            pygame.draw.rect(surf, (20, 20, 30), (rect.x + 90, y + 3, 120, 8))
            pygame.draw.rect(surf, col, (rect.x + 90, y + 3, int(120 * v / mx), 8))
            render.text(surf, str(v), 11, WHITE, (rect.x + 216, y), shadow=False)
        y = rect.y + 222
        for slot in ("up", "throw", "attack", "special", "air"):
            for j in ch["jutsus"].get(slot, []):
                cost = f"{j['hp_req']} HP req" if j.get("hp_req") else f"{j['cost']} ck"
                render.text(surf, f"{j['name']}", 11, (255, 230, 150), (rect.x + 10, y), shadow=False)
                render.text(surf, f"{j['keys']}  [{cost}]", 11, (200, 210, 230), (rect.x + 150, y), shadow=False, bold=False)
                y += 14
        if not is_unlocked(self.game, ch):
            render.outline_text(surf, f"LOCKED ({ch['price']} coins in Shop)", 18, (255, 120, 120), (rect.centerx, rect.y + 120))

    def draw(self, surf):
        menu_bg(surf, self.t)
        title = "SELECT YOUR NINJA"
        if self.mode == "versus":
            title = "SELECT YOUR NINJA" if self.phase == 0 else "SELECT CPU OPPONENT"
        render.outline_text(surf, title, 28, WHITE, (SCREEN_W // 2, 22))
        n = len(ROSTER)
        cw = min(104, (SCREEN_W - 40) // n)
        x0 = (SCREEN_W - cw * n) // 2
        for i, ch in enumerate(ROSTER):
            r = pygame.Rect(x0 + i * cw + 3, 44, cw - 6, 96)
            pygame.draw.rect(surf, UI_DARK, r, border_radius=8)
            render.draw_chibi(surf, r.centerx, r.bottom - 8, 1, ch["palette"], {"bob": math.sin(self.t * 3 + i)}, self.t, 1.15,
                              alpha=255 if is_unlocked(self.game, ch) else 90)
            if not is_unlocked(self.game, ch):
                render.text(surf, "LOCKED", 11, (255, 150, 150), (r.centerx, r.y + 10), center=True)
            if self.cursor[0] == i:
                pygame.draw.rect(surf, P1_COLOR, r, 3, border_radius=8)
                render.text(surf, "P1", 11, P1_COLOR, (r.x + 4, r.y + 2))
            if self.needs_second and self.cursor[1] == i:
                pygame.draw.rect(surf, P2_COLOR, r.inflate(-6, -6), 3, border_radius=8)
                render.text(surf, "P2" if self.two_players else "CPU", 11, P2_COLOR, (r.right - 26, r.y + 2))
        if self.needs_second:
            self.draw_panel(surf, 0, pygame.Rect(10, 148, SCREEN_W // 2 - 15, SCREEN_H - 172))
            self.draw_panel(surf, 1, pygame.Rect(SCREEN_W // 2 + 5, 148, SCREEN_W // 2 - 15, SCREEN_H - 172))
        else:
            self.draw_panel(surf, 0, pygame.Rect(SCREEN_W // 4, 148, SCREEN_W // 2, SCREEN_H - 172))
        help_ = "Left/Right: choose   Attack: confirm   Throw: cancel" + ("   (each player uses own keys)" if self.two_players else "")
        render.text(surf, help_, 12, WHITE, (SCREEN_W // 2, SCREEN_H - 12), center=True)


# ======================================================================
class BattleScene(Scene):
    """The fight itself: rounds, timer, KO handling, Survival waves and Training."""
    def __init__(self, game, mode, stage_def, c1, c2):
        super().__init__(game)
        self.mode, self.stage_def, self.c1, self.c2 = mode, stage_def, c1, c2
        self.stage = build_stage(stage_def)
        self.layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.buffer = pygame.Surface((SCREEN_W, SCREEN_H))
        self.wins = [0, 0]
        self.round = 1
        self.kills = 0
        diff = game.save["difficulty"]
        self.ai = None
        if mode in ("versus", "survival"):
            self.ai = AIController(diff)
        elif mode == "training":
            self.ai = AIController(diff, dummy=True)
        self.null = NullController()
        self.f1 = None
        self.start_round(fresh=True)

    def start_round(self, fresh=False, keep_p1=False):
        """Create both fighters and a fresh World for a new round."""
        if not keep_p1:
            self.f1 = Fighter(self.c1, 1, 220, 1, "P1")
        else:
            self.f1.x, self.f1.y, self.f1.facing = 220, GROUND_Y, 1
            self.f1.cancel_actions()
            self.f1.set_state("idle", force=True)
            self.f1.vx = self.f1.vy = 0
        label2 = "P2" if self.mode == "battle" else ("CPU" if self.mode != "training" else "DUMMY")
        self.f2 = Fighter(self.c2, 2, 740, -1, label2)
        if self.mode == "training":
            self.f1.infinite_chakra = True
        self.world = World(self.stage, [self.f1, self.f2], self.game.audio)
        self.phase = "intro"
        self.phase_t = 0.0
        self.timer = ROUND_TIME
        self.result_text = ""

    def update(self, dt):
        super().update(dt)
        g = self.game
        self.phase_t += dt
        if self.ai:
            self.ai.update(self.f2, self.world, dt)
        c2 = self.ai if self.ai else g.c2
        if self.phase == "intro":
            self.f1.update(dt, self.null, self.world)
            self.f2.update(dt, self.null, self.world)
            self.world.update(dt)
            if self.phase_t > 1.6:
                self.phase = "fight"
        elif self.phase == "fight":
            if self.world.hitstop > 0:           # brief freeze on impact (adds punch)
                self.world.hitstop -= dt
                dt *= 0.06
            self.f1.update(dt, g.c1, self.world)
            self.f2.update(dt, c2, self.world)
            self.world.update(dt)
            if self.mode == "training":
                if self.world.time - self.f2.last_hit > 2.0 and self.f2.hp < MAX_HP:
                    self.f2.hp = MAX_HP
                self.f2.kunai = self.f2.shuriken = 90
                if self.f2.hp <= 1:
                    self.f2.hp = 1
            else:
                self.timer -= dt
            if self.f1.hp <= 0 or self.f2.hp <= 0:
                self.phase, self.phase_t = "ko", 0.0
                self.result_text = "K.O.!"
            elif self.timer <= 0:
                self.phase, self.phase_t = "ko", 0.0
                self.result_text = "TIME UP!"
        elif self.phase == "ko":
            sdt = dt * (0.3 if self.phase_t < 0.8 else 1.0)
            self.f1.update(sdt, self.null, self.world)
            self.f2.update(sdt, self.null, self.world)
            self.world.update(sdt)
            if self.phase_t > 1.2:
                for f in (self.f1, self.f2):
                    if f.hp > 0 and f.on_ground and f.move is None:
                        f.set_state("victory")
            if self.phase_t > 2.8:
                self.resolve_round()

    def resolve_round(self):
        """Decide who won the round, then start the next one, spawn the next Survival
        enemy, or move on to the results screen.
        """
        g = self.game
        if self.f1.hp > self.f2.hp:
            winner = 1
        elif self.f2.hp > self.f1.hp:
            winner = 2
        else:
            winner = 0
        if self.mode == "survival":
            if winner == 1:
                self.kills += 1
                self.f1.hp = min(MAX_HP, self.f1.hp + MAX_HP * 0.25)
                self.f1.chakra = min(100, self.f1.chakra + 30)
                if self.kills % 3 == 0:
                    i = DIFFICULTIES.index(self.ai.difficulty)
                    self.ai.set_difficulty(DIFFICULTIES[min(len(DIFFICULTIES) - 1, i + 1)])
                self.c2 = random.choice([c for c in ROSTER if not c.get("locked")])
                self.start_round(keep_p1=True)
            else:
                coins = self.kills * 25
                g.save["coins"] += coins
                new_best = self.kills > g.save["highscore"]
                g.save["highscore"] = max(g.save["highscore"], self.kills)
                save_save(g.save)
                history.append_match("GUI", "survival", self.c1["name"], "waves",
                                     self.stage["name"], f"{self.kills} KOs",
                                     self.c1["name"] if self.kills else "Defeated", self.t)
                lines = [f"Enemies defeated: {self.kills}", f"Coins earned: {coins}",
                         "NEW HIGHSCORE!" if new_best else f"Best: {g.save['highscore']}",
                         "(Online highscores are unavailable - saved locally)"]
                g.change(ResultScene(g, "SURVIVAL OVER", lines, self.c1, self))
            return
        if winner:
            self.wins[winner - 1] += 1
        if max(self.wins) >= ROUNDS_TO_WIN:
            w = 1 if self.wins[0] >= ROUNDS_TO_WIN else 2
            ch = self.c1 if w == 1 else self.c2
            who = "PLAYER 1" if w == 1 else ("PLAYER 2" if self.mode == "battle" else "CPU")
            # every finished match is appended to the shared match_history.txt log
            history.append_match("GUI", self.mode, self.c1["name"], self.c2["name"],
                                 self.stage["name"], f"{self.wins[0]}-{self.wins[1]}",
                                 ch["name"], self.t)
            g.change(ResultScene(g, f"{who} WINS!", [ch["name"], f"Rounds {self.wins[0]} - {self.wins[1]}"], ch, self))
        else:
            self.round += 1
            self.start_round()

    def draw(self, surf):
        b = self.buffer
        b.blit(self.stage["bg"], (0, 0))
        draw_ambient(b, self.stage, self.t)
        render.draw_world(b, self.layer, self.world, self.t)
        render.post_process(b, self.world)
        ox = oy = 0
        if self.world.shake > 0:
            ox, oy = random.randint(-6, 6), random.randint(-5, 5)
        surf.fill((0, 0, 0))
        surf.blit(b, (ox, oy))
        render.draw_player_hud(surf, self.f1, True, self.t, self.wins[0])
        render.draw_player_hud(surf, self.f2, False, self.t, self.wins[1])
        # timer
        pygame.draw.circle(surf, (15, 15, 22), (SCREEN_W // 2, 34), 28)
        pygame.draw.circle(surf, UI_ACCENT, (SCREEN_W // 2, 34), 28, 3)
        # above 99 seconds the clock reads m:ss so a 5-minute round still fits the dial
        secs = max(0, int(math.ceil(self.timer)))
        label = "--" if self.mode == "training" else (f"{secs // 60}:{secs % 60:02d}" if secs > 99 else str(secs))
        render.text(surf, label, 22 if len(label) < 4 else 19, WHITE, (SCREEN_W // 2, 34), center=True)
        if self.mode == "survival":
            render.text(surf, f"KOs: {self.kills}   CPU: {self.ai.difficulty}", 13, (255, 220, 120), (SCREEN_W // 2, 70), center=True)
        render.draw_inventory(surf, [self.f1, self.f2], self.t)
        if self.phase == "intro":
            msg = f"ROUND {self.round}" if self.phase_t < 1.0 else "FIGHT!"
            if self.mode == "survival":
                msg = f"ENEMY {self.kills + 1}" if self.phase_t < 1.0 else "FIGHT!"
            if self.mode == "training":
                msg = "TRAINING" if self.phase_t < 1.0 else "GO!"
            render.outline_text(surf, msg, 56, (255, 200, 60), (SCREEN_W // 2, SCREEN_H // 2 - 40))
        elif self.phase == "ko":
            render.outline_text(surf, self.result_text, 64, (255, 80, 60), (SCREEN_W // 2, SCREEN_H // 2 - 40))
        render.text(surf, "Esc: menu", 11, (230, 230, 230), (SCREEN_W - 8, SCREEN_H - 16), right=True, bold=False)


# ======================================================================
class ResultScene(Scene):
    """Winner screen - attack to rematch, throw to go back to character select."""
    def __init__(self, game, title, lines, char, battle):
        super().__init__(game)
        self.title, self.lines, self.char, self.battle = title, lines, char, battle

    def update(self, dt):
        super().update(dt)
        n = self.menu_input()
        if self.t < 0.6:
            return
        g = self.game
        if "ok" in n:
            b = self.battle
            first = b.c1
            second = b.c2 if b.mode not in ("survival",) else random.choice([c for c in ROSTER if not c.get("locked")])
            g.change(BattleScene(g, b.mode, b.stage_def, first, second))
        elif "back" in n:
            g.change(CharSelect(g, self.battle.mode, self.battle.stage_def))

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, self.title, 56, (255, 200, 60), (SCREEN_W // 2, 90))
        pose = {"front_arm": 170, "back_arm": -30, "mouth": "smile", "bob": math.sin(self.t * 6) * 3}
        render.draw_chibi(surf, SCREEN_W // 2, 380, 1, self.char["palette"], pose, self.t, 3.0)
        for i, line in enumerate(self.lines):
            render.text(surf, line, 18, WHITE, (SCREEN_W // 2, 400 + i * 24), center=True)
        render.text(surf, "Attack: rematch    Throw: character select    Esc: main menu", 14, (255, 230, 200),
                    (SCREEN_W // 2, SCREEN_H - 18), center=True)


# ======================================================================
class OptionsScene(Scene):
    """Difficulty, music, sound and key configuration. Saves immediately."""
    def __init__(self, game):
        super().__init__(game)
        self.sel = 0

    def rows(self):
        """The list of option rows and their current values."""
        s = self.game.save
        return [
            ("Difficulty", s["difficulty"]),
            ("Fullscreen", "On" if s.get("fullscreen") else "Off"),
            ("Music", "On" if s["music"] else "Off"),
            ("Music type", "MP3" if s["music_type"] == "mp3" else "MIDI"),
            ("Sound effects", "On" if s["sound"] else "Off"),
            ("Configure Player 1 keys", ""),
            ("Configure Player 2 keys", ""),
            ("Reset keys to default", ""),
            ("Back", ""),
        ]

    def update(self, dt):
        super().update(dt)
        g, s = self.game, self.game.save
        n = self.menu_input()
        rows = self.rows()
        if "up" in n:
            self.sel = (self.sel - 1) % len(rows)
        if "down" in n:
            self.sel = (self.sel + 1) % len(rows)
        change = 1 if ("right" in n or "ok" in n) else (-1 if "left" in n else 0)
        if "back" in n:
            save_save(s)
            g.change(MainMenu(g))
            return
        if not change:
            return
        g.audio.play("select")
        if self.sel == 0:
            i = DIFFICULTIES.index(s["difficulty"])
            s["difficulty"] = DIFFICULTIES[(i + change) % len(DIFFICULTIES)]
        elif self.sel == 1:
            g.toggle_fullscreen()          # also remembers the choice in save_data.json
        elif self.sel == 2:
            s["music"] = not s["music"]
        elif self.sel == 3:
            s["music_type"] = "midi" if s["music_type"] == "mp3" else "mp3"
            g.audio.music_playing = None
        elif self.sel == 4:
            s["sound"] = not s["sound"]
        elif "ok" in n and self.sel == 5:
            g.change(KeyConfigScene(g, "1"))
        elif "ok" in n and self.sel == 6:
            g.change(KeyConfigScene(g, "2"))
        elif "ok" in n and self.sel == 7:
            s["keys"] = {p: {a: list(k) for a, k in DEFAULT_KEYS[p].items()} for p in DEFAULT_KEYS}
            g.apply_keys()
        elif "ok" in n and self.sel == 8:
            save_save(s)
            g.change(MainMenu(g))
            return
        save_save(s)
        g.audio.update_music()

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, "OPTIONS", 42, WHITE, (SCREEN_W // 2, 50))
        for i, (name, val) in enumerate(self.rows()):
            r = pygame.Rect(SCREEN_W // 2 - 220, 96 + i * 40, 440, 34)
            sel = i == self.sel
            pygame.draw.rect(surf, UI_ACCENT if sel else UI_DARK, r, border_radius=8)
            col = (20, 20, 20) if sel else WHITE
            render.text(surf, name, 17, col, (r.x + 14, r.y + 8), shadow=not sel)
            if val:
                render.text(surf, f"<  {val}  >", 17, col, (r.right - 14, r.y + 8), right=True, shadow=not sel)
        render.text(surf, "F11 or Alt+Enter toggles fullscreen at any time.   Music files go in assets/music/ (MP3/OGG/WAV for MP3 mode, MID for MIDI mode). Not all computers support MP3!",
                    12, (230, 230, 240), (SCREEN_W // 2, SCREEN_H - 20), center=True, bold=False)


class KeyConfigScene(Scene):
    """Rebind one player's keys: choose a row, press Enter, then press the new key."""
    def __init__(self, game, player):
        super().__init__(game)
        self.player = player
        self.sel = 0
        self.waiting = False

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return False
        rows = len(ACTIONS) + 1
        if self.waiting:
            if e.key != pygame.K_ESCAPE:
                self.game.save["keys"][self.player][ACTIONS[self.sel]] = [e.key]
                self.game.apply_keys()
                save_save(self.game.save)
            self.waiting = False
            return True
        if e.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % rows
            return True
        if e.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % rows
            return True
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.sel == len(ACTIONS):
                self.game.change(OptionsScene(self.game))
            else:
                self.waiting = True
            return True
        return True  # swallow everything else on this screen

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, f"PLAYER {self.player} CONTROLS", 36, WHITE, (SCREEN_W // 2, 40))
        keys = self.game.save["keys"][self.player]
        for i, a in enumerate(ACTIONS + ["back"]):
            r = pygame.Rect(SCREEN_W // 2 - 240, 62 + i * 40, 480, 32)
            sel = i == self.sel
            pygame.draw.rect(surf, UI_ACCENT if sel else UI_DARK, r, border_radius=8)
            col = (20, 20, 20) if sel else WHITE
            if a == "back":
                render.text(surf, "Back", 15, col, r.center, center=True, shadow=not sel)
                continue
            render.text(surf, ACTION_LABELS[a], 15, col, (r.x + 12, r.y + 7), shadow=not sel)
            val = "PRESS A KEY..." if (sel and self.waiting) else ", ".join(pygame.key.name(k).upper() for k in keys[a])
            render.text(surf, val, 15, col, (r.right - 12, r.y + 7), right=True, shadow=not sel)
        render.text(surf, "Up/Down (W/S): select   Enter/Space: change key   Esc: main menu", 13, WHITE,
                    (SCREEN_W // 2, SCREEN_H - 18), center=True)


# ======================================================================
class ShopScene(Scene):
    """Spend coins earned in Survival Mode on the locked fighter and stage."""
    def __init__(self, game):
        super().__init__(game)
        self.items = [("char", c) for c in ROSTER if c.get("locked")] + [("stage", s) for s in STAGES if s.get("locked")]
        self.sel = 0
        self.msg, self.msg_t = "", 0.0

    def update(self, dt):
        super().update(dt)
        self.msg_t = max(0, self.msg_t - dt)
        g, s = self.game, self.game.save
        n = self.menu_input()
        if "back" in n:
            g.change(MainMenu(g))
            return
        if not self.items:
            return
        if "up" in n or "left" in n:
            self.sel = (self.sel - 1) % len(self.items)
        if "down" in n or "right" in n:
            self.sel = (self.sel + 1) % len(self.items)
        if "ok" in n:
            kind, it = self.items[self.sel]
            if it["id"] in s["unlocked"]:
                self.msg = "Already unlocked!"
            elif s["coins"] >= it["price"]:
                s["coins"] -= it["price"]
                s["unlocked"].append(it["id"])
                save_save(s)
                self.msg = f"Unlocked {it['name']}!"
                g.audio.play("heal")
            else:
                self.msg = "Not enough coins - play Survival Mode!"
                g.audio.play("block")
            self.msg_t = 2.0

    def draw(self, surf):
        menu_bg(surf, self.t)
        render.outline_text(surf, "SHOP", 42, WHITE, (SCREEN_W // 2, 46))
        render.text(surf, f"Coins: {self.game.save['coins']}", 20, (255, 220, 120), (SCREEN_W // 2, 86), center=True)
        for i, (kind, it) in enumerate(self.items):
            r = pygame.Rect(SCREEN_W // 2 - 280, 120 + i * 130, 560, 116)
            sel = i == self.sel
            pygame.draw.rect(surf, UI_ACCENT if sel else UI_DARK, r, border_radius=10)
            owned = it["id"] in self.game.save["unlocked"]
            col = (20, 20, 20) if sel else WHITE
            if kind == "char":
                render.draw_chibi(surf, r.x + 60, r.bottom - 12, 1, it["palette"], {"bob": math.sin(self.t * 4)}, self.t, 1.6)
                label = f"Character: {it['name']}"
            else:
                thumb = pygame.transform.smoothscale(build_stage(it)["bg"], (140, 80))
                surf.blit(thumb, (r.x + 10, r.y + 18))
                label = f"Stage: {it['name']}"
            render.text(surf, label, 20, col, (r.x + 160, r.y + 24), shadow=not sel)
            render.text(surf, "OWNED" if owned else f"{it['price']} coins", 18, col, (r.x + 160, r.y + 62), shadow=not sel)
        if self.msg_t > 0:
            render.outline_text(surf, self.msg, 22, (255, 230, 150), (SCREEN_W // 2, SCREEN_H - 50))
        render.text(surf, "Attack: buy   Throw: back", 14, WHITE, (SCREEN_W // 2, SCREEN_H - 18), center=True)


# ======================================================================
class HowToPlay(Scene):
    """In-game manual: controls, movement rules and how jutsu inputs work."""
    PAGES = [
        ("CONTROLS", [
            "ACTION              PLAYER 1     PLAYER 2",
            "Jutsu combo (Up)    W            Up arrow",
            "Run / face left     A            Left arrow",
            "Run / face right    D            Right arrow",
            "Block / substitute  S            Down arrow",
            "Jump                B            Numpad 1",
            "Throw kunai         N            Numpad 2",
            "Throw shuriken      G            Numpad 4",
            "Attack              M            Numpad 3",
            "Chakra / jutsu      H            Numpad 5",
            "Ninja scroll        J            Numpad 6",
            "",
            "Keys can be changed in Option Mode. Esc returns to the main menu.",
            "F11 (or Alt+Enter) switches between fullscreen and windowed.",
        ]),
        ("MOVES", [
            "Tap a direction to walk, keep holding to RUN.",
            "Jump again in mid-air for a DOUBLE JUMP (spinning flip).",
            "Jump + Up at the same time: TELEPORT UP (8 chakra) - you keep one",
            "   jump afterwards, so you can teleport then jump again.",
            "Hold Up + Down on a platform: drop through it.",
            "Hold Block to guard (15% damage). Tap Block right before a hit",
            "   to SUBSTITUTE and teleport behind the attacker (10 chakra).",
            "Attack repeatedly for a combo; the last hit knocks down.",
            "Attack in the air: powerful diving jump attack.",
            "Throw kunai (N / Num2) and shuriken (G / Num4) with their own keys.",
            "Each player has 90 kunai + 90 shuriken.",
            "Ninja scroll heals 30% HP - only 5 per player.",
            "Hold Chakra on the ground to gather chakra.",
        ]),
        ("JUTSU", [
            "Hold the first button, then press CHAKRA:",
            "  Up + Chakra            -> Up jutsu",
            "  Throw + Chakra         -> Throw jutsu",
            "  Attack + Chakra        -> Attack jutsu",
            "  Attack, Attack (hold) + Chakra -> MAIN / ultimate jutsu",
            "  Chakra in the air      -> Aerial jutsu",
            "Some jutsus change with distance (close vs far).",
            "Each fighter's full jutsu list is shown on the character select screen.",
            "Not enough chakra? You'll see how much you need above your head.",
        ]),
        ("CREDITS", [
            "SHINOBI CLASH - Chibi Ninja Battle",
            "",
            "Design, code and artwork:   {author}".format(author=AUTHOR),
            "",
            "Everything in this game is my own original work: the fighters, their",
            "stats and jutsu, the stages, the menus and the chibi characters, which",
            "are drawn entirely in code - the game uses no sprite or image files.",
            "",
            "Built with Python and the Pygame library.",
        ]),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.page = 0

    def update(self, dt):
        super().update(dt)
        n = self.menu_input()
        if "left" in n:
            self.page = (self.page - 1) % len(self.PAGES)
        if "right" in n or "ok" in n:
            self.page = (self.page + 1) % len(self.PAGES)
        if "back" in n:
            self.game.change(MainMenu(self.game))

    def draw(self, surf):
        menu_bg(surf, self.t)
        title, lines = self.PAGES[self.page]
        render.outline_text(surf, f"HOW TO PLAY - {title}", 34, WHITE, (SCREEN_W // 2, 44))
        box = pygame.Rect(90, 80, SCREEN_W - 180, 400)
        pygame.draw.rect(surf, (15, 15, 25), box, border_radius=12)
        mono = pygame.font.SysFont("couriernew,dejavusansmono,monospace", 17, bold=True)
        for i, line in enumerate(lines):
            surf.blit(mono.render(line, True, WHITE), (box.x + 24, box.y + 20 + i * 31))
        render.text(surf, f"Page {self.page + 1}/{len(self.PAGES)}   Left/Right: page   Throw: back", 14, WHITE,
                    (SCREEN_W // 2, SCREEN_H - 24), center=True)
