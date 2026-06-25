"""
NOWPayments integration — create invoices, check status, handle webhooks.
"""

import hmac
import hashlib
import httpx
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Payment, PaymentStatus, Subscription, User, Tier


class NOWPaymentsClient:
    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self):
        self.api_key = settings.NOWPAYMENTS_API_KEY
        self.ipn_secret = settings.NOWPAYMENTS_IPN_SECRET

    @property
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_payment(
        self, user: User, tier: Tier, months: int
    ) -> dict | None:
        """Create a NOWPayments invoice for subscription."""
        # Calculate price
        price_per_month = self._get_price(tier)
        discount = self._get_discount(months)
        total_usd = round(price_per_month * months * (1 - discount), 2)

        order_id = f"sub_{user.telegram_id}_{tier.value}_{months}m_{int(datetime.now(timezone.utc).timestamp())}"

        payload = {
            "price_amount": total_usd,
            "price_currency": "usd",
            "order_id": order_id,
            "order_description": f"{tier.value.capitalize()} subscription — {months} month(s)",
            "ipn_callback_url": settings.NOWPAYMENTS_IPN_URL if hasattr(settings, "NOWPAYMENTS_IPN_URL") else None,
            "success_url": f"https://t.me/{settings.BOT_USERNAME}" if hasattr(settings, "BOT_USERNAME") else None,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.BASE_URL}/invoice",
                    json=payload,
                    headers=self._headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    logger.error(f"NOWPayments invoice error: {resp.status_code} {resp.text}")
                    return None

                data = resp.json()

            # Save payment record
            async with async_session() as session:
                payment = Payment(
                    user_id=user.id,
                    nowpayments_id=str(data.get("id", "")),
                    amount_usd=total_usd,
                    tier=tier.value,
                    months=months,
                    status=PaymentStatus.PENDING,
                    order_id=order_id,
                )
                session.add(payment)
                await session.commit()

            return {
                "payment_id": data.get("id"),
                "invoice_url": data.get("invoice_url"),
                "amount_usd": total_usd,
                "order_id": order_id,
            }

        except Exception as e:
            logger.error(f"NOWPayments create_payment error: {e}")
            return None

    async def check_payment_status(self, payment_id: str) -> str:
        """Check payment status via NOWPayments API."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/payment/{payment_id}",
                    headers=self._headers,
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("payment_status", "unknown")

                    # Update local payment record
                    await self._update_local_status(payment_id, status, data)

                    return status
        except Exception as e:
            logger.error(f"NOWPayments check error: {e}")

        return "unknown"

    async def verify_ipn(self, body: bytes, signature: str) -> bool:
        """Verify IPN webhook signature."""
        if not self.ipn_secret:
            return False
        expected = hmac.new(
            self.ipn_secret.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def process_ipn(self, data: dict):
        """Process IPN callback — activate subscription on successful payment."""
        payment_status = data.get("payment_status")
        payment_id = str(data.get("payment_id", ""))
        order_id = data.get("order_id", "")

        logger.info(f"IPN received: payment={payment_id}, status={payment_status}")

        if payment_status == "finished":
            await self._activate_subscription(payment_id, order_id)
        elif payment_status in ("failed", "expired", "refunded"):
            await self._update_local_status(payment_id, payment_status, data)

    async def _activate_subscription(self, payment_id: str, order_id: str):
        """Activate user subscription after successful payment."""
        async with async_session() as session:
            # Find payment
            result = await session.execute(
                select(Payment).where(Payment.nowpayments_id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                logger.warning(f"Payment not found: {payment_id}")
                return

            if payment.status == PaymentStatus.COMPLETED:
                return  # Already processed

            payment.status = PaymentStatus.COMPLETED

            # Get user
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return

            # Update user tier
            new_tier = Tier(payment.tier)
            expires_at = datetime.now(timezone.utc) + timedelta(days=30 * payment.months)

            user.tier = new_tier

            # Create or extend subscription
            sub_result = await session.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            sub = sub_result.scalar_one_or_none()

            if sub and sub.expires_at and sub.expires_at > datetime.now(timezone.utc):
                # Extend existing subscription
                sub.expires_at = sub.expires_at + timedelta(days=30 * payment.months)
                sub.tier = new_tier
            else:
                sub = Subscription(
                    user_id=user.id,
                    tier=new_tier,
                    expires_at=expires_at,
                    auto_renew=False,
                )
                session.add(sub)

            session.add(payment)
            session.add(user)
            await session.commit()

            logger.info(f"Subscription activated: user={user.telegram_id}, tier={new_tier.value}, until={expires_at}")

    async def _update_local_status(self, payment_id: str, status: str, data: dict):
        """Update local payment status."""
        status_map = {
            "waiting": PaymentStatus.PENDING,
            "confirming": PaymentStatus.CONFIRMING,
            "confirmed": PaymentStatus.CONFIRMING,
            "sending": PaymentStatus.CONFIRMING,
            "finished": PaymentStatus.COMPLETED,
            "failed": PaymentStatus.FAILED,
            "expired": PaymentStatus.EXPIRED,
            "refunded": PaymentStatus.REFUNDED,
        }

        async with async_session() as session:
            result = await session.execute(
                select(Payment).where(Payment.nowpayments_id == payment_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                new_status = status_map.get(status)
                if new_status:
                    payment.status = new_status
                    session.add(payment)
                    await session.commit()

    def _get_price(self, tier: Tier) -> float:
        """Get monthly price for tier from config."""
        if tier == Tier.PRO:
            return float(getattr(settings, "PRICE_PRO_MONTHLY", 29.99))
        elif tier == Tier.ELITE:
            return float(getattr(settings, "PRICE_ELITE_MONTHLY", 79.99))
        return 0

    def _get_discount(self, months: int) -> float:
        """Get discount based on duration."""
        discounts = {1: 0, 3: 0, 6: 0.10, 12: 0.20}
        return discounts.get(months, 0)


nowpayments_client = NOWPaymentsClient()
