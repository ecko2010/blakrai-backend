# BLACK ROOM — Desktop API Documentation

> Повна документація для підключення десктоп/мобільних додатків до API.
> Base URL: `https://<your-domain>/desktop`

---

## Зміст

- [Автентифікація](#автентифікація)
- [Тарифні плани (Tiers)](#тарифні-плани)
- [REST API Endpoints](#rest-api-endpoints)
  - [Система](#система)
  - [Профіль користувача](#профіль-користувача)
  - [Сигнали](#сигнали)
  - [Активовані сигнали](#активовані-сигнали)
  - [Статистика](#статистика)
  - [Ринкові дані](#ринкові-дані)
  - [Свічки (Candles)](#свічки)
  - [Монети](#монети)
  - [Аналітика](#аналітика)
  - [Новини](#новини)
  - [Алерти](#алерти)
  - [Вотчліст](#вотчліст)
  - [Гаманці (Wallet Tracker)](#гаманці-wallet-tracker)
- [WebSocket](#websocket)
- [Типи алертів (детально)](#типи-алертів-детально)
- [Enums](#enums)
- [Помилки](#помилки)
- [Приклади інтеграції](#приклади-інтеграції)

---

## Автентифікація

Всі ендпоінти потребують API ключ у хедері:

```
X-API-Key: brk_xxxxxxxxxxxx
```

- Ключ генерується через Telegram бота
- Серверна валідація: SHA-256 хеш → пошук в `user_api_keys`
- При кожному запиті оновлюється `last_used_at`
- Заблоковані/неактивні юзери отримують `403`

### Коди помилок автентифікації

| Код | Опис |
|-----|------|
| `401` | Відсутній або невалідний API ключ |
| `403` | Акаунт заблоковано або деактивовано |

---

## Тарифні плани

| Функція | FREE | PRO | ELITE |
|---------|------|-----|-------|
| Повний доступ до сигналів | ❌ | ✅ | ✅ |
| AI reasoning (factors) | ❌ | ❌ | ✅ |
| Ліміт алертів | **3** | **20** | **100** |
| Ліміт вотчлісту | **5** | **30** | **100** |
| Ліміт гаманців | **1** | **5** | **20** |
| Real-time WebSocket | ❌ | ✅ | ✅ |
| Ринкові дані | ✅ | ✅ | ✅ |
| Новини | ✅ | ✅ | ✅ |
| Історія сигналів | 7 днів | ✅ повна | ✅ повна |
| Експорт даних | ❌ | ❌ | ✅ |
| Свічки (timeframes) | 1h, 4h | 15m, 1h, 4h, 1d | 15m, 1h, 4h, 1d |
| Глибина свічок | 24h | 7 днів | Без обмежень |
| Транзакції гаманця | ❌ | ✅ | ✅ |
| AI аналіз портфеля | ❌ | ✅ | ✅ |
| AI аналітика (market/trend) | overview (1д) | Всі (7д) | Всі (90д) |

---

## REST API Endpoints

### Система

#### `GET /desktop/status`

Стан системи — БД, Redis, планувальник, біржі.

**Response:**
```json
{
  "db_ok": true,
  "redis_ok": true,
  "scheduler_running": true,
  "scheduler_jobs": 5,
  "last_scan": "2026-04-08T07:00:00+00:00",
  "active_signals": 12,
  "exchanges": {
    "binance": {
      "score": 0.989,
      "success_rate": 0.995,
      "latency_ms": 120.0
    },
    "bybit": {
      "score": 0.975,
      "success_rate": 0.990,
      "latency_ms": 150.0
    }
  },
  "websocket_connections": 3
}
```

---

### Профіль користувача

#### `GET /desktop/me`

**Response:**
```json
{
  "id": 42,
  "telegram_id": 123456789,
  "username": "trader_ua",
  "first_name": "Konstantin",
  "language": "uk",
  "tier": "pro",
  "subscription": {
    "tier": "pro",
    "expires_at": "2026-05-08T00:00:00+00:00",
    "auto_renew": true
  },
  "features": {
    "signals_full_access": true,
    "ai_reasoning": false,
    "alerts_limit": 20,
    "watchlist_limit": 30,
    "wallets_limit": 5,
    "real_time_updates": true,
    "market_data": true,
    "news_access": true,
    "signal_history": true,
    "export_data": false,
    "wallet_tx_history": true,
    "wallet_ai_analysis": true
  },
  "created_at": "2026-01-15T12:00:00+00:00"
}
```

---

### Сигнали

#### `GET /desktop/signals`

Пагінований список сигналів з фільтрами.

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `status` | `string?` | `null` | `"active"`, `"closed"`, або `null` (всі) |
| `coin` | `string?` | `null` | Фільтр по монеті (напр. `BTC`) |
| `direction` | `string?` | `null` | `"long"` або `"short"` |
| `page` | `int` | `1` | Сторінка (≥ 1) |
| `limit` | `int` | `20` | Кількість (1–100) |

> `"closed"` включає: `tp1_hit`, `tp2_hit`, `tp3_hit`, `stopped`, `closed`, `expired`

**Response:**
```json
{
  "signals": [
    {
      "id": 162,
      "coin_symbol": "NEAR",
      "direction": "long",
      "status": "active",
      "confidence": 0.74,
      "exchange": "Binance",
      "timeframe": "4h",
      "created_at": "2026-04-08T07:24:00+00:00",
      "closed_at": null,
      "min_tier": "pro",

      "entry_price": 1.339,
      "entry_zone_low": 1.324,
      "entry_zone_high": 1.354,
      "stop_loss": 1.303,
      "tp1": 1.414,
      "tp2": 1.475,
      "tp3": 1.550,
      "leverage_suggested": 5,
      "pnl_percent": null,
      "peak_profit_percent": 1.05,
      "max_drawdown_percent": -0.45,
      "ai_reasoning": "Strong bullish momentum..."
    }
  ],
  "total": 162,
  "page": 1,
  "pages": 9
}
```

**Tier gating для кожного сигналу:**

- Якщо тір юзера ≥ `min_tier` сигналу → повні дані (entry, SL, TP, PnL...)
- Якщо тір юзера < `min_tier` → заблоковано:
  ```json
  {
    "id": 162,
    "coin_symbol": "NEAR",
    "direction": "long",
    "status": "active",
    "confidence": 0.74,
    "entry_price": null,
    "stop_loss": null,
    "tp1": null,
    "locked": true,
    "upgrade_hint": "Upgrade to PRO to see full details"
  }
  ```
- `factors` (детальний JSON з індикаторами) — тільки **ELITE**

---

#### `GET /desktop/signals/active`

Тільки активні сигнали (без пагінації).

**Response:**
```json
{
  "signals": [ ... ],
  "count": 5
}
```

---

#### `GET /desktop/signals/{signal_id}`

Деталі одного сигналу + історія оновлень.

**Response:**
```json
{
  "id": 160,
  "coin_symbol": "MON",
  "direction": "long",
  "status": "stopped",
  "pnl_percent": 2.71,
  "peak_profit_percent": 5.41,
  "max_drawdown_percent": -1.20,
  "updates": [
    {
      "id": 501,
      "type": "sl_hit",
      "price": 0.03071,
      "details": {
        "pnl": 2.707,
        "peak_profit": 5.414,
        "max_drawdown": -1.203
      },
      "created_at": "2026-04-08T07:59:00+00:00"
    }
  ]
}
```

**Типи оновлень (`type`):**

| Тип | Опис |
|-----|------|
| `tp1_hit` | Досягнуто TP1 |
| `tp2_hit` | Досягнуто TP2 |
| `tp3_hit` | Досягнуто TP3 |
| `sl_hit` | Спрацював стоп-лосс (може бути trailing з прибутком!) |
| `entry_hit` | Ціна зайшла в зону входу |
| `adjustment` | Рівні скориговані |
| `close` | Сигнал закрито вручну |
| `cancel` | Сигнал скасовано |
| `note` | Інформаційне повідомлення |

---

### Активовані сигнали

Нова система доставки сигналів: сигнали приходять користувачам в DM бота з інлайн-кнопками.
Кнопка "Використати сигнал" активує відстеження — юзер отримує сповіщення при TP/SL хітах.
Ці ж операції доступні через API.

#### `GET /desktop/signals/activated`

Список активованих (використаних) сигналів поточного юзера.

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `status` | `string?` | `null` | `"active"`, `"closed"`, `null` (всі) |
| `page` | `int` | `1` | Сторінка |
| `limit` | `int` | `20` | 1–100 |

> `"active"` = ACTIVE, TP1_HIT, TP2_HIT (сигнал ще در грі)
> `"closed"` = TP3_HIT, STOPPED, CLOSED, EXPIRED

**Response:**
```json
{
  "signals": [
    {
      "id": 165,
      "coin_symbol": "ETH",
      "direction": "long",
      "status": "tp1_hit",
      "confidence": 0.82,
      "entry_price": 3250.0,
      "stop_loss": 3180.0,
      "tp1": 3350.0,
      "tp2": 3450.0,
      "tp3": 3600.0,
      "pnl_percent": 3.07,
      "activated_at": "2026-04-08T09:15:00+00:00"
    }
  ],
  "total": 12,
  "page": 1,
  "pages": 1
}
```

> Поле `activated_at` — коли юзер натиснув "Використати сигнал"

---

#### `POST /desktop/signals/{signal_id}/activate`

Активувати сигнал (почати відстеження).

**Response (201):**
```json
{
  "status": "activated",
  "signal_id": 165,
  "signal": { ... }
}
```

**Помилки:**
- `404` — сигнал не знайдено
- `403` — тір юзера нижче за `min_tier` сигналу
- `409` — сигнал вже активовано

---

#### `DELETE /desktop/signals/{signal_id}/activate`

Деактивувати сигнал (зупинити відстеження).

**Response:**
```json
{ "status": "deactivated", "signal_id": 165 }
```

- `404` — сигнал не був активований

---

### Статистика

#### `GET /desktop/stats`

Глобальна + персональна статистика.

**Response:**
```json
{
  "global": {
    "total_signals": 162,
    "active_signals": 5,
    "wins": 85,
    "losses": 42,
    "win_rate": 66.9,
    "average_pnl": 3.45,
    "total_pnl": 438.72,
    "signals_last_30d": 95
  },
  "user": {
    "tier": "pro",
    "alerts_active": 3,
    "watchlist_size": 8,
    "signals_activated": 12,
    "wallets_count": 2
  }
}
```

**Розрахунок:**
- **Wins** = TP1/TP2/TP3 hits + CLOSED/STOPPED з `pnl > 0` (trailing SL з прибутком = win!)
- **Losses** = STOPPED/CLOSED з `pnl ≤ 0`
- **Win Rate** = `wins / (wins + losses) * 100`
- **Average PnL** = середнє по всіх закритих (де `pnl IS NOT NULL`)

---

### Ринкові дані

#### `GET /desktop/market`

Огляд ринку — топ монети з цінами.

| Параметр | Тип | За замовч. | Діапазон |
|----------|-----|-----------|----------|
| `limit` | `int` | `50` | 1–200 |

**Response:**
```json
{
  "coins": [
    {
      "coin": "BTC",
      "name": "Bitcoin",
      "logo_url": "https://...",
      "price": 69693.53,
      "volume_24h": 28500000000,
      "change_1h": 0.15,
      "change_24h": 2.34,
      "change_7d": -1.20,
      "market_cap": 1370000000000,
      "market_cap_rank": 1,
      "exchange": "binance",
      "updated_at": "2026-04-08T08:00:00+00:00"
    }
  ],
  "count": 50
}
```

---

#### `GET /desktop/market/{coin}`

Деталі по одній монеті + історія цін + ціни на різних біржах.

| Параметр | Тип | За замовч. | Діапазон |
|----------|-----|-----------|----------|
| `hours` | `int` | `24` | 1–168 |

**Response:**
```json
{
  "coin": "BTC",
  "name": "Bitcoin",
  "logo_url": "https://...",
  "market_cap": 1370000000000,
  "market_cap_rank": 1,
  "circulating_supply": 19650000,
  "ath": 108000.0,
  "atl": 67.81,
  "exchanges": [
    {
      "exchange": "binance",
      "price": 69693.53,
      "volume_24h": 15000000000,
      "change_24h": 2.34,
      "extra": null
    },
    {
      "exchange": "bybit",
      "price": 69690.00,
      "volume_24h": 8000000000,
      "change_24h": 2.31,
      "extra": null
    }
  ],
  "price_history": [
    { "price": 68500.0, "exchange": "binance", "timestamp": "2026-04-07T08:00:00+00:00" },
    { "price": 69000.0, "exchange": "binance", "timestamp": "2026-04-07T12:00:00+00:00" }
  ],
  "active_signals": [ ... ]
}
```

---

### Свічки

#### `GET /desktop/candles/{coin}`

OHLCV дані для графіків.

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `exchange` | `string?` | `null` | Фільтр по біржі |
| `timeframe` | `string` | `"1h"` | `15m`, `1h`, `4h`, `1d` |
| `limit` | `int` | `200` | 1–1000 |
| `from_ts` | `string?` | `null` | ISO дата початку |
| `to_ts` | `string?` | `null` | ISO дата кінця |

**Обмеження по тарифу:**

| Тір | Таймфрейми | Глибина |
|-----|-----------|---------|
| FREE | `1h`, `4h` | 24 год |
| PRO | `15m`, `1h`, `4h`, `1d` | 7 днів |
| ELITE | `15m`, `1h`, `4h`, `1d` | Без обмежень |

**Response:**
```json
{
  "coin": "BTC",
  "timeframe": "4h",
  "exchange": "binance",
  "count": 42,
  "candles": [
    {
      "t": "2026-04-07T00:00:00+00:00",
      "o": 68500.0,
      "h": 69200.0,
      "l": 68300.0,
      "c": 69000.0,
      "v": 1250.5,
      "ex": "binance"
    }
  ]
}
```

> Свічки повертаються від найстарішої до найновішої.

---

#### `GET /desktop/candles/{coin}/exchanges`

Доступні біржі та таймфрейми для монети.

**Response:**
```json
{
  "coin": "BTC",
  "exchanges": [
    {
      "exchange": "binance",
      "timeframes": [
        { "tf": "1h", "count": 168, "from": "2026-04-01T00:00:00", "to": "2026-04-08T08:00:00" },
        { "tf": "4h", "count": 42, "from": "2026-04-01T00:00:00", "to": "2026-04-08T08:00:00" }
      ]
    }
  ]
}
```

---

### Монети

#### `GET /desktop/coins`

Каталог монет з пошуком.

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `search` | `string?` | `null` | Пошук по символу або назві |
| `limit` | `int` | `100` | 1–500 |
| `offset` | `int` | `0` | Зміщення |

**Дані по тарифу:**

| Поле | FREE | PRO | ELITE |
|------|------|-----|-------|
| `symbol`, `name`, `logo_url`, `market_cap`, `rank`, `exchanges` | ✅ | ✅ | ✅ |
| `circulating_supply`, `total_supply`, `ath`, `atl`, `ath_date`, `atl_date` | ❌ | ✅ | ✅ |
| `coingecko_id`, `categories`, `description`, `homepage_url` | ❌ | ❌ | ✅ |

---

#### `GET /desktop/coins/{symbol}`

Деталі одної монети з тим самим tier gating.

---

### Аналітика

#### `GET /desktop/analysis`

AI-аналітичні звіти.

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `analysis_type` | `string?` | `null` | `"market_overview"`, `"coin_analysis"`, `"trend_report"` |
| `coin` | `string?` | `null` | Фільтр по монеті |
| `days` | `int` | `7` | 1–90 |

**Обмеження по тарифу:**

| Тір | Типи аналізу | Глибина |
|-----|-------------|---------|
| FREE | `market_overview` | 1 день |
| PRO | Всі | 7 днів |
| ELITE | Всі | 90 днів |

---

#### `GET /desktop/analysis/latest`

Останній аналітичний звіт.

**Response:**
```json
{
  "date": "2026-04-08T06:00:00+00:00",
  "overview": {
    "coin": null,
    "type": "market_overview",
    "content": "Ринок показує бичачу динаміку...",
    "metrics": { "btc_dominance": 54.2, "total_mcap_change": 2.1 }
  },
  "trend_report": { ... },
  "coin_analyses": [ ... ]
}
```

> FREE: `trend_report = null`, `coin_analyses` макс 3 записи, `metrics = null`

---

### Новини

#### `GET /desktop/news`

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `coin` | `string?` | `null` | Фільтр по монеті |
| `page` | `int` | `1` | Сторінка |
| `limit` | `int` | `20` | 1–50 |

> FREE: тільки за останні 24 години.

**Response:**
```json
{
  "news": [
    {
      "id": 1420,
      "title": "Bitcoin breaks $70K resistance",
      "summary": "After weeks of consolidation...",
      "source": "CoinDesk",
      "url": "https://coindesk.com/...",
      "sentiment": 0.75,
      "importance": 0.85,
      "coins": ["BTC"],
      "created_at": "2026-04-08T06:30:00+00:00"
    }
  ],
  "total": 245,
  "page": 1,
  "pages": 13
}
```

**Поля:**
- `sentiment`: від `-1.0` (негативний) до `+1.0` (позитивний)
- `importance`: від `0.0` до `1.0` (важливість новини)

---

### Алерти

#### `GET /desktop/alerts`

Список алертів користувача.

**Response:**
```json
{
  "alerts": [
    {
      "id": 15,
      "coin": "BTC",
      "type": "price_above",
      "params": { "target_price": 72000.0 },
      "is_active": true,
      "triggered_count": 0,
      "last_triggered": null,
      "cooldown_minutes": 60,
      "created_at": "2026-04-07T10:00:00+00:00"
    }
  ],
  "count": 3,
  "limit": 20
}
```

---

#### `POST /desktop/alerts`

Створити новий алерт.

| Параметр | Тип | Обов'язковий | Опис |
|----------|-----|-------------|------|
| `coin` | `string` | ✅ | Символ монети (`BTC`, `ETH`...) |
| `alert_type` | `string` | ✅ | Тип алерту (див. [Типи алертів](#типи-алертів-детально)) |
| `params` | `string?` | ❌ | JSON рядок з параметрами алерту |
| `cooldown` | `int` | ❌ | Кулдаун у хвилинах (5–1440, за замовч. 60) |

**Приклад запиту:**
```
POST /desktop/alerts?coin=BTC&alert_type=price_above&params={"target_price":72000}&cooldown=30
```

**Response (201):**
```json
{
  "id": 16,
  "coin": "BTC",
  "type": "price_above",
  "params": { "target_price": 72000 },
  "cooldown_minutes": 30,
  "created_at": "2026-04-08T08:15:00+00:00"
}
```

**Помилки:**
- `400` — невалідний `alert_type` або невалідний JSON в `params`
- `403` — досягнуто ліміт алертів для тарифу

---

#### `DELETE /desktop/alerts/{alert_id}`

Видалити (деактивувати) алерт.

**Response:**
```json
{ "status": "deleted", "id": 16 }
```

- `404` — алерт не знайдено або не належить юзеру

---

### Вотчліст

#### `GET /desktop/watchlist`

**Response:**
```json
{
  "watchlist": [
    {
      "coin": "BTC",
      "added_at": "2026-04-01T12:00:00+00:00",
      "market": {
        "price": 69693.53,
        "change_24h": 2.34,
        "volume_24h": 28500000000
      }
    },
    {
      "coin": "NEAR",
      "added_at": "2026-04-05T15:30:00+00:00",
      "market": null
    }
  ],
  "count": 2,
  "limit": 30
}
```

> `market` може бути `null` якщо немає ринкових даних.

---

#### `POST /desktop/watchlist`

| Параметр | Тип | Опис |
|----------|-----|------|
| `coin` | `string` | Символ монети |

**Response (201):** `{ "coin": "ETH", "added_at": "..." }`

- `403` — ліміт вотчлісту досягнуто
- `409` — монета вже в вотчлісті

---

#### `DELETE /desktop/watchlist/{coin}`

**Response:** `{ "status": "removed", "coin": "ETH" }`

- `404` — монети немає в вотчлісті

---

### Гаманці (Wallet Tracker)

Мультичейн трекер гаманців: EVM (Ethereum, BSC, Arbitrum, Base, Polygon), Solana, Tron.
Автоматичне сканування кожні 60 секунд: баланси, нові токени, транзакції, USD ціни.
Telegram алерти при нових транзакціях, великих переказах, нових токенах.

**Ліміти гаманців:**

| Тір | Ліміт | Транзакції | AI аналіз |
|-----|-------|-----------|-----------|
| FREE | 1 | ❌ | ❌ |
| PRO | 5 | ✅ | ✅ |
| ELITE | 20 | ✅ | ✅ |

---

#### `GET /desktop/wallets`

Список відстежуваних гаманців юзера.

**Response:**
```json
{
  "wallets": [
    {
      "id": 3,
      "address": "0x742d35...5BAf8",
      "chain": "ethereum",
      "label": "Основний ETH",
      "total_value_usd": 12450.75,
      "native_balance": 3.547,
      "last_scanned_at": "2026-04-08T08:05:30+00:00",
      "tokens_count": 8,
      "is_active": true,
      "created_at": "2026-04-01T10:00:00+00:00"
    },
    {
      "id": 5,
      "address": "TRXhj...4kF2",
      "chain": "tron",
      "label": "Основний TRC20",
      "total_value_usd": 520.00,
      "native_balance": 0.0,
      "last_scanned_at": "2026-04-08T08:05:45+00:00",
      "tokens_count": 2,
      "is_active": true,
      "created_at": "2026-04-07T15:30:00+00:00"
    }
  ],
  "limit": 5,
  "count": 2
}
```

---

#### `POST /desktop/wallets`

Додати гаманець для відстеження. Мережа автоматично визначається за форматом адреси.

| Параметр | Тип | Обов'язковий | Опис |
|----------|-----|-------------|------|
| `address` | `string` | ✅ | Адреса гаманця |
| `chain` | `string?` | ❌ | `ethereum`, `bsc`, `arbitrum`, `base`, `polygon`, `solana`, `tron` |
| `label` | `string?` | ❌ | Мітка гаманця |

> Якщо `chain` не вказано — автоматичне визначення по адресі.
> EVM адреси (0x...) за замовчуванням = Ethereum. Для BSC/Arbitrum/Base/Polygon вказуйте `chain` явно.

**Response:**
```json
{
  "id": 6,
  "address": "0x742d35...5BAf8",
  "chain": "ethereum",
  "label": "DeFi wallet",
  "status": "added"
}
```

**Помилки:**
- `400` — невідомий формат адреси / невідома мережа
- `403` — ліміт гаманців досягнуто
- `409` — гаманець вже відстежується

---

#### `DELETE /desktop/wallets/{wallet_id}`

Видалити гаманець з відстеження.

**Response:**
```json
{ "status": "removed", "wallet_id": 3 }
```

---

#### `PATCH /desktop/wallets/{wallet_id}`

Оновити мітку гаманця.

| Параметр | Тип | Опис |
|----------|-----|------|
| `label` | `string?` | Нова мітка (макс. 100 символів) |

**Response:**
```json
{ "wallet_id": 3, "label": "Main ETH", "status": "updated" }
```

---

#### `GET /desktop/wallets/{wallet_id}/portfolio`

Портфель гаманця — всі токени з балансами та USD вартістю.

**Response:**
```json
{
  "wallet_id": 3,
  "address": "0x742d35...5BAf8",
  "chain": "ethereum",
  "label": "Основний ETH",
  "total_value_usd": 12450.75,
  "last_scanned": "2026-04-08T08:05:30+00:00",
  "tokens": [
    {
      "symbol": "ETH",
      "name": "Ethereum",
      "contract_address": null,
      "balance": 3.547,
      "price_usd": 3250.00,
      "value_usd": 11527.75,
      "logo_url": null,
      "decimals": 18
    },
    {
      "symbol": "USDT",
      "name": "Tether USD",
      "contract_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
      "balance": 923.0,
      "price_usd": 1.0,
      "value_usd": 923.0,
      "logo_url": "https://...",
      "decimals": 6
    }
  ]
}
```

> `contract_address = null` означає нативний токен мережі (ETH, BNB, TRX, SOL, MATIC)

---

#### `GET /desktop/wallets/{wallet_id}/transactions`

Транзакції гаманця. **Вимагає PRO+.**

| Параметр | Тип | За замовч. | Опис |
|----------|-----|-----------|------|
| `limit` | `int` | `20` | 1–100 |
| `offset` | `int` | `0` | Зміщення |

**Response:**
```json
{
  "wallet_id": 3,
  "transactions": [
    {
      "tx_hash": "0xabc123...def",
      "chain": "ethereum",
      "block_number": 19567890,
      "timestamp": "2026-04-08T07:45:00+00:00",
      "from_address": "0x742d35...5BAf8",
      "to_address": "0x1234...5678",
      "tx_type": "transfer",
      "token_symbol": "USDT",
      "amount": 500.0,
      "amount_usd": 500.0,
      "token_out_symbol": null,
      "amount_out": null,
      "fee": 0.003,
      "fee_usd": 9.75
    },
    {
      "tx_hash": "0xdef456...abc",
      "chain": "ethereum",
      "block_number": 19567800,
      "timestamp": "2026-04-08T06:30:00+00:00",
      "from_address": "0x9999...1111",
      "to_address": "0x742d35...5BAf8",
      "tx_type": "receive",
      "token_symbol": "ETH",
      "amount": 1.5,
      "amount_usd": 4875.0,
      "token_out_symbol": null,
      "amount_out": null,
      "fee": null,
      "fee_usd": null
    }
  ],
  "count": 2
}
```

**Типи транзакцій (`tx_type`):**

| Тип | Опис |
|-----|------|
| `transfer` | Відправка токенів |
| `receive` | Отримання токенів |
| `swap` | DEX обмін (має `token_out_symbol` + `amount_out`) |
| `approve` | Approve для смарт-контракту |
| `contract` | Інша взаємодія зі смарт-контрактом |

---

#### `GET /desktop/wallets/{wallet_id}/analysis`

AI аналіз портфеля гаманця. **Вимагає PRO+.**
Використовує DeepSeek для оцінки диверсифікації, ризик-профілю та рекомендацій.

**Response:**
```json
{
  "wallet_id": 3,
  "analysis": "📊 Портфель: $12,450\n\n1. Диверсифікація: помірна — 92% в ETH\n2. Ризик-профіль: агресивний\n3. Рекомендації:\n- Розподілити між 3-5 активами\n- Додати стейблкоін буфер 10-20%"
}
```

- `403` — вимагає PRO підписку
- `500` — помилка генерації аналізу (AI timeout)

---

#### `PATCH /desktop/wallets/{wallet_id}/alerts`

Оновити конфігурацію алертів гаманця.

| Параметр | Тип | Опис |
|----------|-----|------|
| `new_tx` | `bool?` | Алерт при нових транзакціях |
| `new_token` | `bool?` | Алерт при нових токенах |
| `large_transfer_usd` | `float?` | Поріг великого переказу (USD) |

**Response:**
```json
{
  "wallet_id": 3,
  "alert_config": {
    "new_tx": true,
    "new_token": true,
    "large_transfer_usd": 1000
  }
}
```

> За замовчуванням: `new_tx=true`, `new_token=true`, `large_transfer_usd=500`

---

## WebSocket

### Підключення

```
wss://<your-domain>/desktop/ws
```

### Протокол

#### 1. Підключення та авторизація

```
Client connects to wss://domain/desktop/ws
Server accepts connection
Client → {"type": "auth", "key": "brk_xxxxxxxxxxxx"}     (протягом 10 секунд!)
Server → {"type": "auth_ok", "tier": "pro", "features": {...}}
```

**Таймаут:** Якщо клієнт не відправить auth протягом 10 секунд — з'єднання закривається з кодом `4001`.

#### 2. Підписка на монети (опціонально)

```
Client → {"type": "subscribe", "coins": ["BTC", "ETH", "NEAR"]}
Server → {"type": "subscribed", "coins": ["BTC", "ETH", "NEAR"]}
```

> Без підписки отримуєте ВСІ сигнали доступні вашому тіру.
> З підпискою — тільки по вибраних монетах.

#### 3. Повідомлення від сервера

| Тип | Коли | Дані |
|-----|------|------|
| `heartbeat` | Кожні 30 сек | `{"type": "heartbeat", "ts": "ISO8601"}` |
| `signal_new` | Новий сигнал | Повний об'єкт сигналу |
| `signal_update` | Оновлення сигналу | TP hit, SL hit, close... |
| `price_alert` | Спрацював алерт | Дані алерту |
| `pong` | Відповідь на ping | `{"type": "pong", "ts": "ISO8601"}` |

#### 4. Повідомлення від клієнта

| Тип | Опис |
|-----|------|
| `{"type": "ping"}` | Запит heartbeat (відповідь: `pong`) |
| `{"type": "subscribe", "coins": [...]}` | Фільтрація по монетах |

### Коди закриття

| Код | Опис |
|-----|------|
| `4000` | Загальна помилка |
| `4001` | Таймаут авторизації або невалідне перше повідомлення |
| `4003` | Невалідний ключ / заблокований акаунт |

### Фільтрація повідомлень

Сигнали фільтруються двома рівнями:
1. **Tier gating:** юзер отримує тільки сигнали де `min_tier ≤ user.tier`
2. **Coin subscription:** якщо підписано на конкретні монети — тільки вони

### Повний приклад (JavaScript)

```javascript
const API_KEY = 'brk_xxxxxxxxxxxx'
const ws = new WebSocket('wss://api.example.com/desktop/ws')

// 1. Авторизація при підключенні
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', key: API_KEY }))
}

// 2. Обробка повідомлень
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data)

  switch (msg.type) {
    case 'auth_ok':
      console.log(`Авторизовано: ${msg.tier}`)
      // Підписатись на конкретні монети
      ws.send(JSON.stringify({
        type: 'subscribe',
        coins: ['BTC', 'ETH', 'NEAR']
      }))
      break

    case 'subscribed':
      console.log(`Підписка: ${msg.coins.join(', ')}`)
      break

    case 'signal_new':
      // Новий сигнал!
      showNotification(`🔔 ${msg.data.coin_symbol} ${msg.data.direction.toUpperCase()}`)
      break

    case 'signal_update':
      // TP хіт, SL, тощо
      updateSignalCard(msg.data)
      break

    case 'price_alert':
      // Спрацював алерт
      showAlert(msg.data)
      break

    case 'heartbeat':
      // Keepalive — ігноруємо або оновлюємо статус з'єднання
      break

    case 'pong':
      break

    case 'error':
      console.error('WS Error:', msg.message)
      break
  }
}

// 3. Реконнект при розриві
ws.onclose = (event) => {
  console.log(`Disconnected: ${event.code}`)
  if (event.code !== 4003) {
    // Реконнект (не для забанених)
    setTimeout(() => reconnect(), 3000)
  }
}

// 4. Keepalive ping (на випадок якщо heartbeat не приходить)
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }))
  }
}, 25000)
```

---

## Типи алертів (детально)

### Цінові алерти

#### `price_above` — Ціна вище порогу

Спрацьовує коли ціна монети перевищує вказану ціну.

```json
{
  "alert_type": "price_above",
  "params": "{\"target_price\": 72000.0}"
}
```

#### `price_below` — Ціна нижче порогу

```json
{
  "alert_type": "price_below",
  "params": "{\"target_price\": 65000.0}"
}
```

#### `custom_range` — Ціна виходить з діапазону

```json
{
  "alert_type": "custom_range",
  "params": "{\"low\": 65000.0, \"high\": 72000.0}"
}
```

### Зміна ціни

#### `change_1h` — Зміна за годину (%)

```json
{
  "alert_type": "change_1h",
  "params": "{\"threshold_percent\": 3.0}"
}
```

#### `change_24h` — Зміна за 24 години (%)

```json
{
  "alert_type": "change_24h",
  "params": "{\"threshold_percent\": 10.0}"
}
```

### Об'ємні алерти

#### `volume_spike` — Сплеск об'єму

Спрацьовує при аномальному збільшенні об'єму торгів.

```json
{
  "alert_type": "volume_spike",
  "params": "{\"multiplier\": 3.0}"
}
```

### Технічні індикатори

#### `rsi_overbought` — RSI перекупленість

```json
{
  "alert_type": "rsi_overbought",
  "params": "{\"threshold\": 70}"
}
```

#### `rsi_oversold` — RSI перепроданість

```json
{
  "alert_type": "rsi_oversold",
  "params": "{\"threshold\": 30}"
}
```

#### `macd_cross` — MACD перетин

Спрацьовує при bullish або bearish кросі MACD.

```json
{
  "alert_type": "macd_cross",
  "params": "{\"direction\": \"bullish\"}"
}
```

#### `bb_breakout` — Bollinger Bands пробій

Ціна виходить за межі Bollinger Bands.

```json
{
  "alert_type": "bb_breakout",
  "params": "{\"band\": \"upper\"}"
}
```

### Рекорди

#### `new_ath` — Новий історичний максимум

```json
{
  "alert_type": "new_ath",
  "params": "{}"
}
```

#### `new_atl` — Новий історичний мінімум

```json
{
  "alert_type": "new_atl",
  "params": "{}"
}
```

### Ринкові алерти

#### `funding_rate` — Funding Rate

Спрацьовує при екстремальному funding rate на ф'ючерсах.

```json
{
  "alert_type": "funding_rate",
  "params": "{\"threshold\": 0.01}"
}
```

#### `correlation_break` — Розрив кореляції

Коли монета різко відхиляється від кореляції з BTC.

```json
{
  "alert_type": "correlation_break",
  "params": "{\"min_correlation\": 0.7}"
}
```

### Рівні підтримки/опору

#### `support_hit` — Ціна досягла підтримки

```json
{
  "alert_type": "support_hit",
  "params": "{\"level\": 64000.0}"
}
```

#### `resistance_hit` — Ціна досягла опору

```json
{
  "alert_type": "resistance_hit",
  "params": "{\"level\": 74000.0}"
}
```

### Кулдаун

Параметр `cooldown` (5–1440 хвилин) задає мінімальний інтервал між повторними спрацюваннями одного алерту. За замовчуванням — 60 хвилин.

Це запобігає спаму, коли ціна коливається навколо порогу алерту.

---

## Enums

### SignalStatus

| Значення | Опис |
|----------|------|
| `active` | Активний сигнал |
| `tp1_hit` | Досягнуто TP1 |
| `tp2_hit` | Досягнуто TP2 |
| `tp3_hit` | Досягнуто TP3 |
| `stopped` | Стоп-лосс спрацював (може бути з прибутком — trailing!) |
| `closed` | Закрито вручну |
| `cancelled` | Скасовано |
| `expired` | Закінчився термін дії |

### SignalDirection

| Значення | Опис |
|----------|------|
| `long` | Довга позиція (ріст) |
| `short` | Коротка позиція (падіння) |

### Tier

| Значення | Опис |
|----------|------|
| `free` | Безкоштовний |
| `pro` | Професійний |
| `elite` | Елітний |

### AlertType (16 типів)

`price_above`, `price_below`, `change_1h`, `change_24h`, `volume_spike`, `rsi_overbought`, `rsi_oversold`, `macd_cross`, `bb_breakout`, `new_ath`, `new_atl`, `funding_rate`, `correlation_break`, `support_hit`, `resistance_hit`, `custom_range`

### ChainType (7 мереж)

| Значення | Мережа | Нативний токен |
|----------|--------|---------------|
| `ethereum` | Ethereum Mainnet | ETH |
| `bsc` | BNB Smart Chain | BNB |
| `arbitrum` | Arbitrum One | ETH |
| `base` | Base | ETH |
| `polygon` | Polygon | MATIC |
| `solana` | Solana | SOL |
| `tron` | TRON | TRX |

---

## Помилки

| HTTP код | Опис |
|----------|------|
| `400` | Невалідні параметри запиту |
| `401` | Відсутній або невалідний API ключ |
| `403` | Доступ заборонено (бан, ліміт тарифу) |
| `404` | Ресурс не знайдено |
| `409` | Конфлікт (дублікат в вотчлісті) |
| `422` | Помилка валідації (FastAPI автоматична) |
| `500` | Внутрішня помилка сервера |

Всі помилки повертають:
```json
{ "detail": "Текст помилки" }
```

---

## Приклади інтеграції

### Python (httpx)

```python
import httpx

API_KEY = "brk_xxxxxxxxxxxx"
BASE = "https://api.example.com/desktop"
HEADERS = {"X-API-Key": API_KEY}

async def get_active_signals():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/signals/active", headers=HEADERS)
        return r.json()["signals"]

async def create_alert(coin: str, alert_type: str, params: dict, cooldown: int = 60):
    import json
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE}/alerts",
            headers=HEADERS,
            params={
                "coin": coin,
                "alert_type": alert_type,
                "params": json.dumps(params),
                "cooldown": cooldown,
            },
        )
        return r.json()

# Приклад: алерт коли BTC > $72K
alert = await create_alert("BTC", "price_above", {"target_price": 72000}, cooldown=30)
```

### Python WebSocket (websockets)

```python
import asyncio
import json
import websockets

API_KEY = "brk_xxxxxxxxxxxx"

async def listen():
    async with websockets.connect("wss://api.example.com/desktop/ws") as ws:
        # Auth
        await ws.send(json.dumps({"type": "auth", "key": API_KEY}))
        auth_response = json.loads(await ws.recv())
        print(f"Auth: {auth_response['type']}, tier: {auth_response.get('tier')}")

        # Subscribe
        await ws.send(json.dumps({"type": "subscribe", "coins": ["BTC", "ETH"]}))

        # Listen
        async for message in ws:
            msg = json.loads(message)
            if msg["type"] == "signal_new":
                print(f"🔔 New: {msg['data']['coin_symbol']} {msg['data']['direction']}")
            elif msg["type"] == "signal_update":
                print(f"📊 Update: {msg['data']}")
            elif msg["type"] == "price_alert":
                print(f"⚡ Alert: {msg['data']}")

asyncio.run(listen())
```

### Оптимальна стратегія підключення

1. **REST для ініціалізації:** `/me` → `/signals/active` → `/watchlist` → `/stats`
2. **WebSocket для real-time:** підключити після ініціалізації
3. **Polling fallback:** якщо WS недоступний — `GET /signals/active` кожні 30 сек
4. **Реконнект:** експоненційний backoff (3s → 6s → 12s → 30s max)
5. **Кеш:** зберігати `/market` і `/coins` локально, оновлювати кожні 5 хв
