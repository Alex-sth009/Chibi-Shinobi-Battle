"""
entities.py - Everything in a battle that is not a fighter
==========================================================
Particles, floating damage numbers, visual effects, melee hitboxes,
projectiles (kunai, shuriken, fireballs, shadows) and summons (shadow clones,
the ninja pup). Each object has update(dt, world) and is removed when dead.

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

from settings import GROUND_Y, SCREEN_W, STAGE_LEFT, STAGE_RIGHT, clamp, sign


class Particle:
    """One small moving dot: smoke, sparks, dust or glowing chakra."""
    def __init__(self, x, y, vx, vy, life, color, size=4, grav=0.0, kind="dot"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.grav, self.kind = color, size, grav, kind
        self.dead = False

    def update(self, dt, world):
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0:
            self.dead = True


class FloatText:
    """Damage numbers and short messages that drift upwards and fade out."""
    def __init__(self, text, x, y, color=(255, 255, 255), life=0.9, size=18, vy=-45):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life = self.max_life = life
        self.size, self.vy = size, vy
        self.dead = False

    def update(self, dt, world):
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0:
            self.dead = True


class FX:
    """Timed visual effect. kind decides how render.py draws it.
    kw: follow=<fighter>, dx, dy, owner, target, color, radius ..."""

    def __init__(self, kind, x, y, life, **kw):
        self.kind, self.x, self.y = kind, x, y
        self.life = self.max_life = life
        self.kw = kw
        self.dead = False

    @property
    def progress(self):
        return 1.0 - self.life / self.max_life

    def update(self, dt, world):
        self.life -= dt
        f = self.kw.get("follow")
        if f is not None:
            self.x = f.x + self.kw.get("dx", 0) * f.facing * f.scale
            self.y = f.y - self.kw.get("dy", 0) * f.scale
        if self.life <= 0:
            self.dead = True


class Hitbox:
    """An invisible damaging box. follow=True -> attached to owner (dx forward, dy up from feet)."""

    def __init__(self, owner, dx, dy, w, h, damage, life=0.1, kbx=160, kby=-120, stun=0.3,
                 interval=None, unblockable=False, knockdown=False, drain=0, kind="melee",
                 follow=True, x=None, y=None, on_hit=None, sfx="hit"):
        self.owner = owner
        self.dx, self.dy, self.w, self.h = dx, dy, w, h
        self.damage, self.life = damage, life
        self.kbx, self.kby, self.stun = kbx, kby, stun
        self.interval = interval
        self.unblockable, self.knockdown, self.drain = unblockable, knockdown, drain
        self.kind, self.follow = kind, follow
        self.x, self.y = x, y
        self.on_hit, self.sfx = on_hit, sfx
        self.cooldowns = {}
        self.done = set()
        self.dead = False

    def rect(self):
        """The area this object currently occupies, used for collision checks."""
        if self.follow:
            s = self.owner.scale
            cx = self.owner.x + self.dx * self.owner.facing * s
            cy = self.owner.y - self.dy * s
            w, h = self.w * s, self.h * s
        else:
            cx, cy, w, h = self.x, self.y, self.w, self.h
        return pygame.Rect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))

    def update(self, dt, world):
        self.life -= dt
        if self.life <= 0 or (self.follow and self.owner.hp <= 0):
            self.dead = True
            return
        r = self.rect()
        for tgt in world.enemies_of(self.owner):
            if tgt in self.done:
                continue
            cd = self.cooldowns.get(tgt, 0) - dt
            self.cooldowns[tgt] = cd
            if cd > 0 or not r.colliderect(tgt.rect()):
                continue
            direction = self.owner.facing if self.follow else sign(tgt.x - r.centerx)
            res = world.hit(self.owner, tgt, self.damage, kbx=self.kbx, kby=self.kby, stun=self.stun,
                            unblockable=self.unblockable, knockdown=self.knockdown, drain=self.drain,
                            kind=self.kind, direction=direction, sfx=self.sfx)
            if res == "miss":
                continue
            if self.interval:
                self.cooldowns[tgt] = self.interval
            else:
                self.done.add(tgt)
            if self.on_hit:
                self.on_hit(self, tgt, res, world)
            if self.dead:
                return


class Projectile:
    """Anything that flies: kunai, shuriken, fireballs, the shadow, exploding kunai.
    `on_hit` / `on_expire` let a jutsu react when the projectile lands or runs out.
    """
    SMALL_WEAPONS = ("kunai", "shuriken", "star")

    def __init__(self, owner, kind, x, y, vx, vy, damage, w=16, h=10, life=2.0, grav=0.0,
                 pierce=False, kbx=120, kby=-60, stun=0.22, unblockable=False, knockdown=False,
                 on_hit=None, on_expire=None, ground_only=False, spin=0.0, drain=0, sfx="hit",
                 color=None):
        self.owner, self.kind = owner, kind
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.damage, self.w, self.h = damage, w, h
        self.life = life
        self.grav, self.pierce = grav, pierce
        self.kbx, self.kby, self.stun = kbx, kby, stun
        self.unblockable, self.knockdown = unblockable, knockdown
        self.on_hit, self.on_expire = on_hit, on_expire
        self.ground_only, self.spin, self.drain, self.sfx = ground_only, spin, drain, sfx
        self.color = color
        self.angle = 0.0
        self.age = 0.0
        self.hit_set = set()
        self.dead = False

    def rect(self):
        """The area this object currently occupies, used for collision checks."""
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), int(self.w), int(self.h))

    def expire(self, world):
        """Called when the projectile dies of old age or leaves the screen."""
        if not self.dead:
            self.dead = True
            if self.on_expire:
                self.on_expire(self, world)

    def update(self, dt, world):
        self.age += dt
        self.life -= dt
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        if self.kind in ("fire", "bigfire") and random.random() < 0.7:
            world.particles.append(Particle(self.x, self.y, random.uniform(-30, 30), random.uniform(-60, 0),
                                            0.35, random.choice([(255, 160, 40), (255, 90, 20), (255, 220, 90)]),
                                            size=self.w * 0.18 + 2, kind="glow"))
        if self.life <= 0 or self.x < -80 or self.x > SCREEN_W + 80 or (self.y > GROUND_Y + 6 and not self.ground_only):
            self.expire(world)
            return
        r = self.rect()
        for tgt in world.enemies_of(self.owner):
            if tgt in self.hit_set:
                continue
            if self.ground_only and not tgt.on_ground:
                continue
            if not r.colliderect(tgt.rect()):
                continue
            direction = sign(self.vx) if abs(self.vx) > 1 else sign(tgt.x - self.x)
            res = world.hit(self.owner, tgt, self.damage, kbx=self.kbx, kby=self.kby, stun=self.stun,
                            unblockable=self.unblockable, knockdown=self.knockdown, drain=self.drain,
                            kind="projectile", direction=direction, sfx=self.sfx)
            if res == "miss":
                continue
            self.hit_set.add(tgt)
            if res == "deflect":
                self.dead = True
                return
            if self.on_hit:
                self.on_hit(self, tgt, res, world)
            if not self.pierce:
                self.dead = True
                return


class Summon:
    """Helper actors. mode:
      rush    - run to the enemy and punch once
      thrower - stand still and throw `count` kunai
      fly     - fly straight at the enemy (air tackle)
      grab    - run to the enemy and hold them (bind)
      bite    - ninja pup: run in and bite `count` times
      drill   - spin-drill forward, multi hit
      pose    - just show a pose (used in scripted jutsu)
    """

    def __init__(self, owner, kind, x, y, mode, life=2.5, speed=450, damage=6, **kw):
        self.owner, self.kind, self.mode = owner, kind, mode
        self.x, self.y = x, y
        self.life, self.speed, self.damage = life, speed, damage
        self.kw = kw
        self.facing = kw.get("facing", owner.facing)
        self.scale = kw.get("scale", 1.0)
        self.t = 0.0
        self.count = 0
        self.state = kw.get("pose", "run")
        self.done = False
        self.grabbed = None
        self.hit_cd = 0.0
        self.vx = self.vy = 0.0
        self.dead = False
        if mode == "fly":
            tgt = None
            enemies = [e for e in owner.world.enemies_of(owner)] if owner.world else []
            if enemies:
                tgt = min(enemies, key=lambda e: abs(e.x - x))
            if tgt:
                ang = math.atan2((tgt.y - 30) - y, tgt.x - x)
            else:
                ang = 0 if self.facing > 0 else math.pi
            self.vx, self.vy = math.cos(ang) * speed, math.sin(ang) * speed
            self.facing = sign(self.vx)
            self.state = "dive"

    @property
    def palette(self):
        return self.owner.char["palette"]

    def rect(self):
        """The area this object currently occupies, used for collision checks."""
        s = self.scale
        if self.kind == "pup":
            return pygame.Rect(int(self.x - 16 * s), int(self.y - 22 * s), int(32 * s), int(22 * s))
        return pygame.Rect(int(self.x - 17 * s), int(self.y - 64 * s), int(34 * s), int(64 * s))

    def poof(self, world):
        """Disappear in a puff of smoke."""
        if not self.dead:
            self.dead = True
            world.smoke(self.x, self.y - 22 * self.scale, 10)
            world.play("poof")

    def update(self, dt, world):
        self.t += dt
        self.life -= dt
        self.hit_cd -= dt
        tgt = world.nearest_enemy(self.owner, self.x)
        if self.life <= 0 or tgt is None:
            if self.grabbed is not None:
                self.grabbed.bound = 0
            self.poof(world)
            return
        dx = tgt.x - self.x
        m = self.mode
        touching = self.rect().colliderect(tgt.rect())

        if m == "rush":
            if not self.done:
                self.facing = sign(dx)
                if touching:
                    self.done = True
                    self.state = "punch"
                    res = world.hit(self.owner, tgt, self.damage, kbx=280, kby=-220, stun=0.45,
                                    direction=self.facing, kind="jutsu", sfx="hit")
                    cb = self.kw.get("on_contact")
                    if cb:
                        cb(self, tgt, res, world)
                    self.life = min(self.life, 0.35)
                else:
                    self.x += self.facing * self.speed * dt
                    self.state = "run"
        elif m == "thrower":
            self.facing = sign(dx)
            total = self.kw.get("count", 3)
            self.state = "throw" if (self.t % 0.25) < 0.12 else "idle"
            if self.count < total and self.t >= 0.25 * (self.count + 1):
                self.count += 1
                world.throw_at(self.owner, self.x + self.facing * 12, self.y - 40, tgt, "kunai", self.damage)
            if self.count >= total and self.t > 0.25 * total + 0.3:
                self.poof(world)
        elif m == "fly":
            self.x += self.vx * dt
            self.y += self.vy * dt
            if touching and not self.done:
                self.done = True
                world.hit(self.owner, tgt, self.damage, kbx=320, kby=-260, stun=0.5, knockdown=True,
                          direction=self.facing, kind="jutsu", sfx="heavy")
                self.life = min(self.life, 0.1)
            if self.y > GROUND_Y + 4 or self.x < -40 or self.x > SCREEN_W + 40:
                self.poof(world)
        elif m == "grab":
            if self.grabbed is None and not self.done:
                self.facing = sign(dx)
                if touching:
                    self.done = True
                    res = world.hit(self.owner, tgt, self.damage, kbx=0, kby=0, stun=0.2,
                                    direction=self.facing, kind="jutsu", sfx="hit")
                    cb = self.kw.get("on_contact")
                    if res == "hit":
                        self.grabbed = tgt
                        self.state = "grab"
                        self.life = self.kw.get("bind", 1.3)
                    else:
                        self.life = 0.2
                    if cb:
                        cb(self, tgt, res, world)
                else:
                    self.x += self.facing * self.speed * dt
                    self.state = "run"
            elif self.grabbed is not None:
                self.x = self.grabbed.x - self.facing * 20
                self.y = self.grabbed.y
        elif m == "bite":
            self.facing = sign(dx)
            total = self.kw.get("count", 3)
            if not touching and self.count == 0:
                self.x += self.facing * self.speed * dt
                self.state = "run"
            else:
                self.state = "bite"
                if touching and self.hit_cd <= 0 and self.count < total:
                    self.count += 1
                    self.hit_cd = 0.25
                    last = self.count == total
                    world.hit(self.owner, tgt, self.damage, kbx=260 if last else 40, kby=-240 if last else -40,
                              stun=0.35, direction=self.facing, kind="jutsu", knockdown=last, sfx="hit")
                if self.count >= total or (not touching and self.count > 0 and self.hit_cd < -0.4):
                    self.life = min(self.life, 0.2)
        elif m == "drill":
            self.state = "drill"
            self.x += self.facing * self.speed * dt
            if touching and self.hit_cd <= 0 and self.count < self.kw.get("count", 4):
                self.count += 1
                self.hit_cd = self.kw.get("interval", 0.12)
                world.hit(self.owner, tgt, self.damage, kbx=160, kby=-140, stun=0.3,
                          direction=self.facing, kind="jutsu", sfx="hit")
            if self.x < STAGE_LEFT - 30 or self.x > STAGE_RIGHT + 30:
                self.poof(world)
        elif m == "pose":
            pass

        if m not in ("fly", "drill"):
            self.x = clamp(self.x, STAGE_LEFT, STAGE_RIGHT)
