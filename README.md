# Space Shooter

A small portrait space shooter made with Python and Pygame. Your ship stays at the bottom, enemies drift down from the top, and the ship fires on its own. It is meant to be played in a phone browser.

Play it at https://somatsukamoto.github.io/space-shooter/ once GitHub Pages is switched on (see below).

## How to play

- Drag left and right anywhere on the screen to move the ship. The ship follows your finger; it does not jump to where you first touch.
- On a computer, the left and right arrow keys (or A and D) move the ship.
- Shots fire automatically.
- Each enemy you destroy is worth 10 points.
- If an enemy hits your ship, the game ends. Tap the screen, or press a key, to play again.
- Your best score for this visit is kept until you close the page.

The picture is drawn at 360 by 640 pixels and scaled to fit the screen, so it stays tall on a phone.

## Run it on your computer

You need Python 3.8 or newer.

```bash
pip install pygame pygbag
python main.py
```

If the `python` command is not found, use `python3 main.py` instead. You can also install the pinned versions in `requirements.txt` with `pip install -r requirements.txt`.

Close the window, or press Escape, to quit.

## Build the web version

[pygbag](https://pygame-web.github.io/) packages this game so a browser can run the Python code. From this folder:

```bash
pygbag .
```

If that command is not found, use `python -m pygbag .` (or `python3 -m pygbag .`). Then open http://localhost:8000 . The page asks you to click or tap before the game starts. That screen is part of pygbag, and it is what unlocks the page on a phone.

To only write the website files, which is what GitHub Actions does:

```bash
pygbag --build --width 360 --height 640 --title "Space Shooter" .
```

The site is written to `build/web`. The first load in a browser downloads the Python runtime, so it is slower than later visits.

## Publish on GitHub Pages

Pushes to the `main` branch run `.github/workflows/pages.yml`. That workflow builds the game and deploys the `build/web` folder with GitHub's Pages actions.

After this is merged, turn the site on yourself:

1. Open the repository **Settings**.
2. Open **Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.

The game is then published at https://somatsukamoto.github.io/space-shooter/ . Nothing is deployed until that source is selected.

## Files

- `main.py` is the whole game. It creates the window, reads touch and keys, moves the ships, checks hits, and draws every frame.
- `requirements.txt` lists the two libraries: `pygame` for playing on your computer, and `pygbag` for the browser build.
- `.github/workflows/pages.yml` is the GitHub Actions workflow that builds `build/web` and deploys it to GitHub Pages.
- `.gitignore` tells git to skip the build output and Python's cache files. The website is built on GitHub, not stored in the repository.

There are no image files. Ships, bullets, and stars are rectangles, circles, and polygons drawn in code.

## How the game loop works

Each frame, `main` does three things in order:

1. **Input.** Read the touch, the mouse, or the keyboard.
2. **Update.** Move the ship, the bullets, and the enemies, then see what hit.
3. **Draw.** Paint the stars and the ships, then show the new picture.

After drawing, the loop waits with `await asyncio.sleep(0)`. That hands the browser a chance to show the frame. Pygbag requires it. On your computer it just lets the loop share the machine. The same `main.py` runs in both places.
