"""
Space Shooter

A small portrait game: move the ship, dodge enemies, and let it shoot for you.
This one file is the whole game. Read it from top to bottom.

Run on your computer:
    pip install pygame pygbag
    python main.py

Web build (what GitHub Actions runs):
    pygbag --build --width 360 --height 640 --title "Space Shooter" .
"""

import asyncio
import math
import random
import sys

import pygame

# The game thinks in a tall phone screen. (0, 0) is the top-left corner,
# and y grows downward. On a phone, pygbag stretches this picture to fit.
WIDTH = 360
HEIGHT = 640
FPS = 60

POINTS_PER_ENEMY = 10
PLAYER_SPEED = 6
BULLET_SPEED = 11
FIRE_EVERY = 14  # frames between shots, at 60 frames per second

BLACK = (0, 0, 0)
PLAYER_CORE = (70, 255, 240)
PLAYER_GLOW = (0, 130, 140)
ENGINE = (255, 150, 40)
BULLET_CORE = (255, 255, 190)
BULLET_GLOW = (255, 200, 40)
SCORE_COLOR = (190, 255, 220)
HINT_COLOR = (190, 200, 220)
GAME_OVER_COLOR = (255, 90, 150)

# kind -> (width, height, core color, glow color)
ENEMIES = {
    "diamond": (32, 32, (255, 70, 180), (150, 0, 90)),
    "dart": (28, 36, (255, 160, 40), (140, 70, 0)),
    "saucer": (42, 24, (140, 255, 120), (20, 110, 40)),
}


def fit_phone_browser():
    """Stop a phone browser from scrolling or zooming while the player drags.

    Pygbag already scales our 360x640 canvas to the screen. These lines only
    restyle the page around that canvas. On a desktop they do nothing.
    """
    if sys.platform != "emscripten":
        return
    try:
        import platform

        page = platform.document
        page.body.style.background = "#000000"
        page.body.style.margin = "0"
        page.body.style.overflow = "hidden"
        page.body.style.touchAction = "none"
        page.body.style.userSelect = "none"
        page.body.style.overscrollBehavior = "none"
        page.documentElement.style.overflow = "hidden"
        page.documentElement.style.touchAction = "none"
        canvas = page.getElementById("canvas")
        if canvas is not None:
            canvas.style.touchAction = "none"
    except Exception:
        # If the page is not ready, the game still runs.
        pass


def open_window():
    """Open the game window.

    Desktop pygame can enlarge the window and still report mouse positions
    in the 360x640 coordinate system (the SCALED flag). The browser build
    lets pygbag do that scaling instead.
    """
    pygame.display.set_caption("Space Shooter")
    if sys.platform == "emscripten":
        return pygame.display.set_mode((WIDTH, HEIGHT))
    try:
        return pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
    except pygame.error:
        return pygame.display.set_mode((WIDTH, HEIGHT))


class Star:
    """A single background star that drifts downward."""

    def __init__(self):
        self.x = random.randrange(WIDTH)
        self.y = random.randrange(HEIGHT)
        # Three depths: far stars are dim and slow, near stars are bright.
        roll = random.random()
        if roll < 0.6:
            self.speed = 0.6
            self.radius = 1
            self.color = (80, 90, 110)
        elif roll < 0.9:
            self.speed = 1.4
            self.radius = 1
            self.color = (160, 175, 195)
        else:
            self.speed = 2.5
            self.radius = 2
            self.color = (230, 240, 255)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randrange(WIDTH)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)


