"""Run with .venv/bin/python -m unittest discover -s tests -v."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import random
import unittest
import pygame
import main


class ArcadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        random.seed(12)
        self.game = main.Game()
        self.controls = main.Input()

    def enemy(self, x=180, y=300, kind='dart'):
        enemy = main.Enemy(x, kind, 0)
        enemy.y, enemy.age = y, 0
        return enemy

    def test_combo_cap_and_timeout(self):
        g = self.game
        for _ in range(6):
            g._destroy(self.enemy())
        self.assertEqual(g.score, 200)
        self.assertEqual(g.best, 200)
        for _ in range(180):
            g.invincible = 2
            g.update(self.controls)
        self.assertEqual(g.combo, 0)
        score = g.score
        g._destroy(self.enemy())
        self.assertEqual(g.score-score, 10)

    def test_dart_near_miss_body_and_bullet(self):
        g = self.game
        e = self.enemy(y=540)
        g.enemies = [e]
        g.player.y = 565
        self.assertTrue(g.player.hitbox().colliderect(e.hitbox()))
        g._resolve_hits()
        self.assertEqual(g.hp, 3)
        g.player.y = 540
        g._resolve_hits()
        self.assertEqual(g.hp, 2)
        g._resolve_hits()
        self.assertEqual(g.hp, 2, 'Invulnerability prevents consecutive damage')
        g.reset()
        g.enemies = [self.enemy()]
        g.bullets = [main.Shot(189, 300)]
        g._resolve_hits()
        self.assertEqual(g.score, 10)

    def test_pickups_and_triple_shot_expire(self):
        g = self.game
        g.pickups = [main.Pickup(g.player.x, g.player.y, 'P')]
        g.update(self.controls)
        self.assertEqual(g.power, 720)
        g.bullets.clear()
        g.fire_timer = 0
        g.update(self.controls)
        self.assertEqual(len(g.bullets), 3)
        self.assertEqual(sorted(round(b.vx,2) for b in g.bullets), [-2.51,0,2.51])
        g.power = 1
        g.bullets.clear()
        g.fire_timer = 0
        g.update(self.controls)
        self.assertEqual(len(g.bullets), 1)
        g.hp = 2
        g.pickups = [main.Pickup(g.player.x,g.player.y,'H')]
        g.update(self.controls)
        self.assertEqual(g.hp, 3)

    def test_boss_arrival_volley_and_defeat(self):
        g = self.game
        g.wave_time = 1499
        g.update(self.controls)
        self.assertIsNotNone(g.boss)
        g.boss.y = 126
        g.boss.age = 58
        g.update(self.controls)
        self.assertEqual(len(g.enemy_shots), 5)
        g.boss.hp = 1
        g.bullets = [main.Shot(g.boss.x,g.boss.y)]
        g._resolve_hits()
        self.assertIsNone(g.boss)
        self.assertEqual(g.wave, 2)
        self.assertEqual(g.score, 1000)
        self.assertEqual(g.best, 1000)
        self.assertFalse(g.enemy_shots)
        self.assertEqual([p.kind for p in g.pickups], ['P','H'])

    def test_death_and_restart_preserve_best(self):
        g = self.game
        g.score = g.best = 1234
        for _ in range(3):
            g.invincible = 0
            g.damage()
        self.assertTrue(g.over)
        self.controls.tapped = True
        g.update(self.controls)
        self.assertTrue(g.over, 'Do not restart accidentally on the death frame')
        self.controls.tapped = False
        for _ in range(36):
            g.update(self.controls)
        self.controls.tapped = True
        g.update(self.controls)
        self.assertFalse(g.over)
        self.assertEqual((g.hp,g.score,g.best), (3,0,1234))
        self.assertFalse(g.pickups or g.enemy_shots or g.boss)

    def test_long_simulation_and_render(self):
        g = self.game
        screen = pygame.Surface((main.WIDTH,main.HEIGHT))
        for frame in range(3600):
            g.invincible = 2
            self.controls.left = frame % 240 < 120
            self.controls.right = not self.controls.left
            g.update(self.controls)
            if frame % 120 == 0:
                g.draw(screen)
        self.assertLessEqual(len(g.particles),400)
        self.assertLess(len(g.enemy_shots),200)
        self.assertGreater(g.frames,3500)
        g.over = True
        g.draw(screen)
