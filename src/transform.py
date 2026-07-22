"""mtg-check transform — runs on TRMNL's sandbox runtime after each poll.

Input: first Scryfall search page (+ trmnl globals / custom field values).
Fetches remaining pages, sorts per user setting, picks the current card
deterministically from wall-clock time (index = now / rotation window,
modulo set size) — every card shows exactly once per full cycle, no
server-side state needed.
"""
import json
import re
import time
import urllib.request

MAX_PAGES = 6  # 175 cards/page -> up to ~1050 cards
RARITY_RANK = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3, "special": 4, "bonus": 5}
COLOR_RANK = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "trmnl-mtg-check/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def field(input, key, default=""):
    trmnl = input.get("trmnl") or {}
    cfv = (trmnl.get("plugin_settings") or {}).get("custom_fields_values") or {}
    value = cfv.get(key, input.get(key, default))
    return default if value in (None, "") else value


def color_bucket(card, face):
    if "Land" in (face.get("type_line") or card.get("type_line") or ""):
        return 7
    colors = face.get("colors")
    if colors is None:
        colors = card.get("colors") or []
    if len(colors) == 0:
        return 6            # colorless
    if len(colors) > 1:
        return 5            # multicolor
    return COLOR_RANK.get(colors[0], 6)


def number_key(card):
    digits = "".join(ch for ch in card.get("collector_number", "0") if ch.isdigit())
    return (int(digits or 0), card.get("collector_number", ""))


def shape_face(card):
    """Front face for double-faced/adventure cards; the card itself otherwise.
    Defensive: card_faces can theoretically be an empty list."""
    if card.get("image_uris"):
        return card
    faces = card.get("card_faces") or []
    return faces[0] if faces else card


LEGAL_FORMATS = ["standard", "pioneer", "modern", "legacy", "pauper", "commander"]

SYMBOL_RE = re.compile(r"\{([^}]+)\}")


def symbolize(text):
    """Replace Scryfall symbol notation ({T}, {W}, {W/U}, {2}, ...) with the
    official symbol SVGs, sized to the surrounding text via em height."""
    def repl(match):
        code = "".join(ch for ch in match.group(1) if ch.isalnum())
        if not code:
            return match.group(1)
        return ('<img src="https://svgs.scryfall.io/card-symbols/%s.svg"'
                ' style="height: 0.85em"/>' % code)
    return SYMBOL_RE.sub(repl, text)


def clip(text, limit):
    """Truncate without cutting through a {symbol}; returns (text, was_cut)."""
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    if cut.rfind("{") > cut.rfind("}"):
        cut = cut[:cut.rfind("{")]
    return cut, True


