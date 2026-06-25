"""
Signal card — generates beautiful image for new signal announcement.
Uses Pillow for rendering with coin icons, gradient backgrounds, key levels.
Design: Pure black bg, white + green accents, NO blue glow, NO purple.
"""

import io
import re
import httpx
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from loguru import logger


# ─── Color Palette (Pure Black + White + Green accents) ──
COLORS = {
    "bg": (0, 0, 0),                # Pure black
    "card_bg": (10, 10, 10),        # Card panels — near-black
    "card_border": (30, 30, 30),    # Subtle grey border
    "accent_long": (0, 220, 130),   # Green for LONG
    "accent_short": (255, 60, 70),  # Red for SHORT
    "white": (255, 255, 255),
    "text_primary": (235, 235, 235),
    "text_secondary": (140, 140, 140),
    "text_dim": (75, 75, 75),
    "gold": (255, 200, 60),
    "tp_green": (0, 220, 130),
    "sl_red": (255, 60, 70),
    "entry_white": (255, 255, 255),
    "divider": (30, 30, 30),
    "grid": (18, 18, 18),           # Subtle grid lines
}

WIDTH = 1080


# Font cache to avoid repeated disk lookups
_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}
_cjk_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont | None] = {}


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load system font — DejaVu first (best Cyrillic), fallback to Noto/macOS."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    font_paths = [
        # DejaVu — best Latin/Cyrillic coverage (Ukrainian apostrophe etc.)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Noto Sans CJK — CJK fallback
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
    ]
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, size)
            _font_cache[key] = font
            return font
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _get_cjk_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | None:
    """Load CJK font for Chinese/Japanese/Korean text."""
    key = (size, bold)
    if key in _cjk_font_cache:
        return _cjk_font_cache[key]
    cjk_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for path in cjk_paths:
        try:
            font = ImageFont.truetype(path, size)
            _cjk_font_cache[key] = font
            return font
        except (IOError, OSError):
            continue
    _cjk_font_cache[key] = None
    return None


def _has_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\u30a0-\u30ff\u3040-\u309f\uac00-\ud7af]', text))


def _smart_font(size: int, bold: bool, text: str) -> ImageFont.FreeTypeFont:
    """Pick the right font based on text content — CJK font for CJK text, DejaVu otherwise."""
    if _has_cjk(text):
        cjk = _get_cjk_font(size, bold)
        if cjk:
            return cjk
    return _get_font(size, bold)


def _normalize_text(text: str) -> str:
    """Normalize Unicode characters that might render as squares.
    Converts exotic apostrophes/quotes to ASCII equivalents."""
    # Normalize various apostrophe/quote chars to ASCII
    text = text.replace('\u02BC', "'")   # MODIFIER LETTER APOSTROPHE (Ukrainian)
    text = text.replace('\u2019', "'")   # RIGHT SINGLE QUOTATION MARK
    text = text.replace('\u2018', "'")   # LEFT SINGLE QUOTATION MARK
    text = text.replace('\u201C', '"')   # LEFT DOUBLE QUOTATION MARK
    text = text.replace('\u201D', '"')   # RIGHT DOUBLE QUOTATION MARK
    text = text.replace('\u2014', '-')   # EM DASH
    text = text.replace('\u2013', '-')   # EN DASH
    text = text.replace('\u2026', '...')  # ELLIPSIS
    return text