class Burst:
    """A short expanding ring shown when something explodes."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.life = 12

    def update(self):
        self.life -= 1

    def draw(self, screen):
        radius = (13 - self.life) * 2
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius, width=2)


class Player:
    """The ship at the bottom of the screen. x and y are its center."""

    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 64
        self.w = 40
        self.h = 36
        self.cooldown = 8
        # Set on the first frame of a drag so the ship does not jump.
        self.grab_offset = None

    def rect(self):
        return pygame.Rect(
            int(self.x - self.w / 2),
            int(self.y - self.h / 2),
            self.w,
            self.h,
        )

    def hitbox(self):
        # A little smaller than the drawing, so a near miss feels fair.
        return self.rect().inflate(-12, -14)

    def move(self, pointer):
        if pointer.pointer_down:
            if self.grab_offset is None:
                # Remember where the finger grabbed the ship.
                # The ship then follows the drag instead of jumping to the finger.
                self.grab_offset = pointer.pointer_x - self.x
            self.x = pointer.pointer_x - self.grab_offset
        else:
            self.grab_offset = None
            if pointer.left:
                self.x -= PLAYER_SPEED
            if pointer.right:
                self.x += PLAYER_SPEED

        half = self.w / 2
        if self.x < half:
            self.x = half
        elif self.x > WIDTH - half:
            self.x = WIDTH - half

    def try_fire(self):
        self.cooldown -= 1
        if self.cooldown > 0:
            return None
        self.cooldown = FIRE_EVERY
        return Bullet(self.x, self.y - self.h / 2 - 8)

    def draw(self, screen, frame):
        nose_y = self.y - self.h / 2
        tail_y = self.y + self.h / 2 - 4
        points = [
            (self.x, nose_y),
            (self.x + self.w / 2, tail_y - 6),
            (self.x + 7, tail_y),
            (self.x - 7, tail_y),
            (self.x - self.w / 2, tail_y - 6),
        ]
        outline = [(int(x), int(y)) for x, y in points]
        pygame.draw.polygon(screen, PLAYER_GLOW, outline, width=6)
        pygame.draw.polygon(screen, PLAYER_CORE, outline)
        pygame.draw.circle(screen, (230, 255, 255), (int(self.x), int(self.y - 4)), 3)

        # The flame flickers by changing length every few frames.
        flame = 6 + (frame % 6)
        flame_points = [
            (int(self.x - 4), int(tail_y)),
            (int(self.x + 4), int(tail_y)),
            (int(self.x), int(tail_y + flame)),
        ]
        pygame.draw.polygon(screen, ENGINE, flame_points)


class Bullet:
    """A shot that travels up the screen. x and y are its center."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.w = 4
        self.h = 14

    def rect(self):
        return pygame.Rect(
            int(self.x - self.w / 2),
            int(self.y - self.h / 2),
            self.w,
            self.h,
        )

    def update(self):
        self.y -= BULLET_SPEED

    def draw(self, screen):
        glow = self.rect().inflate(4, 6)
        pygame.draw.rect(screen, BULLET_GLOW, glow)
        pygame.draw.rect(screen, BULLET_CORE, self.rect())


class Enemy:
    """An enemy that drifts down from the top. x and y are its center."""

    def __init__(self, x, kind, speed):
        self.x = x
        self.y = -30
        self.kind = kind
        self.speed = speed
        self.w, self.h, self.core, self.glow = ENEMIES[kind]
        self.alive = True

    def rect(self):
        return pygame.Rect(
            int(self.x - self.w / 2),
            int(self.y - self.h / 2),
            self.w,
            self.h,
        )

    def hitbox(self):
        return self.rect().inflate(-8, -6)

    def update(self):
        self.y += self.speed

    def draw(self, screen):
        if self.kind == "diamond":
            points = [
                (self.x, self.y - self.h / 2),
                (self.x + self.w / 2, self.y),
                (self.x, self.y + self.h / 2),
                (self.x - self.w / 2, self.y),
            ]
            self._draw_polygon(screen, points)
        elif self.kind == "dart":
            points = [
                (self.x - self.w / 2, self.y - self.h / 2 + 4),
                (self.x + self.w / 2, self.y - self.h / 2 + 4),
                (self.x, self.y + self.h / 2),
            ]
            self._draw_polygon(screen, points)
        else:
            body = self.rect()
            pygame.draw.ellipse(screen, self.glow, body.inflate(8, 6))
            pygame.draw.ellipse(screen, self.core, body)
            pygame.draw.line(
                screen,
                (230, 255, 230),
                (int(self.x - 8), int(self.y)),
                (int(self.x + 8), int(self.y)),
                width=2,
            )

    def _draw_polygon(self, screen, points):
        outline = [(int(x), int(y)) for x, y in points]
        pygame.draw.polygon(screen, self.glow, outline, width=5)
        pygame.draw.polygon(screen, self.core, outline)


