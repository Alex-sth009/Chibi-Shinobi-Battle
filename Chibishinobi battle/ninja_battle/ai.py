"""
ai.py - The computer opponent
=============================
The CPU does not cheat: it 'presses buttons' through the same Controller a
human uses, so it obeys exactly the same rules. It queues button presses with
small delays, which is how it performs multi-key jutsu inputs.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import random

from controls import Controller
from settings import sign

PARAMS = {
    #            think   aggression block  sub   jutsu  throw
    "Easy":   dict(react=0.45, aggro=0.35, block=0.15, sub=0.05, jutsu=0.12, throw=0.20),
    "Normal": dict(react=0.28, aggro=0.55, block=0.35, sub=0.15, jutsu=0.25, throw=0.30),
    "Hard":   dict(react=0.17, aggro=0.75, block=0.55, sub=0.35, jutsu=0.40, throw=0.35),
    "Expert": dict(react=0.09, aggro=0.90, block=0.70, sub=0.60, jutsu=0.55, throw=0.40),
}

THREAT_STATES = ("attack", "dash", "drill", "bigdrill", "air_attack", "ball", "top", "spin_kick", "spin", "slam")


class AIController(Controller):
    """The computer player. It plays by exactly the same rules as a human: it fills
    a queue of timed button presses and releases, which is how it can perform
    multi-key jutsu inputs. Difficulty only changes reaction time and how often
    it blocks, substitutes, throws and uses jutsu.
    """
    def __init__(self, difficulty="Normal", dummy=False):
        super().__init__()
        self.set_difficulty(difficulty)
        self.dummy = dummy
        self.queue = []          # [delay, op, action]
        self.think = 0.5
        self.hold_timer = 0.0

    def set_difficulty(self, difficulty):
        """Switch the behaviour numbers (used when Survival Mode ramps up)."""
        self.difficulty = difficulty
        self.cfg = PARAMS.get(difficulty, PARAMS["Normal"])

    # queue helpers
    def q(self, delay, op, action):
        """Queue one button operation to happen after `delay` seconds."""
        self.queue.append([delay, op, action])

    def tap(self, action, start=0.0, length=0.06):
        """Queue a quick press-and-release of a button."""
        self.q(start, "press", action)
        self.q(start + length, "release", action)

    def update(self, me, world, dt):
        """Run the queued button presses, then think again when the queue is empty."""
        self.begin_frame()
        if self.dummy or me.hp <= 0:
            self.release_all()
            self.queue.clear()
            return
        # run queued button operations
        for item in list(self.queue):
            item[0] -= dt
            if item[0] <= 0:
                self.queue.remove(item)
                if item[1] == "press":
                    self.release(item[2]) if item[2] in self.held and item[2] not in self.pressed else None
                    self.press(item[2])
                elif item[1] == "release":
                    self.release(item[2])
                elif item[1] == "hold":
                    self.hold(item[2])
        self.hold_timer -= dt
        if self.hold_timer <= 0:
            for a in ("left", "right", "down", "chakra", "up", "shuriken"):
                if not any(qi[2] == a for qi in self.queue):
                    self.release(a)
        self.think -= dt
        if self.think > 0 or self.queue:
            return
        self.think = self.cfg["react"] * random.uniform(0.7, 1.3)
        self.decide(me, world)

    def decide(self, me, world):
        """Choose what to do right now: heal, block/substitute, jutsu, charge chakra,
        chase across platforms, throw weapons from far away, or attack up close.
        """
        opp = world.nearest_enemy(me)
        if opp is None:
            return
        p = self.cfg
        dx = opp.x - me.x
        adx = abs(dx)
        toward = "right" if dx > 0 else "left"
        away = "left" if dx > 0 else "right"

        threat = (opp.state in THREAT_STATES or opp.move is not None) and adx < 150
        for pr in world.projectiles:
            if pr.owner.team != me.team and abs(pr.x - me.x) < 170 and sign(pr.vx) == sign(me.x - pr.x) \
                    and abs(pr.y - (me.y - 30)) < 60:
                threat = True

        r = random.random()
        if me.hp < 35 and me.scrolls > 0 and random.random() < 0.3:
            self.tap("scroll")
            return
        if threat and me.on_ground and r < p["block"]:
            if random.random() < p["sub"] / max(p["block"], 0.01) and me.chakra >= 10:
                self.tap("down", 0.0, 0.05)
            else:
                self.hold("down")
                self.hold_timer = 0.35
            return
        if random.random() < p["jutsu"] and self.try_jutsu(me, world, adx):
            return
        if me.chakra < 45 and adx > 260 and random.random() < 0.55:
            self.hold("chakra")
            self.hold_timer = random.uniform(0.5, 1.1)
            return
        # platforms
        if opp.y < me.y - 60 and me.on_ground and random.random() < 0.45:
            if random.random() < 0.3 and me.chakra > 20:
                self.q(0, "hold", "up")
                self.tap("jump", 0.02)
                self.q(0.1, "release", "up")
            else:
                self.tap("jump")
            self.hold(toward)
            self.hold_timer = 0.3
            return
        if opp.y > me.y + 60 and me.on_ground and random.random() < 0.45:
            self.hold("up")
            self.hold("down")
            self.hold_timer = 0.15
            return
        if not me.on_ground and me.air_jumps > 0 and random.random() < 0.25 and \
                (opp.y < me.y - 40 or me.y > 380):
            self.tap("jump")
            return
        if adx > 95:
            self.hold(toward)
            self.hold_timer = random.uniform(0.2, 0.5)
            if adx > 220 and random.random() < p["throw"]:
                self.tap(random.choice(["throw", "shuriken"]), 0.05)
            elif random.random() < 0.08:
                self.tap("jump", 0.05)
            return
        # close range
        if random.random() < p["aggro"]:
            self.tap(toward, 0, 0.03)
            hits = random.randint(1, me.char["combo"])
            for i in range(hits):
                self.tap("attack", 0.05 + i * 0.14, 0.05)
            if random.random() < 0.15:
                self.tap("jump", 0.0)
                self.tap("attack", 0.25)
        else:
            if random.random() < 0.5:
                self.hold(away)
                self.hold_timer = 0.25
            else:
                self.hold("down")
                self.hold_timer = 0.3

    def try_jutsu(self, me, world, adx):
        """Pick an affordable jutsu and queue the exact button combination for it."""
        options = []
        for slot, entries in me.char["jutsus"].items():
            if slot == "air":
                continue
            for j in entries:
                ok_cond = j.get("cond") is None or j["cond"](me, world)
                if ok_cond and me.can_afford(j):
                    if slot in ("special", "attack") and adx > 300 and "Throw" not in j["name"] \
                            and "Star" not in j["name"] and "Eye" not in j["name"]:
                        continue
                    options.append(slot)
                    break
        if not options or not me.on_ground:
            return False
        slot = random.choice(options)
        if slot == "up":
            self.q(0, "hold", "up")
            self.tap("chakra", 0.03)
            self.q(0.12, "release", "up")
        elif slot == "throw":
            key = "shuriken" if random.random() < 0.5 else "throw"
            self.q(0, "hold", key)
            self.tap("chakra", 0.03)
            self.q(0.12, "release", key)
        elif slot == "attack":
            self.q(0, "press", "attack")
            self.tap("chakra", 0.03)
            self.q(0.12, "release", "attack")
        elif slot == "special":
            self.tap("attack", 0.0, 0.05)
            self.q(0.1, "press", "attack")
            self.tap("chakra", 0.14)
            self.q(0.3, "release", "attack")
        return True