async def _fetch_coin_logo(symbol: str, size: int = 64) -> Image.Image | None:
    """Fetch coin logo from CoinGecko CDN."""
    try:
        symbol_lower = symbol.lower()
        coin_ids = {
            "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
            "sol": "solana", "xrp": "ripple", "ada": "cardano",
            "doge": "dogecoin", "avax": "avalanche-2", "dot": "polkadot",
            "matic": "matic-network", "link": "chainlink", "uni": "uniswap",
            "atom": "cosmos", "ltc": "litecoin", "near": "near",
            "arb": "arbitrum", "op": "optimism", "apt": "aptos",
            "sui": "sui", "sei": "sei-network", "inj": "injective-protocol",
            "pepe": "pepe", "wif": "dogwifcoin", "bonk": "bonk",
            "shib": "shiba-inu", "ton": "the-open-network", "trx": "tron",
        }
        coin_id = coin_ids.get(symbol_lower, symbol_lower)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                params={"localization": "false", "tickers": "false", "market_data": "false"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                logo_url = data.get("image", {}).get("small")
                if logo_url:
                    img_resp = await client.get(logo_url, timeout=5)
                    if img_resp.status_code == 200:
                        logo = Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
                        return logo.resize((size, size), Image.LANCZOS)
    except Exception as e:
        logger.debug(f"Could not fetch logo for {symbol}: {e}")
    return None


def _draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill: tuple, outline: tuple | None = None):
    """Draw a rounded rectangle with optional outline."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)


def _draw_grid_overlay(img: Image.Image, region_w: int = 500, region_h: int = 400):
    """Draw a subtle transparent grid pattern in the top-left area."""
    overlay = Image.new("RGBA", (img.width, img.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    step = 40
    grid_color = (*COLORS["grid"], 40)  # Very subtle alpha

    for x in range(0, region_w, step):
        alpha = int(40 * (1 - x / region_w))
        draw.line([(x, 0), (x, region_h)], fill=(*COLORS["grid"], alpha), width=1)
    for yy in range(0, region_h, step):
        alpha = int(40 * (1 - yy / region_h))
        draw.line([(0, yy), (region_w, yy)], fill=(*COLORS["grid"], alpha), width=1)

    # Composite onto image
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img.paste(img_rgba.convert("RGB"))


def _draw_gradient_glow_fast(img: Image.Image, accent: tuple, secondary: tuple):
    """Subtle dark vignette — pure black, no colored glow."""
    # No colored glow — pure black background stays clean
    pass


def _draw_progress_bar(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
                       progress: float, color: tuple, bg_color: tuple = (25, 32, 48)):
    """Draw a rounded progress bar."""
    _draw_rounded_rect(draw, (x, y, x + w, y + h), h // 2, bg_color)
    if progress > 0:
        pw = max(h, int(w * min(progress, 1.0)))
        _draw_rounded_rect(draw, (x, y, x + pw, y + h), h // 2, color)


def _draw_dot(draw: ImageDraw.Draw, cx: int, cy: int, r: int, color: tuple):
    """Draw a filled circle (used as icon replacement for emoji)."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


