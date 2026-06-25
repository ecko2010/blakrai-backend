"""
Blockchain chain adapters — EVM, Solana, Tron.
All use httpx (already in deps) to talk to JSON-RPC / REST APIs.
No heavy SDK dependencies needed.
"""

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.models import ChainType


# ─── Data classes ─────────────────────────────────────────

@dataclass
class TokenBalance:
    contract_address: str | None  # None = native
    symbol: str
    name: str | None
    decimals: int
    balance_raw: str
    balance: float
    logo_url: str | None = None


@dataclass
class TxInfo:
    tx_hash: str
    block_number: int | None
    timestamp: datetime | None
    from_address: str | None
    to_address: str | None
    tx_type: str  # transfer, swap, approve, contract, receive
    token_symbol: str | None
    amount: float | None
    amount_usd: float | None = None
    token_out_symbol: str | None = None
    amount_out: float | None = None
    fee: float | None = None
    raw_data: dict | None = None


# ─── Utility ──────────────────────────────────────────────

_NATIVE_SYMBOLS: dict[ChainType, str] = {
    ChainType.ETHEREUM: "ETH",
    ChainType.BSC: "BNB",
    ChainType.ARBITRUM: "ETH",
    ChainType.BASE: "ETH",
    ChainType.POLYGON: "MATIC",
    ChainType.SOLANA: "SOL",
    ChainType.TRON: "TRX",
}

_NATIVE_DECIMALS: dict[ChainType, int] = {
    ChainType.ETHEREUM: 18,
    ChainType.BSC: 18,
    ChainType.ARBITRUM: 18,
    ChainType.BASE: 18,
    ChainType.POLYGON: 18,
    ChainType.SOLANA: 9,
    ChainType.TRON: 6,
}

EVM_CHAINS = {ChainType.ETHEREUM, ChainType.BSC, ChainType.ARBITRUM, ChainType.BASE, ChainType.POLYGON}

# Public fallback RPC endpoints
_PUBLIC_RPC: dict[ChainType, str] = {
    ChainType.ETHEREUM: "https://eth.llamarpc.com",
    ChainType.BSC: "https://bsc-dataseed1.binance.org",
    ChainType.ARBITRUM: "https://arb1.arbitrum.io/rpc",
    ChainType.BASE: "https://mainnet.base.org",
    ChainType.POLYGON: "https://polygon-rpc.com",
}

# Alchemy chain slugs (for building URLs)
_ALCHEMY_SLUGS: dict[ChainType, str] = {
    ChainType.ETHEREUM: "eth-mainnet",
    ChainType.ARBITRUM: "arb-mainnet",
    ChainType.BASE: "base-mainnet",
    ChainType.POLYGON: "polygon-mainnet",
}


def _get_evm_rpc(chain: ChainType) -> str:
    """Return RPC URL — Alchemy if key set, else public fallback."""
    if settings.ALCHEMY_API_KEY and chain in _ALCHEMY_SLUGS:
        slug = _ALCHEMY_SLUGS[chain]
        return f"https://{slug}.g.alchemy.com/v2/{settings.ALCHEMY_API_KEY}"
    return _PUBLIC_RPC.get(chain, _PUBLIC_RPC[ChainType.ETHEREUM])


def _get_solana_rpc() -> str:
    if settings.HELIUS_API_KEY:
        return f"https://mainnet.helius-rpc.com/?api-key={settings.HELIUS_API_KEY}"
    return "https://api.mainnet-beta.solana.com"


def _wei_to_eth(wei_hex: str, decimals: int = 18) -> float:
    """Convert hex wei string to float."""
    try:
        return int(wei_hex, 16) / (10 ** decimals)
    except (ValueError, TypeError):
        return 0.0


# ─── Base adapter ─────────────────────────────────────────

class ChainAdapter:
    """Base class for chain adapters."""

    chain: ChainType

    async def get_native_balance(self, address: str) -> TokenBalance:
        raise NotImplementedError

    async def get_token_balances(self, address: str) -> list[TokenBalance]:
        raise NotImplementedError

    async def get_recent_transactions(self, address: str, limit: int = 20) -> list[TxInfo]:
        raise NotImplementedError

    async def get_all_balances(self, address: str) -> list[TokenBalance]:
        """Native + token balances."""
        native = await self.get_native_balance(address)
        tokens = await self.get_token_balances(address)
        return [native] + tokens


# ─── EVM Adapter ──────────────────────────────────────────