class Input:
    """Keys and touch/mouse state for one frame, plus finger state that lasts longer.

    Touch on a phone arrives as mouse events, finger events, or both.
    We keep whichever one is actually down.
    """

    def __init__(self):
        self.quit = False
        self.tapped = False
        self.left = False
        self.right = False
        self.pointer_down = False
        self.pointer_x = 0
        self._finger_down = False
        self._finger_x = 0

    def read(self):
        self.quit = False
        self.tapped = False
        keys = pygame.key.get_pressed()
        self.left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        self.right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit = True
            elif event.type == pygame.KEYDOWN:
                self.tapped = True
                if event.key == pygame.K_ESCAPE:
                    self.quit = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.tapped = True
                self.pointer_x = event.pos[0]
            elif event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
                # Finger x is usually 0..1 across the screen. A value above 1
                # is already in pixels, so leave it alone.
                self._finger_down = True
                if event.x > 1:
                    self._finger_x = event.x
                else:
                    self._finger_x = event.x * WIDTH
                if event.type == pygame.FINGERDOWN:
                    self.tapped = True
            elif event.type == pygame.FINGERUP:
                self._finger_down = False

        if pygame.mouse.get_pressed()[0]:
            self.pointer_down = True
            self.pointer_x = pygame.mouse.get_pos()[0]
        elif self._finger_down:
            self.pointer_down = True
            self.pointer_x = self._finger_x
        else:
            self.pointer_down = False


class Particle:
    def __init__(self, x, y, color, big=False):
        self.x, self.y, self.color = x, y, color
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1, 6 if big else 3.5)
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = self.total = random.randint(18, 40)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= .97
        self.vy *= .97
        self.life -= 1

    def draw(self, screen):
        color = tuple(int(c * self.life / self.total) for c in self.color)
        pygame.draw.line(screen, color, (int(self.x), int(self.y)),
                         (int(self.x - self.vx * 2), int(self.y - self.vy * 2)), 2)


class Shot:
    def __init__(self, x, y, vx=0, vy=-11, hostile=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.hostile = hostile

    def rect(self):
        return pygame.Rect(int(self.x) - 3, int(self.y) - 5, 6, 10)

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen):
        x, y = int(self.x), int(self.y)
        if self.hostile:
            pygame.draw.circle(screen, (90, 20, 65), (x, y), 7)
            pygame.draw.circle(screen, (255, 75, 145), (x, y), 4)
            pygame.draw.circle(screen, (255, 225, 235), (x, y), 2)
        else:
            pygame.draw.line(screen, (20, 90, 110), (x, y + 14), (x, y - 7), 7)
            pygame.draw.line(screen, (90, 255, 240), (x, y + 8), (x, y - 7), 3)
            pygame.draw.line(screen, (240, 255, 255), (x, y + 3), (x, y - 7))


class Pickup:
    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.age = 0

    def rect(self):
        return pygame.Rect(int(self.x) - 15, int(self.y) - 15, 30, 30)

    def update(self):
        self.y += 1.8
        self.age += 1

    def draw(self, screen, font):
        color = (80, 255, 220) if self.kind == 'P' else (255, 120, 200)
        rect = self.rect()
        pygame.draw.circle(screen, (15, 40, 55), rect.center, 18)
        pygame.draw.rect(screen, color, rect, 2, border_radius=8)
        icon = font.render(self.kind, True, color)
        screen.blit(icon, icon.get_rect(center=rect.center))


class Boss:
    def __init__(self, wave):
        self.x, self.y = WIDTH / 2, -70
        self.age = 0
        self.max_hp = self.hp = 100 + (wave - 1) * 30

    def rect(self):
        return pygame.Rect(int(self.x) - 65, int(self.y) - 28, 130, 56)

    def update(self):
        self.age += 1
        self.y = min(126, self.y + 1.8)
        self.x = WIDTH / 2 + math.sin(self.age / 75) * 85

    def draw(self, screen):
        x, y = self.x, self.y
        points = [(x-68,y-15),(x-38,y-28),(x,y-12),(x+38,y-28),
                  (x+68,y-15),(x+48,y+20),(x+18,y+12),(x,y+30),
                  (x-18,y+12),(x-48,y+20)]
        pygame.draw.polygon(screen, (85, 30, 100), points, 7)
        pygame.draw.polygon(screen, (190, 60, 160), points)
        pygame.draw.lines(screen, (255, 140, 220), False, points[:5], 2)
        for offset in (-42, 0, 42):
            pygame.draw.circle(screen, (45, 15, 65), (int(x+offset),int(y)), 11)
            pygame.draw.circle(screen, (255, 220, 130), (int(x+offset),int(y)), 5)


