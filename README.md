# Magic: The Gathering (MtG) Card Show — a TRMNL plugin

A [TRMNL](https://usetrmnl.com) e-ink plugin that rotates through the cards of any Magic: The Gathering set, one card at a time — like a slow-motion spoiler season on your wall.

Powered by the excellent [Scryfall API](https://scryfall.com/docs/api). No server required: the plugin uses TRMNL's polling strategy plus a serverless transform.

## Features

- **Full card view**: card image on the left; name, mana cost, type line, keywords, oracle text, flavor text and P/T laid out like the real card on the right
- **Prices**: Cardmarket (EUR), foil and TCGplayer (USD) — appear automatically once Scryfall lists them
- **EDHREC rank** (compressed, e.g. `>31k`) and a **Cardmarket QR code** to jump straight to the listing
- **Rotation without repeats**: walks the whole set in your chosen order, one card per interval, then starts over — stateless (time-based), so it never loses its place
- All four TRMNL view sizes (full / half horizontal / half vertical / quadrant) for mashups
- Optional **two-cards-side-by-side** full-screen layout
- Tuned for both TRMNL OG (800×480) and TRMNL X (1872×1404)

## Configuration (plugin settings UI)

| Setting | Description |
| --- | --- |
| Set | Dropdown of current sets (The Hobbit, Marvel Super Heroes, Star Trek, …) |
| Custom set code | Overrides the dropdown — any code from [scryfall.com/sets](https://scryfall.com/sets) |
| Card order | Collector number · Color (then mana cost) · Rarity (then mana cost) |
| Next card every | 15 min · 30 min · 1 h · 6 h · 1 day |
| Two cards side by side | Full screen shows current + next card |

## Install

**Option A — import into TRMNL**: create a new Private Plugin (strategy: polling), paste the contents of `src/settings.yml` and the four `src/*.liquid` templates, and add `src/transform.py` as the serverless transform (language: Python).

**Option B — trmnlp** (recommended for tinkering):

```sh
git clone https://github.com/Shackless/trmnl-mtg-check.git
cd trmnl-mtg-check
docker run --rm -p 4567:4567 -v "$(pwd):/plugin" trmnl/trmnlp serve --bind 0.0.0.0
# → http://localhost:4567 (live preview against the real Scryfall API)
```

To push it into your TRMNL account: `trmnlp login`, then `trmnlp push`.

## Development notes

See [CLAUDE.md](CLAUDE.md) for the architecture, the TRMNL framework quirks this plugin works around, and how to preview the TRMNL X layout locally.

## Credits & legal

- Card data and images via [Scryfall](https://scryfall.com); prices via Cardmarket/TCGplayer through Scryfall.
- Magic: The Gathering is © Wizards of the Coast. This project is unofficial fan content and is not affiliated with or endorsed by Wizards of the Coast or Scryfall.
- Code licensed under the [MIT License](LICENSE).
