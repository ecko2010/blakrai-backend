"""
Digest image — daily/weekly summary card with key stats, top signals, and performance chart.
"""

import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from app.images.signal_card import _get_font, _draw_rounded_rect, _draw_progress_bar, COLORS

WIDTH = 1080
DIGEST_HEIGHT = 1850


def _draw_gradient(img: Image.Image, top_color: tuple, bottom_color: tuple):
    """Simple top-to-bottom linear gradient fill."""
    w, h = img.size
    for yy in range(h):
        ratio = yy / h
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        ImageDraw.Draw(img).line([(0, yy), (w, yy)], fill=(r, g, b))


async def generate_digest_image(
    period: str,  # "daily" or "weekly"
    date_range: str,
    total_signals: int,
    win_rate: float,
    total_pnl: float,
    tp1_rate: float,
    tp2_rate: float,
    tp3_rate: float,
    top_signals: list[dict],
    pnl_series: list[float] | None = None,
    portfolio_start: list[int] | None = None,
    lang: str = "uk",
) -> bytes:
    """Generate a comprehensive digest summary image.

    Args:
        portfolio_start: list of starting capitals for simulation, e.g. [1000, 5000, 10000]
    """
    is_positive = total_pnl >= 0

    bg_top = (5, 5, 5) if is_positive else (8, 3, 3)
    bg_bottom = (0, 0, 0)
    accent = COLORS["tp_green"] if is_positive else COLORS["sl_red"]

    img = Image.new("RGB", (WIDTH, DIGEST_HEIGHT), bg_top)
    _draw_gradient(img, bg_top, bg_bottom)
    draw = ImageDraw.Draw(img)

    font_huge = _get_font(62, bold=True)
    font_title = _get_font(40, bold=True)
    font_subtitle = _get_font(26)
    font_label = _get_font(20)
    font_value = _get_font(32, bold=True)
    font_small = _get_font(18)

    y = 40

    # ─── Header ─────────────────────────────────
    if period == "daily":
        header = {"uk": "ЩОДЕННИЙ ДАЙДЖЕСТ", "ru": "ЕЖЕДНЕВНЫЙ ДАЙДЖЕСТ"}.get(lang, "DAILY DIGEST")
    else:
        header = {"uk": "ТИЖНЕВИЙ ДАЙДЖЕСТ", "ru": "НЕДЕЛЬНЫЙ ДАЙДЖЕСТ"}.get(lang, "WEEKLY DIGEST")

    text_w = draw.textlength(header, font=font_title)
    draw.text(((WIDTH - text_w) / 2, y), header, font=font_title, fill=COLORS["white"])
    y += 55

    date_w = draw.textlength(date_range, font=font_subtitle)
    draw.text(((WIDTH - date_w) / 2, y), date_range, font=font_subtitle, fill=COLORS["text_secondary"])
    y += 60

    # ─── Key Metrics Row ────────────────────────
    _draw_rounded_rect(draw, (40, y, WIDTH - 40, y + 180), 20, COLORS["card_bg"])

    # 3 columns
    col_w = (WIDTH - 80) // 3

    # Total PnL
    cx = 40 + col_w // 2
    pnl_label = {"uk": "Загальний PnL", "ru": "Общий PnL"}.get(lang, "Total PnL")
    lbl_w = draw.textlength(pnl_label, font=font_label)
    draw.text((cx - lbl_w / 2, y + 20), pnl_label, font=font_label, fill=COLORS["text_secondary"])
    pnl_text = f"{'+' if total_pnl > 0 else ''}{total_pnl:.1f}%"
    pnl_w = draw.textlength(pnl_text, font=font_huge)
    pnl_color = COLORS["tp_green"] if total_pnl > 0 else COLORS["sl_red"]
    draw.text((cx - pnl_w / 2, y + 55), pnl_text, font=font_huge, fill=pnl_color)
    _signals_word = {"uk": "сигналів", "ru": "сигналов"}.get(lang, "signals")
    count_text = f"{total_signals} {_signals_word}"
    ct_w = draw.textlength(count_text, font=font_small)
    draw.text((cx - ct_w / 2, y + 135), count_text, font=font_small, fill=COLORS["text_secondary"])

    # Win Rate
    cx = 40 + col_w + col_w // 2
    wr_label = "Win Rate"
    lbl_w = draw.textlength(wr_label, font=font_label)
    draw.text((cx - lbl_w / 2, y + 20), wr_label, font=font_label, fill=COLORS["text_secondary"])
    wr_text = f"{win_rate:.0f}%"
    wr_w = draw.textlength(wr_text, font=font_huge)
    wr_color = COLORS["tp_green"] if win_rate >= 55 else COLORS["gold"] if win_rate >= 45 else COLORS["sl_red"]
    draw.text((cx - wr_w / 2, y + 55), wr_text, font=font_huge, fill=wr_color)

    # Average per signal
    cx = 40 + col_w * 2 + col_w // 2
    avg_label = {"uk": "Середній", "ru": "Средний"}.get(lang, "Per Signal")
    lbl_w = draw.textlength(avg_label, font=font_label)
    draw.text((cx - lbl_w / 2, y + 20), avg_label, font=font_label, fill=COLORS["text_secondary"])
    avg_pnl = total_pnl / total_signals if total_signals > 0 else 0
    avg_text = f"{'+' if avg_pnl > 0 else ''}{avg_pnl:.2f}%"
    avg_w = draw.textlength(avg_text, font=font_huge)
    draw.text((cx - avg_w / 2, y + 55), avg_text, font=font_huge, fill=pnl_color)

    y += 200

    # ─── TP Hit Rates ───────────────────────────
    _draw_rounded_rect(draw, (40, y, WIDTH - 40, y + 130), 20, COLORS["card_bg"])
    tp_title = "TP Hit Rates"
    draw.text((80, y + 15), tp_title, font=font_subtitle, fill=COLORS["text_secondary"])

    bar_y_start = y + 55
    bar_height = 20
    max_bar = WIDTH - 280

    for i, (rate, label) in enumerate([(tp1_rate, "TP1"), (tp2_rate, "TP2"), (tp3_rate, "TP3")]):
        bx = 80 + i * ((WIDTH - 160) // 3)
        draw.text((bx, bar_y_start), f"{label}: {rate:.0f}%", font=font_value, fill=COLORS["white"])
        # Mini bar
        bar_w = int(((WIDTH - 160) // 3 - 40) * rate / 100)
        _draw_rounded_rect(draw, (bx, bar_y_start + 40, bx + ((WIDTH - 160) // 3 - 40), bar_y_start + 40 + 12), 6, (25, 25, 25))
        if bar_w > 0:
            bar_color = COLORS["tp_green"] if i < 2 else COLORS["gold"]
            _draw_rounded_rect(draw, (bx, bar_y_start + 40, bx + bar_w, bar_y_start + 40 + 12), 6, bar_color)

    y += 150

    # ─── PnL Chart (matplotlib) ─────────────────
    if pnl_series and len(pnl_series) >= 2:
        chart_img = _render_pnl_chart(pnl_series, accent)
        if chart_img:
            chart = Image.open(io.BytesIO(chart_img)).convert("RGBA")
            chart = chart.resize((WIDTH - 80, 300), Image.LANCZOS)
            img.paste(chart, (40, y), chart)
            y += 320
    else:
        y += 20

    # ─── Portfolio Simulation ($1K/$5K/$10K) ────
    if portfolio_start is None:
        portfolio_start = [1_000, 5_000, 10_000]
    if total_pnl != 0:
        sim_title = {"uk": "Симуляція портфоліо", "ru": "Симуляция портфолио"}.get(lang, "Portfolio Simulation")
        draw.text((80, y), sim_title, font=font_subtitle, fill=COLORS["gold"])
        y += 40
        _draw_rounded_rect(draw, (40, y, WIDTH - 40, y + 30 + len(portfolio_start) * 50), 20, COLORS["card_bg"])
        py = y + 15
        for start_cap in portfolio_start:
            end_cap = start_cap * (1 + total_pnl / 100)
            diff = end_cap - start_cap
            diff_sign = "+" if diff >= 0 else ""
            row_color = COLORS["tp_green"] if diff >= 0 else COLORS["sl_red"]
            row_text = f"${start_cap:,}  →  ${end_cap:,.0f}  ({diff_sign}{diff:,.0f})"
            draw.text((80, py), row_text, font=font_value, fill=row_color)
            py += 50
        y = py + 15

    # ─── Top Signals ────────────────────────────
    if top_signals:
        top_title = {"uk": "Топ сигнали", "ru": "Топ сигналы"}.get(lang, "Top Signals")
        draw.text((80, y), top_title, font=font_subtitle, fill=COLORS["gold"])
        y += 45

        for i, sig in enumerate(top_signals[:5]):
            _draw_rounded_rect(draw, (40, y, WIDTH - 40, y + 70), 15, COLORS["card_bg"])
            rank = f"#{i + 1}"
            draw.text((70, y + 18), rank, font=font_value, fill=COLORS["gold"])
            draw.text((140, y + 12), sig.get("coin", ""), font=font_value, fill=COLORS["white"])
            draw.text((140, y + 45), sig.get("direction", ""), font=font_small, fill=COLORS["text_secondary"])

            pnl = sig.get("pnl", 0)
            pnl_str = f"{'+' if pnl > 0 else ''}{pnl:.2f}%"
            p_w = draw.textlength(pnl_str, font=font_value)
            p_color = COLORS["tp_green"] if pnl > 0 else COLORS["sl_red"]
            draw.text((WIDTH - 80 - p_w, y + 18), pnl_str, font=font_value, fill=p_color)

            y += 80

    # ─── Footer ─────────────────────────────────
    footer_y = DIGEST_HEIGHT - 60
    draw.text((50, footer_y), "BLACKROOM", font=_get_font(22, bold=True), fill=accent)
    bot_handle = "@blackroomapp_bot"
    tw = draw.textlength(bot_handle, font=_get_font(17))
    draw.text((WIDTH - 50 - tw, footer_y + 3), bot_handle, font=_get_font(17), fill=COLORS["text_dim"])

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


def _render_pnl_chart(pnl_series: list[float], accent_color: tuple) -> bytes | None:
    """Render a small cumulative PnL line chart using matplotlib."""
    try:
        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        cumulative = np.cumsum(pnl_series)
        x = range(len(cumulative))

        # Fill area
        color_hex = "#{:02x}{:02x}{:02x}".format(*accent_color[:3])
        ax.fill_between(x, cumulative, alpha=0.15, color=color_hex)
        ax.plot(x, cumulative, color=color_hex, linewidth=2.5)

        # Zero line
        ax.axhline(y=0, color="#444", linewidth=0.5, linestyle="--")

        ax.tick_params(colors="white", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#444")
        ax.spines["left"].set_color("#444")

        plt.tight_layout(pad=0.5)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, transparent=True, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return None
