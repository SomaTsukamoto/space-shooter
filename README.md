# Space Shooter — Neon Overdrive

A portrait arcade shooter made with Python and Pygame, playable on a computer
or packaged for a phone browser with pygbag. All ships and effects are drawn
in code; no image downloads or asset files are required.

## How to play

- Drag left and right anywhere on the screen. Your ship follows the drag
  without jumping to your finger. On a computer, use the arrow keys or A / D.
- Your ship fires automatically. Dodge enemies and pink enemy bullets.
- You have three shields, displayed at the top right. After taking a hit,
  your ship flashes and is invulnerable briefly. The yellow triangle has a
  forgiving collision area inside its body; its narrow tip is harmless.
- Destroy enemies within three seconds of each other to build a combo.
  Points increase from 10 to 20, 30, 40, then 50 per enemy at the x5 cap.
- Every ten kills drops a **P** pickup. Catch it for **12 seconds of triple
  shot** with a faster firing rate. Another P refreshes the timer.
- Every eighteenth kill drops an **H** pickup that restores one shield, up to three.
  On kills that are multiples of both ten and eighteen, P takes priority.
- Green saucers charge a shot (look for the pink ring), then fire toward you.
- After 25 seconds of ordinary combat, a **Dreadnought boss** arrives with
  aimed five-bullet fans. Move after each volley to dodge it.
- Defeat the boss to earn 1,000 points times the sector number, get both
  pickups, and advance to a faster sector. There is no final sector.
- When all shields are gone, tap or press a key to restart. Best score lasts
  for the current session. Escape closes the desktop game.

The logical screen is 360 × 640. The game uses a fixed 60 Hz simulation to
keep movement and timers independent of the display frame rate. Slow frames
are capped at six simulation steps to avoid a long catch-up after switching tabs.

## Run on your computer

Python 3.12 or 3.13 is recommended for the pinned Pygame version.
From this project folder, set up a local virtual environment once:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Then launch the game:

```bash
.venv/bin/python main.py
```

After editing the code, save it, close the game, and run that command again.
Dependencies only need reinstalling if `requirements.txt` changes.

## Browser version

```bash
.venv/bin/python -m pygbag --width 360 --height 640 --title "Neon Overdrive" .
```

Open http://localhost:8000 and click or tap the launch screen. The first visit
needs to download the Python browser runtime. Internet access is required.
Test touch controls on a real phone as well as on a desktop browser.

To build the static website:

```bash
.venv/bin/python -m pygbag --build --width 360 --height 640 --title "Neon Overdrive" .
```

Output is written to `build/web`.

## GitHub Pages

`.github/workflows/pages.yml` builds and deploys the browser version on pushes
to `main`. In the repository's **Settings → Pages**, select **GitHub Actions**
as the source. The configured site URL is
https://somatsukamoto.github.io/space-shooter/ . Local edits become available
there only after they are pushed and the deployment succeeds.

## Checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests use Pygame's dummy display and audio drivers. They cover scoring,
combo expiry, the yellow dart's collision area, damage protection, upgrades,
boss progression, restart, and a minute of simulated combat with rendering.
They do not replace playing the game or testing a real phone browser.
