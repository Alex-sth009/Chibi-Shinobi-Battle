"""
cli_app.py - Terminal interface (second interface over the same engine)
=======================================================================
This module is a *user interface only*. It imports the engine modules
(characters.py, fighter.py, world.py, stages.py, ai.py) and drives them exactly
as the graphical interface does. It does not modify, subclass or re-implement a
single line of game logic - the engine cannot tell which interface is running it.

Run:  python cli_app.py

Features
  1  Roster browser        - stats and jutsu of every fighter, read from the data layer
  2  Simulated match       - two fighters chosen by name, played out with a text commentary
  3  Data file check       - validates the external data/storage files and reports problems
  4  Match history         - reads match_history.txt (written by BOTH interfaces)
  5  Quit

All user input is validated here in the interface layer: digits, symbols, empty
input, unknown names and repeated selections are rejected with a clear message
and the prompt is repeated, so the engine only ever receives valid values.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import os
import sys

# The engine draws with pygame surfaces, so pygame must exist - but the terminal
# interface needs no window. The dummy drivers let the same engine run headless.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
except ImportError:                                  # dependency missing
    print("This game needs pygame.  Install it with:  pip install pygame-ce")
    sys.exit(1)

import history
from ai import AIController
from characters import ROSTER
from fighter import Fighter
from settings import ASSET_DIR, BASE_DIR, MAX_HP, ROUNDS_TO_WIN, ROUND_TIME
from stages import STAGES, build_stage
from world import World

DT = 1.0 / 60.0
LINE = "-" * 68


# =====================================================================
#  Input validation (interface layer only)
# =====================================================================
def ask_choice(prompt, options):
    """Ask for a menu number. Rejects letters, symbols, blanks and out-of-range values."""
    while True:
        raw = input(prompt).strip()
        if raw == "":
            print("  [!] Empty input. Please type a number from the menu.")
            continue
        if not raw.isdigit():                         # letters or symbols typed
            print(f"  [!] '{raw}' is not a number. Menu choices are digits only.")
            continue
        value = int(raw)
        if value not in options:
            print(f"  [!] {value} is not on the menu. Choose one of {sorted(options)}.")
            continue
        return value


def ask_fighter(prompt, taken=None):
    """Ask for a fighter by name.

    Rejects: digits, symbols, blank input, unknown names, and a name already
    chosen in this match (the duplicate check).
    """
    taken = taken or []
    names = {c["name"].split()[0].lower(): c for c in ROSTER}
    while True:
        raw = input(prompt).strip()
        if raw == "":
            print("  [!] Empty input. Type a fighter's first name, e.g. Kaito.")
            continue
        if any(ch.isdigit() for ch in raw):
            print(f"  [!] '{raw}' contains a number. Fighter names are letters only.")
            continue
        if not raw.replace(" ", "").isalpha():        # punctuation / symbols
            print(f"  [!] '{raw}' contains a symbol. Fighter names are letters only.")
            continue
        key = raw.split()[0].lower()
        if key not in names:
            print(f"  [!] No fighter called '{raw}'. Available: "
                  f"{', '.join(c['name'].split()[0] for c in ROSTER)}.")
            continue
        if key in taken:
            print(f"  [!] {raw.capitalize()} has already been selected in this match. Pick another.")
            continue
        return names[key], key


# =====================================================================
#  Screens
# =====================================================================
def show_roster():
    """Print every fighter's statistics and jutsu, read from characters.py."""
    print(LINE)
    print(f"{'FIGHTER':<20}{'STR':>4}{'JUT':>4}{'SPD':>4}{'CHK':>5}{'CMB':>4}   TITLE")
    print(LINE)
    for c in ROSTER:
        lock = "  [LOCKED - shop]" if c.get("locked") else ""
        print(f"{c['name']:<20}{c['strength']:>4}{c['jutsu_power']:>4}{c['speed']:>4}"
              f"{c['chakra_gain']:>5}{c['combo']:>4}   {c['title']}{lock}")
    print(LINE)
    ch, _ = ask_fighter("Fighter name for a full jutsu list (or Ctrl+C to go back): ")
    print(f"\n{ch['name']} - {ch['title']}")
    for slot in ("up", "throw", "attack", "special", "air"):
        for j in ch["jutsus"].get(slot, []):
            cost = f"{j['hp_req']} HP" if j.get("hp_req") else f"{j['cost']} chakra"
            print(f"   {j['name']:<22} {j['keys']:<34} {cost}")
            print(f"      {j['desc']}")
    print()


