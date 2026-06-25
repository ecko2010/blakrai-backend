"""
AI-powered wallet portfolio analytics.
Generates weekly digests, analyzes portfolio composition, detects patterns.
"""

from datetime import datetime, timezone, timedelta

import httpx
from loguru import logger

from app.config import settings
from app.database import async_session
from app.models import TrackedWallet, WalletToken, WalletTransaction, User, Tier, ChainType


async def generate_portfolio_analysis(wallet_id: int) -> str | None:
    """
    Generate AI analysis for a single wallet portfolio.
    Returns formatted text or None on failure.
    """
    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet:
            return None

        tokens = wallet.tokens or []
        if not tokens:
            return "Портфель порожній — немає токенів для аналізу."

    total_usd = sum(t.value_usd or 0 for t in tokens)
    token_lines = []
    for t in sorted(tokens, key=lambda x: x.value_usd or 0, reverse=True)[:15]:
        pct = ((t.value_usd / total_usd) * 100) if total_usd and t.value_usd else 0
        token_lines.append(f"- {t.symbol}: {t.balance:,.6g} (${t.value_usd:,.2f}, {pct:.1f}%)")

    portfolio_text = "\n".join(token_lines)

    # Get recent transactions for context
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet_id)
            .order_by(WalletTransaction.timestamp.desc().nullslast())
            .limit(20)
        )
        recent_txs = result.scalars().all()

    tx_summary = ""
    if recent_txs:
        buys = sum(1 for tx in recent_txs if tx.tx_type == "receive")
        sells = sum(1 for tx in recent_txs if tx.tx_type == "transfer")
        swaps = sum(1 for tx in recent_txs if tx.tx_type == "swap")
        tx_summary = f"\nОстанні {len(recent_txs)} транзакцій: {buys} отримань, {sells} відправок, {swaps} swap-ів"

    prompt = f"""Проаналізуй крипто-портфель гаманця ({wallet.chain.value}, адреса: {wallet.address[:12]}...):

Загальна вартість: ${total_usd:,.2f}

Токени:
{portfolio_text}
{tx_summary}

Дай коротку аналітику:
1. Оцінка диверсифікації (добре/погано)
2. Ризик-профіль (консервативний/помірний/агресивний)
3. Ключові спостереження
4. Рекомендації (коротко, 2-3 пункти)

Відповідай українською, коротко та конкретно. Не більше 500 символів."""

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Ти — крипто-аналітик. Даєш коротку практичну аналітику портфелів. Відповідай українською."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 600,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Portfolio AI analysis error: {e}")
        return None


async def generate_weekly_wallet_digest(user_id: int) -> str | None:
    """
    Generate weekly digest for all user wallets.
    Called by scheduler on Sunday.
    """
    from sqlalchemy import select, func

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return None

        # Only PRO+ get AI digests
        if user.tier == Tier.FREE:
            return None

        result = await session.execute(
            select(TrackedWallet).where(
                TrackedWallet.user_id == user_id,
                TrackedWallet.is_active == True,
            )
        )
        wallets = result.scalars().all()

    if not wallets:
        return None

    digest_parts = []
    total_portfolio_usd = 0.0

    for wallet in wallets:
        label = wallet.label or wallet.address[:8] + "..."
        chain = wallet.chain.value.upper()
        val = wallet.total_value_usd or 0
        total_portfolio_usd += val

        tokens = wallet.tokens or []
        top3 = sorted(tokens, key=lambda t: t.value_usd or 0, reverse=True)[:3]
        top3_str = ", ".join(f"{t.symbol} (${t.value_usd:,.0f})" for t in top3 if t.value_usd)

        digest_parts.append(
            f"📋 <b>{label}</b> [{chain}]\n"
            f"   💰 ${val:,.2f}" + (f" | Top: {top3_str}" if top3_str else "")
        )

    # Count transactions this week
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    async with async_session() as session:
        wallet_ids = [w.id for w in wallets]
        if wallet_ids:
            tx_count = await session.scalar(
                select(func.count(WalletTransaction.id)).where(
                    WalletTransaction.wallet_id.in_(wallet_ids),
                    WalletTransaction.created_at >= week_ago,
                )
            ) or 0
        else:
            tx_count = 0

    header = (
        f"📊 <b>Тижневий дайджест гаманців</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏦 Гаманців: {len(wallets)} | "
        f"💰 Загалом: ${total_portfolio_usd:,.2f}\n"
        f"📝 Транзакцій за тиждень: {tx_count}\n\n"
    )

    body = "\n\n".join(digest_parts)

    # For ELITE: add AI analysis of the largest wallet
    ai_note = ""
    if user.tier == Tier.ELITE and wallets:
        biggest = max(wallets, key=lambda w: w.total_value_usd or 0)
        if biggest.total_value_usd and biggest.total_value_usd > 10:
            analysis = await generate_portfolio_analysis(biggest.id)
            if analysis:
                ai_note = f"\n\n🤖 <b>AI Аналітика</b> ({biggest.label or biggest.address[:8]}...):\n{analysis}"

    return header + body + ai_note


async def send_weekly_digests():
    """Send weekly wallet digests to all users with tracked wallets. Called by scheduler."""
    from sqlalchemy import select
    from aiogram import Bot

    async with async_session() as session:
        result = await session.execute(
            select(TrackedWallet.user_id).where(TrackedWallet.is_active == True).distinct()
        )
        user_ids = [r[0] for r in result.all()]

    if not user_ids:
        return

    logger.info(f"Sending wallet digests to {len(user_ids)} users")

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    sent = 0

    try:
        for uid in user_ids:
            try:
                digest = await generate_weekly_wallet_digest(uid)
                if not digest:
                    continue

                async with async_session() as session:
                    user = await session.get(User, uid)
                    if not user or not user.telegram_id:
                        continue

                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=digest,
                    parse_mode="HTML",
                )
                sent += 1

            except Exception as e:
                logger.debug(f"Wallet digest send failed for user {uid}: {e}")

    finally:
        await bot.session.close()

    logger.info(f"Wallet digests sent: {sent}/{len(user_ids)}")
