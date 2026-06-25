"""
Wallet Tracker service — polls tracked wallets, updates balances, detects new transactions,
sends alerts via Telegram, enriches with USD prices.
"""

import asyncio
from datetime import datetime, timezone, timedelta

from loguru import logger
from sqlalchemy import select, and_, func, or_

from app.config import settings
from app.database import async_session
from app.models import (
    TrackedWallet, WalletToken, WalletTransaction, ChainType,
    User, Tier,
)
from app.wallet.chains import get_adapter, detect_chain, EVM_CHAINS, TokenBalance, TxInfo


# ─── Tier limits ──────────────────────────────────────────

WALLET_LIMITS = {
    Tier.FREE: 1,
    Tier.PRO: 5,
    Tier.ELITE: 20,
}

# Features by tier
TIER_FEATURES = {
    Tier.FREE: {"portfolio_view", "basic_alerts"},
    Tier.PRO: {"portfolio_view", "basic_alerts", "tx_alerts", "token_alerts", "analytics"},
    Tier.ELITE: {"portfolio_view", "basic_alerts", "tx_alerts", "token_alerts", "analytics",
                 "ai_digest", "whale_alerts", "full_history"},
}


# ─── Price helper ─────────────────────────────────────────

async def _get_prices_usd(symbols: list[str]) -> dict[str, float]:
    """
    Get USD prices for a list of token symbols.
    Uses CoinGecko via existing CoinMeta or market snapshot data.
    Falls back to exchange manager for USDT pairs.
    """
    prices: dict[str, float] = {}
    if not symbols:
        return prices

    try:
        from app.models import CoinMeta, MarketSnapshot
        async with async_session() as session:
            # Try CoinMeta first (has market data from CoinGecko)
            for sym in symbols:
                usdt_sym = sym.upper() + "USDT" if not sym.upper().endswith("USDT") else sym.upper()
                result = await session.execute(
                    select(MarketSnapshot.price)
                    .where(MarketSnapshot.coin_symbol == usdt_sym)
                    .order_by(MarketSnapshot.created_at.desc())
                    .limit(1)
                )
                price = result.scalar_one_or_none()
                if price:
                    prices[sym.upper()] = price
    except Exception as e:
        logger.debug(f"Price lookup from DB failed: {e}")

    # Fallback to exchange manager for missing prices
    missing = [s for s in symbols if s.upper() not in prices]
    if missing:
        try:
            from app.exchanges.manager import exchange_manager
            for sym in missing[:20]:  # Limit lookups
                try:
                    pair = f"{sym.upper()}USDT"
                    best = await exchange_manager.get_best_price(pair)
                    if best and best.get("best_bid"):
                        prices[sym.upper()] = (best["best_bid"] + best.get("best_ask", best["best_bid"])) / 2
                except Exception:
                    pass
        except Exception:
            pass

    # Well-known stablecoins
    for stable in ("USDT", "USDC", "DAI", "BUSD", "TUSD"):
        prices[stable] = 1.0

    return prices


# ─── Tracker class ────────────────────────────────────────