class Game:
    """A fixed-step arcade game. All timers below count 60 Hz simulation ticks."""
    def __init__(self):
        self.best = 0
        self.font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 54)
        self.small_font = pygame.font.Font(None, 20)
        self.tiny_font = pygame.font.Font(None, 16)
        self.world = pygame.Surface((WIDTH, HEIGHT))
        self.background = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(self.background, (5+int(y/90), 7, 22+int(y/35)), (0,y), (WIDTH,y))
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((4, 4, 18, 210))
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets, self.enemy_shots, self.enemies = [], [], []
        self.particles, self.pickups, self.popups = [], [], []
        self.stars = [Star() for _ in range(64)]
        self.score = self.kills = self.combo = self.combo_timer = 0
        self.frames = 0
        self.hp = 3
        self.invincible = self.power = self.flash = self.shake = 0
        self.wave = 1
        self.wave_time = 0
        self.spawn_timer = 45
        self.fire_timer = 0
        self.boss = None
        self.over = False
        self.banner, self.banner_time = 'SECTOR 01', 150
        self.over_time = 0

    def notice(self, text, duration=120):
        self.banner, self.banner_time = text, duration

    def explode(self, x, y, color, big=False):
        self.particles.extend(Particle(x,y,color,big) for _ in range(48 if big else 16))
        # A hard cap keeps repeated explosions inexpensive on a phone.
        self.particles = self.particles[-400:]
        self.shake = max(self.shake, 10 if big else 3)

    def damage(self):
        if self.invincible or self.over:
            return
        self.hp -= 1
        self.combo = self.combo_timer = 0
        self.invincible = 110
        self.flash, self.shake = 8, 12
        self.explode(self.player.x, self.player.y, PLAYER_CORE, True)
        if self.hp <= 0:
            self.over = True
            self.over_time = 0
            self.best = max(self.best, self.score)

    def _destroy(self, enemy):
        enemy.alive = False
        self.kills += 1
        self.combo += 1
        self.combo_timer = 180
        points = 10 * min(5, self.combo)
        self.score += points
        self.best = max(self.best, self.score)
        self.explode(enemy.x, enemy.y, enemy.core)
        self.popups.append([enemy.x, enemy.y, f'+{points}', 40])
        # Guaranteed upgrades, rather than waiting for a lucky drop.
        if self.kills % 10 == 0:
            self.pickups.append(Pickup(enemy.x, enemy.y, 'P'))
        elif self.kills % 18 == 0:
            self.pickups.append(Pickup(enemy.x, enemy.y, 'H'))

    def update(self, pointer):
        self.frames += 1
        for star in self.stars:
            star.update()
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for popup in self.popups:
            popup[1] -= .7
            popup[3] -= 1
        self.popups = [p for p in self.popups if p[3] > 0]
        self.shake = max(0, self.shake - .4)
        self.flash = max(0, self.flash - 1)
        self.banner_time = max(0, self.banner_time - 1)
        if self.over:
            self.over_time += 1
            if pointer.tapped and self.over_time > 35:
                self.reset()
            return
        self.invincible = max(0, self.invincible - 1)
        self.power = max(0, self.power - 1)
        self.combo_timer = max(0, self.combo_timer - 1)
        if not self.combo_timer:
            self.combo = 0
        self.player.move(pointer)
        self.fire_timer -= 1
        if self.fire_timer <= 0:
            self.fire_timer = 8 if self.power else 12
            angles = (-.23, 0, .23) if self.power else (0,)
            for angle in angles:
                self.bullets.append(Shot(self.player.x, self.player.y-24, math.sin(angle)*11, -math.cos(angle)*11))
        self.wave_time += 1
        if self.boss is None and self.wave_time >= 60 * 25:
            self.boss = Boss(self.wave)
            self.enemies.clear()
            self.enemy_shots.clear()
            self.notice('WARNING / BOSS INBOUND', 150)
        if self.boss is None:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.spawn_timer = max(22, 54 - self.wave*4)
                kind = random.choice(list(ENEMIES))
                enemy = Enemy(random.randint(32, WIDTH-32), kind, min(3.8, 1.7+self.wave*.2))
                enemy.age = 0
                self.enemies.append(enemy)
        else:
            self.boss.update()
            if self.boss.y >= 126 and self.boss.age % max(30, 62-self.wave*3) == 0:
                # Aimed fan: moving after the volley leaves a safe gap.
                angle = math.atan2(self.player.y-self.boss.y, self.player.x-self.boss.x)
                for offset in (-.5, -.25, 0, .25, .5):
                    self.enemy_shots.append(Shot(self.boss.x, self.boss.y+26,
                                                math.cos(angle+offset)*3,
                                                math.sin(angle+offset)*3, True))
        for enemy in self.enemies:
            enemy.update()
            enemy.age += 1
            if enemy.kind == 'saucer' and enemy.age == 100:
                angle = math.atan2(self.player.y-enemy.y, self.player.x-enemy.x)
                self.enemy_shots.append(Shot(enemy.x, enemy.y, math.cos(angle)*2.7, math.sin(angle)*2.7, True))
        self.enemies = [e for e in self.enemies if e.y < HEIGHT+40]
        for shot in self.bullets + self.enemy_shots:
            shot.update()
        self.bullets = [b for b in self.bullets if -30 < b.x < WIDTH+30 and -25 < b.y < HEIGHT+30]
        self.enemy_shots = [b for b in self.enemy_shots if -30 < b.x < WIDTH+30 and -25 < b.y < HEIGHT+30]
        self._resolve_hits()
        if self.over:
            return
        for pickup in self.pickups[:]:
            pickup.update()
            if pickup.rect().colliderect(self.player.rect().inflate(12,12)):
                if pickup.kind == 'P':
                    self.power = 60 * 12
                    self.notice('TRIPLE SHOT / 12 SEC', 90)
                else:
                    self.hp = min(3, self.hp+1)
                    self.notice('SHIELD RESTORED', 90)
                self.explode(pickup.x, pickup.y, PLAYER_CORE)
                self.pickups.remove(pickup)
            elif pickup.y > HEIGHT+30:
                self.pickups.remove(pickup)

    def _resolve_hits(self):
        for bullet in self.bullets[:]:
            for enemy in self.enemies:
                if enemy.alive and bullet.rect().colliderect(enemy.hitbox()):
                    self._destroy(enemy)
                    self.bullets.remove(bullet)
                    break
            else:
                if self.boss and bullet.rect().colliderect(self.boss.rect()):
                    self.boss.hp -= 1
                    self.bullets.remove(bullet)
                    if self.boss.hp <= 0:
                        x, y = self.boss.x, self.boss.y
                        self.score += 1000 * self.wave
                        self.best = max(self.best, self.score)
                        self.explode(x, y, (255,110,210), True)
                        self.flash = 10
                        self.pickups.extend([Pickup(x-35,y,'P'),Pickup(x+35,y,'H')])
                        self.boss = None
                        self.enemy_shots.clear()
                        self.wave += 1
                        self.wave_time = 0
                        self.spawn_timer = 80
                        self.notice(f'SECTOR {self.wave:02d} / CLEAR +1000', 150)
        self.enemies = [e for e in self.enemies if e.alive]
        for enemy in self.enemies:
            # The yellow dart's narrow tip and empty corners are harmless.
            box = (pygame.Rect(int(enemy.x)-6,int(enemy.y)-14,12,18)
                   if enemy.kind == 'dart' else enemy.hitbox())
            if self.player.hitbox().colliderect(box):
                self.damage()
        if self.boss and self.player.hitbox().colliderect(self.boss.rect()):
            self.damage()
        for shot in self.enemy_shots[:]:
            if self.player.hitbox().colliderect(shot.rect()):
                self.enemy_shots.remove(shot)
                self.damage()

    def text(self, screen, text, x, y, color=HINT_COLOR, font=None, center=False):
        font = font or self.small_font
        image = font.render(text, True, color)
        rect = image.get_rect(midtop=(x,y)) if center else image.get_rect(topleft=(x,y))
        screen.blit(font.render(text, True, (0,0,0)), rect.move(1,2))
        screen.blit(image, rect)

    def draw(self, screen):
        world = self.world
        world.blit(self.background, (0,0))
        # A scrolling perspective grid gives the starfield a sense of speed.
        for x in range(-360, 721, 90):
            pygame.draw.line(world, (19,20,47), (180+(x-180)*.15,180), (x,HEIGHT))
        for i in range(10):
            t = ((i/10 + self.frames/900) % 1) ** 2
            y = int(180+t*(HEIGHT-180))
            pygame.draw.line(world, (25,22,52), (0,y), (WIDTH,y))
        for star in self.stars:
            star.draw(world)
        for enemy in self.enemies:
            enemy.draw(world)
            if enemy.kind == 'saucer' and 65 < enemy.age < 100:
                pygame.draw.circle(world, (255,90,140), (int(enemy.x),int(enemy.y)), 26, 1)
        if self.boss:
            self.boss.draw(world)
        for shot in self.bullets + self.enemy_shots:
            shot.draw(world)
        for pickup in self.pickups:
            pickup.draw(world, self.font)
        if not self.over and (not self.invincible or self.frames % 8 < 4):
            if self.power:
                pygame.draw.circle(world, (20,65,85), (int(self.player.x),int(self.player.y)), 29, 2)
            self.player.draw(world, self.frames)
        for particle in self.particles:
            particle.draw(world)
        for x,y,label,life in self.popups:
            self.text(world,label,int(x),int(y),BULLET_GLOW,center=True)
        screen.fill((6,7,22))
        offset = (random.randint(-int(self.shake),int(self.shake)), random.randint(-int(self.shake),int(self.shake))) if self.shake >= 1 else (0,0)
        screen.blit(world, offset)
        if self.flash:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((110,200,255,int(self.flash*9)))
            screen.blit(overlay,(0,0))
        pygame.draw.rect(screen, (8,12,28), (0,0,WIDTH,76))
        pygame.draw.line(screen, (40,90,110), (14,75), (WIDTH-14,75))
        self.text(screen,'NEON / OVERDRIVE',16,10,PLAYER_CORE,self.tiny_font)
        self.text(screen,f'{self.score:06d}',16,29,(240,250,255),self.font)
        self.text(screen,f'SECTOR {self.wave:02d}',250,10,HINT_COLOR,self.tiny_font)
        for i in range(3):
            rect = pygame.Rect(256+i*27,34,21,10)
            pygame.draw.rect(screen, PLAYER_CORE if i < self.hp else (35,45,65),rect,border_radius=3)
        if self.combo >= 2 and not self.over:
            self.text(screen,f'{self.combo} CHAIN / x{min(5,self.combo)}',180,88,BULLET_GLOW,center=True)
            pygame.draw.rect(screen,(65,48,35),(135,108,90,3))
            pygame.draw.rect(screen,BULLET_GLOW,(135,108,int(90*self.combo_timer/180),3))
        if self.boss:
            self.text(screen,'DREADNOUGHT',180,81,GAME_OVER_COLOR,self.tiny_font,True)
            pygame.draw.rect(screen,(55,25,55),(35,99,290,5))
            pygame.draw.rect(screen,GAME_OVER_COLOR,(35,99,int(290*self.boss.hp/self.boss.max_hp),5))
        if self.banner_time and not self.over:
            self.text(screen,self.banner,180,213,PLAYER_CORE,center=True)
            pygame.draw.line(screen,(35,95,110),(65,240),(295,240))
        if self.frames < 180:
            self.text(screen,'DRAG TO MOVE / AUTO FIRE',180,470,HINT_COLOR,center=True)
            self.text(screen,'ARROWS OR A / D',180,493,HINT_COLOR,self.tiny_font,True)
        if self.power and not self.over:
            self.text(screen,f'TRIPLE SHOT  {math.ceil(self.power/60):02d}s',16,603,PLAYER_CORE,self.tiny_font)
            pygame.draw.rect(screen,PLAYER_CORE,(16,622,int(328*self.power/720),3))
        if self.over:
            screen.blit(self.shade,(0,0))
            self.text(screen,'SIGNAL LOST',180,226,GAME_OVER_COLOR,self.big_font,True)
            self.text(screen,f'SCORE  {self.score:06d}',180,296,(240,250,255),self.font,True)
            self.text(screen,f'BEST  {self.best:06d}  /  SECTOR {self.wave:02d}',180,335,HINT_COLOR,center=True)
            pygame.draw.rect(screen,(40,160,170),(60,399,240,44),1,border_radius=8)
            self.text(screen,'TAP / PRESS KEY TO RETRY',180,414,PLAYER_CORE,center=True)


async def main():
    pygame.init()
    fit_phone_browser()
    screen = open_window()
    clock = pygame.time.Clock()
    game, controls = Game(), Input()
    accumulator = 0.0
    pending_tap = False
    while True:
        # Fixed simulation steps keep speed stable when display FPS fluctuates.
        accumulator += min(clock.tick(FPS)/1000, .1)
        controls.read()
        pending_tap = pending_tap or controls.tapped
        if controls.quit:
            break
        while accumulator >= 1/FPS:
            controls.tapped = pending_tap
            game.update(controls)
            pending_tap = False
            accumulator -= 1/FPS
        game.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == '__main__':
    asyncio.run(main())
