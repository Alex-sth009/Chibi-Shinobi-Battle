"""
main.py - Program entry point and the main game loop
====================================================
Creates the window, loads the save file, builds both player controllers and
then runs the loop: read input -> update the current scene -> draw it.

--------------------------------------------------------------------------
  SHINOBI CLASH - Chibi Ninja Battle
  Author : Alex
  Year   : 2026
  This game - the code, the fighters, their jutsu and the artwork drawn by
  the code - is my own original work.
--------------------------------------------------------------------------
"""
import sys

import pygame

from audio import Audio
from controls import KeyboardController
from scenes import MainMenu
from settings import FPS, SCREEN_H, SCREEN_W, TITLE, load_save, save_save


class Game:
    """Owns the window, the save file, the audio, both controllers and the
    currently active scene.
    """
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.save = load_save()
        self.screen = None          # fixed 960x540 drawing canvas
        self.window = None          # the real window (may be any size)
        self.set_display(self.save.get("fullscreen", False))
        self.clock = pygame.time.Clock()
        self.audio = Audio(self.save)
        self.c1 = KeyboardController(self.save["keys"]["1"])
        self.c2 = KeyboardController(self.save["keys"]["2"])
        self.enter_pressed = False
        self.running = True
        self.scene = MainMenu(self)
        self.audio.update_music()

    def set_display(self, fullscreen):
        """(Re)create the window in windowed or fullscreen mode.

        Two paths, chosen automatically:
          * Hardware scaling - pygame's SCALED flag lets the graphics card stretch a
            960x540 picture to the monitor for free. Used whenever the driver supports
            it, which is the normal case on Windows and macOS.
          * Software scaling - otherwise the game is drawn on a 960x540 canvas and
            scaled onto the window once per frame into a reused buffer.
        Either way the picture keeps its 16:9 shape and is centred, so widescreen or
        4:3 monitors get black bars rather than a stretched or cropped image.
        """
        self.save["fullscreen"] = bool(fullscreen)
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.hardware_scaled = False
        try:
            win = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | flags)
            self.hardware_scaled = win.get_size() == (SCREEN_W, SCREEN_H)
        except pygame.error:
            win = None
        if not self.hardware_scaled:                      # software fallback
            win = pygame.display.set_mode((0, 0) if fullscreen else (SCREEN_W, SCREEN_H), flags)
        self.window = win
        if self.hardware_scaled:
            self.screen = win                             # scenes draw straight to it
            self.view_size, self.view_pos, self._view_buf = (SCREEN_W, SCREEN_H), (0, 0), None
        else:
            if self.screen is None or self.screen is self.window:
                self.screen = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
            ww, wh = self.window.get_size()
            scale = min(ww / SCREEN_W, wh / SCREEN_H)     # same factor both axes = no stretching
            self.view_size = (max(1, int(SCREEN_W * scale)), max(1, int(SCREEN_H * scale)))
            self.view_pos = ((ww - self.view_size[0]) // 2, (wh - self.view_size[1]) // 2)
            self._view_buf = pygame.Surface(self.view_size).convert()
        pygame.display.set_caption(TITLE)

    def toggle_fullscreen(self):
        """F11 or Alt+Enter: switch between fullscreen and windowed, and remember it."""
        self.set_display(not self.save.get("fullscreen", False))
        save_save(self.save)

    def apply_keys(self):
        """Reload both players' key maps after they were changed in Options."""
        self.c1.set_keymap(self.save["keys"]["1"])
        self.c2.set_keymap(self.save["keys"]["2"])

    def change(self, scene):
        """Switch to another screen and let go of any held keys."""
        self.scene = scene
        self.c1.release_all()
        self.c2.release_all()

    def run(self):
        """The main loop: read input, update the active scene, draw it, repeat 60x/sec."""
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            self.c1.begin_frame()
            self.c2.begin_frame()
            self.enter_pressed = False
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                # F11 (or Alt+Enter) toggles fullscreen from any screen, except while
                # the key-config screen is waiting for a key to assign.
                if e.type == pygame.KEYDOWN and not getattr(self.scene, "waiting", False) and (
                        e.key == pygame.K_F11
                        or (e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and (e.mod & pygame.KMOD_ALT))):
                    self.toggle_fullscreen()
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    waiting = getattr(self.scene, "waiting", False)
                    if not waiting and not isinstance(self.scene, MainMenu):
                        self.change(MainMenu(self))
                        continue
                if self.scene.handle_event(e):
                    continue
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.enter_pressed = True
                self.c1.handle_event(e)
                self.c2.handle_event(e)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            self.present()
        pygame.quit()
        sys.exit()

    def present(self):
        """Show the finished frame. With hardware scaling this is just a flip; otherwise
        the canvas is scaled into a reused buffer and centred on a black background."""
        if not self.hardware_scaled:
            if self.view_pos != (0, 0):
                self.window.fill((0, 0, 0))
            pygame.transform.scale(self.screen, self.view_size, self._view_buf)
            self.window.blit(self._view_buf, self.view_pos)
        pygame.display.flip()


if __name__ == "__main__":
    Game().run()
