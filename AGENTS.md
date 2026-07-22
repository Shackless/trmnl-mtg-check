# AGENTS.md — trmnl-mtg-check

Agent instructions for working on this TRMNL plugin. Everything here was learned empirically while building it; trust it over intuition.

## Architecture

- `strategy: polling` against the Scryfall search API (page 1 as polled input) + `src/transform.py` on TRMNL's serverless sandbox runtime: fetches remaining pages (`MAX_PAGES` guard), sorts per user setting, picks the current card **statelessly** via `index = now // rotate_window % count`. No server, no state file — every card shows exactly once per cycle.
- User configuration via `custom_fields:` in `src/settings.yml`. Values reach the transform under `input["trmnl"]["plugin_settings"]["custom_fields_values"]` and Liquid/polling_url directly as `{{ keyname }}`.
- The polling URL carries a default chain (`{{ set_custom | default: set | default: "hob" }}`) so instances without saved field values still work, plus a `split: ":_" | last` guard against a TRMNL quirk (see pitfalls).

## Local development

```sh
docker run --rm -p 4567:4567 -v "$(pwd):/plugin" trmnl/trmnlp serve --bind 0.0.0.0
```

- OG preview (800×480): `http://localhost:4567/render/full.png`
- **TRMNL X preview** (this is the layout truth for big screens):
  `http://localhost:4567/render/full.png?width=1872&height=1404&screen_classes=screen%20screen--4bit%20screen--v2%20screen--lg%20screen--density-2x`
  (classes/dimensions from `https://usetrmnl.com/api/models`, model `v2`)
- Always verify the rendered **PNG**, not just the HTML preview, and always verify **both** sizes before pushing.
- trmnlp caches poll+transform results in the container — recreate the container (`docker rm -f`, not `restart`) when results look stale.

## TRMNL framework pitfalls (v3.1.x, all verified the hard way)

- **`.flex--col` becomes `display: block` in the `screen--lg` context** (TRMNL X). `justify-content` silently stops working. Columns that must distribute on the X need inline `style="display: flex; flex-direction: column; ..."`.
- **`.flex--col` has `flex: 1 1 0`** — as a sibling of a growing element it steals space. Text blocks next to images need `style="flex: 0 0 auto"`.
- **Footer pinning** (stats always at the bottom, text flows on top): normal flow, then `<div style="flex: 1 1 0; min-height: 0"></div>` as a spacer, then the bottom block. Collapses to zero on small screens.
- **Margin tokens exist only in steps 5/10/16/20/24/40** (`mt--10` etc.; ~4× scaled on the X). `mt--15`, `mt--30` and named sizes like `mt--large` are silent no-ops. Responsive variants (`lg:mt--20`) work for existing steps.
- **Typography**: don't stack `lg:` size bumps — the X already scales base classes (~2.3×). Size the base classes so 800×480 looks well-filled (body text `value--xsmall`, not `label--small`).
- **`data-clamp` is unreliable** with `white-space: pre-line` multi-paragraph text (can collapse to one line). Truncate server-side in the transform instead (`[:260]` + ellipsis).
- **Select options with label/value MUST be real YAML mappings** (`- The Hobbit (Aug 2026): hob`, unquoted). Quoted as a string, TRMNL stores the parameterized label as the value (`the_hobbit_(aug_2026):_hob`) — hence the `split(":_")[-1]` guards in URL and transform.
- **Recipe review forbids inline styles** for: `display`, `justify-content`, `padding`, `margin`, `text-align`, `font-size`, `object-fit`, `background-color`, `color`, `border-radius`. Use framework utilities instead: `flex flex--col` (the combo — also sidesteps the lg display:block bug), `stretch` (a flex-grow spacer, replaces space-between constructs), `w--full`/`h--full`, `text--right`/`text--center`, `block`, `pr--5`, `lg:mt--{5|10|16|20|24|40}`. Still allowed inline (verified: no utility exists, including arbitrary variants): `flex` basis values, `min-width: 0`/`min-height: 0` (fundamental flexbox requirement for shrinkable text columns), `max-height`, `white-space: pre-line`, `align-items`. For fixed px sizes use arbitrary utilities `w--[110px]`/`h--[110px]` (these DO exist); `min-w--[0px]`/percentage variants do NOT.
- **`.flex` defaults to `align-items: center`** — in a `flex--col` column this horizontally centers narrow children. Fix: inline `align-items: flex-start` (allowed) or give text lines `w--full`.
- **The clamp engine mismeasures next to `stretch` spacers** (short names get ellipsized despite free space). Let the growing element grow itself (`style="flex: 1 1 0; min-width: 0"`) instead of pairing it with a spacer sibling.
- Scryfall requires an `Accept` header and a real `User-Agent`; default urllib gets HTTP 400/403.
- Adventure/split cards keep `oracle_text` only in `card_faces`, not top-level — see `shape()` in the transform.
- The platform caches rendered screens: markup pushes do **not** trigger an immediate re-render (next poll or "Force Refresh" does). Put a visible marker in the markup when you need to detect staleness.

## Publishing checklist

- `src/settings.yml` must not contain an `id:` line in this public repo (it's account-specific; `trmnlp push` adds it locally).
- Keep the title bar and labels in English.
- Payloads/templates: keywords line auto-hides when the keywords already lead the oracle text (`shape()` dedup).

## "The card never changes on its own!"

If a user reports the card only changes on manual refresh: check the **playlist item's schedule/duration** on usetrmnl.com. With a single-item playlist that value effectively becomes the content refresh cadence and overrides the plugin's 15-minute `refresh_interval` (a 24 h duration = one new card per day). Diagnosis: `GET https://trmnl.com/api/current_screen` with the device API key — if `refresh_rate` reports ~86400 s instead of ~900 s, that's the gate. Fix: set the playlist item duration to 15 minutes.

## Maintainer release flow (how changes reach devices)

GitHub is a **push mirror** of the maintainer's private Gitea (one-way). The TRMNL recipe is a snapshot of the maintainer's plugin instance — **merging a PR on GitHub alone changes nothing on TRMNL**. Full flow:

1. Merge the PR on GitHub.
2. Maintainer pulls GitHub into the source repo (`git pull github main`, resolve, push origin) so the mirror stays consistent.
3. Verify renders at both sizes (see Local development above).
4. `trmnlp push` (the `id:` in `src/settings.yml` targets the maintainer's plugin — pushes from other accounts are rejected, so the committed id is harmless).
5. Update the published recipe on usetrmnl.com (recipe updates may go through TRMNL review again).
