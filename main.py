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


class Game:
    """Everything that changes while you play: ships, score, and game over."""

    def __init__(self):
        self.best = 0
        self.font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 52)
        self.small_font = pygame.font.Font(None, 22)
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, 120))
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.bursts = []
        self.stars = [Star() for _ in range(48)]
        self.score = 0
        self.over = False
        self.show_hint = True
        self.frames = 0
        self.spawn_timer = 40

    def update(self, pointer):
        self.frames += 1
        for star in self.stars:
            star.update()
        for burst in self.bursts:
            burst.update()
        self.bursts = [burst for burst in self.bursts if burst.life > 0]

        if self.over:
            # A new tap or key press starts a fresh run. Best score is kept.
            if pointer.tapped:
                self.reset()
            return

        if self.frames > 180 or pointer.pointer_down or pointer.left or pointer.right:
            self.show_hint = False

        self.player.move(pointer)
        self._fire()
        self._spawn()
        self._move_shots_and_enemies()
        self._resolve_hits()

    def _fire(self):
        bullet = self.player.try_fire()
        if bullet is not None:
            self.bullets.append(bullet)

    def _difficulty(self):
        # Every 10 destroyed enemies, new enemies arrive a little faster.
        step = self.score // (POINTS_PER_ENEMY * 10)
        interval = max(24, 56 - step * 4)
        speed = min(4.0, 1.65 + step * 0.22)
        return interval, speed

    def _spawn(self):
        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return
        interval, speed = self._difficulty()
        self.spawn_timer = interval
        kind = random.choice(list(ENEMIES))
        margin = 36
        x = random.randint(margin, WIDTH - margin)
        self.enemies.append(Enemy(x, kind, speed))

    def _move_shots_and_enemies(self):
        for bullet in self.bullets:
            bullet.update()
        # Drop shots that have left the top of the screen.
        self.bullets = [bullet for bullet in self.bullets if bullet.y > -20]

        for enemy in self.enemies:
            enemy.update()
        # Enemies that fly past the ship are simply gone. Only a hit ends the game.
        self.enemies = [enemy for enemy in self.enemies if enemy.y < HEIGHT + 40]

    def _resolve_hits(self):
        # 当たり判定: 見た目より少し小さい矩形が重なったら命中
        kept_bullets = []
        for bullet in self.bullets:
            hit = None
            for enemy in self.enemies:
                if enemy.alive and bullet.rect().colliderect(enemy.hitbox()):
                    hit = enemy
                    break
            if hit is None:
                kept_bullets.append(bullet)
            else:
                self._destroy(hit)
        self.bullets = kept_bullets
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]

        # Bullets are checked first, so a shot on the same frame as a crash
        # still counts as destroying that enemy.
        for enemy in self.enemies:
            if self.player.hitbox().colliderect(enemy.hitbox()):
                self.over = True
                self.bursts.append(Burst(self.player.x, self.player.y, PLAYER_CORE))
                break

    def _destroy(self, enemy):
        enemy.alive = False
        self.score += POINTS_PER_ENEMY
        if self.score > self.best:
            self.best = self.score
        self.bursts.append(Burst(enemy.x, enemy.y, enemy.core))

    def draw(self, screen):
        screen.fill(BLACK)
        for star in self.stars:
            star.draw(screen)
        for enemy in self.enemies:
            enemy.draw(screen)
        for bullet in self.bullets:
            bullet.draw(screen)
        self.player.draw(screen, self.frames)
        for burst in self.bursts:
            burst.draw(screen)

        if self.over:
            screen.blit(self.shade, (0, 0))
            self._draw_text(screen, self.big_font, "GAME OVER", 270, GAME_OVER_COLOR)
            self._draw_text(screen, self.font, f"SCORE {self.score}", 320, SCORE_COLOR)
            self._draw_text(screen, self.small_font, f"BEST {self.best}", 352, HINT_COLOR)
            self._draw_text(screen, self.small_font, "Tap to restart", 400, HINT_COLOR)
            return

        self._draw_text(screen, self.font, f"SCORE {self.score}", 32, SCORE_COLOR)
        if self.show_hint:
            self._draw_text(screen, self.small_font, "Drag left and right", 300, HINT_COLOR)
            self._draw_text(screen, self.small_font, "Arrow keys work too", 326, HINT_COLOR)

    def _draw_text(self, screen, font, text, y, color):
        shadow = font.render(text, True, BLACK)
        image = font.render(text, True, color)
        rect = image.get_rect(center=(WIDTH // 2, y))
        screen.blit(shadow, rect.move(2, 2))
        screen.blit(image, rect)


async def main():
    pygame.init()
    fit_phone_browser()
    screen = open_window()
    clock = pygame.time.Clock()
    game = Game()
    controls = Input()

    running = True
    while running:
        # ゲームループ: 毎フレーム「入力 → 更新 → 描画」を繰り返す
        controls.read()
        if controls.quit:
            running = False
            break

        game.update(controls)
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
        # ブラウザに1フレーム描画させる（pygbagでは必須）
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
