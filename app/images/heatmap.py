"""
Heatmap — generates market correlation and performance heatmaps.
Uses matplotlib + seaborn for professional chart rendering.
"""

import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger


async def generate_performance_heatmap(
    coins: list[str],
    daily_pnls: dict[str, list[float]],
    days_labels: list[str],
    title: str = "Signal Performance Heatmap",
) -> bytes:
    """
    Generate a heatmap of per-coin daily PnL.
    coins: list of coin symbols
    daily_pnls: {coin: [pnl_day1, pnl_day2, ...]}
    days_labels: ["Mon", "Tue", ...]
    """
    # Build matrix
    data = []
    for coin in coins:
        row = daily_pnls.get(coin, [0] * len(days_labels))
        data.append(row[:len(days_labels)])

    matrix = np.array(data) if data else np.zeros((1, len(days_labels)))

    fig, ax = plt.subplots(figsize=(max(10, len(days_labels) * 1.2), max(6, len(coins) * 0.6)))

    # Dark theme
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")

    cmap = sns.diverging_palette(10, 150, as_cmap=True)  # Red to Green

    sns.heatmap(
        matrix,
        xticklabels=days_labels,
        yticklabels=coins,
        cmap=cmap,
        center=0,
        annot=True,
        fmt=".1f",
        linewidths=1,
        linecolor="#1a1a1a",
        cbar_kws={"label": "PnL %", "shrink": 0.8},
        ax=ax,
    )

    ax.set_title(title, color="white", fontsize=16, pad=15, fontweight="bold")
    ax.tick_params(colors="white", labelsize=10)
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")

    # Colorbar text color
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_tick_params(color="white")
    cbar.ax.yaxis.label.set_color("white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


async def generate_correlation_heatmap(
    coins: list[str],
    correlation_matrix: np.ndarray,
    title: str = "Coin Correlation Matrix",
) -> bytes:
    """Generate a correlation heatmap between coins."""
    fig, ax = plt.subplots(figsize=(max(8, len(coins) * 0.8), max(6, len(coins) * 0.6)))
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")

    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))

    sns.heatmap(
        correlation_matrix,
        mask=mask,
        xticklabels=coins,
        yticklabels=coins,
        cmap="coolwarm",
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        linecolor="#1a1a1a",
        vmin=-1,
        vmax=1,
        square=True,
        ax=ax,
    )

    ax.set_title(title, color="white", fontsize=14, pad=15, fontweight="bold")
    ax.tick_params(colors="white", labelsize=9, rotation=45)

    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


async def generate_winrate_heatmap(
    timeframes: list[str],
    directions: list[str],
    win_rates: np.ndarray,
    title: str = "Win Rate by Timeframe & Direction",
) -> bytes:
    """Generate win rate heatmap by timeframe and direction."""
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")

    sns.heatmap(
        win_rates,
        xticklabels=timeframes,
        yticklabels=directions,
        cmap="RdYlGn",
        annot=True,
        fmt=".0f",
        linewidths=1,
        linecolor="#1a1a1a",
        vmin=0,
        vmax=100,
        ax=ax,
    )

    ax.set_title(title, color="white", fontsize=14, pad=10, fontweight="bold")
    ax.tick_params(colors="white")

    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()
