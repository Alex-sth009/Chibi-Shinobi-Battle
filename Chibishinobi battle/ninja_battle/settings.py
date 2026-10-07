"""
settings.py - Tunable game values, default controls, save file
==============================================================
Every number that shapes how the game feels lives here: gravity, jump power,
health/chakra limits, weapon counts, the substitution timing window and the
default key bindings for both players. Change a value here and the whole
game changes - no other file needs editing.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import copy
import json
import os

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
SAVE_FILE = os.path.join(BASE_DIR, "save_data.json")

# ----------------------------------------------------------------- screen
SCREEN_W, SCREEN_H = 960, 540
FPS = 60
TITLE = "Shinobi Clash - Chibi Ninja Battle"
AUTHOR = "Alex"          # shown on the title screen and the credits page
VERSION = "1.0"

# ----------------------------------------------------------------- physics
GRAVITY = 1900.0               # downward pull, pixels per second squared
GROUND_Y = 470                 # y position of the main floor (0 = top of the screen)
STAGE_LEFT, STAGE_RIGHT = 24, SCREEN_W - 24
JUMP_VELOCITY = 720.0          # upward speed of a normal jump
AIR_JUMPS = 1                  # extra mid-air jumps (1 = double jump, 2 = triple jump...)
AIR_JUMP_POWER = 0.92          # mid-air jump strength vs a ground jump
TELEPORT_HEIGHT = 170          # W + jump teleport distance

# ----------------------------------------------------------------- fighters
MAX_HP = 100.0                 # full health bar
MAX_CHAKRA = 100.0             # full chakra bar
START_CHAKRA = 20.0            # chakra each fighter starts a round with
START_KUNAI = 90               # kunai per player (thrown with the throw key)
START_SHURIKEN = 90            # shuriken per player (thrown with the shuriken key)
START_SCROLLS = 5              # ninja scrolls per player
SCROLL_HEAL_PERCENT = 0.30     # ninja scroll heals 30% of max HP
PASSIVE_CHAKRA_PER_SEC = 0.6   # slow regen even without charging
CHAKRA_CHARGE_RATE = 1.30      # charging speed multiplier: 1.30 = 30% faster than the
                               # per-character chakra_gain stat (1.0 = the raw stat)

SUBSTITUTION_WINDOW = 0.22     # seconds: tap block this close to a hit to substitute
SUBSTITUTION_COST = 10         # chakra used by a substitution
TELEPORT_COST = 8              # chakra used by teleport-up
BLOCK_DAMAGE_TAKEN = 0.15      # a blocked hit only does 15% of its damage
COMBO_WINDOW = 0.45            # seconds allowed between attacks to continue a combo

KUNAI_DAMAGE = 3.0
SHURIKEN_DAMAGE = 2.5
THROW_COOLDOWN = 0.28          # delay between thrown weapons

ROUND_TIME = 300               # seconds per round (300 = 5 minutes)
ROUNDS_TO_WIN = 2              # first to 2 rounds wins the match

DIFFICULTIES = ["Easy", "Normal", "Hard", "Expert"]

# ----------------------------------------------------------------- controls
ACTIONS = ["up", "left", "right", "down", "jump", "throw", "shuriken", "attack", "chakra", "scroll"]
ACTION_LABELS = {
    "up": "Up (jutsu combo)",
    "left": "Left (run / face)",
    "right": "Right (run / face)",
    "down": "Block / Substitute",
    "jump": "Jump",
    "throw": "Throw kunai",
    "shuriken": "Throw shuriken",
    "attack": "Attack",
    "chakra": "Chakra / Jutsu",
    "scroll": "Ninja scroll (+30% HP)",
}

# Each action can have several keys (list).
DEFAULT_KEYS = {
    "1": {
        "up": [pygame.K_w], "left": [pygame.K_a], "right": [pygame.K_d], "down": [pygame.K_s],
        "jump": [pygame.K_b], "throw": [pygame.K_n], "shuriken": [pygame.K_g], "attack": [pygame.K_m],
        "chakra": [pygame.K_h], "scroll": [pygame.K_j],
    },
    "2": {
        "up": [pygame.K_UP], "left": [pygame.K_LEFT], "right": [pygame.K_RIGHT], "down": [pygame.K_DOWN],
        "jump": [pygame.K_KP1], "throw": [pygame.K_KP2], "shuriken": [pygame.K_KP4], "attack": [pygame.K_KP3],
        "chakra": [pygame.K_KP5], "scroll": [pygame.K_KP6],
    },
}

DEFAULT_SAVE = {
    "keys": DEFAULT_KEYS,
    "difficulty": "Normal",
    "music": True,
    "music_type": "mp3",     # "mp3" or "midi"
    "fullscreen": False,     # F11 / Alt+Enter in game, or Option Mode
    "sound": True,
    "coins": 0,
    "unlocked": [],
    "highscore": 0,
}

# ----------------------------------------------------------------- colours
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
UI_DARK = (20, 22, 34)
UI_PANEL = (34, 38, 58)
UI_ACCENT = (255, 140, 40)
P1_COLOR = (80, 170, 255)
P2_COLOR = (255, 90, 90)
HP_COLOR = (230, 60, 60)
CHAKRA_COLOR = (70, 150, 255)


def now():   # ------------------------------------------------ helper functions
    """Global clock in seconds (used for input timing)."""
    return pygame.time.get_ticks() / 1000.0


def load_save():
    data = copy.deepcopy(DEFAULT_SAVE)
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        for k, v in loaded.items():
            if k == "keys":
                for p in ("1", "2"):
                    for a in ACTIONS:
                        if p in v and a in v[p]:
                            data["keys"][p][a] = list(v[p][a])
            else:
                data[k] = v
    except (OSError, ValueError):
        pass
    return data


def save_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sign(v):
    return 1 if v >= 0 else -1
