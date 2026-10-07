"""
world.py - The battle arena and the hit resolver
================================================
The World owns every object in a fight and, most importantly, decides what
happens when something hits a fighter: deflect, substitution, block, or a
clean hit with damage, knockback and screen shake.

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

from entities import FX, FloatText, Particle, Projectile
from settings import (BLOCK_DAMAGE_TAKEN, GROUND_Y, MAX_CHAKRA, SUBSTITUTION_COST,
                      SUBSTITUTION_WINDOW, now, sign)


class World:
    """Everything inside one round: the fighters, their projectiles, hitboxes,
    summons and effects, plus the rules for what a hit actually does.
    """
    def __init__(self, stage, fighters, audio):
        self.stage = stage
        self.platforms = stage["platforms"]
        self.fighters = fighters
        self.audio = audio
        self.projectiles, self.hitboxes, self.summons = [], [], []
        self.particles, self.texts, self.fx = [], [], []
        self.time = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.hitstop = 0.0
        for f in fighters:
            f.world = self

    # --------------------------------------------------------------- queries
    def enemies_of(self, f):
        """All living fighters on the other team."""
        return [o for o in self.fighters if o.team != f.team and o.hp > 0]

    def nearest_enemy(self, f, x=None):
        """The closest living opponent (used for aiming and for the CPU)."""
        x = f.x if x is None else x
        es = self.enemies_of(f)
        return min(es, key=lambda e: abs(e.x - x)) if es else None

    def floor_below(self, x, y):
        """Height of the first platform (or the ground) underneath a point."""
        best = GROUND_Y
        for p in self.platforms:
            if p.left <= x <= p.right and p.top >= y - 2 and p.top < best:
                best = p.top
        return best

    # --------------------------------------------------------------- spawning
    def add_projectile(self, p):
        self.projectiles.append(p)
        return p

    def add_hitbox(self, h):
        self.hitboxes.append(h)
        return h

    def add_summon(self, s):
        self.summons.append(s)
        return s

    def add_fx(self, fx):
        self.fx.append(fx)
        return fx

    def text(self, txt, x, y, color=(255, 255, 255), size=18, life=0.9):
        """Spawn a floating message, e.g. a damage number."""
        self.texts.append(FloatText(txt, x, y, color, life, size))

    def play(self, name):
        if self.audio:
            self.audio.play(name)

    def smoke(self, x, y, n=14):
        """Puff of smoke - used for teleports, clones and substitutions."""
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(30, 140)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp - 20, random.uniform(0.35, 0.7),
                                           random.choice([(230, 230, 230), (200, 200, 205), (170, 170, 180)]),
                                           size=random.uniform(6, 12), kind="smoke"))

    def sparks(self, x, y, color=(255, 230, 120), n=10):
        """Small bright flecks thrown out by an impact."""
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(120, 360)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.15, 0.3),
                                           color, size=3, kind="spark"))

    def dust(self, x, y, n=8):
        """Dust kicked up on landing or when running into a wall."""
        for _ in range(n):
            self.particles.append(Particle(x + random.uniform(-14, 14), y, random.uniform(-90, 90),
                                           random.uniform(-60, -10), 0.4, (190, 170, 140), size=5, kind="smoke"))

    def throw_at(self, owner, x, y, tgt, kind, damage, speed=650):
        """Throw a weapon from (x, y) aimed at a target - used by shadow clones."""
        ang = math.atan2((tgt.y - 30) - y, tgt.x - x)
        self.add_projectile(Projectile(owner, kind, x, y, math.cos(ang) * speed, math.sin(ang) * speed, damage,
                                       w=18, h=10, spin=900 if kind == "shuriken" else 0))
        self.play("throw")

    def spawn_log(self, x, y):
        """Leave behind the wooden log of a substitution jutsu."""
        self.add_fx(FX("log", x, y, 0.9))

    def banner(self, text, f):
        """Show the name of the jutsu that was just performed above the fighter."""
        self.add_fx(FX("banner", f.x, f.y - 100 * f.scale, 1.2, text=text, color=f.char["palette"]["accent"]))

    # --------------------------------------------------------------- combat
    def hit(self, att, tgt, dmg, kbx=150, kby=-100, stun=0.25, unblockable=False, knockdown=False,
            drain=0, kind="melee", direction=None, sfx="hit", sub_ok=True):
        """Returns 'miss' | 'deflect' | 'sub' | 'block' | 'hit'."""
        if tgt.hp <= 0 or tgt.invuln > 0:
            return "miss"
        if direction is None:
            direction = sign(tgt.x - att.x)
        cx, cy = tgt.x, tgt.y - 30 * tgt.scale

        if kind == "projectile" and tgt.deflect > 0:
            self.sparks(cx, cy, (160, 220, 255), 8)
            self.play("block")
            return "deflect"

        # Substitution jutsu: block pressed right before the hit lands
        c = tgt.ctrl
        if (sub_ok and c is not None and tgt.bound <= 0 and tgt.sub_cd <= 0 and tgt.move is None
                and tgt.chakra >= SUBSTITUTION_COST and now() - c.last_press["down"] <= SUBSTITUTION_WINDOW):
            tgt.substitute(att, self)
            return "sub"

        # Guard
        if (not unblockable and tgt.state == "block" and tgt.bound <= 0 and tgt.facing == -direction):
            tgt.hp -= dmg * BLOCK_DAMAGE_TAKEN
            tgt.vx = direction * 140
            tgt.block_flash = 0.12
            self.sparks(cx + tgt.facing * 12, cy, (150, 200, 255), 6)
            self.play("block")
            if tgt.hp <= 0:
                tgt.hp = 0
                tgt.knock_out(direction, self)
            return "block"

        total = dmg * att.damage_mult()
        tgt.hp -= total
        tgt.last_hit = self.time
        drain_total = drain + (6 if kind == "melee" and att.has_buff("sight") else 0)
        if drain_total:
            tgt.chakra = max(0.0, tgt.chakra - drain_total)
            att.chakra = min(MAX_CHAKRA, att.chakra + drain_total * 0.5)
        att.chakra = min(MAX_CHAKRA, att.chakra + 0.8)
        att.register_hit(self)
        if total >= 1:
            self.text(str(int(round(total))), tgt.x + random.uniform(-10, 10), tgt.y - 70 * tgt.scale,
                      (255, 230, 120) if total < 12 else (255, 120, 60), 16 if total < 12 else 22)
        self.sparks(cx, cy)
        self.play(sfx)
        if total >= 12:
            self.shake = max(self.shake, 0.25)
            self.flash = max(self.flash, 0.10)
            self.hitstop = max(self.hitstop, 0.07)
            self.add_fx(FX("impact", cx, cy, 0.28, color=(255, 240, 180)))
        else:
            self.add_fx(FX("impact", cx, cy, 0.18, color=(255, 220, 150), small=True))
            self.hitstop = max(self.hitstop, 0.025)
        if tgt.hp <= 0:
            tgt.hp = 0
            tgt.knock_out(direction, self)
            return "hit"
        if tgt.armor > 0:
            tgt.hurt_flash = 0.1
            return "hit"
        tgt.get_hit(direction, kbx, kby, stun, knockdown)
        return "hit"

    # --------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        for group in (self.hitboxes, self.projectiles, self.summons, self.fx, self.particles, self.texts):
            for obj in list(group):
                if not obj.dead:
                    obj.update(dt, self)
            group[:] = [o for o in group if not o.dead]
        # weapons clash in mid-air
        small = [p for p in self.projectiles if p.kind in Projectile.SMALL_WEAPONS and not p.dead]
        for i, a in enumerate(small):
            for b in small[i + 1:]:
                if a.owner.team != b.owner.team and not a.dead and not b.dead and a.rect().colliderect(b.rect()):
                    a.dead = b.dead = True
                    self.sparks((a.x + b.x) / 2, (a.y + b.y) / 2, (230, 230, 255), 8)
                    self.play("block")
        self.projectiles[:] = [p for p in self.projectiles if not p.dead]
