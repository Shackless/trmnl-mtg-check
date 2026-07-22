# Contributing

Pull requests are very welcome — bug fixes, new card layouts, more sets in the dropdown, better Scryfall field usage, you name it. Issues are welcome too if you'd rather report than patch.

## Dev setup

```sh
docker run --rm -p 4567:4567 -v "$(pwd):/plugin" trmnl/trmnlp serve --bind 0.0.0.0
```

Preview at http://localhost:4567 — this polls the real Scryfall API and runs `src/transform.py` locally.

## Before you open a PR

- **Verify both device sizes** (rendered PNG, not just the HTML preview):
  - TRMNL OG: `http://localhost:4567/render/full.png`
  - TRMNL X: `http://localhost:4567/render/full.png?width=1872&height=1404&screen_classes=screen%20screen--4bit%20screen--v2%20screen--lg%20screen--density-2x`
  - Check all four views (`full`, `half_horizontal`, `half_vertical`, `quadrant`) if your change touches shared data.
- **No blacklisted inline styles** (`display`, `justify-content`, `text-align`, `margin`, `padding`, `font-size`, `object-fit`, colors) — use TRMNL framework utility classes. See [AGENTS.md](AGENTS.md) for the full rules and the framework quirks this plugin works around.
- Keep `id: 389435` in `src/settings.yml` — it targets the maintainer's plugin for recipe updates and is a no-op for everyone else.
- Screenshots of your renders in the PR description are appreciated.

## Working with AI agents

This repo ships agent instructions in [AGENTS.md](AGENTS.md) (CLAUDE.md points there). If you let an agent make changes, make sure it reads that file first — it encodes hard-won TRMNL framework pitfalls that are not documented upstream.

## What happens after merge

The published TRMNL recipe is updated by the maintainer (`trmnlp push` + recipe update on usetrmnl.com) — see the release flow section in AGENTS.md. Your change ships to all recipe users with the next recipe update.
