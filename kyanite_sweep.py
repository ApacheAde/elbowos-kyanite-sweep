#!/usr/bin/env python3
"""Kyanite Sweep — neon minesweeper arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "KYANITE SWEEP"
HANDLE = "x.com/ElbowOS"
COLS, ROWS, MINES = 8, 10, 12
BG, INK, GOLD, CYAN = (4, 10, 28), (220, 245, 255), (255, 210, 70), (70, 230, 255)
ICE, DEEP, ROSE, LIME = (40, 90, 170), (8, 22, 52), (255, 90, 140), (140, 255, 120)
NUMC = [
    (90, 210, 255), (80, 255, 190), (255, 210, 70), (255, 120, 80),
    (200, 90, 255), (255, 80, 160), (180, 240, 255), (255, 255, 255),
]


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 64)
        self.font_md = pygame.font.Font(None, 46)
        self.font_sm = pygame.font.Font(None, 32)
        self.font_n = pygame.font.Font(None, 52)
        self.margin_x = 70
        self.top = 300
        self.cell = 118
        self.reset()

    def reset(self) -> None:
        self.mine = [[False] * COLS for _ in range(ROWS)]
        self.open = [[False] * COLS for _ in range(ROWS)]
        self.flag = [[False] * COLS for _ in range(ROWS)]
        self.adj = [[0] * COLS for _ in range(ROWS)]
        self.score = 0
        self.sparks: list[Spark] = []
        self.cursor = [0, 0]
        self.pulse = 0.0
        self.cool = 0.0
        self.boom = 0.0
        self.scan = 0.0
        self.placed = False
        self.done = False

    def neighbors(self, c, r):
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    yield nc, nr

    def plant(self, safe_c, safe_r) -> None:
        cells = [(c, r) for r in range(ROWS) for c in range(COLS)
                 if abs(c - safe_c) > 1 or abs(r - safe_r) > 1]
        random.shuffle(cells)
        for c, r in cells[:MINES]:
            self.mine[r][c] = True
        for r in range(ROWS):
            for c in range(COLS):
                self.adj[r][c] = sum(1 for nc, nr in self.neighbors(c, r) if self.mine[nr][nc])
        self.placed = True

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            ang = random.random() * 6.283
            spd = random.uniform(50, 280)
            self.sparks.append(Spark(x, y, spd * math.cos(ang), spd * math.sin(ang),
                                     random.uniform(0.25, 0.7), col, random.randint(3, 8)))

    def cell_xy(self, c, r):
        return (self.margin_x + c * self.cell + self.cell // 2,
                self.top + r * self.cell + self.cell // 2)

    def reveal(self, c, r) -> None:
        if self.flag[r][c] or self.open[r][c]:
            return
        if not self.placed:
            self.plant(c, r)
        if self.mine[r][c]:
            self.open[r][c] = True
            self.boom = 0.6
            self.score = max(0, self.score - 40)
            self.burst(*self.cell_xy(c, r), ROSE, 22)
            return
        stack = [(c, r)]
        seen = set()
        while stack:
            cc, rr = stack.pop()
            if (cc, rr) in seen or self.open[rr][cc] or self.flag[rr][cc]:
                continue
            seen.add((cc, rr))
            self.open[rr][cc] = True
            self.score += 12 if self.adj[rr][cc] else 8
            self.burst(*self.cell_xy(cc, rr), CYAN if self.adj[rr][cc] else ICE, 7)
            if self.adj[rr][cc] == 0:
                stack.extend(self.neighbors(cc, rr))
        if self.won():
            self.done = True
            self.score += 250
            for r in range(ROWS):
                for c in range(COLS):
                    if self.mine[r][c]:
                        self.burst(*self.cell_xy(c, r), GOLD, 8)

    def won(self) -> bool:
        for r in range(ROWS):
            for c in range(COLS):
                if not self.mine[r][c] and not self.open[r][c]:
                    return False
        return True

    def toggle_flag(self, c, r) -> None:
        if self.open[r][c]:
            return
        self.flag[r][c] = not self.flag[r][c]
        if self.flag[r][c]:
            self.score += 5
            self.burst(*self.cell_xy(c, r), GOLD, 8)

    def autoplay(self) -> None:
        if self.cool > 0 or self.done:
            if self.done and self.cool <= 0:
                self.reset()
            return
        c, r = self.cursor
        if not self.placed:
            self.reveal(COLS // 2, ROWS // 2)
            self.cursor = [COLS // 2, ROWS // 2]
            self.cool = 0.18
            return
        for rr in range(ROWS):
            for cc in range(COLS):
                if not self.open[rr][cc] or self.adj[rr][cc] == 0:
                    continue
                closed = [(nc, nr) for nc, nr in self.neighbors(cc, rr)
                          if not self.open[nr][nc]]
                flagged = sum(1 for nc, nr in closed if self.flag[nr][nc])
                if flagged == self.adj[rr][cc]:
                    for nc, nr in closed:
                        if not self.flag[nr][nc]:
                            self.cursor = [nc, nr]
                            self.reveal(nc, nr)
                            self.cool = 0.12
                            return
                if len(closed) == self.adj[rr][cc]:
                    for nc, nr in closed:
                        if not self.flag[nr][nc]:
                            self.cursor = [nc, nr]
                            self.toggle_flag(nc, nr)
                            self.cool = 0.12
                            return
        hidden = [(cc, rr) for rr in range(ROWS) for cc in range(COLS)
                  if not self.open[rr][cc] and not self.flag[rr][cc] and not self.mine[rr][cc]]
        if hidden:
            cc, rr = random.choice(hidden)
            self.cursor = [cc, rr]
            self.reveal(cc, rr)
            self.cool = 0.14
        else:
            self.done = True
            self.cool = 0.8

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.scan += dt * 90
        self.cool = max(0.0, self.cool - dt)
        self.boom = max(0.0, self.boom - dt)
        if self.record:
            self.autoplay()
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.vy += 220 * dt
            alive.append(sp)
        self.sparks = alive

    def handle(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key in (pygame.K_LEFT, pygame.K_a):
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
            self.cursor[0] = min(COLS - 1, self.cursor[0] + 1)
        elif ev.key in (pygame.K_UP, pygame.K_w):
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self.cursor[1] = min(ROWS - 1, self.cursor[1] + 1)
        elif ev.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.reveal(*self.cursor)
        elif ev.key == pygame.K_f:
            self.toggle_flag(*self.cursor)
        elif ev.key == pygame.K_r:
            self.reset()

    def draw(self, s: pygame.Surface) -> None:
        s.fill(BG)
        for i in range(14):
            y = int((self.scan + i * 160) % (H + 80)) - 40
            pygame.draw.line(s, (12, 36, 70), (0, y), (W, y), 3)
        board = pygame.Rect(self.margin_x - 16, self.top - 16,
                            COLS * self.cell + 32, ROWS * self.cell + 32)
        pygame.draw.rect(s, DEEP, board, border_radius=22)
        pygame.draw.rect(s, CYAN, board, width=4, border_radius=22)
        glow = abs(math.sin(self.pulse * 3.2))
        for r in range(ROWS):
            for c in range(COLS):
                x = self.margin_x + c * self.cell
                y = self.top + r * self.cell
                tile = pygame.Rect(x + 6, y + 6, self.cell - 12, self.cell - 12)
                if self.open[r][c]:
                    pygame.draw.rect(s, (14, 32, 68), tile, border_radius=14)
                    if self.mine[r][c]:
                        pygame.draw.circle(s, ROSE, tile.center, 22)
                        pygame.draw.circle(s, (255, 200, 220), tile.center, 10)
                    elif self.adj[r][c]:
                        n = self.adj[r][c]
                        lab = self.font_n.render(str(n), True, NUMC[n - 1])
                        s.blit(lab, lab.get_rect(center=tile.center))
                    else:
                        pygame.draw.circle(s, (30, 70, 120), tile.center, 8)
                else:
                    col = (28 + int(18 * glow), 58, 128) if (c + r) % 2 == 0 else (18, 44, 102)
                    pygame.draw.rect(s, col, tile, border_radius=14)
                    hi = pygame.Rect(tile.x + 8, tile.y + 8, tile.w - 28, 14)
                    pygame.draw.rect(s, (90, 160, 230), hi, border_radius=6)
                    pygame.draw.rect(s, (120, 200, 255), tile, width=2, border_radius=14)
                    if self.flag[r][c]:
                        pts = [(tile.centerx - 8, tile.y + 22),
                               (tile.centerx + 22, tile.centery - 4),
                               (tile.centerx - 8, tile.centery + 10)]
                        pygame.draw.polygon(s, GOLD, pts)
                        pygame.draw.line(s, INK, (tile.centerx - 8, tile.y + 20),
                                         (tile.centerx - 8, tile.bottom - 18), 4)
        cc, cr = self.cursor
        cx = self.margin_x + cc * self.cell
        cy = self.top + cr * self.cell
        pygame.draw.rect(s, GOLD, (cx + 2, cy + 2, self.cell - 4, self.cell - 4),
                         width=4, border_radius=16)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, INK)
        s.blit(title, title.get_rect(center=(W // 2, 78)))
        handle = self.font_sm.render(HANDLE, True, CYAN)
        s.blit(handle, handle.get_rect(center=(W // 2, 128)))
        flags = sum(self.flag[r][c] for r in range(ROWS) for c in range(COLS))
        score = self.font_md.render(f"SCORE  {self.score}    FLAGS  {flags}/{MINES}", True, GOLD)
        s.blit(score, score.get_rect(center=(W // 2, 196)))
        hint = self.font_sm.render("arrows move   space open   F flag   R reset", True, (140, 190, 220))
        s.blit(hint, hint.get_rect(center=(W // 2, H - 64)))
        if self.boom > 0:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 70, 120, int(70 * self.boom / 0.6)))
            s.blit(flash, (0, 0))
        if self.done:
            win = self.font_md.render("LATTICE CLEAR", True, GOLD)
            s.blit(win, win.get_rect(center=(W // 2, 248)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/KYANITE_SWEEP_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