class EVMAdapter(ChainAdapter):
    """
    EVM chain adapter.
    Uses Alchemy enhanced APIs when available (getTokenBalances, getAssetTransfers).
    Falls back to basic eth_getBalance + manual scanning.
    """

    def __init__(self, chain: ChainType):
        self.chain = chain
        self._rpc = _get_evm_rpc(chain)
        self._has_alchemy = settings.ALCHEMY_API_KEY != "" and chain in _ALCHEMY_SLUGS
        self._timeout = httpx.Timeout(15.0, connect=10.0)

    async def _rpc_call(self, method: str, params: list) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._rpc,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            data = resp.json()
            if "error" in data:
                logger.warning(f"EVM RPC error ({self.chain.value}): {data['error']}")
                return None
            return data.get("result")

    async def get_native_balance(self, address: str) -> TokenBalance:
        sym = _NATIVE_SYMBOLS[self.chain]
        dec = _NATIVE_DECIMALS[self.chain]
        result = await self._rpc_call("eth_getBalance", [address, "latest"])
        balance = _wei_to_eth(result, dec) if result else 0.0
        return TokenBalance(
            contract_address=None,
            symbol=sym,
            name=sym,
            decimals=dec,
            balance_raw=str(int(result or "0x0", 16)),
            balance=balance,
        )

    async def get_token_balances(self, address: str) -> list[TokenBalance]:
        """Get ERC-20 token balances using Alchemy getTokenBalances or fallback."""
        if not self._has_alchemy:
            return []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._rpc,
                    json={
                        "jsonrpc": "2.0", "id": 1,
                        "method": "alchemy_getTokenBalances",
                        "params": [address, "erc20"],
                    },
                )
                data = resp.json()
                raw_balances = data.get("result", {}).get("tokenBalances", [])

            # Filter non-zero
            non_zero = [
                tb for tb in raw_balances
                if tb.get("tokenBalance") and tb["tokenBalance"] != "0x0"
                and int(tb["tokenBalance"], 16) > 0
            ]

            if not non_zero:
                return []

            # Batch metadata fetch
            tokens = []
            for tb in non_zero[:50]:  # Limit to 50 tokens
                contract = tb["contractAddress"]
                balance_raw = int(tb["tokenBalance"], 16)

                meta = await self._get_token_metadata(contract)
                decimals = meta.get("decimals", 18)
                symbol = meta.get("symbol", "???")
                name = meta.get("name")
                logo = meta.get("logo")
                balance = balance_raw / (10 ** decimals) if decimals else float(balance_raw)

                if balance < 0.000001:
                    continue

                tokens.append(TokenBalance(
                    contract_address=contract,
                    symbol=symbol,
                    name=name,
                    decimals=decimals,
                    balance_raw=str(balance_raw),
                    balance=balance,
                    logo_url=logo,
                ))

            return tokens

        except Exception as e:
            logger.warning(f"EVM token balance fetch error ({self.chain.value}): {e}")
            return []

    async def _get_token_metadata(self, contract: str) -> dict:
        """Fetch token metadata via Alchemy getTokenMetadata."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._rpc,
                    json={
                        "jsonrpc": "2.0", "id": 1,
                        "method": "alchemy_getTokenMetadata",
                        "params": [contract],
                    },
                )
                data = resp.json()
                return data.get("result", {})
        except Exception:
            return {}

    async def get_recent_transactions(self, address: str, limit: int = 20) -> list[TxInfo]:
        """Fetch recent transactions using Alchemy getAssetTransfers."""
        if not self._has_alchemy:
            return await self._get_txs_basic(address, limit)

        try:
            txs: list[TxInfo] = []
            addr_lower = address.lower()

            # Outgoing + incoming in parallel
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for direction in ("from", "to"):
                    params: dict = {
                        "fromBlock": "0x0",
                        "toBlock": "latest",
                        "category": ["external", "erc20"],
                        "maxCount": hex(limit),
                        "order": "desc",
                        "withMetadata": True,
                    }
                    params[f"{direction}Address"] = address

                    resp = await client.post(
                        self._rpc,
                        json={
                            "jsonrpc": "2.0", "id": 1,
                            "method": "alchemy_getAssetTransfers",
                            "params": [params],
                        },
                    )
                    data = resp.json()
                    transfers = data.get("result", {}).get("transfers", [])

                    for t in transfers:
                        ts = None
                        meta = t.get("metadata", {})
                        if meta.get("blockTimestamp"):
                            try:
                                ts = datetime.fromisoformat(meta["blockTimestamp"].replace("Z", "+00:00"))
                            except Exception:
                                pass

                        from_addr = (t.get("from") or "").lower()
                        to_addr = (t.get("to") or "").lower()

                        if from_addr == addr_lower:
                            tx_type = "transfer"
                        elif to_addr == addr_lower:
                            tx_type = "receive"
                        else:
                            tx_type = "contract"

                        txs.append(TxInfo(
                            tx_hash=t.get("hash", ""),
                            block_number=int(t.get("blockNum", "0x0"), 16) if t.get("blockNum") else None,
                            timestamp=ts,
                            from_address=t.get("from"),
                            to_address=t.get("to"),
                            tx_type=tx_type,
                            token_symbol=t.get("asset"),
                            amount=t.get("value"),
                            raw_data=t,
                        ))

            # Deduplicate by hash, sort by block desc
            seen = set()
            unique = []
            for tx in txs:
                if tx.tx_hash not in seen:
                    seen.add(tx.tx_hash)
                    unique.append(tx)
            unique.sort(key=lambda x: x.block_number or 0, reverse=True)
            return unique[:limit]

        except Exception as e:
            logger.warning(f"EVM tx fetch error ({self.chain.value}): {e}")
            return []

    async def _get_txs_basic(self, address: str, limit: int = 20) -> list[TxInfo]:
        """Basic tx fetch for non-Alchemy chains (BSC etc) via block explorer APIs."""
        # For BSC: use bscscan-like free APIs; for others: limited without Alchemy
        # This is a minimal fallback — returns empty for now
        # Will be enhanced per-chain as needed
        return []


# ─── Solana Adapter ───────────────────────────────────────

class SolanaAdapter(ChainAdapter):
    """Solana adapter using JSON-RPC."""

    chain = ChainType.SOLANA

    def __init__(self):
        self._rpc = _get_solana_rpc()
        self._timeout = httpx.Timeout(15.0, connect=10.0)

    async def _rpc_call(self, method: str, params: list) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._rpc,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            data = resp.json()
            if "error" in data:
                logger.warning(f"Solana RPC error: {data['error']}")
                return None
            return data.get("result")

    async def get_native_balance(self, address: str) -> TokenBalance:
        result = await self._rpc_call("getBalance", [address, {"commitment": "confirmed"}])
        lamports = result.get("value", 0) if result else 0
        balance = lamports / 1_000_000_000
        return TokenBalance(
            contract_address=None,
            symbol="SOL",
            name="Solana",
            decimals=9,
            balance_raw=str(lamports),
            balance=balance,
        )

    async def get_token_balances(self, address: str) -> list[TokenBalance]:
        """Get SPL token accounts."""
        try:
            result = await self._rpc_call("getTokenAccountsByOwner", [
                address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed", "commitment": "confirmed"},
            ])
            if not result:
                return []

            accounts = result.get("value", [])
            tokens = []

            for acc in accounts:
                info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                token_amount = info.get("tokenAmount", {})
                amount = float(token_amount.get("uiAmount") or 0)
                if amount < 0.000001:
                    continue

                mint = info.get("mint", "")
                decimals = token_amount.get("decimals", 0)

                tokens.append(TokenBalance(
                    contract_address=mint,
                    symbol=mint[:6].upper(),  # Will be resolved via metadata later
                    name=None,
                    decimals=decimals,
                    balance_raw=token_amount.get("amount", "0"),
                    balance=amount,
                ))

            return tokens

        except Exception as e:
            logger.warning(f"Solana token fetch error: {e}")
            return []

    async def get_recent_transactions(self, address: str, limit: int = 20) -> list[TxInfo]:
        """Get recent transaction signatures and basic info."""
        try:
            sigs_result = await self._rpc_call("getSignaturesForAddress", [
                address,
                {"limit": limit, "commitment": "confirmed"},
            ])
            if not sigs_result:
                return []

            txs = []
            for sig_info in sigs_result:
                ts = None
                if sig_info.get("blockTime"):
                    ts = datetime.fromtimestamp(sig_info["blockTime"], tz=timezone.utc)

                txs.append(TxInfo(
                    tx_hash=sig_info.get("signature", ""),
                    block_number=sig_info.get("slot"),
                    timestamp=ts,
                    from_address=None,
                    to_address=None,
                    tx_type="transfer",
                    token_symbol="SOL",
                    amount=None,
                    raw_data=sig_info,
                ))

            return txs

        except Exception as e:
            logger.warning(f"Solana tx fetch error: {e}")
            return []


# ─── Tron Adapter ─────────────────────────────────────────

class TronAdapter(ChainAdapter):
    """Tron adapter using TronGrid REST API (no key needed for basic ops)."""

    chain = ChainType.TRON
    BASE_URL = "https://api.trongrid.io"

    def __init__(self):
        self._timeout = httpx.Timeout(15.0, connect=10.0)

    async def get_native_balance(self, address: str) -> TokenBalance:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self.BASE_URL}/v1/accounts/{address}")
                data = resp.json()

            account = data.get("data", [{}])[0] if data.get("data") else {}
            balance_sun = account.get("balance", 0)
            balance = balance_sun / 1_000_000

            return TokenBalance(
                contract_address=None,
                symbol="TRX",
                name="TRON",
                decimals=6,
                balance_raw=str(balance_sun),
                balance=balance,
            )
        except Exception as e:
            logger.warning(f"Tron balance error: {e}")
            return TokenBalance(None, "TRX", "TRON", 6, "0", 0.0)

    async def get_token_balances(self, address: str) -> list[TokenBalance]:
        """Get TRC-20 token balances."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/v1/accounts/{address}/tokens",
                    params={"limit": 50},
                )
                data = resp.json()

            tokens = []
            for item in data.get("data", []):
                # Skip TRX (native)
                if item.get("id") == "_":
                    continue

                balance_raw = int(item.get("balance", 0))
                decimals = item.get("decimals", 0)
                balance = balance_raw / (10 ** decimals) if decimals else float(balance_raw)

                if balance < 0.000001:
                    continue

                tokens.append(TokenBalance(
                    contract_address=item.get("id", ""),
                    symbol=item.get("abbr", item.get("name", "???")[:6]),
                    name=item.get("name"),
                    decimals=decimals,
                    balance_raw=str(balance_raw),
                    balance=balance,
                    logo_url=item.get("imgUrl"),
                ))

            return tokens

        except Exception as e:
            logger.warning(f"Tron token fetch error: {e}")
            return []

    async def get_recent_transactions(self, address: str, limit: int = 20) -> list[TxInfo]:
        """Get recent TRC-20 + TRX transactions."""
        try:
            txs = []
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Normal TRX transactions
                resp = await client.get(
                    f"{self.BASE_URL}/v1/accounts/{address}/transactions",
                    params={"limit": limit, "order_by": "block_timestamp,desc"},
                )
                data = resp.json()

                for item in data.get("data", []):
                    raw_data = item.get("raw_data", {}).get("contract", [{}])[0]
                    param = raw_data.get("parameter", {}).get("value", {})

                    ts = None
                    if item.get("block_timestamp"):
                        ts = datetime.fromtimestamp(item["block_timestamp"] / 1000, tz=timezone.utc)

                    amount_sun = param.get("amount", 0)
                    amount = amount_sun / 1_000_000 if amount_sun else None

                    from_hex = param.get("owner_address", "")
                    to_hex = param.get("to_address", "")

                    is_outgoing = from_hex and address in from_hex
                    tx_type = "transfer" if is_outgoing else "receive"

                    txs.append(TxInfo(
                        tx_hash=item.get("txID", ""),
                        block_number=item.get("blockNumber"),
                        timestamp=ts,
                        from_address=from_hex,
                        to_address=to_hex,
                        tx_type=tx_type,
                        token_symbol="TRX",
                        amount=amount,
                        raw_data=item,
                    ))

            return txs[:limit]

        except Exception as e:
            logger.warning(f"Tron tx fetch error: {e}")
            return []


