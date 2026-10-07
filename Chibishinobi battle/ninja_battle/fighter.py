"""
fighter.py - The playable ninja
===============================
Movement (walk, run, jump, double jump, teleport), defence (block and the
substitution jutsu), attacks (combos, jump attack), weapons, chakra charging,
ninja scrolls and the jutsu input system all live in this class.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import random

from entities import Hitbox, Particle, Projectile
from settings import (COMBO_WINDOW, GRAVITY, GROUND_Y, JUMP_VELOCITY, KUNAI_DAMAGE, MAX_CHAKRA, MAX_HP,
                      PASSIVE_CHAKRA_PER_SEC, SCROLL_HEAL_PERCENT, SHURIKEN_DAMAGE, START_CHAKRA,
                      START_KUNAI, START_SCROLLS, START_SHURIKEN, STAGE_LEFT, STAGE_RIGHT,
                      SUBSTITUTION_COST, TELEPORT_COST, TELEPORT_HEIGHT, THROW_COOLDOWN, AIR_JUMPS,
                      CHAKRA_CHARGE_RATE,
                      AIR_JUMP_POWER, clamp, now, sign)

TIMERS = ("stun", "invuln", "armor", "bound", "suspend", "lock", "attack_cd", "throw_cd", "sub_cd",
          "combo_timer", "deflect", "drop_timer", "hit_timer", "block_flash", "hurt_flash", "pet_out",
          "land_t", "flip_t")

BALL_STATES = ("ball", "top", "slam", "drill", "bigdrill")


class Fighter:
    """One ninja on the battlefield.

    The same class is used by both human players, the CPU and the training dummy;
    only the Controller that drives it differs. Key ideas:
      state     - what the fighter is doing ('idle', 'run', 'attack', 'block'...)
      timers    - countdowns in TIMERS tick down every frame (stun, invuln, ...)
      tasks     - actions scheduled for later, which is how jutsu are choreographed
      move      - a scripted movement (dash, roll, slam) that takes over control
    """
    def __init__(self, char, team, x, facing, label="P1"):
        self.char = char
        self.team = team
        self.label = label
        size = char.get("palette", {}).get("size", 1.0)
        self.w, self.h = int(34 * size), int(68 * size)
        self.x, self.y = float(x), float(GROUND_Y)
        self.vx = self.vy = 0.0
        self.facing = facing
        self.on_ground = True
        self.hp = MAX_HP
        self.hp_display = MAX_HP
        self.chakra = START_CHAKRA
        self.kunai, self.shuriken, self.scrolls = START_KUNAI, START_SHURIKEN, START_SCROLLS
        self.state, self.state_t, self.anim_t = "idle", 0.0, random.random()
        for t in TIMERS:
            setattr(self, t, 0.0)
        self.combo_i = 0
        self.attack_pose = "punch"
        self.buffs = {}
        self.tasks = []
        self.move = None
        self.scale = 1.0
        self.kd_ground = 0.0
        self.move_hold = 0.0
        self.hit_count = 0
        self.last_hit = -10.0
        self.air_hitbox = None
        self.last_throw = None
        self.last_throw_time = -10.0
        self.air_jumps = AIR_JUMPS      # mid-air jumps left (refilled on landing / teleport)
        self.pet_x = self.x - facing * 26
        self.ctrl = None
        self.world = None
        self.infinite_chakra = False

    # ------------------------------------------------------------ stats
    @property
    def jp(self):
        """Jutsu power multiplier taken from the character's Jutsu Power stat."""
        return 0.7 + 0.1 * self.char["jutsu_power"]

    def str_dmg(self):
        """Damage of one normal punch/kick, from the Strength stat."""
        return 1.6 + 0.9 * self.char["strength"]

    def speed_stat(self):
        """Current speed stat, including temporary boosts (Wild Focus, Gate Burst)."""
        s = self.char["speed"]
        if self.has_buff("focus"):
            s = max(s, 8)
        if self.has_buff("gate"):
            s = max(s, 9)
        return s

    def walk_speed(self):
        """Pixels per second while walking."""
        return 70 + self.speed_stat() * 12

    def run_speed(self):
        """Pixels per second while running."""
        return 140 + self.speed_stat() * 28

    def damage_mult(self):
        """Extra damage from active buffs (Hawk Eye, Gate Burst)."""
        m = 1.0
        if self.has_buff("hawk"):
            m *= 1.4
        if self.has_buff("gate"):
            m *= 1.2      # BALANCE (v1.1): 1.3 -> 1.2, Gate Burst was too dominant
        return m

    def charge_rate(self):
        """Chakra gained per second while the chakra button is held."""
        return self.char["chakra_gain"] * CHAKRA_CHARGE_RATE * self.regen_mult()

    def regen_mult(self):
        """Chakra gain multiplier (doubled while Meditation is active)."""
        return 2.0 if self.has_buff("meditate") else 1.0

    def has_buff(self, name):
        """Is this buff currently active?"""
        return self.buffs.get(name, 0) > 0

    def add_buff(self, name, dur):
        """Switch a buff on for `dur` seconds."""
        self.buffs[name] = dur

    def rect(self):
        """The fighter's collision box. It changes shape when rolling as a ball or
        lying knocked down, so hits land where the character actually is.
        """
        import pygame
        if self.state in BALL_STATES:
            d = 44 * self.scale * (self.w / 34)
            return pygame.Rect(int(self.x - d / 2), int(self.y - d), int(d), int(d))
        w, h = self.w * self.scale, self.h * self.scale
        if self.state in ("knockdown", "ko") and self.on_ground:
            return pygame.Rect(int(self.x - h / 2), int(self.y - w), int(h), int(w))
        return pygame.Rect(int(self.x - w / 2), int(self.y - h), int(w), int(h))

    # ------------------------------------------------------------ helpers
    def set_state(self, s, force=False):
        """Switch animation/behaviour state and restart its timer."""
        if s != self.state or force:
            self.state = s
            self.state_t = 0.0

    def schedule(self, delay, fn):
        """Run a function after `delay` seconds - the backbone of scripted jutsu."""
        self.tasks.append([delay, fn])

    def face_opponent(self):
        """Automatically turn towards the enemy when standing still."""
        if self.world:
            e = self.world.nearest_enemy(self)
            if e and abs(e.x - self.x) > 4:
                self.facing = sign(e.x - self.x)

    def cancel_actions(self):
        """Drop everything in progress (called when hit, or when KO'd)."""
        self.tasks.clear()
        if self.move:
            self.end_move(cancelled=True)
        self.lock = 0
        self.deflect = 0
        self.scale = 1.0
        if self.air_hitbox:
            self.air_hitbox.dead = True
            self.air_hitbox = None

    def start_move(self, state, duration, vx=None, vy=None, hitbox=None, scale=None, gravity=True,
                   bounce=False, homing=0.0, on_land=None, on_end=None, armor=True):
        """Begin a scripted movement such as a dash, a roll or a body slam.
        While a move runs the player has no control, the given hitbox travels with
        the fighter, and `armor` means small hits won't interrupt it.
        """
        self.move = dict(state=state, t=duration, vx=vx, hitbox=hitbox, gravity=gravity, bounce=bounce,
                         homing=homing, on_land=on_land, on_end=on_end)
        if vy is not None:
            self.vy = vy
            if vy < 0:
                self.on_ground = False
        if scale:
            self.scale = scale
        if hitbox is not None:
            hitbox.life = duration + 0.05
            self.world.add_hitbox(hitbox)
        self.set_state(state, force=True)
        if armor:
            self.armor = max(self.armor, duration)

    def end_move(self, cancelled=False):
        """Finish a scripted movement and hand control back to the player."""
        m = self.move
        if m is None:
            return
        self.move = None
        if m["hitbox"] is not None:
            m["hitbox"].dead = True
        self.scale = 1.0
        if not cancelled:
            self.armor = 0
        self.set_state("idle" if self.on_ground else "jump", force=True)
        if not cancelled and m["on_end"]:
            m["on_end"]()

    def update_move(self, dt):
        """Advance the current scripted movement by one frame."""
        m = self.move
        m["t"] -= dt
        if m["vx"] is not None:
            if m["homing"]:
                e = self.world.nearest_enemy(self)
                if e:
                    m["vx"] += sign(e.x - self.x) * m["homing"] * dt
                    top = 520
                    m["vx"] = clamp(m["vx"], -top, top)
            self.vx = m["vx"]
            if abs(m["vx"]) > 1:
                self.facing = sign(m["vx"])
        if m["bounce"] and (self.x <= STAGE_LEFT + 1 or self.x >= STAGE_RIGHT - 1) and m["vx"]:
            m["vx"] = -m["vx"]
            self.x = clamp(self.x, STAGE_LEFT + 2, STAGE_RIGHT - 2)
            self.world.dust(self.x, self.y)
        if m["t"] <= 0:
            self.end_move()

    # ------------------------------------------------------------ reactions
    def get_hit(self, direction, kbx, kby, stun, knockdown):
        """React to taking damage: knockback, stun or a full knockdown."""
        self.cancel_actions()
        self.vx = direction * kbx
        if kby:
            self.vy = kby
            if kby < 0:
                self.on_ground = False
        self.combo_i = 0
        self.hurt_flash = 0.12
        if knockdown:
            self.set_state("knockdown", force=True)
            self.kd_ground = 0.0
            self.stun = 0
        else:
            self.stun = max(self.stun, stun)
            self.set_state("hurt", force=True)

    def knock_out(self, direction, world):
        """HP reached zero: fly backwards and stay down."""
        self.cancel_actions()
        self.bound = 0
        self.set_state("ko", force=True)
        self.vx = direction * 300
        self.vy = -420
        self.on_ground = False
        world.play("ko")
        world.shake = 0.5

    def substitute(self, att, world):
        """SUBSTITUTION JUTSU - swap places with a log and reappear behind the
        attacker. Triggered by tapping block in the instant before a hit lands.
        """
        world.spawn_log(self.x, self.y)
        world.smoke(self.x, self.y - 30)
        self.chakra -= SUBSTITUTION_COST
        behind = att.x - att.facing * 50
        if behind < STAGE_LEFT + 5 or behind > STAGE_RIGHT - 5:
            behind = att.x + att.facing * 50
        self.x = clamp(behind, STAGE_LEFT, STAGE_RIGHT)
        self.y = min(att.y, GROUND_Y)
        self.vx = self.vy = 0
        self.facing = sign(att.x - self.x)
        self.invuln, self.sub_cd, self.stun = 0.4, 0.5, 0
        self.set_state("idle", force=True)
        world.smoke(self.x, self.y - 30)
        world.text("Substitution!", self.x, self.y - 80, (200, 255, 200), 16)
        world.play("poof")

    def register_hit(self, world):
        """Count consecutive hits so the '3 HITS!' combo message can be shown."""
        self.hit_count = self.hit_count + 1 if self.hit_timer > 0 else 1
        self.hit_timer = 1.0
        if self.hit_count >= 3:
            world.text(f"{self.hit_count} HITS!", self.x, self.y - 95 * self.scale, (255, 200, 60), 16, 0.6)

    # ------------------------------------------------------------ main update
    def update(self, dt, ctrl, world):
        """One frame of life: tick timers and buffs, run scheduled jutsu steps,
        read the controller (if the fighter is free to act) and apply physics.
        """
        self.ctrl = ctrl
        self.anim_t += dt
        self.state_t += dt
        for t in TIMERS:
            v = getattr(self, t)
            if v > 0:
                setattr(self, t, max(0.0, v - dt))
        for b in list(self.buffs):
            self.buffs[b] -= dt
            if self.buffs[b] <= 0:
                del self.buffs[b]
        for task in list(self.tasks):
            if task not in self.tasks:
                continue
            task[0] -= dt
            if task[0] <= 0:
                self.tasks.remove(task)
                if self.hp > 0:
                    task[1]()
        self.hp_display += (self.hp - self.hp_display) * min(1.0, dt * 3)
        self.pet_x += ((self.x - self.facing * 30) - self.pet_x) * min(1.0, dt * 8)

        if self.hp <= 0:
            self.set_state("ko")
            self.physics(dt, world)
            return

        self.chakra = min(MAX_CHAKRA, self.chakra + PASSIVE_CHAKRA_PER_SEC * self.regen_mult() * dt)
        if self.infinite_chakra:
            self.chakra = MAX_CHAKRA

        if self.move:
            self.update_move(dt)
        elif self.state == "knockdown":
            if self.on_ground:
                self.kd_ground += dt
                if self.kd_ground > 0.6:
                    self.set_state("idle", force=True)
                    self.invuln = 0.45
        elif self.bound > 0:
            self.vx = 0
            self.set_state("hurt")
        elif self.stun > 0:
            self.set_state("hurt")
        elif self.lock > 0:
            self.vx *= 0.8
        else:
            if self.state == "hurt":
                self.set_state("idle")
            self.handle_input(ctrl, world, dt)
        self.physics(dt, world)

    def physics(self, dt, world):
        """Gravity, movement, stage limits and landing on the ground/platforms.
        Platforms are one-way: you only land on them when falling onto the top.
        """
        grav_off = self.suspend > 0 or (self.move is not None and not self.move["gravity"])
        if grav_off:
            self.vy = 0 if self.suspend > 0 else self.vy
        else:
            self.vy += GRAVITY * dt
        prev_y = self.y
        self.x += self.vx * dt
        self.y += self.vy * dt
        uncontrolled = self.stun > 0 or self.state in ("knockdown", "ko", "hurt") or self.lock > 0
        if self.on_ground and uncontrolled and self.move is None:
            self.vx *= max(0.0, 1 - 9 * dt)
        self.x = clamp(self.x, STAGE_LEFT, STAGE_RIGHT)
        if self.y < 40:
            self.y, self.vy = 40, max(self.vy, 0)
        landed = False
        if self.vy >= 0:
            if self.y >= GROUND_Y:
                self.y = GROUND_Y
                landed = True
            elif self.drop_timer <= 0 and self.state not in ("ko",):
                for p in world.platforms:
                    if p.left - 6 <= self.x <= p.right + 6 and prev_y <= p.top + 1 and self.y >= p.top:
                        self.y = p.top
                        landed = True
                        break
        was_air = not self.on_ground
        self.on_ground = landed
        if landed:
            fall_speed = self.vy
            self.vy = 0
            if was_air:
                self.on_land(world, fall_speed)

    def on_land(self, world, fall_speed):
        """Touch-down: refill the mid-air jump, squash the sprite, raise dust."""
        self.land_t = 0.14
        self.air_jumps = AIR_JUMPS
        self.flip_t = 0
        if fall_speed > 350:
            world.dust(self.x, self.y, 5)
        if self.air_hitbox:
            self.air_hitbox.dead = True
            self.air_hitbox = None
        if self.move and self.move["on_land"]:
            cb = self.move["on_land"]
            self.end_move()
            cb()
            return
        if self.state in ("jump", "air_attack", "attack", "throw") and self.move is None and self.lock <= 0:
            self.set_state("idle", force=True)
            self.attack_cd = max(self.attack_cd, 0.12)
        if fall_speed > 600:
            world.dust(self.x, self.y, 6)

    # ------------------------------------------------------------ input
    def handle_input(self, c, world, dt):
        """Read the controller and act on it. Order matters: jutsu are checked first,
        then scroll, jump/teleport, drop-through, attack, throw, then movement,
        blocking and chakra charging.
        """
        t = now()
        on_ground = self.on_ground

        # Jutsu: chakra button + held first button
        if c.p("chakra"):
            slot = self.detect_slot(c, t)
            if slot and self.try_jutsu(slot, world):
                return

        if c.p("scroll"):
            self.use_scroll(world)

        if c.p("jump"):
            if c.h("up") and self.chakra >= TELEPORT_COST:
                self.teleport_up(world)
            elif on_ground:
                self.vy = -JUMP_VELOCITY
                self.on_ground = False
                self.air_jumps = AIR_JUMPS
                self.set_state("jump", force=True)
                world.dust(self.x, self.y, 4)
                world.play("jump")
            elif self.air_jumps > 0:
                self.air_jump(world)

        # Up + Down: drop through platforms
        if c.h("up") and c.h("down") and on_ground and self.y < GROUND_Y - 1:
            self.drop_timer = 0.25
            self.on_ground = False
            self.y += 3
            self.set_state("jump", force=True)
            return

        if c.p("attack") and self.attack_cd <= 0:
            if on_ground:
                self.ground_attack(world)
            else:
                self.air_attack(world)
            return

        if self.throw_cd <= 0:
            if c.p("throw"):
                self.throw_weapon("kunai", world)
            elif c.p("shuriken"):
                self.throw_weapon("shuriken", world)

        if self.state in ("attack", "throw") and self.state_t < 0.2:
            if on_ground:
                self.vx *= 0.85
            return
        if self.state == "air_attack":
            return

        left, right = c.h("left"), c.h("right")
        if on_ground and c.h("down") and not c.h("up"):
            self.set_state("block")
            self.vx = 0
            self.face_opponent()
            return
        if on_ground and c.h("chakra"):
            self.set_state("charge")
            self.vx = 0
            # chakra_gain is the character's base rate; CHAKRA_CHARGE_RATE scales it for
            # everyone (currently +30%), and regen_mult doubles it during Meditation.
            self.chakra = min(MAX_CHAKRA, self.chakra + self.charge_rate() * dt)
            if random.random() < 0.6:
                col = self.char["palette"].get("chakra", (90, 170, 255))
                world.particles.append(Particle(self.x + random.uniform(-18, 18), self.y - random.uniform(0, 20),
                                                random.uniform(-10, 10), random.uniform(-160, -80),
                                                0.5, col, size=random.uniform(4, 8), kind="glow"))
            return

        direction = (1 if right else 0) - (1 if left else 0)
        if direction:
            self.facing = direction
            self.move_hold += dt
            running = self.move_hold > 0.18
            spd = self.run_speed() if running else self.walk_speed()
            if on_ground:
                self.vx = direction * spd
                self.set_state("run" if running else "walk")
            else:
                self.vx = direction * spd * 0.85
        else:
            self.move_hold = 0
            if on_ground:
                self.vx = 0
                self.set_state("idle")
                self.face_opponent()
        if not on_ground and self.state not in ("jump",):
            self.set_state("jump")

    def detect_slot(self, c, t):
        """Work out WHICH jutsu the player is asking for from the button being held
        when the chakra button is pressed (up / throw / attack / double-attack / air).
        """
        if not self.on_ground:
            return "air"
        if c.h("up"):
            return "up"
        if (c.h("throw") or c.h("shuriken") or t - c.last_press["throw"] < 0.3
                or t - c.last_press["shuriken"] < 0.3):
            return "throw"
        if c.h("attack") and c.last_press["attack"] - c.prev_press["attack"] < 0.5 and t - c.last_press["attack"] < 1.2:
            return "special"
        if c.h("attack") or t - c.last_press["attack"] < 0.3:
            return "attack"
        return None

    def can_afford(self, j):
        """Enough chakra (or enough health, for Meditation) to use this jutsu?"""
        if j.get("hp_req"):
            return self.hp >= j["hp_req"]
        return self.chakra >= j["cost"]

    def try_jutsu(self, slot, world):
        """Pay the cost and perform the best matching jutsu for this slot.
        Entries are tried in order, so 'close range' versions come before 'far' ones.
        """
        entries = self.char["jutsus"].get(slot, [])
        options = [j for j in entries if j.get("cond") is None or j["cond"](self, world)]
        if not options:
            return False
        for j in options:
            if self.can_afford(j):
                if slot == "throw" and self.last_throw is not None and now() - self.last_throw_time < 0.35:
                    # refund the weapon thrown by the same key press
                    if not self.last_throw.dead:
                        self.last_throw.dead = True
                        if self.last_throw.kind == "kunai":
                            self.kunai += 1
                        else:
                            self.shuriken += 1
                if not j.get("hp_req"):
                    self.chakra -= j["cost"]
                self.combo_i = 0
                self.vx = 0
                world.banner(j["name"], self)
                world.play("jutsu")
                j["fn"](self, world)
                return True
        need = options[0]
        if need.get("hp_req"):
            world.text(f"Need {need['hp_req']} HP", self.x, self.y - 80, (255, 150, 150), 14, 0.6)
        else:
            world.text(f"Need {need['cost']} chakra", self.x, self.y - 80, (150, 190, 255), 14, 0.6)
        return False

    # ------------------------------------------------------------ actions
    def teleport_up(self, world):
        """Up + Jump: vanish in smoke and reappear higher up. Also refills the
        mid-air jump so you can teleport and then jump again.
        """
        self.chakra -= TELEPORT_COST
        world.smoke(self.x, self.y - 30, 10)
        self.y = max(60, self.y - TELEPORT_HEIGHT)
        self.vy = -120
        self.on_ground = False
        self.invuln = max(self.invuln, 0.15)
        self.air_jumps = max(self.air_jumps, AIR_JUMPS)   # you may jump once after teleporting
        self.set_state("jump", force=True)
        world.smoke(self.x, self.y - 30, 10)
        world.play("poof")

    def air_jump(self, world):
        """Double jump: a spinning flip in mid-air."""
        self.air_jumps -= 1
        self.vy = -JUMP_VELOCITY * AIR_JUMP_POWER
        self.set_state("jump", force=True)
        self.flip_t = 0.45
        from entities import FX
        world.add_fx(FX("ring", self.x, self.y + 4, 0.35, radius=46,
                        color=self.char["palette"].get("chakra", (150, 200, 255))))
        for i in range(8):
            world.particles.append(Particle(self.x + random.uniform(-14, 14), self.y - 6,
                                            random.uniform(-120, 120), random.uniform(-40, 60), 0.35,
                                            self.char["palette"].get("chakra", (150, 200, 255)),
                                            size=5, kind="glow"))
        world.play("jump")

    def use_scroll(self, world):
        """Use one ninja scroll to instantly restore 30% of maximum health."""
        if self.scrolls <= 0:
            world.text("No scrolls!", self.x, self.y - 80, (255, 150, 150), 14, 0.6)
            return
        if self.hp >= MAX_HP:
            return
        self.scrolls -= 1
        heal = MAX_HP * SCROLL_HEAL_PERCENT
        self.hp = min(MAX_HP, self.hp + heal)
        self.lock = 0.25
        self.set_state("cast", force=True)
        world.text(f"+{int(heal)} HP", self.x, self.y - 80, (120, 255, 140), 20)
        from entities import FX
        world.add_fx(FX("heal", self.x, self.y, 0.8, follow=self))
        world.play("heal")

    def ground_attack(self, world):
        """Normal attack. Repeated presses chain into a combo, up to the character's
        combo limit; the final hit knocks the opponent down.
        """
        if self.combo_timer > 0 and self.combo_i < self.char["combo"]:
            self.combo_i += 1
        else:
            self.combo_i = 1
        final = self.combo_i >= self.char["combo"]
        self.combo_timer = COMBO_WINDOW
        poses = ["punch", "punch2", "kick", "punch", "kick2"]
        self.attack_pose = "kick2" if final else poses[(self.combo_i - 1) % 4]
        dmg = self.str_dmg() * (1.6 if final else 1.0)
        self.vx = self.facing * 70
        self.face_opponent()
        world.add_hitbox(Hitbox(self, 30, 38, 42, 38, dmg, life=0.1,
                                kbx=340 if final else 80, kby=-330 if final else -30,
                                stun=0.35, knockdown=final, sfx="heavy" if final else "hit"))
        self.set_state("attack", force=True)
        self.attack_cd = 0.4 if final else 0.16
        if final:
            self.combo_timer = 0
        world.play("swish")

    def air_attack(self, world):
        """Jump attack: a powerful diving kick that knocks the opponent down."""
        self.set_state("air_attack", force=True)
        self.attack_pose = "dive"
        self.vy = max(self.vy, 520)
        self.vx = self.facing * 280
        if self.air_hitbox:
            self.air_hitbox.dead = True
        self.air_hitbox = world.add_hitbox(Hitbox(self, 14, 8, 36, 30, 4 + self.char["strength"] * 1.5,
                                                  life=1.0, kbx=280, kby=-260, stun=0.5, knockdown=True,
                                                  sfx="heavy"))
        self.attack_cd = 0.3
        world.play("swish")

    def throw_weapon(self, want, world):
        """want: "kunai" (throw key) or "shuriken" (shuriken key)."""
        if want == "kunai" and self.kunai <= 0:
            want = "shuriken" if self.shuriken > 0 else None
        elif want == "shuriken" and self.shuriken <= 0:
            want = "kunai" if self.kunai > 0 else None
        if want is None:
            world.text("No weapons!", self.x, self.y - 80, (255, 150, 150), 14, 0.6)
            return
        y = self.y - 40 * self.scale
        if want == "kunai":
            self.kunai -= 1
            p = Projectile(self, "kunai", self.x + self.facing * 14, y, self.facing * 740, 0, KUNAI_DAMAGE,
                           w=22, h=8, life=1.6)
        else:
            self.shuriken -= 1
            vy = 260 if not self.on_ground else 0
            p = Projectile(self, "shuriken", self.x + self.facing * 14, y, self.facing * 620, vy, SHURIKEN_DAMAGE,
                           w=16, h=16, life=1.6, spin=1000)
        world.add_projectile(p)
        self.last_throw, self.last_throw_time = p, now()
        self.throw_cd = THROW_COOLDOWN
        if self.on_ground:
            self.set_state("throw", force=True)
        world.play("throw")
