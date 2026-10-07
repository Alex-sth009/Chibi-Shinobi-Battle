"""
history.py - Persistent match history (shared by both interfaces)
=================================================================
Every finished match is appended as one bar-separated line to match_history.txt.
Both the graphical interface (scenes.py) and the terminal interface (cli_app.py)
call append_match(), so the same log grows no matter how the game was played.

A missing or unreadable log is never fatal: reading returns an empty list and
writing is wrapped so that a storage error cannot crash a match.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import datetime
import os

from settings import BASE_DIR

HISTORY_FILE = os.path.join(BASE_DIR, "match_history.txt")
HEADER = "# timestamp|interface|mode|player1|player2|stage|rounds|winner|seconds"
FIELDS = 9


def append_match(interface, mode, p1, p2, stage, rounds, winner, seconds):
    """Append one completed match to match_history.txt.

    interface  "CLI" or "GUI"      mode     battle / versus / survival / training
    p1, p2     fighter names        stage    arena name
    rounds     e.g. "2-1"           winner   winning label, or "Draw"
    seconds    match length
    """
    line = "|".join([
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(interface), str(mode), str(p1), str(p2), str(stage),
        str(rounds), str(winner), f"{seconds:.1f}",
    ])
    try:
        new_file = not os.path.exists(HISTORY_FILE)
        with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
            if new_file:
                fh.write(HEADER + "\n")
            fh.write(line + "\n")
        return True
    except OSError as err:                      # disk full, read-only folder, ...
        print(f"[history] could not write match_history.txt: {err}")
        return False


def read_matches():
    """Return the stored matches as a list of dictionaries (empty if none/broken)."""
    rows = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                parts = raw.split("|")
                if len(parts) != FIELDS:        # skip a corrupted line, keep the rest
                    continue
                rows.append(dict(zip(
                    ["time", "interface", "mode", "p1", "p2", "stage", "rounds", "winner", "seconds"], parts)))
    except FileNotFoundError:
        return []
    except OSError as err:
        print(f"[history] could not read match_history.txt: {err}")
        return []
    return rows


def summary():
    """Short statistics over the whole log, used by the CLI history screen."""
    rows = read_matches()
    if not rows:
        return "No matches recorded yet."
    cli = sum(1 for r in rows if r["interface"] == "CLI")
    gui = len(rows) - cli
    try:
        total = sum(float(r["seconds"]) for r in rows)
    except ValueError:
        total = 0.0
    return (f"{len(rows)} matches recorded ({cli} from the CLI, {gui} from the GUI); "
            f"total play time {total/60:.1f} minutes.")