# ─── Address detection ────────────────────────────────────

def detect_chain(address: str) -> ChainType | None:
    """
    Auto-detect blockchain from address format.
    Returns the most likely chain, or None if unrecognizable.
    """
    addr = address.strip()

    # EVM: 0x + 40 hex chars
    if addr.startswith("0x") and len(addr) == 42:
        try:
            int(addr[2:], 16)
            return ChainType.ETHEREUM  # Default to ETH; user can override
        except ValueError:
            return None

    # Tron: T + 33 chars (base58)
    if addr.startswith("T") and len(addr) == 34:
        return ChainType.TRON

    # Solana: base58, 32-44 chars, no 0x prefix
    if 32 <= len(addr) <= 44 and not addr.startswith("0x") and not addr.startswith("T"):
        # Basic base58 check
        import string
        b58_chars = set(string.digits + string.ascii_letters) - {"0", "O", "I", "l"}
        if all(c in b58_chars for c in addr):
            return ChainType.SOLANA

    return None


def detect_evm_chain_from_activity(address: str) -> list[ChainType]:
    """
    For 0x addresses, check which EVM chains have balance.
    Called async — returns list of chains with non-zero balance.
    """
    # This is called from the tracker service to disambiguate EVM chains
    return [ChainType.ETHEREUM]  # Default; fully resolved in tracker.py


# ─── Factory ──────────────────────────────────────────────

_adapters: dict[ChainType, ChainAdapter] = {}


def get_adapter(chain: ChainType) -> ChainAdapter:
    """Get or create chain adapter singleton."""
    if chain not in _adapters:
        if chain in EVM_CHAINS:
            _adapters[chain] = EVMAdapter(chain)
        elif chain == ChainType.SOLANA:
            _adapters[chain] = SolanaAdapter()
        elif chain == ChainType.TRON:
            _adapters[chain] = TronAdapter()
        else:
            raise ValueError(f"Unsupported chain: {chain}")
    return _adapters[chain]
