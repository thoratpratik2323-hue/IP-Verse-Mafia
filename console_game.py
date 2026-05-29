"""
console_game.py — Premium Retro Cyberpunk Console Space Shooter.
A zero-dependency, real-time terminal arcade game designed for Windows terminals.

Controls:
  [A] or Left Arrow   : Move Left
  [D] or Right Arrow  : Move Right
  [Spacebar]          : Shoot Laser
  [Q]                 : Quit Game
"""

from __future__ import annotations

import os
import sys
import time
import random

# Windows-native non-blocking keyboard input library
try:
    import msvcrt
except ImportError:
    msvcrt = None


# Cyberpunk ANSI Color Palette
COLOR_CYAN = "\033[96m"
COLOR_MAGENTA = "\033[95m"
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"

# Terminal Setup
WIDTH = 50
HEIGHT = 20

def enable_ansi():
    """Enables virtual terminal processing on Windows to support ANSI colors."""
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

class Game:
    def __init__(self):
        self.player_x = WIDTH // 2
        self.score = 0
        self.level = 1
        self.running = True
        
        # Lists for game entities
        self.lasers = []  # List of [x, y]
        self.aliens = []  # List of [x, y, type_char]
        self.explosions = [] # List of [x, y, tick_life]
        
        self.alien_spawn_timer = 0
        self.spawn_interval = 8 # Spawn an alien every 8 frames
        self.frame_tick = 0
        self.high_score = 0
        self.load_high_score()

    def load_high_score(self):
        try:
            self.high_score = 0
        except Exception:
            pass

    def get_input(self) -> str | None:
        """Fetches non-blocking keyboard input using msvcrt."""
        if not msvcrt:
            return None
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            # Handle special/arrow keys
            if ch in (b'\x00', b'\xe0'):
                arrow = msvcrt.getch()
                if arrow == b'K': # Left Arrow
                    return 'left'
                elif arrow == b'M': # Right Arrow
                    return 'right'
            try:
                char = ch.decode('utf-8').lower()
                if char == 'a':
                    return 'left'
                elif char == 'd':
                    return 'right'
                elif char == ' ':
                    return 'shoot'
                elif char == 'q':
                    return 'quit'
            except UnicodeDecodeError:
                pass
        return None

    def spawn_alien(self):
        x = random.randint(1, WIDTH - 2)
        type_char = random.choice(['▼', '👾', '🔶'])
        self.aliens.append([x, 0, type_char])

    def update(self):
        self.frame_tick += 1
        
        # 1. Update Lasers
        new_lasers = []
        for lx, ly in self.lasers:
            if ly > 0:
                new_lasers.append([lx, ly - 1])
        self.lasers = new_lasers
        
        # 2. Update Aliens
        new_aliens = []
        alien_speed = 0.5 if self.frame_tick % 2 == 0 else 0
        
        for ax, ay, char in self.aliens:
            new_y = ay + alien_speed
            if new_y >= HEIGHT - 1:
                # Alien reached the defense line! Game Over!
                self.running = False
            else:
                new_aliens.append([ax, new_y, char])
        self.aliens = new_aliens
        
        # 3. Handle Spawning
        self.alien_spawn_timer += 1
        adjusted_interval = max(3, self.spawn_interval - self.level)
        if self.alien_spawn_timer >= adjusted_interval:
            self.spawn_alien()
            self.alien_spawn_timer = 0
            
        # 4. Laser-Alien Collisions
        active_aliens = []
        for ax, ay, char in self.aliens:
            hit = False
            for lx, ly in self.lasers:
                # Check hit radius
                if abs(lx - ax) <= 1 and abs(ly - int(ay)) <= 1:
                    hit = True
                    self.lasers.remove([lx, ly])
                    break
            if hit:
                self.score += 10
                self.explosions.append([ax, int(ay), 3])
                # Speed scaling
                if self.score % 100 == 0:
                    self.level += 1
            else:
                active_aliens.append([ax, ay, char])
        self.aliens = active_aliens
        
        # 5. Update Explosions
        new_explosions = []
        for ex, ey, life in self.explosions:
            if life > 1:
                new_explosions.append([ex, ey, life - 1])
        self.explosions = new_explosions

        if self.score > self.high_score:
            self.high_score = self.score

    def render(self):
        """Draws the entire frame using an optimized ANSI string buffer to prevent flickering."""
        # Clean terminal screen and reset cursor to home (0,0)
        sys.stdout.write("\033[H")
        
        # 1. Header & Cyberpunk HUD
        sys.stdout.write(f"{COLOR_MAGENTA}╔══════════════════════════════════════════════════╗{COLOR_RESET}\n")
        sys.stdout.write(f"{COLOR_MAGENTA}║  {COLOR_BOLD}{COLOR_CYAN}🧬 IP PRIME: RETRO ARCADE{COLOR_RESET}{COLOR_MAGENTA}                      ║{COLOR_RESET}\n")
        sys.stdout.write(f"{COLOR_MAGENTA}╠══════════════════════════════════════════════════╣{COLOR_RESET}\n")
        
        hud_score = f"SCORE: {self.score}".ljust(15)
        hud_level = f"LEVEL: {self.level}".ljust(15)
        hud_high = f"HIGH: {self.high_score}".ljust(14)
        sys.stdout.write(f"{COLOR_MAGENTA}║  {COLOR_GREEN}{hud_score}{COLOR_YELLOW}{hud_level}{COLOR_CYAN}{hud_high}{COLOR_MAGENTA}║{COLOR_RESET}\n")
        sys.stdout.write(f"{COLOR_MAGENTA}╠══════════════════════════════════════════════════╣{COLOR_RESET}\n")
        
        # 2. Render Playfield
        grid = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
        
        # Place lasers
        for lx, ly in self.lasers:
            if 0 <= ly < HEIGHT and 0 <= lx < WIDTH:
                grid[ly][lx] = f"{COLOR_MAGENTA}¦{COLOR_RESET}"
                
        # Place explosions
        for ex, ey, life in self.explosions:
            if 0 <= ey < HEIGHT and 0 <= ex < WIDTH:
                grid[ey][ex] = f"{COLOR_RED}*{COLOR_RESET}"
                
        # Place aliens
        for ax, ay, char in self.aliens:
            iy = int(ay)
            if 0 <= iy < HEIGHT and 0 <= ax < WIDTH:
                grid[iy][ax] = f"{COLOR_GREEN}{char}{COLOR_RESET}"
                
        # Place player
        if 0 <= self.player_x < WIDTH:
            grid[HEIGHT - 1][self.player_x] = f"{COLOR_CYAN}▲{COLOR_RESET}"
            
        # Compile grid to string
        for row in grid:
            sys.stdout.write(f"{COLOR_MAGENTA}║{COLOR_RESET}" + "".join(row) + f"{COLOR_MAGENTA}║{COLOR_RESET}\n")
            
        # 3. Footer controls
        sys.stdout.write(f"{COLOR_MAGENTA}╚══════════════════════════════════════════════════╝{COLOR_RESET}\n")
        sys.stdout.write(f"{COLOR_DIM}  Controls: [A] Left | [D] Right | [Space] Fire | [Q] Quit  {COLOR_RESET}\n")
        sys.stdout.flush()

    def run(self):
        enable_ansi()
        # Initial screen clear
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\033[?25l") # Hide terminal cursor
        sys.stdout.flush()
        
        # Start intro screen
        self.show_intro()
        
        while self.running:
            # Inputs
            inp = self.get_input()
            if inp == 'left':
                self.player_x = max(1, self.player_x - 2)
            elif inp == 'right':
                self.player_x = min(WIDTH - 2, self.player_x + 2)
            elif inp == 'shoot':
                self.lasers.append([self.player_x, HEIGHT - 2])
            elif inp == 'quit':
                self.running = False
                break
                
            # Physics/Loop
            self.update()
            self.render()
            time.sleep(0.04) # ~25 frames per second
            
        # Game Over Screen
        self.show_game_over()
        sys.stdout.write("\033[?25h") # Show cursor back
        sys.stdout.flush()

    def show_intro(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        logo = f"""
  {COLOR_BOLD}{COLOR_CYAN}✨ C Y B E R P U N K   S H O O T E R ✨{COLOR_RESET}
  {COLOR_MAGENTA}=======================================:{COLOR_RESET}
  
       {COLOR_GREEN}▲  -- PLAYER SHIP (Move A/D or Arrows){COLOR_RESET}
       {COLOR_RED}▼  -- ALIEN INVASION (Destroy them!){COLOR_RESET}
       {COLOR_YELLOW}¦  -- LASER FIRE (Press Spacebar){COLOR_RESET}
       
  {COLOR_BOLD}{COLOR_MAGENTA}Press ANY KEY to start the mission, pilot...{COLOR_RESET}
        """
        print(logo)
        if msvcrt:
            # Wait for key press
            while not msvcrt.kbhit():
                time.sleep(0.1)
            msvcrt.getch() # Clear buffer

    def show_game_over(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        over_screen = f"""
  {COLOR_BOLD}{COLOR_RED}💥 M I S S I O N   F A I L E D 💥{COLOR_RESET}
  {COLOR_MAGENTA}==================================={COLOR_RESET}
  
       {COLOR_BOLD}{COLOR_YELLOW}FINAL SCORE : {self.score}{COLOR_RESET}
       {COLOR_BOLD}{COLOR_CYAN}LEVEL RECOGNITION : LEVEL {self.level}{COLOR_RESET}
       
  {COLOR_GREEN}Congratulations, Pratik Sir! Great defense.{COLOR_RESET}
  
  {COLOR_DIM}Press ANY KEY to return to cockpit...{COLOR_RESET}
        """
        print(over_screen)
        if msvcrt:
            time.sleep(0.5) # Prevent accidental keypress skips
            while msvcrt.kbhit():
                msvcrt.getch() # clear buffer
            while not msvcrt.kbhit():
                time.sleep(0.1)
            msvcrt.getch() # Clear buffer

if __name__ == "__main__":
    game = Game()
    game.run()