class WalletTracker:
    """Main wallet tracking service."""

    async def add_wallet(self, user_id: int, address: str, chain: ChainType | None = None,
                         label: str | None = None) -> TrackedWallet | str:
        """
        Add a wallet to track. Auto-detects chain if not specified.
        Returns TrackedWallet on success, error string on failure.
        """
        address = address.strip()

        # Auto-detect chain
        if chain is None:
            chain = detect_chain(address)
            if chain is None:
                return "unknown_chain"

        # Check tier limits
        async with async_session() as session:
            user = await session.execute(select(User).where(User.id == user_id))
            user = user.scalar_one_or_none()
            if not user:
                return "user_not_found"

            limit = WALLET_LIMITS.get(user.tier, 1)
            count = await session.scalar(
                select(func.count(TrackedWallet.id)).where(
                    TrackedWallet.user_id == user_id,
                    TrackedWallet.is_active == True,
                )
            )
            if (count or 0) >= limit:
                return "limit_reached"

            # Check duplicate
            existing = await session.scalar(
                select(TrackedWallet.id).where(
                    TrackedWallet.user_id == user_id,
                    TrackedWallet.address == address,
                    TrackedWallet.chain == chain,
                )
            )
            if existing:
                return "already_tracked"

            wallet = TrackedWallet(
                user_id=user_id,
                address=address,
                chain=chain,
                label=label,
                is_active=True,
                alert_config={"new_tx": True, "large_transfer_usd": 500, "new_token": True},
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)

        # Initial scan in background
        asyncio.create_task(self._scan_wallet(wallet.id))

        return wallet

    async def remove_wallet(self, user_id: int, wallet_id: int) -> bool:
        """Deactivate a tracked wallet."""
        async with async_session() as session:
            wallet = await session.get(TrackedWallet, wallet_id)
            if not wallet or wallet.user_id != user_id:
                return False
            wallet.is_active = False
            session.add(wallet)
            await session.commit()
        return True

    async def get_user_wallets(self, user_id: int, active_only: bool = True) -> list[TrackedWallet]:
        """Get all wallets for a user."""
        async with async_session() as session:
            q = select(TrackedWallet).where(TrackedWallet.user_id == user_id)
            if active_only:
                q = q.where(TrackedWallet.is_active == True)
            q = q.order_by(TrackedWallet.created_at.desc())
            result = await session.execute(q)
            return list(result.scalars().all())

    async def get_wallet_portfolio(self, wallet_id: int) -> dict:
        """Get full portfolio for a wallet."""
        async with async_session() as session:
            wallet = await session.get(TrackedWallet, wallet_id)
            if not wallet:
                return {}

            tokens = wallet.tokens or []
            total_usd = sum(t.value_usd or 0 for t in tokens)

            return {
                "wallet": wallet,
                "tokens": sorted(tokens, key=lambda t: t.value_usd or 0, reverse=True),
                "total_value_usd": total_usd,
                "chain": wallet.chain.value,
                "address": wallet.address,
                "label": wallet.label,
                "last_scanned": wallet.last_scanned_at,
            }

    async def get_wallet_transactions(self, wallet_id: int, limit: int = 50, offset: int = 0) -> list[WalletTransaction]:
        """Get paginated transactions for a wallet."""
        async with async_session() as session:
            result = await session.execute(
                select(WalletTransaction)
                .where(WalletTransaction.wallet_id == wallet_id)
                .order_by(WalletTransaction.timestamp.desc().nullslast())
                .offset(offset).limit(limit)
            )
            return list(result.scalars().all())

    # ─── Polling ──────────────────────────────────────

    async def poll_all_wallets(self):
        """Poll all active wallets. Called by scheduler."""
        async with async_session() as session:
            result = await session.execute(
                select(TrackedWallet.id).where(TrackedWallet.is_active == True)
            )
            wallet_ids = [r[0] for r in result.all()]

        if not wallet_ids:
            return

        logger.info(f"Polling {len(wallet_ids)} tracked wallets")

        # Process in batches to respect rate limits
        batch_size = 5
        for i in range(0, len(wallet_ids), batch_size):
            batch = wallet_ids[i:i + batch_size]
            tasks = [self._scan_wallet(wid) for wid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            if i + batch_size < len(wallet_ids):
                await asyncio.sleep(2)  # Rate limit breathing room

        logger.info(f"Wallet poll complete for {len(wallet_ids)} wallets")

    async def _scan_wallet(self, wallet_id: int):
        """Scan a single wallet: update balances, detect new transactions."""
        try:
            async with async_session() as session:
                wallet = await session.get(TrackedWallet, wallet_id)
                if not wallet or not wallet.is_active:
                    return

                adapter = get_adapter(wallet.chain)

                # 1. Fetch balances
                try:
                    all_balances = await adapter.get_all_balances(wallet.address)
                except Exception as e:
                    logger.warning(f"Balance fetch failed for wallet {wallet_id}: {e}")
                    all_balances = []

                # 2. Get USD prices
                symbols = [b.symbol for b in all_balances if b.symbol]
                prices = await _get_prices_usd(symbols)

                # 3. Update token records
                total_usd = 0.0
                for bal in all_balances:
                    price = prices.get(bal.symbol.upper(), 0)
                    value_usd = bal.balance * price if price else None

                    if value_usd:
                        total_usd += value_usd

                    # Upsert token
                    existing = await session.execute(
                        select(WalletToken).where(
                            WalletToken.wallet_id == wallet_id,
                            WalletToken.contract_address == bal.contract_address,
                        )
                    )
                    token = existing.scalar_one_or_none()

                    if token:
                        token.balance_raw = bal.balance_raw
                        token.balance = bal.balance
                        token.price_usd = price if price else token.price_usd
                        token.value_usd = value_usd
                        if bal.symbol and bal.symbol != "???":
                            token.symbol = bal.symbol
                        if bal.name:
                            token.name = bal.name
                        if bal.logo_url:
                            token.logo_url = bal.logo_url
                    else:
                        # New token detected
                        token = WalletToken(
                            wallet_id=wallet_id,
                            contract_address=bal.contract_address,
                            symbol=bal.symbol,
                            name=bal.name,
                            decimals=bal.decimals,
                            balance_raw=bal.balance_raw,
                            balance=bal.balance,
                            price_usd=price if price else None,
                            value_usd=value_usd,
                            logo_url=bal.logo_url,
                        )
                        session.add(token)

                        # Alert: new token (skip zero-balance to avoid repeated alerts)
                        if (wallet.last_scanned_at
                                and bal.balance > 0.000001
                                and wallet.alert_config
                                and wallet.alert_config.get("new_token")):
                            await self._send_alert(
                                wallet, "new_token",
                                f"🆕 Новий токен: <b>{bal.symbol}</b>\n"
                                f"Баланс: {bal.balance:,.6g}"
                                + (f" (${value_usd:,.2f})" if value_usd else ""),
                            )

                    session.add(token)

                # Remove non-native tokens with zero balance
                # Keep native tokens (contract_address is None) to avoid
                # re-detecting them as "new" on every scan cycle
                result = await session.execute(
                    select(WalletToken).where(
                        WalletToken.wallet_id == wallet_id,
                        WalletToken.balance <= 0.000001,
                        WalletToken.contract_address.isnot(None),
                    )
                )
                for dead_token in result.scalars().all():
                    await session.delete(dead_token)

                # 4. Fetch & store new transactions
                try:
                    recent_txs = await adapter.get_recent_transactions(wallet.address, limit=20)
                    new_tx_count = 0

                    for tx in recent_txs:
                        # Check if already stored
                        exists = await session.scalar(
                            select(WalletTransaction.id).where(
                                WalletTransaction.wallet_id == wallet_id,
                                WalletTransaction.tx_hash == tx.tx_hash,
                            )
                        )
                        if exists:
                            continue

                        # Enrich with USD price
                        if tx.amount and tx.token_symbol:
                            price = prices.get(tx.token_symbol.upper(), 0)
                            tx.amount_usd = tx.amount * price if price else None

                        wt = WalletTransaction(
                            wallet_id=wallet_id,
                            tx_hash=tx.tx_hash,
                            chain=wallet.chain,
                            block_number=tx.block_number,
                            timestamp=tx.timestamp,
                            from_address=tx.from_address,
                            to_address=tx.to_address,
                            tx_type=tx.tx_type,
                            token_symbol=tx.token_symbol,
                            amount=tx.amount,
                            amount_usd=tx.amount_usd,
                            token_out_symbol=tx.token_out_symbol,
                            amount_out=tx.amount_out,
                            fee=tx.fee,
                            fee_usd=tx.fee_usd,
                            raw_data=tx.raw_data,
                        )
                        session.add(wt)
                        new_tx_count += 1

                        # Alert: new transaction (only after initial scan)
                        if wallet.last_scanned_at and wallet.alert_config and wallet.alert_config.get("new_tx"):
                            await self._send_tx_alert(wallet, tx, prices)

                except Exception as e:
                    logger.warning(f"TX fetch failed for wallet {wallet_id}: {e}")

                # 5. Update wallet summary
                wallet.total_value_usd = total_usd
                native_bal = next((b for b in all_balances if b.contract_address is None), None)
                if native_bal:
                    wallet.native_balance = native_bal.balance
                wallet.last_scanned_at = datetime.now(timezone.utc)
                if recent_txs:
                    wallet.last_tx_hash = recent_txs[0].tx_hash

                session.add(wallet)
                await session.commit()

        except Exception as e:
            logger.error(f"Wallet scan error (id={wallet_id}): {e}", exc_info=True)

    # ─── Alerts ───────────────────────────────────────

    async def _send_alert(self, wallet: TrackedWallet, alert_type: str, text: str):
        """Send alert to wallet owner via Telegram."""
        try:
            from app.models import User
            async with async_session() as session:
                user = await session.get(User, wallet.user_id)
                if not user or not user.telegram_id:
                    return

            label = wallet.label or wallet.address[:8] + "..."
            chain_label = wallet.chain.value.upper()
            full_text = (
                f"🔔 <b>Wallet Alert</b> [{chain_label}]\n"
                f"📋 {label}\n\n"
                f"{text}"
            )

            from aiogram import Bot
            from app.config import settings
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=user.telegram_id,
                text=full_text,
                parse_mode="HTML",
            )
            await bot.session.close()

        except Exception as e:
            logger.debug(f"Wallet alert send failed: {e}")

    async def _send_tx_alert(self, wallet: TrackedWallet, tx: TxInfo, prices: dict):
        """Send transaction-specific alert."""
        if not wallet.alert_config:
            return

        # Build alert text
        addr_short = wallet.address[:6] + "..." + wallet.address[-4:]
        amount_str = f"{tx.amount:,.6g}" if tx.amount else "?"
        token = tx.token_symbol or "?"

        if tx.tx_type == "receive":
            emoji = "📥"
            action = "Отримано"
        elif tx.tx_type == "swap":
            emoji = "🔄"
            action = "Swap"
        elif tx.tx_type == "transfer":
            emoji = "📤"
            action = "Відправлено"
        else:
            emoji = "📝"
            action = tx.tx_type.capitalize()

        text = f"{emoji} <b>{action}</b>: {amount_str} {token}"
        if tx.amount_usd and tx.amount_usd > 0:
            text += f" (${tx.amount_usd:,.2f})"

        if tx.token_out_symbol and tx.amount_out:
            text += f"\n→ Отримано: {tx.amount_out:,.6g} {tx.token_out_symbol}"

        # Large transfer alert
        large_threshold = wallet.alert_config.get("large_transfer_usd", 500)
        if tx.amount_usd and tx.amount_usd >= large_threshold:
            text += f"\n\n⚠️ <b>Велика транзакція!</b> (>{large_threshold}$)"

        await self._send_alert(wallet, "transaction", text)

    # ─── Cleanup ──────────────────────────────────────

    async def cleanup_old_transactions(self, days: int = 90):
        """Remove old wallet transactions to prevent unbounded growth."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with async_session() as session:
            from sqlalchemy import delete
            result = await session.execute(
                delete(WalletTransaction).where(WalletTransaction.created_at < cutoff)
            )
            await session.commit()
            if result.rowcount:
                logger.info(f"Cleaned up {result.rowcount} old wallet transactions")


# Singleton
wallet_tracker = WalletTracker()