def shape(card):
    face = shape_face(card)
    imgs = face.get("image_uris") or card.get("image_uris") or {}
    mana = symbolize(face.get("mana_cost") or "")
    pt = f'{face["power"]}/{face["toughness"]}' if face.get("power") else face.get("loyalty", "")
    # Adventure/split cards keep oracle_text/flavor only in card_faces, not top-level
    oracle = face.get("oracle_text")
    flavor = face.get("flavor_text")
    if not oracle and card.get("card_faces"):
        oracle = "\n&mdash;\n".join(f.get("oracle_text", "") for f in card["card_faces"])
        flavor = flavor or next((f.get("flavor_text") for f in card["card_faces"] if f.get("flavor_text")), None)
        pt = pt or next((f'{f["power"]}/{f["toughness"]}' for f in card["card_faces"] if f.get("power")), "")
    prices = card.get("prices") or {}
    legalities = card.get("legalities") or {}
    oracle = oracle or ""
    body, body_cut = clip(oracle, 260)
    paras = oracle.split("\n")
    if len(paras) >= 2 and len(paras[0]) + len(paras[1]) <= 219:
        first = paras[0] + "\n" + paras[1]
    else:
        first, _ = clip(paras[0], 220)
    legal_in = [f.capitalize() for f in LEGAL_FORMATS if legalities.get(f) == "legal"]
    return {
        "name": face.get("name", card["name"]),
        "mana": mana,
        # Plain-text fallback for clamped one-liners (the clamp engine drops
        # trailing <img> symbols, leaving a dangling separator)
        "mana_txt": (face.get("mana_cost") or "").replace("{", "").replace("}", ""),
        "type": face.get("type_line", card.get("type_line", "")),
        "text": symbolize(body) + ("&hellip;" if body_cut else ""),
        "text_first": symbolize(first),
        "flavor": (flavor or "")[:180],
        "pt": pt,
        "rarity": card.get("rarity", ""),
        "cn": card.get("collector_number", ""),
        "artist": card.get("artist", ""),
        "img": imgs.get("normal", ""),
        "art": imgs.get("art_crop", ""),
        "price_eur": prices.get("eur"),
        "price_eur_foil": prices.get("eur_foil"),
        "price_usd": prices.get("usd"),
        "edhrec": card.get("edhrec_rank"),
        "edhrec_fmt": (f">{card['edhrec_rank'] // 1000}k" if (card.get("edhrec_rank") or 0) >= 1000
                       else (f"#{card['edhrec_rank']}" if card.get("edhrec_rank") else "")),
        "spoiled": (card.get("preview") or {}).get("previewed_at", ""),
        "buy_url": (card.get("purchase_uris") or {}).get("cardmarket", ""),
        "spoiled_by": (card.get("preview") or {}).get("source", ""),
        "keywords": (lambda kw, first: "" if kw and all(k.strip().lower() in first for k in kw.split(",")) else kw)(
            ", ".join((card.get("keywords") or [])[:4]), (oracle or "").split("\n")[0].lower()),
        "legal": ("All formats" if len(legal_in) == len(LEGAL_FORMATS) else " &middot; ".join(legal_in)),
        "released": card.get("released_at", ""),
        "reprint": card.get("reprint", False),
    }


def run(input):
    cards = list(input.get("data") or [])
    next_page = input.get("next_page") if input.get("has_more") else None
    pages = 0
    while next_page and pages < MAX_PAGES:
        page = fetch(next_page)
        cards.extend(page.get("data") or [])
        next_page = page.get("next_page") if page.get("has_more") else None
        pages += 1
    if not cards:
        wanted = field(input, "set_custom", "") or field(input, "set", "hob")
        return {"error": f"No cards found for set '{wanted}'", "total": 0}

    lands = str(field(input, "lands", "all")).split(":_")[-1]
    if lands in ("basics", "none"):
        needle = "Basic Land" if lands == "basics" else "Land"
        kept = [c for c in cards
                if needle not in (shape_face(c).get("type_line") or c.get("type_line") or "")]
        if kept:  # a pure land set would otherwise filter down to nothing
            cards = kept

    # Not defensive fiction — an observed TRMNL quirk: select options that were
    # once saved from quoted string options (not YAML label/value mappings) persist
    # as the parameterized label, e.g. "the_hobbit_(aug_2026):_hob". Instances keep
    # that broken value until re-saved, so we extract the part after the last ":_".
    sort = str(field(input, "sort", "number")).split(":_")[-1]
    if sort == "color":
        cards.sort(key=lambda c: (color_bucket(c, shape_face(c)), c.get("cmc", 0), c.get("name", "")))
    elif sort == "rarity":
        cards.sort(key=lambda c: (RARITY_RANK.get(c.get("rarity"), 9), c.get("cmc", 0), c.get("name", "")))
    else:
        cards.sort(key=number_key)

    rotate_digits = "".join(ch for ch in str(field(input, "rotate", "15")).split(":_")[-1] if ch.isdigit())
    rotate_min = max(int(rotate_digits or 15), 5)
    idx = (int(time.time()) // (rotate_min * 60)) % len(cards)
    two_up = str(field(input, "two_up", "false")).lower() in ("true", "yes", "1")

    sample = cards[0]
    return {
        "card": shape(cards[idx]),
        "card_next": shape(cards[(idx + 1) % len(cards)]),
        "two_up": two_up,
        "pos": idx + 1,
        "total": len(cards),
        "set_name": sample.get("set_name", ""),
        "release": sample.get("released_at", ""),
    }

