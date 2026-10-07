# Shinobi Clash – Chibi Ninja Battle

**An original 2D fighting game — design, code and artwork by Alex.**

Every fighter, stat, jutsu, stage and menu in this project is my own work, and the
chibi characters are drawn entirely in code — the game ships with no sprite or
image files. Built with Python and Pygame.

*(To put a different name on it, change `AUTHOR` in `settings.py`; it appears on the
title screen and on the in-game Credits page, and it is written in the header of
every source file.)*

A 1v1 chibi ninja fighting game in Python + Pygame.

## Two interfaces, one engine

* `python main.py`     – the graphical game (Pygame window)
* `python cli_app.py`  – the terminal interface: roster browser, simulated match with a
  text commentary, data-file checker and the match history viewer

`cli_app.py` imports the engine (`characters.py`, `fighter.py`, `world.py`, `stages.py`,
`ai.py`) and drives it with the same calls the GUI makes — it contains no game logic of
its own, and the engine contains no `print()` or drawing code.

## Data and storage files

| File | Written by | Contents |
|---|---|---|
| `save_data.json` | both interfaces | difficulty, music/sound, key bindings, coins, unlocked items, high score |
| `match_history.txt` | both interfaces (`history.py`) | one appended row per match: `timestamp\|interface\|mode\|p1\|p2\|stage\|rounds\|winner\|seconds` |
| `assets/sprites/`, `assets/music/` | you (optional) | sprite sheets and music; the game runs fine without them |

## Run
```
pip install pygame        (on Python 3.13+/3.14 use:  pip install pygame-ce)
python main.py
```

## Modes
Battle (2 players) · Versus (vs CPU) · Survival (earn coins, local highscore) ·
Training (dummy, infinite chakra) · Options (difficulty, key config, MP3/MIDI music, sound) ·
Shop (unlock Tetsu + Volcano Rim stage) · How to Play.
Story, War, Game and Community are shown as *Unavailable*.

## Controls (change them in Option Mode)
| Action | Player 1 | Player 2 |
|---|---|---|
| Jutsu combo (Up) | W | Up |
| Run / face left | A | Left |
| Run / face right | D | Right |
| Block / Substitute | S | Down |
| Jump | B | Numpad 1 |
| Throw kunai | N | Numpad 2 |
| Throw shuriken | G | Numpad 4 |
| Attack | M | Numpad 3 |
| Chakra / Jutsu | H | Numpad 5 |
| Ninja scroll (+30% HP) | J | Numpad 6 |

* Hold a direction to walk, then run. **Up + Down** = drop through a platform.
* **Jump**, then jump again in mid-air for a **double jump** (spinning flip).
* **Up + Jump** = teleport up (8 chakra). You keep one jump afterwards, so teleport then jump again for maximum height.
* Hold **Block** to guard. Tap it just before a hit to **substitute** and appear behind the attacker.
* Mash **Attack** for combos. Attack in the air = diving jump attack.
* **Throw kunai** and **throw shuriken** have their own buttons (90 of each). Either one + Chakra does the throw jutsu.
* Hold **Chakra** to charge. Jutsu: hold Up / Throw / Attack and press Chakra.
  Attack, Attack (hold) + Chakra = main jutsu. Chakra in the air = aerial jutsu.
* Menus: movement keys to choose, Attack (or Enter) to confirm, Throw to cancel, Esc = main menu.
* **F11** (or **Alt+Enter**) switches between fullscreen and windowed at any time; it is also
  a row in Option Mode and the choice is remembered in `save_data.json`.
* Player 2's numpad needs **NumLock ON**.

## Editing
* `characters.py` – roster, stats, palettes, every jutsu (add new fighters here)
* `settings.py` – HP, chakra, weapon counts, scroll heal, substitution window, default keys,
  `ROUND_TIME` (300 s = 5 minutes per round), `CHAKRA_CHARGE_RATE` (1.30 = charging 30% faster),
  `AIR_JUMPS` (1 = double jump, 2 = triple jump) and `AIR_JUMP_POWER`
* `stages.py` – backgrounds & platforms
* `ai.py` – CPU difficulty tuning
* `render.py` – chibi drawing, HUD, effects (`RS` = fighter size, `_outlined()` = ink outline,
  `post_process()` = vignette & stage colour grade, `STAGE_TINT` = per-stage grading)

## Using your own sprite art
Characters are drawn in code, so no image files are needed. To use sprite art you've made
or have the rights to, add horizontal strips of square frames facing right:
`assets/sprites/<id>/idle.png`, `run.png`, `walk.png`, `jump.png`, `attack.png`, `block.png`,
`charge.png`, `cast.png`, `hurt.png`, `knockdown.png`, `ko.png`, `victory.png`.
Missing states fall back to `idle.png`, then to the drawn chibi.

## Music
Put `.mp3/.ogg/.wav` (MP3 setting) or `.mid` (MIDI setting) files in `assets/music/`.


## Code guide

Every file starts with a header explaining what it does, and every class and
function carries a docstring describing its job. The logic worth knowing:

* `Fighter.update()` – one frame of a ninja: timers, scheduled jutsu steps, input, physics.
* `Fighter.handle_input()` – the order buttons are checked in (jutsu first, then jump, attack, movement).
* `Fighter.detect_slot()` – how holding a button + chakra picks which jutsu comes out.
* `World.hit()` – the heart of combat: deflect → substitution → block → damage.
* `characters.py` helpers (`dash_strike`, `rapid_strikes`, `throw_spread`…) – reusable
  building blocks that all 8 fighters' jutsu are made from.
* `render.pose_for()` – converts a fighter's state into limb angles, i.e. the animation.


## Version history

**v1.1 – balance and feel pass.** Fighter damage was measured with an automated test
(each fighter attacking a passive dummy for 60 s, three runs each). The gap between the
strongest and weakest fighter fell from 6.05x to 2.58x, and in a 28-match CPU-vs-CPU
tournament the win-rate spread narrowed from 0-100% to 14-71%. All tuning was done in
`characters.py` data values only; the lines changed are marked `# BALANCE (v1.1)`.
Also added: double jump, impact hit-stop, cartoon outlines, stage colour grading.
