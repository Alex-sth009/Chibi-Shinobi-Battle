"""
controls.py - Input handling
============================
A Controller stores which buttons are held, which were pressed THIS frame and
when each button was last pressed (needed for timing tricks like the
substitution and the double-tap ultimate jutsu). Humans and the CPU use the
same Controller interface, so a fighter never knows who is controlling it.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import pygame

from settings import ACTIONS, now


class Controller:
    """Remembers the state of one player's buttons for the current frame.

    `held`    - buttons currently down
    `pressed` - buttons that went down THIS frame (used for taps)
    `last_press` / `prev_press` - timestamps, needed for timed inputs such as the
    substitution (block just before a hit) and the double-tap ultimate jutsu.
    """
    def __init__(self):
        self.held = set()
        self.pressed = set()
        self.released = set()
        self.last_press = {a: -10.0 for a in ACTIONS}
        self.prev_press = {a: -10.0 for a in ACTIONS}

    def begin_frame(self):
        """Called once per frame BEFORE reading events: clears the 'this frame' sets."""
        self.pressed.clear()
        self.released.clear()

    def press(self, action):
        """Mark a button as newly pressed and remember when it happened."""
        if action in self.held:
            return
        t = now()
        self.prev_press[action] = self.last_press[action]
        self.last_press[action] = t
        self.held.add(action)
        self.pressed.add(action)

    def release(self, action):
        """Mark a button as released (it is no longer held)."""
        if action in self.held:
            self.held.discard(action)
            self.released.add(action)

    def hold(self, action):
        """Force a button to be 'held' without counting as a fresh press (used by the CPU)."""
        self.held.add(action)

    def release_all(self):
        """Let go of every button - used when switching screens so keys don't stick."""
        for a in list(self.held):
            self.release(a)

    def h(self, action):
        """Is the action held?"""
        return action in self.held

    def p(self, action):
        """Was the action pressed this frame?"""
        return action in self.pressed


class KeyboardController(Controller):
    """A human player: turns pygame key events into game actions using the key map
    saved in save_data.json (editable in Option Mode).
    """
    def __init__(self, keymap):
        super().__init__()
        self.lookup = {}
        self.set_keymap(keymap)

    def set_keymap(self, keymap):
        """Rebuild the key -> action lookup after the player rebinds their controls."""
        self.lookup = {}
        for action, keys in keymap.items():
            for k in keys:
                self.lookup[k] = action
        self.held.clear()

    def handle_event(self, event):
        """Feed one pygame keyboard event into this controller."""
        if event.type == pygame.KEYDOWN and event.key in self.lookup:
            self.press(self.lookup[event.key])
        elif event.type == pygame.KEYUP and event.key in self.lookup:
            self.release(self.lookup[event.key])


class NullController(Controller):
    """Used during intros / KO screens: no input."""
    pass