async def generate_signal_card(
    coin_symbol: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    tp1: float,
    tp2: float | None,
    tp3: float | None,
    confidence: float,
    exchange: str,
    leverage: int | None = None,
    factors: list[str] | None = None,
    lang: str = "uk",
) -> bytes:
    """Generate a premium signal card image.
    Pure black bg, white + green accents only, no emoji."""
    is_long = direction.upper() == "LONG"

    accent = COLORS["accent_long"] if is_long else COLORS["accent_short"]

    # Calculate dynamic height based on content
    level_count = 2 + (1 if tp2 else 0) + (1 if tp3 else 0)  # entry + tp1 + (tp2?) + (tp3?) + SL
    level_count += 1  # stop loss
    factor_count = min(len(factors), 4) if factors else 0
    card_level_h = 52 + level_count * 72
    HEIGHT = 130 + card_level_h + 28 + 120 + 18 + 58 + 18
    if factor_count:
        HEIGHT += 48 + factor_count * 30 + 18
    HEIGHT += 55  # footer
    HEIGHT = max(720, HEIGHT)

    img = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])

    # No colored glow — pure black
    _draw_gradient_glow_fast(img, accent, accent)

    # Subtle grid overlay in top-left
    _draw_grid_overlay(img, region_w=420, region_h=350)

    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = _get_font(50, bold=True)
    font_sub = _get_font(24)
    font_label = _get_font(20)
    font_value = _get_font(32, bold=True)
    font_small = _get_font(18)
    font_big = _get_font(42, bold=True)
    font_pct = _get_font(22, bold=True)

    y = 40

    # ─── Header: Logo + COIN / USDT + Exchange + Badge ───
    logo = await _fetch_coin_logo(coin_symbol, size=68)
    if logo:
        img.paste(logo, (50, y + 2), logo)
        text_x = 135
    else:
        text_x = 50

    # Coin symbol + " / USDT" with clear separation
    sym_text = _normalize_text(coin_symbol.upper())
    sym_font = _smart_font(50, True, sym_text)
    sym_w = draw.textlength(sym_text, font=sym_font)
    draw.text((text_x, y - 2), sym_text, font=sym_font, fill=COLORS["white"])
    draw.text((text_x + sym_w + 4, y + 12), " / USDT", font=_get_font(28), fill=COLORS["text_secondary"])

    # Exchange + type on second line
    exch_text = f"{exchange.upper()}  ·  {'Futures' if leverage else 'Spot'}"
    draw.text((text_x, y + 52), exch_text, font=font_sub, fill=COLORS["text_dim"])

    # Direction badge (top-right)
    badge_text = "LONG" if is_long else "SHORT"
    badge_arrow = "\u25B2 " if is_long else "\u25BC "
    full_badge = badge_arrow + badge_text
    badge_font = _get_font(28, bold=True)
    badge_w = int(draw.textlength(full_badge, font=badge_font)) + 44
    badge_x = WIDTH - badge_w - 45
    _draw_rounded_rect(draw, (badge_x, y + 6, badge_x + badge_w, y + 52), 12, (*accent[:3], 25), outline=accent)
    draw.text((badge_x + 22, y + 12), full_badge, font=badge_font, fill=accent)

    y += 100

    # ─── Thin accent line ────────────────────────────
    draw.line([(50, y), (WIDTH - 50, y)], fill=COLORS["divider"], width=1)
    y += 18

    # ─── Trading Levels Card ─────────────────────────
    _draw_rounded_rect(draw, (36, y, WIDTH - 36, y + card_level_h), 16, COLORS["card_bg"], outline=COLORS["card_border"])

    cy = y + 20
    levels_label = {"uk": "ТОРГОВІ РІВНІ", "ru": "ТОРГОВЫЕ УРОВНИ"}.get(lang, "TRADING LEVELS")
    draw.text((68, cy), levels_label, font=font_label, fill=COLORS["text_dim"])
    cy += 38

    def draw_level(ly: int, label: str, color: tuple, price: float, show_pct: bool = True, is_last: bool = False):
        # Colored dot as icon
        _draw_dot(draw, 78, ly + 16, 6, color)
        # Label
        draw.text((95, ly + 2), label, font=font_label, fill=COLORS["text_secondary"])
        # Price
        draw.text((68, ly + 26), f"${price:,.6g}", font=font_value, fill=color)
        # Percentage from entry
        if show_pct and entry_price > 0:
            pct = (price - entry_price) / entry_price * 100
            pct_str = f"{pct:+.2f}%"
            pct_color = COLORS["tp_green"] if pct > 0 else COLORS["sl_red"] if pct < 0 else COLORS["text_secondary"]
            tw = draw.textlength(pct_str, font=font_pct)
            draw.text((WIDTH - 68 - tw, ly + 10), pct_str, font=font_pct, fill=pct_color)
        # Separator (unless last)
        if not is_last:
            draw.line([(68, ly + 64), (WIDTH - 68, ly + 64)], fill=COLORS["divider"], width=1)

    draw_level(cy, "Entry", COLORS["entry_white"], entry_price, show_pct=False)
    cy += 72

    draw_level(cy, "Take Profit 1", COLORS["tp_green"], tp1)
    cy += 72

    if tp2:
        draw_level(cy, "Take Profit 2", COLORS["tp_green"], tp2)
        cy += 72

    if tp3:
        draw_level(cy, "Take Profit 3", COLORS["gold"], tp3)
        cy += 72

    draw_level(cy, "Stop Loss", COLORS["sl_red"], stop_loss, is_last=True)

    y += card_level_h + 16

    # ─── Stats Row: Confidence + Leverage + R:R ──────
    stat_w = (WIDTH - 110) // 3
    gap = 8
    rr_ratio = abs(tp1 - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0

    stats = [
        ({"uk": "Впевненість", "ru": "Уверенность"}.get(lang, "Confidence"),
         f"{confidence:.0f}%",
         COLORS["tp_green"] if confidence >= 70 else COLORS["gold"] if confidence >= 50 else COLORS["sl_red"]),
        ("Leverage" if leverage else "Spot",
         f"{leverage}x" if leverage else "--",
         COLORS["gold"] if leverage else COLORS["text_secondary"]),
        ("Risk / Reward",
         f"1:{rr_ratio:.1f}",
         COLORS["white"]),
    ]

    for idx, (label, value, color) in enumerate(stats):
        sx = 42 + idx * (stat_w + gap)
        _draw_rounded_rect(draw, (sx, y, sx + stat_w, y + 105), 14, COLORS["card_bg"], outline=COLORS["card_border"])
        draw.text((sx + 18, y + 14), label, font=font_label, fill=COLORS["text_secondary"])
        draw.text((sx + 18, y + 44), value, font=font_big, fill=color)

    y += 120

    # ─── Confidence Bar ──────────────────────────────
    _draw_rounded_rect(draw, (36, y, WIDTH - 36, y + 48), 14, COLORS["card_bg"], outline=COLORS["card_border"])
    bar_label = {"uk": "AI Впевненість", "ru": "AI Уверенность"}.get(lang, "AI Confidence")
    draw.text((56, y + 12), bar_label, font=font_small, fill=COLORS["text_secondary"])
    bar_x = 280
    bar_w = WIDTH - 90 - bar_x
    conf_color = COLORS["tp_green"] if confidence >= 70 else COLORS["gold"] if confidence >= 50 else COLORS["sl_red"]
    _draw_progress_bar(draw, bar_x, y + 15, bar_w, 18, confidence / 100.0, conf_color)
    # Value at end of bar
    conf_text = f"{confidence:.0f}%"
    cw = draw.textlength(conf_text, font=_get_font(16, bold=True))
    draw.text((WIDTH - 52 - cw, y + 12), conf_text, font=_get_font(16, bold=True), fill=conf_color)

    y += 58

    # ─── Key Factors ─────────────────────────────────
    if factors:
        visible = factors[:4]
        fh = 48 + len(visible) * 30
        _draw_rounded_rect(draw, (36, y, WIDTH - 36, y + fh), 14, COLORS["card_bg"], outline=COLORS["card_border"])
        factor_label = _normalize_text({"uk": "Ключові фактори", "ru": "Ключевые факторы"}.get(lang, "Key Factors"))
        draw.text((68, y + 12), factor_label, font=font_label, fill=COLORS["text_dim"])
        fy = y + 40
        for ftext in visible:
            _draw_dot(draw, 80, fy + 8, 3, COLORS["text_secondary"])
            draw.text((92, fy), _normalize_text(ftext), font=font_small, fill=COLORS["text_primary"])
            fy += 30
        y += fh + 14

    # ─── Footer ──────────────────────────────────────
    footer_y = HEIGHT - 48
    draw.text((50, footer_y), "BLACKROOM", font=_get_font(23, bold=True), fill=accent)
    bot_handle = "@blackroomapp_bot"
    tw = draw.textlength(bot_handle, font=font_small)
    draw.text((WIDTH - 50 - tw, footer_y + 3), bot_handle, font=font_small, fill=COLORS["text_dim"])

    # Export
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ─── FREE channel simplified card ───────────────────────

FREE_WIDTH = 1080
FREE_HEIGHT = 700


async def generate_signal_card_free(
    coin_symbol: str,
    direction: str,
    entry_approx: str,
    potential_pct: float,
    confidence: float,
    exchange: str,
    lang: str = "uk",
) -> bytes:
    """Generate a minimal signal card for FREE channels.
    Same design language: pure black bg, white + green accents, no emoji."""
    is_long = direction.upper() == "LONG"
    accent = COLORS["accent_long"] if is_long else COLORS["accent_short"]

    img = Image.new("RGB", (FREE_WIDTH, FREE_HEIGHT), COLORS["bg"])
    _draw_gradient_glow_fast(img, accent, accent)

    _draw_grid_overlay(img, region_w=350, region_h=280)

    draw = ImageDraw.Draw(img)
    font_title = _get_font(46, bold=True)
    font_sub = _get_font(22)
    font_value = _get_font(30, bold=True)
    font_label = _get_font(20)
    font_big = _get_font(42, bold=True)

    y = 40

    # Header: logo + COIN / USDT
    logo = await _fetch_coin_logo(coin_symbol, size=60)
    if logo:
        img.paste(logo, (50, y + 2), logo)
        text_x = 130
    else:
        text_x = 50

    sym = _normalize_text(coin_symbol.upper())
    sym_font = _smart_font(46, True, sym)
    sw = draw.textlength(sym, font=sym_font)
    draw.text((text_x, y), sym, font=sym_font, fill=COLORS["white"])
    draw.text((text_x + sw + 4, y + 12), " / USDT", font=_get_font(24), fill=COLORS["text_secondary"])
    draw.text((text_x, y + 50), exchange.upper(), font=font_sub, fill=COLORS["text_dim"])

    badge_text = "\u25B2 LONG" if is_long else "\u25BC SHORT"
    badge_font = _get_font(26, bold=True)
    badge_w = int(draw.textlength(badge_text, font=badge_font)) + 36
    badge_x = FREE_WIDTH - badge_w - 45
    _draw_rounded_rect(draw, (badge_x, y + 8, badge_x + badge_w, y + 50), 10, (*accent[:3], 25), outline=accent)
    draw.text((badge_x + 18, y + 13), badge_text, font=badge_font, fill=accent)

    y += 100
    draw.line([(50, y), (FREE_WIDTH - 50, y)], fill=COLORS["divider"], width=1)
    y += 16

    # Entry zone + Potential
    _draw_rounded_rect(draw, (36, y, FREE_WIDTH - 36, y + 170), 16, COLORS["card_bg"], outline=COLORS["card_border"])

    zone_label = {"uk": "Зона входу", "ru": "Зона входа"}.get(lang, "Entry Zone")
    draw.text((68, y + 16), zone_label, font=font_label, fill=COLORS["text_secondary"])
    draw.text((68, y + 42), f"~{entry_approx}", font=font_value, fill=COLORS["entry_white"])

    pot_label = {"uk": "Потенціал", "ru": "Потенциал"}.get(lang, "Potential")
    draw.text((68, y + 92), pot_label, font=font_label, fill=COLORS["text_secondary"])
    draw.text((68, y + 118), f"+{potential_pct:.1f}%", font=font_big, fill=COLORS["tp_green"])

    y += 186

    # Confidence bar
    _draw_rounded_rect(draw, (36, y, FREE_WIDTH - 36, y + 55), 14, COLORS["card_bg"], outline=COLORS["card_border"])
    conf_label = {"uk": "Впевненість AI", "ru": "Уверенность AI"}.get(lang, "AI Confidence")
    conf_color = COLORS["tp_green"] if confidence >= 70 else COLORS["gold"] if confidence >= 50 else COLORS["sl_red"]
    draw.text((56, y + 15), f"{conf_label}:", font=font_label, fill=COLORS["text_secondary"])
    bar_x = 300
    bar_w = FREE_WIDTH - 100 - bar_x
    _draw_progress_bar(draw, bar_x, y + 18, bar_w, 18, confidence / 100.0, conf_color)
    tw = draw.textlength(f"{confidence:.0f}%", font=font_value)
    draw.text((FREE_WIDTH - 68 - tw, y + 12), f"{confidence:.0f}%", font=font_value, fill=conf_color)

    y += 68

    # CTA
    _draw_rounded_rect(draw, (36, y, FREE_WIDTH - 36, y + 52), 14, (15, 15, 15))
    cta_text = {
        "uk": "Точні TP/SL доступні на Pro / Elite",
        "ru": "Точные TP/SL доступны на Pro / Elite",
    }.get(lang, "Exact TP/SL available on Pro / Elite")
    # Lock icon as text
    draw.text((68, y + 14), "[PRO]", font=_get_font(16, bold=True), fill=COLORS["gold"])
    draw.text((130, y + 14), cta_text, font=font_sub, fill=COLORS["gold"])

    # Footer
    footer_y = FREE_HEIGHT - 45
    draw.text((50, footer_y), "BLACKROOM", font=_get_font(22, bold=True), fill=accent)
    bot_handle = "@blackroomapp_bot"
    tw = draw.textlength(bot_handle, font=_get_font(17))
    draw.text((FREE_WIDTH - 50 - tw, footer_y + 3), bot_handle, font=_get_font(17), fill=COLORS["text_dim"])

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ─── Result card (TP hit / SL hit / Closed) ─────────────

RESULT_HEIGHT = 550


async def generate_result_card(
    coin_symbol: str,
    direction: str,
    result_type: str,  # "tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "closed"
    entry_price: float,
    exit_price: float,
    pnl_pct: float,
    signal_id: int,
    lang: str = "uk",
) -> bytes:
    """Generate a result card for completed signals. No emoji icons."""
    is_win = pnl_pct > 0
    accent = COLORS["tp_green"] if is_win else COLORS["sl_red"]

    img = Image.new("RGB", (WIDTH, RESULT_HEIGHT), COLORS["bg"])
    _draw_gradient_glow_fast(img, accent, accent)

    _draw_grid_overlay(img, region_w=350, region_h=250)

    draw = ImageDraw.Draw(img)
    font_big = _get_font(46, bold=True)
    font_title = _get_font(36, bold=True)
    font_sub = _get_font(22)
    font_value = _get_font(28, bold=True)
    font_label = _get_font(20)

    y = 35

    # Result header — text-based, no emoji
    # If SL hit but PnL is positive (trailing SL above entry), show as "CLOSED" not "STOP LOSS"
    effective_type = result_type
    if result_type == "sl_hit" and pnl_pct > 0:
        effective_type = "closed"

    headers = {
        "tp1_hit": {"uk": "TP1 ДОСЯГНУТО", "en": "TP1 HIT", "ru": "TP1 ДОСТИГНУТ"},
        "tp2_hit": {"uk": "TP2 ДОСЯГНУТО", "en": "TP2 HIT", "ru": "TP2 ДОСТИГНУТ"},
        "tp3_hit": {"uk": "TP3 ДОСЯГНУТО", "en": "TP3 HIT", "ru": "TP3 ДОСТИГНУТ"},
        "sl_hit": {"uk": "СТОП-ЛОСС", "en": "STOP LOSS", "ru": "СТОП-ЛОСС"},
        "closed": {"uk": "ЗАКРИТО", "en": "CLOSED", "ru": "ЗАКРЫТ"},
    }
    header_text = headers.get(effective_type, headers["closed"]).get(lang, headers.get(effective_type, headers["closed"])["en"])

    # Status dot before text
    status_dot_color = COLORS["tp_green"] if is_win else COLORS["sl_red"]
    _draw_dot(draw, 65, y + 22, 10, status_dot_color)
    draw.text((85, y), header_text, font=font_big, fill=accent)

    y += 60
    draw.line([(50, y), (WIDTH - 50, y)], fill=COLORS["divider"], width=1)
    y += 16

    # Coin + PnL card
    _draw_rounded_rect(draw, (36, y, WIDTH - 36, y + 200), 16, COLORS["card_bg"], outline=COLORS["card_border"])

    # Coin
    logo = await _fetch_coin_logo(coin_symbol, size=52)
    if logo:
        img.paste(logo, (60, y + 22), logo)
        cx = 128
    else:
        cx = 60

    is_long = direction.upper() == "LONG"
    sym = _normalize_text(coin_symbol.upper())
    sym_font = _smart_font(36, True, sym)
    sw = draw.textlength(sym, font=sym_font)
    draw.text((cx, y + 20), sym, font=sym_font, fill=COLORS["white"])
    draw.text((cx + sw + 6, y + 28), "/ USDT", font=font_sub, fill=COLORS["text_secondary"])

    dir_text = "\u25B2 LONG" if is_long else "\u25BC SHORT"
    draw.text((cx, y + 60), dir_text, font=font_sub, fill=COLORS["accent_long"] if is_long else COLORS["accent_short"])

    # PnL
    pnl_str = f"{pnl_pct:+.2f}%"
    pnl_font = _get_font(50, bold=True)
    tw = draw.textlength(pnl_str, font=pnl_font)
    draw.text((WIDTH - 68 - tw, y + 28), pnl_str, font=pnl_font, fill=accent)

    # Entry -> Exit
    draw.text((68, y + 108), "Entry", font=font_label, fill=COLORS["text_secondary"])
    draw.text((68, y + 134), f"${entry_price:,.6g}", font=font_value, fill=COLORS["entry_white"])

    draw.text((WIDTH // 2, y + 108), "Exit", font=font_label, fill=COLORS["text_secondary"])
    draw.text((WIDTH // 2, y + 134), f"${exit_price:,.6g}", font=font_value, fill=accent)

    # Signal ID
    id_text = f"#{signal_id}"
    id_w = draw.textlength(id_text, font=font_sub)
    draw.text((WIDTH - 68 - id_w, y + 170), id_text, font=font_sub, fill=COLORS["text_dim"])

    y += 220

    # Footer
    footer_y = RESULT_HEIGHT - 45
    draw.text((50, footer_y), "BLACKROOM", font=_get_font(22, bold=True), fill=accent)
    bot_handle = "@blackroomapp_bot"
    tw = draw.textlength(bot_handle, font=_get_font(17))
    draw.text((WIDTH - 50 - tw, footer_y + 3), bot_handle, font=_get_font(17), fill=COLORS["text_dim"])

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()
