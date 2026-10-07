"""
characters.py - THE ROSTER (edit fighters and jutsu here)
=========================================================
Each fighter is a dictionary of stats, colours and jutsu. A jutsu is just a
function that receives (fighter, world) and makes things happen, built from
the reusable helpers at the top of the file (dash_strike, rapid_strikes...).

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

from entities import FX, Hitbox, Projectile, Summon
from settings import GROUND_Y, MAX_HP, STAGE_LEFT, STAGE_RIGHT, clamp, sign


# =====================================================================
#  Helpers
# =====================================================================
def J(name, cost, fn, keys, desc, cond=None, hp_req=None):
    """Build one jutsu entry: display name, chakra cost, the function that performs
    it, the button combination shown in the menus, and an optional condition.
    """
    return {"name": name, "cost": cost, "fn": fn, "keys": keys, "desc": desc, "cond": cond, "hp_req": hp_req}


def enemy_dist(f, w):
    """Horizontal distance to the nearest opponent.
    """
    e = w.nearest_enemy(f)
    return abs(e.x - f.x) if e else 9999


def near(px):
    """Condition: use this jutsu only when the enemy is closer than `px` pixels.
    """
    return lambda f, w: enemy_dist(f, w) <= px


def far(px):
    """Condition: use this jutsu only when the enemy is further than `px` pixels.
    """
    return lambda f, w: enemy_dist(f, w) > px


def buffed(name):
    """Condition: only available while a given buff is active.
    """
    return lambda f, w: f.has_buff(name)


def face(f, w):
    """Turn to face the nearest enemy and return them.
    """
    e = w.nearest_enemy(f)
    if e and abs(e.x - f.x) > 2:
        f.facing = sign(e.x - f.x)
    return e


def cast(f, t, armor=False):
    """Lock the fighter into a casting pose for `t` seconds (armor = can't be
    interrupted by small hits).
    """
    f.lock = max(f.lock, t)
    f.vx = 0
    f.set_state("cast", force=True)
    if armor:
        f.armor = max(f.armor, t)


def throw_spread(f, w, count, dmg, kind="shuriken", spread=0.16, speed=640):
    """Fire several projectiles in a fan aimed at the enemy.
    """
    e = face(f, w)
    sx, sy = f.x + f.facing * 14, f.y - 40 * f.scale
    base = math.atan2((e.y - 30) - sy, e.x - sx) if e else (0 if f.facing > 0 else math.pi)
    for i in range(count):
        a = base + (i - (count - 1) / 2) * spread
        w.add_projectile(Projectile(f, kind, sx, sy, math.cos(a) * speed, math.sin(a) * speed, dmg * f.jp,
                                    w=16, h=16, life=1.6, spin=1000 if kind != "kunai" else 0,
                                    color=(120, 200, 255)))
    w.play("throw")


def triple_throw(dmg):
    """Build the shared 'three chakra shuriken' jutsu used by several fighters.
    """
    def fn(f, w):
        cast(f, 0.3)
        throw_spread(f, w, 3, dmg, kind="star")
    return fn


def buff_jutsu(name, dur, color, text):
    """Build a jutsu that simply switches a power-up on for a while.
    """
    def fn(f, w):
        cast(f, 0.5)
        f.add_buff(name, dur)
        w.add_fx(FX("burst", f.x, f.y - 30, 0.6, color=color, follow=f, dy=30))
        w.text(text, f.x, f.y - 90, color, 18)
    return fn


def dash_strike(f, w, dmg, speed=620, dur=0.35, windup=0.25, state="dash", kbx=380, kby=-350,
                knockdown=True, unblockable=False, fx=None, interval=None, hw=44, hh=40, scale=None,
                drain=0, stop=True, stun=0.5, sfx="heavy", armor=False, on_hit=None):
    """Build a charge-up-then-lunge attack (used by Thunder Palm, Drill Fang...).
    The fighter winds up, then dashes forward carrying a hitbox.
    """
    face(f, w)
    cast(f, windup, armor=armor)
    if fx:
        w.add_fx(FX(fx, f.x, f.y, windup + dur, follow=f, dx=20, dy=32))

    def go():
        def hit_cb(hb, tgt, res, world):
            if stop and f.move is not None:
                f.end_move()
            if on_hit:
                on_hit(hb, tgt, res, world)
        hb = Hitbox(f, 22, 30, hw, hh, dmg * f.jp, kbx=kbx, kby=kby, stun=stun, knockdown=knockdown,
                    unblockable=unblockable, interval=interval, kind="jutsu", sfx=sfx, drain=drain,
                    on_hit=hit_cb)
        f.start_move(state, dur, vx=f.facing * speed, hitbox=hb, scale=scale)
        w.play("swish")
    f.schedule(windup, go)


def rapid_strikes(f, w, hits, interval, dmg, final_dmg, dash_in=True, drain=0):
    """Close-range multi-hit: first strike must connect, then the rest are guaranteed."""
    e = face(f, w)
    if not e:
        return
    total = hits * interval + 0.3
    cast(f, total, armor=False)
    if dash_in and abs(e.x - f.x) > 60:
        w.smoke(f.x, f.y - 30, 8)
        f.x = clamp(e.x - f.facing * 42, STAGE_LEFT, STAGE_RIGHT)
        w.smoke(f.x, f.y - 30, 8)
    st = {"ok": None}

    def strike(i):
        def run():
            if e.hp <= 0 or st["ok"] is False:
                return
            last = i == hits - 1
            f.attack_pose = random.choice(["punch", "punch2", "palm", "kick"]) if not last else "palm"
            f.set_state("attack", force=True)
            res = w.hit(f, e, (final_dmg if last else dmg) * f.jp, kbx=400 if last else 15,
                        kby=-360 if last else 0, stun=interval + 0.2, knockdown=last,
                        unblockable=i > 0, sub_ok=i == 0, kind="jutsu", direction=f.facing, drain=drain,
                        sfx="heavy" if last else "hit")
            if i == 0:
                st["ok"] = res == "hit"
                if not st["ok"]:
                    f.lock = 0.2
                    f.armor = 0
                    return
                f.armor = total
            if st["ok"] and not last:
                e.bound = max(e.bound, interval + 0.12)
        return run

    for i in range(hits):
        f.schedule(0.05 + i * interval, strike(i))


def slam_landing(dmg, width=150):
    """Build the shockwave that goes off when a jumping slam hits the ground.
    """
    def make(f, w):
        def land():
            w.add_fx(FX("ring", f.x, f.y - 6, 0.5, radius=width * 0.7, color=(230, 210, 170)))
            w.dust(f.x, f.y, 16)
            w.add_hitbox(Hitbox(f, 0, 0, width, 70, dmg * f.jp, life=0.12, kbx=380, kby=-420, stun=0.5,
                                knockdown=True, kind="jutsu", follow=False, x=f.x, y=f.y - 30, sfx="explode"))
            w.shake = 0.35
            w.play("explode")
        return land
    return make


# =====================================================================
#  1. KAITO  -  shadow clone fighter (Str 3 / Jutsu 4 / Speed 6)
# =====================================================================
def kaito_clone(f, w):
    """Clone Strike: a shadow clone rushes in to punch, or stands back throwing
    kunai when the enemy is far away.
    """
    e = face(f, w)
    cast(f, 0.35)
    sx = clamp(f.x + f.facing * 36, STAGE_LEFT, STAGE_RIGHT)
    w.smoke(sx, f.y - 25, 10)
    if e and abs(e.x - f.x) < 260:
        w.add_summon(Summon(f, "clone", sx, f.y, "rush", life=2.0, speed=520, damage=4.0 * f.jp))
    else:
        w.add_summon(Summon(f, "clone", sx, f.y, "thrower", life=2.5, damage=1.6 * f.jp, count=2))


def kaito_pinwheel(f, w):
    """Pinwheel Shuriken: a giant shuriken that turns into a kunai-throwing clone.
    """
    face(f, w)
    cast(f, 0.35)

    def to_clone(p, world):
        world.smoke(p.x, p.y, 12)
        world.add_summon(Summon(p.owner, "clone", clamp(p.x, STAGE_LEFT, STAGE_RIGHT), GROUND_Y, "thrower",
                                life=2.2, damage=2.2 * p.owner.jp, count=3))
    w.add_projectile(Projectile(f, "bigshuriken", f.x + f.facing * 24, f.y - 44, f.facing * 430, 0, 8 * f.jp,
                                w=44, h=44, life=0.85, spin=1100, kbx=220, kby=-160, stun=0.4,
                                on_hit=lambda p, t, r, wd: to_clone(p, wd), on_expire=to_clone))
    w.play("throw")


def kaito_barrage(f, w):
    """Clone Barrage: four clones kick the enemy into the air, then Kaito spikes
    them back down. The chain stops if the first kick is blocked or substituted.
    """
    e = face(f, w)
    if not e:
        return
    cast(f, 1.7, armor=True)
    st = {"ok": None}
    offsets = [-40, 40, -26, 26]

    def kick(i):
        def run():
            if st["ok"] is False or e.hp <= 0:
                return
            sx = clamp(e.x + offsets[i], STAGE_LEFT, STAGE_RIGHT)
            sy = min(GROUND_Y, e.y + 20 * i)
            w.smoke(sx, sy - 25, 6)
            w.add_summon(Summon(f, "clone", sx, sy, "pose", life=0.35, pose="kick_up",
                                facing=sign(e.x - sx)))
            res = w.hit(f, e, 3.2 * f.jp, kbx=0, kby=-430 if i == 0 else -280, stun=0.7,
                        unblockable=i > 0, sub_ok=i == 0, kind="jutsu", direction=f.facing)
            if i == 0:
                st["ok"] = res == "hit"
                if not st["ok"]:
                    f.lock, f.armor = 0.2, 0
        return run

    for i in range(4):
        f.schedule(0.15 + i * 0.18, kick(i))

    def finisher():
        if not st["ok"] or e.hp <= 0:
            return
        w.smoke(f.x, f.y - 30, 8)
        f.x = clamp(e.x - f.facing * 12, STAGE_LEFT, STAGE_RIGHT)
        f.y = max(60, e.y - 40)
        f.attack_pose = "dive"
        f.set_state("air_attack", force=True)
        w.hit(f, e, 14 * f.jp, kbx=200, kby=650, stun=0.6, knockdown=True, unblockable=True, sub_ok=False,
              kind="jutsu", direction=f.facing, sfx="explode")
        f.vy = -200
        w.shake = 0.35
    f.schedule(0.15 + 4 * 0.18 + 0.1, finisher)


def kaito_orb(f, w):
    """Spiral Orb (ultimate): a clone grabs the enemy so they cannot move while
    Kaito charges a swirling ball of chakra and drives it into them.
    """
    face(f, w)
    cast(f, 0.3)
    sx = clamp(f.x + f.facing * 30, STAGE_LEFT, STAGE_RIGHT)
    w.smoke(sx, f.y - 25, 8)

    def grabbed(s, t, res, world):
        if res != "hit":
            return
        t.bound = 1.3
        f.lock, f.armor = 1.3, 1.3
        f.set_state("cast", force=True)
        world.add_fx(FX("orb_charge", f.x, f.y, 0.75, follow=f, dx=16, dy=34))

        def strike():
            if t.hp <= 0:
                return
            world.smoke(f.x, f.y - 30, 8)
            f.x = clamp(t.x - f.facing * 34, STAGE_LEFT, STAGE_RIGHT)
            f.y = t.y
            f.attack_pose = "palm"
            f.set_state("attack", force=True)
            world.add_fx(FX("orb_blast", t.x, t.y - 30, 0.5))
            t.bound = 0
            world.hit(f, t, 22 * f.jp, kbx=540, kby=-420, stun=0.8, knockdown=True, unblockable=True,
                      sub_ok=False, kind="jutsu", direction=f.facing, sfx="explode")
            world.shake = 0.5
        f.schedule(0.75, strike)

    w.add_summon(Summon(f, "clone", sx, f.y, "grab", life=1.6, speed=560, damage=1, bind=1.3, on_contact=grabbed))


def kaito_air(f, w):
    """Clone Tackle: a clone flies at the enemy while Kaito is in the air.
    """
    w.smoke(f.x, f.y - 30, 6)
    w.add_summon(Summon(f, "clone", f.x + f.facing * 10, f.y, "fly", life=1.2, speed=620, damage=8 * f.jp))


# =====================================================================
#  2. REN  -  fire & lightning prodigy (Str 2 / Jutsu 2 / Speed 8)
# =====================================================================
def ren_ember_volley(f, w):
    """Ember Volley: five small fireballs fired in quick succession.
    """
    e = face(f, w)
    cast(f, 0.5)

    def shoot(i):
        def run():
            tgt = w.nearest_enemy(f)
            ang = math.atan2((tgt.y - 30) - (f.y - 40), tgt.x - f.x) if tgt else (0 if f.facing > 0 else math.pi)
            ang += random.uniform(-0.12, 0.12)
            w.add_projectile(Projectile(f, "fire", f.x + f.facing * 16, f.y - 40, math.cos(ang) * 560,
                                        math.sin(ang) * 560, 1.9 * f.jp, w=16, h=16, life=1.5, sfx="hit"))
        return run
    for i in range(5):
        f.schedule(0.05 + i * 0.07, shoot(i))


def ren_great_fireball(f, w):
    """Great Fireball: one huge piercing fireball, used when the enemy is close.
    """
    face(f, w)
    cast(f, 0.55)

    def fire():
        w.add_projectile(Projectile(f, "bigfire", f.x + f.facing * 40, f.y - 44, f.facing * 380, 0, 10.5 * f.jp,
                                    w=70, h=70, life=1.3, pierce=True, kbx=320, kby=-320, knockdown=True,
                                    stun=0.5, sfx="explode"))
        w.play("explode")
    f.schedule(0.2, fire)


def ren_rising_dragon(f, w):
    """Rising Dragon: kick the enemy skywards, juggle them with teleporting hits,
    then slam them into the ground.
    """
    e = face(f, w)
    if not e:
        return
    cast(f, 1.6, armor=True)
    if abs(e.x - f.x) > 70:
        w.smoke(f.x, f.y - 30, 8)
        f.x = clamp(e.x - f.facing * 40, STAGE_LEFT, STAGE_RIGHT)
    st = {"ok": None}

    def first():
        f.attack_pose = "kick_up"
        f.set_state("attack", force=True)
        res = w.hit(f, e, 6 * f.jp, kbx=0, kby=-650, stun=1.0, kind="jutsu", direction=f.facing)
        st["ok"] = res == "hit"
        if not st["ok"]:
            f.lock, f.armor = 0.2, 0

    def air_hit(i):
        def run():
            if not st["ok"] or e.hp <= 0:
                return
            side = 1 if i % 2 == 0 else -1
            f.x = clamp(e.x - f.facing * 30 * side, STAGE_LEFT, STAGE_RIGHT)
            f.facing = sign(e.x - f.x)
            f.y = e.y + 8
            f.suspend = e.suspend = 0.2
            e.vy = 0
            f.attack_pose = random.choice(["punch", "kick", "punch2"])
            f.set_state("attack", force=True)
            w.smoke(f.x, f.y - 30, 4)
            w.hit(f, e, 2.5 * f.jp, kbx=0, kby=-40, stun=0.5, unblockable=True, sub_ok=False, kind="jutsu",
                  direction=f.facing)
        return run

    def slam():
        if not st["ok"] or e.hp <= 0:
            return
        f.y = max(60, e.y - 30)
        f.attack_pose = "dive"
        f.set_state("air_attack", force=True)
        w.hit(f, e, 12 * f.jp, kbx=150, kby=750, stun=0.6, knockdown=True, unblockable=True, sub_ok=False,
              kind="jutsu", direction=f.facing, sfx="explode")
        w.shake = 0.4

    f.schedule(0.05, first)
    for i in range(4):
        f.schedule(0.35 + i * 0.15, air_hit(i))
    f.schedule(1.05, slam)


def ren_thunder_palm(f, w):
    """Thunder Palm (ultimate): lightning gathers in his hand, then a huge lunge.
    Hawk Eye makes it 30% stronger.
    """
    boost = 1.3 if f.has_buff("hawk") else 1.0
    dash_strike(f, w, 21 * boost, speed=800, dur=0.4, windup=0.55, state="dash", kbx=560, kby=-380,
                fx="lightning", hw=48, stop=True, armor=True, sfx="explode")


def ren_air(f, w):
    """Aerial Ember: a fireball thrown down at the enemy from mid-air.
    """
    e = face(f, w)
    ang = math.atan2((e.y - 30) - f.y, e.x - f.x) if e else math.pi / 4
    w.add_projectile(Projectile(f, "bigfire", f.x, f.y - 30, math.cos(ang) * 480, math.sin(ang) * 480, 8 * f.jp,
                                w=32, h=32, life=1.2, kbx=220, kby=-200, stun=0.4))
    w.play("jutsu")


# =====================================================================
#  3. MIRA  -  medic with monster strength (Str 2 / Jutsu 1 / Speed 7)
# =====================================================================
def mira_fury(f, w):
    """Fury Fists: a rapid flurry of close-range chakra punches.
    """
    rapid_strikes(f, w, 6, 0.09, 4.0, 11, dash_in=False)


def mira_heal(f, w):
    """Healing Touch: medical jutsu that restores 20 HP over about a second.
    """
    cast(f, 1.0)
    w.add_fx(FX("heal", f.x, f.y, 1.0, follow=f))
    w.play("heal")

    def tick():
        f.hp = min(MAX_HP, f.hp + 4)
        w.text("+4", f.x, f.y - 80, (120, 255, 140), 14, 0.5)
    for i in range(5):
        f.schedule(0.15 + i * 0.18, tick)


def mira_uppercut(f, w):
    """Power Uppercut: a rising chakra punch that launches the enemy.
    """
    face(f, w)
    cast(f, 0.12)

    def go():
        f.attack_pose = "uppercut"
        hb = Hitbox(f, 18, 40, 40, 60, 15 * f.jp, kbx=160, kby=-640, stun=0.6, knockdown=True, kind="jutsu",
                    sfx="heavy")
        f.start_move("attack", 0.35, vx=f.facing * 140, vy=-520, hitbox=hb)
        f.attack_pose = "uppercut"
    f.schedule(0.1, go)


def mira_shatter(f, w):
    """Shattering Punch (ultimate): one enormous punch that cracks the ground.
    """
    def cracked(hb, tgt, res, world):
        world.add_fx(FX("crack", tgt.x, GROUND_Y, 0.9))
        world.shake = 0.6
    dash_strike(f, w, 34, speed=520, dur=0.3, windup=0.45, state="dash", kbx=680, kby=-300, fx="fist_glow",
                stop=True, armor=True, sfx="explode", on_hit=cracked)


# =====================================================================
#  4. YUNA  -  gentle-palm eye user (Str 2 / Jutsu 2 / Speed 8)
# =====================================================================
def yuna_soft_palm(f, w):
    """Soft Palm: a single precise strike that also drains the enemy's chakra.
    """
    dash_strike(f, w, 17, speed=420, dur=0.2, windup=0.15, state="dash", kbx=380, kby=-150, knockdown=False,
                stun=0.7, fx="palm_glow", drain=15, stop=True)


def yuna_whirl(f, w):
    """Whirl Guard: spin with arms out - damages nearby foes and deflects weapons.
    """
    cast(f, 0.05)
    hb = Hitbox(f, 0, 30, 96, 76, 5 * f.jp, interval=0.15, kbx=160, kby=-120, stun=0.3, kind="jutsu")
    f.start_move("spin", 1.0, vx=0, hitbox=hb)
    f.deflect = 1.0
    w.add_fx(FX("dome", f.x, f.y, 1.0, follow=f, dy=30))


def yuna_hundred(f, w):
    """Hundred Palms (ultimate): a blinding chain of palm strikes.
    """
    rapid_strikes(f, w, 9, 0.1, 3.4, 15, dash_in=True, drain=3)


# =====================================================================
#  5. SORA  -  shadow strategist (Str 3 / Jutsu 3 / Speed 6)
# =====================================================================
def sora_meditate(f, w):
    """Meditation: think up a plan instead of attacking - doubles chakra gain.
    Costs no chakra but needs at least 40 health.
    """
    cast(f, 0.7)
    f.add_buff("meditate", 10)
    w.add_fx(FX("burst", f.x, f.y - 30, 0.7, color=(200, 200, 255), follow=f, dy=30))
    w.text("Chakra x2", f.x, f.y - 90, (200, 200, 255), 16)


def sora_shadow(strangle):
    """Build Sora's shadow jutsu. The shadow creeps along the ground and, if it
    connects, holds the enemy still: then either an exploding kunai (Shadow Bind)
    or crushing shadow tendrils (Shadow Crush, his ultimate).
    """
    def fn(f, w):
        face(f, w)
        cast(f, 0.45)

        def on_hit(p, t, res, world):
            if res != "hit":
                return
            dur = 2.0 if strangle else 1.6
            t.bound = dur
            t.vx = 0
            world.add_fx(FX("shadow_link", 0, 0, dur, owner=f, target=t))
            f.lock = dur
            f.set_state("cast", force=True)
            if strangle:
                world.add_fx(FX("strangle", t.x, t.y, dur, follow=t))
                for i in range(4):
                    f.schedule(0.3 + i * 0.4, lambda: world.hit(f, t, 7.5 * f.jp, kbx=0, kby=0, stun=0.2,
                                                                unblockable=True, sub_ok=False, kind="jutsu")
                               if t.hp > 0 else None)
            else:
                def throw():
                    if t.hp <= 0:
                        return
                    ang = math.atan2((t.y - 30) - (f.y - 40), t.x - f.x)

                    def boom(pk, tgt, r, wd):
                        wd.add_fx(FX("explosion", pk.x, pk.y, 0.5))
                        wd.play("explode")
                        wd.shake = 0.35
                    world.add_projectile(Projectile(f, "tagkunai", f.x + f.facing * 14, f.y - 40,
                                                    math.cos(ang) * 720, math.sin(ang) * 720, 18 * f.jp,
                                                    w=22, h=10, life=1.5, unblockable=True, knockdown=True,
                                                    kbx=380, kby=-380, on_hit=boom, sfx="explode"))
                    world.play("throw")
                f.schedule(0.5, throw)

        w.add_projectile(Projectile(f, "shadow", f.x + f.facing * 24, f.y - 5, f.facing * 620, 0, 0.5,
                                    w=48, h=14, life=1.15, ground_only=True, on_hit=on_hit, kbx=0, kby=0,
                                    stun=0.1))
    return fn


def sora_cyclone(f, w):
    """Cyclone Kick: a travelling spin kick that hits several times.
    """
    face(f, w)
    hb = Hitbox(f, 0, 28, 84, 52, 7 * f.jp, interval=0.15, kbx=140, kby=-220, stun=0.35, kind="jutsu")
    f.start_move("spin_kick", 0.6, vx=f.facing * 160, hitbox=hb)


# =====================================================================
#  6. TARO  -  beast-partner brawler with ninja pup (Str 3 / Jutsu 4 / Speed 7)
# =====================================================================
def taro_pup(f, w):
    """Pup Assault: Kuro charges in and bites the enemy three times.
    """
    cast(f, 0.3)
    f.pet_out = 2.4
    w.add_summon(Summon(f, "pup", f.pet_x, f.y, "bite", life=2.4, speed=620, damage=4 * f.jp, count=3))
    w.play("jump")


def taro_pup_air(f, w):
    """Aerial Pup Assault: Kuro dives at the enemy from the air.
    """
    f.pet_out = 1.3
    w.add_summon(Summon(f, "pup", f.x, f.y - 20, "fly", life=1.2, speed=640, damage=7 * f.jp))


def taro_drill(f, w):
    """Drill Fang: Taro spins into a drill and rams straight through the enemy.
    """
    f.pet_out = 1.0
    dash_strike(f, w, 6.2, speed=620, dur=0.55, windup=0.2, state="drill", kbx=200, kby=-120, knockdown=False,
                interval=0.12, stun=0.3, stop=False, sfx="hit")


def taro_twin(f, w):
    """Twin Drill (ultimate): Taro and a copy drill the enemy from both sides.
    """
    e = face(f, w)
    f.pet_out = 1.2
    dash_strike(f, w, 6.8, speed=700, dur=0.6, windup=0.25, state="drill", kbx=200, kby=-150, knockdown=False,
                interval=0.12, stun=0.3, stop=False, sfx="hit")
    if e:
        sx = clamp(e.x + f.facing * 170, STAGE_LEFT, STAGE_RIGHT)
        w.smoke(sx, f.y - 20)
        f.schedule(0.25, lambda: w.add_summon(Summon(f, "clone_drill", sx, f.y, "drill", life=0.8, speed=700,
                                                     damage=5 * f.jp, facing=-f.facing, count=4)))


def taro_great_fang(f, w):
    """Titan Fang (ultimate): only while Wild Focus is active - a giant fused drill
    that hits repeatedly. Using it consumes the Wild Focus buff.
    """
    f.buffs.pop("focus", None)
    f.pet_out = 1.3
    w.text("Titan Fang!", f.x, f.y - 110, (255, 120, 80), 22)
    dash_strike(f, w, 5.6, speed=650, dur=0.85, windup=0.35, state="bigdrill", kbx=420, kby=-300,
                knockdown=False, interval=0.1, hw=80, hh=80, scale=2.1, stun=0.35, stop=False, armor=True,
                sfx="heavy")


# =====================================================================
#  7. GORO  -  big-bodied tank (Str 3 / Jutsu 2 / Speed 6)
# =====================================================================
def goro_roll(f, w):
    """Boulder Roll: curl into a ball and roll, bouncing off the stage edges.
    """
    face(f, w)
    cast(f, 0.25)
    f.schedule(0.2, lambda: f.start_move(
        "ball", 1.3, vx=f.facing * 520, scale=1.7, bounce=True,
        hitbox=Hitbox(f, 0, 28, 60, 56, 16 * f.jp, kbx=420, kby=-360, stun=0.5, knockdown=True, kind="jutsu",
                      sfx="heavy")))


def goro_body_slam(f, w):
    """Body Slam: grow huge, leap at the enemy and crash down with a shockwave.
    """
    e = face(f, w)
    dx = (e.x - f.x) if e else f.facing * 200
    f.start_move("slam", 3.0, vx=clamp(dx / 0.95, -520, 520), vy=-950, scale=2.0,
                 on_land=slam_landing(22, 160)(f, w))


def goro_top(f, w):
    """Spinning Top: enlarge and spin on the spot, hitting anyone close repeatedly.
    """
    face(f, w)
    f.start_move("top", 1.1, vx=f.facing * 90, scale=1.9,
                 hitbox=Hitbox(f, 0, 28, 72, 58, 8 * f.jp, interval=0.18, kbx=260, kby=-260, stun=0.35,
                               kind="jutsu"))


def goro_mega(f, w):
    """Mega Boulder (ultimate): a supersized boulder that steers towards the enemy.
    """
    face(f, w)
    cast(f, 0.3, armor=True)
    f.schedule(0.3, lambda: f.start_move(
        "ball", 2.2, vx=f.facing * 460, scale=2.4, bounce=True, homing=900,
        hitbox=Hitbox(f, 0, 22, 44, 44, 11 * f.jp, interval=0.25, kbx=440, kby=-380, stun=0.5, knockdown=True,
                      kind="jutsu", sfx="heavy")))


def goro_air_slam(f, w):
    """Aerial Slam: drop from the sky and shake the ground on landing.
    """
    f.start_move("slam", 2.0, vx=f.facing * 150, vy=700, scale=1.8, on_land=slam_landing(15, 130)(f, w))


# =====================================================================
#  8. TETSU  -  taijutsu master (shop unlock)
# =====================================================================
def tetsu_rising(f, w):
    """Rising Leaf: a launching rising kick.
    """
    face(f, w)
    hb = Hitbox(f, 18, 40, 44, 64, 11 * f.jp, kbx=150, kby=-660, stun=0.6, knockdown=True, kind="jutsu",
                sfx="heavy")
    f.attack_pose = "kick_up"
    f.start_move("attack", 0.35, vx=f.facing * 160, vy=-560, hitbox=hb)
    f.attack_pose = "kick_up"


def tetsu_storm(f, w):
    """Kunai Storm: five kunai thrown in a fan.
    """
    cast(f, 0.35)
    throw_spread(f, w, 5, 2.6, kind="kunai", spread=0.12, speed=760)


def tetsu_hurricane(f, w):
    """Hurricane Heel: travelling spin kicks.
    """
    face(f, w)
    hb = Hitbox(f, 0, 26, 90, 50, 2.8 * f.jp, interval=0.14, kbx=150, kby=-200, stun=0.35, kind="jutsu")
    f.start_move("spin_kick", 0.7, vx=f.facing * 220, hitbox=hb)


def tetsu_gate(f, w):
    """Gate Burst (ultimate): pushes his body past its limit - 10 seconds of extra
    power and speed, plus an immediate dash strike.
    """
    f.add_buff("gate", 7)      # BALANCE (v1.1): 10s -> 7s, the buff was too dominant
    w.text("Gate Burst!", f.x, f.y - 110, (255, 90, 90), 22)
    dash_strike(f, w, 17, speed=900, dur=0.35, windup=0.4, kbx=600, kby=-420, fx="burst_aura", armor=True,
                sfx="explode")


def tetsu_axe(f, w):
    """Falling Axe: a heel drop from the air that slams the enemy down.
    """
    face(f, w)
    hb = Hitbox(f, 10, 6, 44, 34, 10 * f.jp, kbx=220, kby=500, stun=0.5, knockdown=True, kind="jutsu",
                sfx="heavy")
    f.attack_pose = "dive"
    f.start_move("air_attack", 1.5, vx=f.facing * 200, vy=950, hitbox=hb,
                 on_land=lambda: (w.dust(f.x, f.y, 12), setattr(w, "shake", 0.25)))
    f.attack_pose = "dive"


# =====================================================================
#  ROSTER
# =====================================================================
ROSTER = [
    {
        "id": "kaito", "name": "Kaito Arashi", "title": "The Clone Brawler",
        "description": "A loud, stubborn orphan who never gives up. He floods the battlefield with shadow "
                       "copies of himself and dreams of becoming his village's leader.",
        "strength": 3, "jutsu_power": 4, "speed": 6, "chakra_gain": 6, "combo": 4,
        "palette": {"skin": (250, 215, 180), "hair": (90, 55, 35), "hair_style": "messy",
                    "outfit": (40, 150, 130), "outfit_dark": (25, 95, 85), "pants": (50, 60, 80),
                    "accent": (230, 80, 60), "eye": (40, 90, 60), "chakra": (80, 220, 170)},
        "jutsus": {
            "up": [J("Clone Strike", 30, kaito_clone, "Up + Chakra",
                     "A clone punches nearby foes, or throws kunai if they are far.")],
            "throw": [J("Pinwheel Shuriken", 35, kaito_pinwheel, "Throw + Chakra",
                        "Giant shuriken that turns into a kunai-throwing clone.")],
            "attack": [J("Clone Barrage", 80, kaito_barrage, "Attack + Chakra",
                         "Four clones kick the foe skyward, then a crushing drop kick.")],
            "special": [J("Spiral Orb", 90, kaito_orb, "Attack x2 (hold) + Chakra",
                          "A clone grabs the enemy while Kaito slams a swirling chakra orb.")],
            "air": [J("Clone Tackle", 30, kaito_air, "Chakra in air", "A clone tackles the enemy.")],
        },
    },
    {
        "id": "ren", "name": "Ren Kurogane", "title": "The Lone Flame",
        "description": "Last heir of a fallen clan, cold and brilliant. His golden hawk eyes read every "
                       "move, and he fights with fire and lightning to settle an old score.",
        "strength": 2, "jutsu_power": 2, "speed": 8, "chakra_gain": 9, "combo": 5,
        "palette": {"skin": (245, 220, 195), "hair": (200, 200, 215), "hair_style": "swept",
                    "outfit": (110, 70, 160), "outfit_dark": (70, 40, 110), "pants": (40, 40, 55),
                    "accent": (240, 200, 60), "eye": (60, 60, 80), "chakra": (170, 120, 255)},
        "jutsus": {
            "throw": [J("Great Fireball", 30, ren_great_fireball, "Throw + Chakra (close)",
                        "A huge piercing fireball when the enemy is close.", cond=near(160)),
                      J("Ember Volley", 30, ren_ember_volley, "Throw + Chakra (far)",
                        "A stream of small fireballs.")],
            "attack": [J("Hawk Eye", 70, buff_jutsu("hawk", 12, (255, 200, 60), "Hawk Eye!"), "Attack + Chakra",
                         "12s: +40% damage, and a stronger Thunder Palm.")],
            "up": [J("Rising Dragon", 80, ren_rising_dragon, "Up + Chakra",
                     "Kick the foe into the air and chain a juggle combo.")],
            "special": [J("Thunder Palm", 90, ren_thunder_palm, "Attack x2 (hold) + Chakra",
                          "Lightning gathers in his hand, then a devastating lunge.")],
            "air": [J("Aerial Ember", 30, ren_air, "Chakra in air", "A fireball fired from the air.")],
        },
    },
    {
        "id": "mira", "name": "Mira Hoshino", "title": "The Iron Blossom",
        "description": "A sharp-minded medical ninja with incredible chakra control. What she lacks in "
                       "raw power she makes up with healing arts and fists that crack the ground.",
        # BALANCE (v1.1): strength 2 -> 3 and jutsu power 1 -> 2. Isolated damage testing put
        # Mira at 39% of the roster average, far below every other fighter.
        "strength": 4, "jutsu_power": 2, "speed": 7, "chakra_gain": 9, "combo": 4,
        "palette": {"skin": (240, 200, 170), "hair": (30, 30, 40), "hair_style": "bob",
                    "outfit": (230, 180, 40), "outfit_dark": (170, 120, 20), "pants": (60, 50, 70),
                    "accent": (60, 160, 220), "eye": (40, 120, 90), "chakra": (120, 255, 150)},
        "jutsus": {
            "attack": [J("Fury Fists", 30, mira_fury, "Attack + Chakra (close)",
                         "An onslaught of chakra punches.", cond=near(110)),
                       J("Triple Star Throw", 30, triple_throw(4), "Attack + Chakra (far)",
                         "Three chakra-charged shuriken.")],
            "throw": [J("Healing Touch", 50, mira_heal, "Throw + Chakra", "Restores 20 HP over time.")],
            "up": [J("Power Uppercut", 50, mira_uppercut, "Up + Chakra", "Chakra-fuelled rising punch.")],
            "special": [J("Shattering Punch", 90, mira_shatter, "Attack x2 (hold) + Chakra",
                          "All her chakra released in one ground-cracking punch.")],
            "air": [J("Aerial Triple Star", 30, triple_throw(4), "Chakra in air", "Three shuriken from above.")],
        },
    },
    {
        "id": "yuna", "name": "Yuna Shirogane", "title": "The Quiet Palm",
        "description": "Shy and gentle, but unbreakably determined. Her clan's True Sight lets her see "
                       "chakra paths, and her palm strikes seal away an opponent's energy.",
        "strength": 2, "jutsu_power": 2, "speed": 8, "chakra_gain": 6, "combo": 4,
        "palette": {"skin": (250, 225, 205), "hair": (40, 50, 110), "hair_style": "long",
                    "outfit": (200, 70, 80), "outfit_dark": (140, 40, 55), "pants": (50, 50, 70),
                    "accent": (240, 240, 240), "eye": (160, 160, 200), "chakra": (170, 210, 255)},
        "jutsus": {
            "up": [J("True Sight", 60, buff_jutsu("sight", 15, (170, 210, 255), "True Sight!"), "Up + Chakra",
                     "15s: her attacks drain the enemy's chakra.")],
            "attack": [J("Soft Palm", 30, yuna_soft_palm, "Attack + Chakra (close)",
                         "One powerful palm strike that drains chakra.", cond=near(110)),
                       J("Triple Star Throw", 30, triple_throw(4), "Attack + Chakra (far)",
                         "Three chakra-charged shuriken.")],
            "throw": [J("Whirl Guard", 50, yuna_whirl, "Throw + Chakra",
                        "Spinning chakra dome: deflects weapons and hurts foes.")],
            "special": [J("Hundred Palms", 90, yuna_hundred, "Attack x2 (hold) + Chakra",
                          "A blinding chain of palm strikes.")],
            "air": [J("Aerial Triple Star", 30, triple_throw(4), "Chakra in air", "Three shuriken from above.")],
        },
    },
    {
        "id": "sora", "name": "Sora Kagemura", "title": "The Lazy Genius",
        "description": "A strategist who would rather watch clouds than fight. When he does, his shadow "
                       "stretches out to trap enemies in a plan they never saw coming.",
        # BALANCE (v1.1): chakra gain 4.5 -> 6.5 and combo 3 -> 4. Sora lost every test match
        # because his shadow jutsu cost more chakra than he could realistically accumulate.
        "strength": 3, "jutsu_power": 3, "speed": 6, "chakra_gain": 6.5, "combo": 4,
        "palette": {"skin": (235, 200, 165), "hair": (235, 235, 240), "hair_style": "spiky",
                    "outfit": (50, 90, 170), "outfit_dark": (30, 55, 115), "pants": (45, 45, 60),
                    "accent": (120, 200, 120), "eye": (50, 50, 60), "chakra": (140, 140, 200)},
        "jutsus": {
            "up": [J("Meditation", 0, sora_meditate, "Up + Chakra (40+ HP)",
                     "10s: chakra gain doubled.", hp_req=40)],
            "throw": [J("Shadow Bind", 40, sora_shadow(False), "Throw + Chakra",
                        "Shadow traps the foe, then an exploding kunai.")],
            "attack": [J("Cyclone Kick", 55, sora_cyclone, "Attack + Chakra (close)",
                         "Rapid full-circle spinning kicks.", cond=near(130)),
                       J("Triple Star Throw", 40, triple_throw(6), "Attack + Chakra (far)",
                         "Three chakra-charged shuriken.")],
            "special": [J("Shadow Crush", 90, sora_shadow(True), "Attack x2 (hold) + Chakra",
                          "Binds the foe and crushes them with shadow tendrils.")],
            "air": [J("Aerial Triple Star", 40, triple_throw(4.5), "Chakra in air", "Three shuriken from above.")],
        },
    },
    {
        "id": "taro", "name": "Taro Kibamaru", "title": "The Wild Fang",
        "description": "Brash, impatient and fearless. Taro fights side by side with his loyal ninja pup "
                       "Kuro, and together they drill through anything in their way.",
        "strength": 3, "jutsu_power": 4, "speed": 7, "chakra_gain": 6, "combo": 3,
        "palette": {"skin": (225, 180, 140), "hair": (170, 50, 40), "hair_style": "bandana",
                    "outfit": (120, 85, 55), "outfit_dark": (80, 55, 35), "pants": (55, 55, 55),
                    "accent": (60, 60, 60), "eye": (90, 50, 30), "chakra": (255, 150, 90),
                    "companion": "pup"},
        "jutsus": {
            "up": [J("Pup Assault", 30, taro_pup, "Up + Chakra", "Kuro dashes in and bites the enemy.")],
            "throw": [J("Wild Focus", 70, buff_jutsu("focus", 15, (255, 120, 80), "Wild Focus!"), "Throw + Chakra",
                        "15s: speed becomes 8 and unlocks Titan Fang.")],
            "attack": [J("Drill Fang", 50, taro_drill, "Attack + Chakra", "Spins into a drill and rams the foe.")],
            "special": [J("Titan Fang", 90, taro_great_fang, "Attack x2 (hold) + Chakra (Wild Focus)",
                          "Giant fused drill (needs Wild Focus).", cond=buffed("focus")),
                        J("Twin Drill", 90, taro_twin, "Attack x2 (hold) + Chakra",
                          "Taro and a copy drill the foe from both sides.")],
            "air": [J("Aerial Pup Assault", 30, taro_pup_air, "Chakra in air", "Kuro dives at the enemy.")],
        },
    },
    {
        "id": "goro", "name": "Goro Ookawa", "title": "The Rolling Boulder",
        "description": "Big-hearted and bigger-bodied, Goro loves snacks more than fighting. His clan's "
                       "expansion arts turn him into a giant rolling boulder of pure force.",
        # BALANCE (v1.1): chakra gain 6 -> 7 so his expensive expansion jutsu are usable.
        "strength": 3, "jutsu_power": 2, "speed": 6, "chakra_gain": 8, "combo": 4,
        "palette": {"skin": (240, 200, 160), "hair": (70, 130, 60), "hair_style": "topknot",
                    "outfit": (150, 150, 160), "outfit_dark": (100, 100, 110), "pants": (70, 60, 50),
                    "accent": (200, 60, 60), "eye": (50, 40, 30), "chakra": (255, 200, 80), "size": 1.25},
        "jutsus": {
            "up": [J("Boulder Roll", 30, goro_roll, "Up + Chakra", "Becomes a spinning ball and rolls forward.")],
            "throw": [J("Body Slam", 40, goro_body_slam, "Throw + Chakra", "Grows huge, leaps and slams down.")],
            "attack": [J("Spinning Top", 75, goro_top, "Attack + Chakra", "Enlarges and spins into nearby foes.")],
            "special": [J("Mega Boulder", 90, goro_mega, "Attack x2 (hold) + Chakra",
                          "A supersized boulder that chases the enemy.")],
            "air": [J("Aerial Slam", 30, goro_air_slam, "Chakra in air", "Enlarges and crashes down.")],
        },
    },
    {
        "id": "tetsu", "name": "Tetsu Midorikawa", "title": "Master of Taijutsu",
        "description": "A tireless martial artist who cannot mould ninjutsu at all, so he trained his "
                       "body to its absolute limit. Unlock him in the Shop.",
        # BALANCE (v1.1): strength 5 -> 4 and combo 5 -> 4 after CPU-vs-CPU testing showed
        # Tetsu winning 100% of his matches; his damage per exchange was far above the roster.
        "strength": 3, "jutsu_power": 2, "speed": 7, "chakra_gain": 5, "combo": 4,
        "locked": True, "price": 400,
        "palette": {"skin": (235, 195, 160), "hair": (20, 20, 25), "hair_style": "short",
                    "outfit": (200, 120, 50), "outfit_dark": (140, 80, 30), "pants": (200, 120, 50),
                    "accent": (230, 60, 60), "eye": (30, 30, 30), "chakra": (255, 110, 90)},
        "jutsus": {
            "up": [J("Rising Leaf", 40, tetsu_rising, "Up + Chakra", "Launching rising kick.")],
            "throw": [J("Kunai Storm", 40, tetsu_storm, "Throw + Chakra", "Five kunai in a fan.")],
            "attack": [J("Hurricane Heel", 60, tetsu_hurricane, "Attack + Chakra", "Travelling spin kicks.")],
            "special": [J("Gate Burst", 90, tetsu_gate, "Attack x2 (hold) + Chakra",
                          "Opens his inner limit: 10s power & speed boost plus a dash strike.")],
            "air": [J("Falling Axe", 30, tetsu_axe, "Chakra in air", "A heel drop from the sky.")],
        },
    },
]

# Training dummy (not selectable)
DUMMY = {
    "id": "dummy", "name": "Training Dummy", "title": "", "description": "",
    "strength": 0, "jutsu_power": 0, "speed": 0, "chakra_gain": 0, "combo": 1,
    "palette": {"skin": (200, 160, 110), "hair": (150, 110, 70), "hair_style": "short",
                "outfit": (170, 130, 80), "outfit_dark": (120, 90, 55), "pants": (140, 100, 60),
                "accent": (220, 220, 220), "eye": (60, 40, 20), "chakra": (200, 200, 200)},
    "jutsus": {},
}


def get_char(cid):
    """Look up a character by id (falls back to the training dummy).
    """
    for c in ROSTER:
        if c["id"] == cid:
            return c
    return DUMMY