def simulate_match():
    """Choose two fighters and a stage, then play a full match with commentary."""
    print("\nAvailable fighters:", ", ".join(c["name"].split()[0] for c in ROSTER))
    c1, k1 = ask_fighter("Player 1 fighter: ")
    c2, k2 = ask_fighter("Player 2 fighter: ", taken=[k1])
    print("\nStages:")
    for i, s in enumerate(STAGES, 1):
        print(f"  {i}. {s['name']}{'  [LOCKED]' if s.get('locked') else ''}")
    idx = ask_choice("Stage number: ", set(range(1, len(STAGES) + 1))) - 1
    stage = build_stage(STAGES[idx])

    print(f"\n{LINE}\n{c1['name']}  vs  {c2['name']}   @ {stage['name']}\n{LINE}")
    wins, elapsed = [0, 0], 0.0
    rnd = 1
    while max(wins) < ROUNDS_TO_WIN:
        f1 = Fighter(c1, 1, 220, 1, "P1")
        f2 = Fighter(c2, 2, 740, -1, "P2")
        world = World(stage, [f1, f2], None)
        a1, a2 = AIController("Hard"), AIController("Hard")
        clock, last_report = 0.0, 0.0
        print(f"\n-- Round {rnd} --")
        while f1.hp > 0 and f2.hp > 0 and clock < ROUND_TIME:
            a1.update(f1, world, DT)
            a2.update(f2, world, DT)
            f1.update(DT, a1, world)
            f2.update(DT, a2, world)
            world.update(DT)
            clock += DT
            if clock - last_report >= 5.0:            # commentary every 5 seconds
                last_report = clock
                print(f"   t={clock:5.1f}s   {f1.label} {f1.char['name'].split()[0]:<7} "
                      f"HP {f1.hp:5.1f} CK {f1.chakra:5.1f}   |   "
                      f"{f2.label} {f2.char['name'].split()[0]:<7} HP {f2.hp:5.1f} CK {f2.chakra:5.1f}")
        elapsed += clock
        if f1.hp <= 0 and f2.hp > 0:
            wins[1] += 1
            print(f"   K.O.!  {c2['name']} takes round {rnd}.")
        elif f2.hp <= 0 and f1.hp > 0:
            wins[0] += 1
            print(f"   K.O.!  {c1['name']} takes round {rnd}.")
        else:
            leader = 0 if f1.hp > f2.hp else 1
            wins[leader] += 1
            print(f"   TIME UP - round {rnd} on health to "
                  f"{(c1 if leader == 0 else c2)['name']}.")
        rnd += 1

    winner = c1["name"] if wins[0] > wins[1] else c2["name"]
    print(f"\n{LINE}\n  RESULT: {winner} wins the match {wins[0]}-{wins[1]}  "
          f"({elapsed:.1f} s)\n{LINE}")
    history.append_match("CLI", "versus", c1["name"], c2["name"], stage["name"],
                         f"{wins[0]}-{wins[1]}", winner, elapsed)
    print("Result appended to match_history.txt\n")


def check_data_files():
    """Validate the external data and storage files, reporting problems cleanly."""
    print(LINE)
    checks = [
        ("save_data.json", os.path.join(BASE_DIR, "save_data.json"), "settings, key bindings, coins"),
        ("match_history.txt", history.HISTORY_FILE, "one line per finished match"),
        ("assets/sprites/", os.path.join(ASSET_DIR, "sprites"), "optional sprite sheets"),
        ("assets/music/", os.path.join(ASSET_DIR, "music"), "optional music tracks"),
    ]
    for name, path, purpose in checks:
        state = "found   " if os.path.exists(path) else "missing "
        note = "" if os.path.exists(path) else "  (created automatically when first needed)"
        print(f"  [{state}] {name:<20} {purpose}{note}")
    # the roster is data too: validate every record before it can break a match
    problems = 0
    for c in ROSTER:
        for key in ("name", "strength", "jutsu_power", "speed", "chakra_gain", "combo", "palette", "jutsus"):
            if key not in c:
                print(f"  [!] fighter '{c.get('id', '?')}' is missing the field '{key}'")
                problems += 1
        for slot, entries in c.get("jutsus", {}).items():
            for j in entries:
                if not callable(j.get("fn")):
                    print(f"  [!] {c['name']} jutsu '{j.get('name')}' has no callable action")
                    problems += 1
    print(f"  [{'ok      ' if not problems else 'FAILED  '}] roster: {len(ROSTER)} fighters validated, "
          f"{problems} problems found")
    print(LINE + "\n")


def show_history():
    """Print the shared match log written by both interfaces."""
    rows = history.read_matches()
    print(LINE)
    if not rows:
        print("  match_history.txt is empty - play a match first.")
    else:
        print(f"  {'WHEN':<20}{'UI':<5}{'MATCH':<34}{'RESULT':<10}")
        for r in rows[-12:]:
            match = f"{r['p1'].split()[0]} vs {r['p2'].split()[0]} @ {r['stage']}"
            print(f"  {r['time']:<20}{r['interface']:<5}{match:<34}{r['rounds']} {r['winner'].split()[0]}")
    print("\n  " + history.summary())
    print(LINE + "\n")


# =====================================================================
def main():
    pygame.init()
    print("\n" + "=" * 68)
    print("  SHINOBI CLASH - terminal interface        (engine: characters/fighter/world)")
    print("=" * 68)
    actions = {1: show_roster, 2: simulate_match, 3: check_data_files, 4: show_history}
    while True:
        print("  1) Roster browser     2) Simulate a match     3) Check data files")
        print("  4) Match history      5) Quit")
        choice = ask_choice("Select: ", {1, 2, 3, 4, 5})
        if choice == 5:
            print("Goodbye.\n")
            return
        try:
            actions[choice]()
        except KeyboardInterrupt:
            print("\n  (cancelled)\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.\n")
