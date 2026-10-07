"""
audio.py - Sound effects and music
==================================
Sound effects are generated in code (sine/noise bursts) so the game needs no
audio files at all. Music is optional: drop MP3/OGG/WAV or MID files into
assets/music/ and they are played on a loop.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import array
import glob
import math
import os
import random

import pygame

from settings import ASSET_DIR


class Audio:
    """Creates all sound effects at start-up and handles optional background music."""
    def __init__(self, save):
        self.save = save
        self.ok = False
        self.sounds = {}
        self.music_playing = None
        try:
            pygame.mixer.init(22050, -16, 2, 512)
            self.ok = True
        except pygame.error:
            return
        try:
            self._build()
        except Exception:  # never crash the game because of audio
            self.sounds = {}

    # ------------------------------------------------------------ synthesis
    def _make(self, dur, f0, f1=None, noise=0.0, vol=0.5, decay=2.0, square=False):
        """Build one sound effect from maths: a sine tone sliding from f0 to f1, mixed
        with noise and faded out. No sound files needed.
        """
        rate, channels = pygame.mixer.get_init()[0], pygame.mixer.get_init()[2]
        n = int(rate * dur)
        f1 = f0 if f1 is None else f1
        buf = array.array("h")
        phase = 0.0
        for i in range(n):
            k = i / n
            freq = f0 + (f1 - f0) * k
            phase += 2 * math.pi * freq / rate
            s = math.sin(phase)
            if square:
                s = 1.0 if s > 0 else -1.0
            s = s * (1 - noise) + (random.random() * 2 - 1) * noise
            env = (1 - k) ** decay
            v = int(max(-1, min(1, s * env * vol)) * 32000)
            for _ in range(channels):
                buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        """Create the library of effects used by the game (hits, throws, jutsu, KO...)."""
        self.sounds = {
            "hit": self._make(0.12, 180, 60, noise=0.6, vol=0.6),
            "heavy": self._make(0.25, 120, 40, noise=0.7, vol=0.8),
            "swish": self._make(0.08, 900, 300, noise=0.8, vol=0.25),
            "throw": self._make(0.10, 1400, 500, noise=0.5, vol=0.25),
            "block": self._make(0.10, 1200, 900, noise=0.2, vol=0.35, square=True),
            "jutsu": self._make(0.35, 300, 900, noise=0.1, vol=0.35),
            "poof": self._make(0.25, 400, 100, noise=0.9, vol=0.4),
            "ko": self._make(0.6, 300, 50, noise=0.3, vol=0.6, decay=1.0),
            "heal": self._make(0.4, 600, 1200, vol=0.3, decay=1.0),
            "explode": self._make(0.5, 90, 30, noise=0.85, vol=0.9, decay=1.2),
            "select": self._make(0.06, 700, 900, vol=0.3, square=True),
            "confirm": self._make(0.15, 500, 1000, vol=0.35, square=True),
            "jump": self._make(0.08, 300, 600, vol=0.2),
        }

    def play(self, name):
        """Play one effect by name, unless the player switched sound off in Options."""
        if not self.ok or not self.save.get("sound", True):
            return
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    # ------------------------------------------------------------ music
    def update_music(self):
        """Start/stop looping music, picking MP3-style or MIDI files as set in Options."""
        if not self.ok:
            return
        if not self.save.get("music", True):
            if self.music_playing:
                pygame.mixer.music.stop()
                self.music_playing = None
            return
        exts = ("*.mid", "*.midi") if self.save.get("music_type") == "midi" else ("*.mp3", "*.ogg", "*.wav")
        files = []
        for e in exts:
            files += glob.glob(os.path.join(ASSET_DIR, "music", e))
        if not files:
            return
        want = sorted(files)[0]
        if self.music_playing == want:
            return
        try:
            pygame.mixer.music.load(want)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            self.music_playing = want
        except pygame.error:
            self.music_playing = None
