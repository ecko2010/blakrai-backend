"""
Trilingual localization system (Ukrainian / English / Russian).
Every user-facing string goes through this module.
Usage:
    from app.localization.texts import t
    msg = t("signal.new_title", lang="uk", coin="BTC")
"""

from typing import Any

_TEXTS: dict[str, dict[str, str]] = {
    # ─── Bot start / onboarding ───────────────────────────
    "start.welcome": {
        "uk": (
            "🚀 <b>Ласкаво просимо до BLACK ROOM!</b>\n\n"
            "Найпотужніша AI-система торгових сигналів для криптовалют.\n\n"
            "Оберіть мову / Choose your language:"
        ),
        "en": (
            "🚀 <b>Welcome to BLACK ROOM!</b>\n\n"
            "The most powerful AI-powered crypto trading signal system.\n\n"
            "Choose your language:"
        ),
        "ru": (
            "🚀 <b>Добро пожаловать в BLACK ROOM!</b>\n\n"
            "Самая мощная AI-система торговых сигналов для криптовалют.\n\n"
            "Выберите язык:"
        ),
    },
    "start.language_set": {
        "uk": "✅ Мову встановлено: <b>Українська</b>",
        "en": "✅ Language set: <b>English</b>",
        "ru": "✅ Язык установлен: <b>Русский</b>",
    },
    "start.main_menu": {
        "uk": (
            "📊 <b>BLACK ROOM</b> — Головне меню\n\n"
            "Ваш тариф: <b>{tier}</b>\n"
            "Активних сигналів: <b>{active_signals}</b>\n\n"
            "Оберіть дію:"
        ),
        "en": (
            "📊 <b>BLACK ROOM</b> — Main Menu\n\n"
            "Your plan: <b>{tier}</b>\n"
            "Active signals: <b>{active_signals}</b>\n\n"
            "Choose an action:"
        ),
        "ru": (
            "📊 <b>BLACK ROOM</b> — Главное меню\n\n"
            "Ваш тариф: <b>{tier}</b>\n"
            "Активных сигналов: <b>{active_signals}</b>\n\n"
            "Выберите действие:"
        ),
    },

    # ─── Tier names ───────────────────────────────────────
    "tier.free": {"uk": "🆓 Free", "en": "🆓 Free", "ru": "🆓 Free"},
    "tier.pro": {"uk": "⭐ Pro", "en": "⭐ Pro", "ru": "⭐ Pro"},
    "tier.elite": {"uk": "👑 Elite", "en": "👑 Elite", "ru": "👑 Elite"},

    # ─── Buttons ──────────────────────────────────────────

    # ─── Signals ──────────────────────────────────────────
    "signal.new_title": {
        "uk": "🔔 <b>НОВИЙ СИГНАЛ</b>",
        "en": "🔔 <b>NEW SIGNAL</b>",
        "ru": "🔔 <b>НОВЫЙ СИГНАЛ</b>",
    },
    "signal.direction_long": {"uk": "🟢 LONG", "en": "🟢 LONG", "ru": "🟢 LONG"},
    "signal.direction_short": {"uk": "🔴 SHORT", "en": "🔴 SHORT", "ru": "🔴 SHORT"},
    "signal.body": {
        "uk": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b> ({coin_name})\n"
            "📊 Біржа: {exchange} | Пара: {pair}\n"
            "⏰ Таймфрейм: {timeframe}\n\n"
            "▫️ Вхід: <code>{entry_price}</code>\n"
            "🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)\n"
            "🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)\n"
            "🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)\n"
            "🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)\n\n"
            "📏 R:R — {risk_reward}\n"
            "🧠 Впевненість AI: {confidence}%\n"
            "⚡ Плече: x{leverage}\n\n"
            "📝 <i>{reasoning}</i>\n\n"
            "🆔 #{signal_id}"
        ),
        "en": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b> ({coin_name})\n"
            "📊 Exchange: {exchange} | Pair: {pair}\n"
            "⏰ Timeframe: {timeframe}\n\n"
            "▫️ Entry: <code>{entry_price}</code>\n"
            "🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)\n"
            "🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)\n"
            "🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)\n"
            "🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)\n\n"
            "📏 R:R — {risk_reward}\n"
            "🧠 AI Confidence: {confidence}%\n"
            "⚡ Leverage: x{leverage}\n\n"
            "📝 <i>{reasoning}</i>\n\n"
            "🆔 #{signal_id}"
        ),
        "ru": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b> ({coin_name})\n"
            "📊 Биржа: {exchange} | Пара: {pair}\n"
            "⏰ Таймфрейм: {timeframe}\n\n"
            "▫️ Вход: <code>{entry_price}</code>\n"
            "🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)\n"
            "🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)\n"
            "🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)\n"
            "🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)\n\n"
            "📏 R:R — {risk_reward}\n"
            "🧠 Уверенность AI: {confidence}%\n"
            "⚡ Плечо: x{leverage}\n\n"
            "📝 <i>{reasoning}</i>\n\n"
            "🆔 #{signal_id}"
        ),
    },
    "signal.body_free": {
        "uk": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b>\n"
            "📊 Біржа: {exchange}\n\n"
            "▫️ Зона входу: ~{entry_approx}\n"
            "🎯 Потенціал: +{potential}%\n"
            "🧠 AI Впевненість: {confidence}%\n\n"
            "🔒 <i>Точні TP/SL та деталі доступні на тарифах Pro/Elite</i>\n\n"
            "💎 /subscribe — отримати повний доступ\n\n"
            "🆔 #{signal_id}"
        ),
        "en": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b>\n"
            "📊 Exchange: {exchange}\n\n"
            "▫️ Entry zone: ~{entry_approx}\n"
            "🎯 Potential: +{potential}%\n"
            "🧠 AI Confidence: {confidence}%\n\n"
            "🔒 <i>Exact TP/SL and details available on Pro/Elite plans</i>\n\n"
            "💎 /subscribe — get full access\n\n"
            "🆔 #{signal_id}"
        ),
        "ru": (
            "{direction_icon}\n\n"
            "🪙 <b>{coin_symbol}</b>\n"
            "📊 Биржа: {exchange}\n\n"
            "▫️ Зона входа: ~{entry_approx}\n"
            "🎯 Потенциал: +{potential}%\n"
            "🧠 Уверенность AI: {confidence}%\n\n"
            "🔒 <i>Точные TP/SL и детали доступны на тарифах Pro/Elite</i>\n\n"
            "💎 /subscribe — получить полный доступ\n\n"
            "🆔 #{signal_id}"
        ),
    },

    # ─── Signal updates ───────────────────────────────────
    "signal.tp1_hit": {
        "uk": "✅ <b>TP1 ДОСЯГНУТО!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибуток: +{pnl}%",
        "en": "✅ <b>TP1 HIT!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Profit: +{pnl}%",
        "ru": "✅ <b>TP1 ДОСТИГНУТ!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибыль: +{pnl}%",
    },
    "signal.tp2_hit": {
        "uk": "✅✅ <b>TP2 ДОСЯГНУТО!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибуток: +{pnl}%",
        "en": "✅✅ <b>TP2 HIT!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Profit: +{pnl}%",
        "ru": "✅✅ <b>TP2 ДОСТИГНУТ!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибыль: +{pnl}%",
    },
    "signal.tp3_hit": {
        "uk": "✅✅✅ <b>TP3 ДОСЯГНУТО!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибуток: +{pnl}%\n🏆 Повна перемога!",
        "en": "✅✅✅ <b>TP3 HIT!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Profit: +{pnl}%\n🏆 Full win!",
        "ru": "✅✅✅ <b>TP3 ДОСТИГНУТ!</b>\n\n🪙 {coin_symbol} #{signal_id}\n💰 Прибыль: +{pnl}%\n🏆 Полная победа!",
    },
    "signal.sl_hit": {
        "uk": "🛑 <b>СТОП-ЛОСС</b>\n\n🪙 {coin_symbol} #{signal_id}\n📉 Збиток: {pnl}%",
        "en": "🛑 <b>STOP LOSS HIT</b>\n\n🪙 {coin_symbol} #{signal_id}\n📉 Loss: {pnl}%",
        "ru": "🛑 <b>СТОП-ЛОСС</b>\n\n🪙 {coin_symbol} #{signal_id}\n📉 Убыток: {pnl}%",
    },
    "signal.closed": {
        "uk": "🔒 <b>СИГНАЛ ЗАКРИТО</b>\n\n🪙 {coin_symbol} #{signal_id}\n📊 Результат: {pnl}%",
        "en": "🔒 <b>SIGNAL CLOSED</b>\n\n🪙 {coin_symbol} #{signal_id}\n📊 Result: {pnl}%",
        "ru": "🔒 <b>СИГНАЛ ЗАКРЫТ</b>\n\n🪙 {coin_symbol} #{signal_id}\n📊 Результат: {pnl}%",
    },

    # ─── Stats ────────────────────────────────────────────
    "stats.title": {
        "uk": "📈 <b>СТАТИСТИКА BLACK ROOM</b>",
        "en": "📈 <b>BLACK ROOM STATISTICS</b>",
        "ru": "📈 <b>СТАТИСТИКА BLACK ROOM</b>",
    },
    "stats.body": {
        "uk": (
            "📅 Період: <b>{period}</b>\n\n"
            "📊 Всього сигналів: <b>{total}</b>\n"
            "✅ Прибуткових: <b>{wins}</b> ({win_rate}%)\n"
            "❌ Збиткових: <b>{losses}</b>\n"
            "⏳ Активних: <b>{active}</b>\n\n"
            "💰 Середній прибуток: <b>+{avg_win}%</b>\n"
            "📉 Середній збиток: <b>{avg_loss}%</b>\n"
            "📊 Загальний PnL: <b>{total_pnl}%</b>\n\n"
            "🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>\n"
            "🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>\n"
            "🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>\n\n"
            "📏 Profit Factor: <b>{profit_factor}</b>\n"
            "📐 Sharpe Ratio: <b>{sharpe}</b>\n"
            "📉 Max Drawdown: <b>{max_dd}%</b>\n"
            "🔥 Win Streak: <b>{win_streak}</b>\n"
            "❄️ Loss Streak: <b>{loss_streak}</b>"
        ),
        "en": (
            "📅 Period: <b>{period}</b>\n\n"
            "📊 Total signals: <b>{total}</b>\n"
            "✅ Winning: <b>{wins}</b> ({win_rate}%)\n"
            "❌ Losing: <b>{losses}</b>\n"
            "⏳ Active: <b>{active}</b>\n\n"
            "💰 Avg win: <b>+{avg_win}%</b>\n"
            "📉 Avg loss: <b>{avg_loss}%</b>\n"
            "📊 Total PnL: <b>{total_pnl}%</b>\n\n"
            "🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>\n"
            "🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>\n"
            "🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>\n\n"
            "📏 Profit Factor: <b>{profit_factor}</b>\n"
            "📐 Sharpe Ratio: <b>{sharpe}</b>\n"
            "📉 Max Drawdown: <b>{max_dd}%</b>\n"
            "🔥 Win Streak: <b>{win_streak}</b>\n"
            "❄️ Loss Streak: <b>{loss_streak}</b>"
        ),
        "ru": (
            "📅 Период: <b>{period}</b>\n\n"
            "📊 Всего сигналов: <b>{total}</b>\n"
            "✅ Прибыльных: <b>{wins}</b> ({win_rate}%)\n"
            "❌ Убыточных: <b>{losses}</b>\n"
            "⏳ Активных: <b>{active}</b>\n\n"
            "💰 Средний профит: <b>+{avg_win}%</b>\n"
            "📉 Средний убыток: <b>{avg_loss}%</b>\n"
            "📊 Общий PnL: <b>{total_pnl}%</b>\n\n"
            "🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>\n"
            "🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>\n"
            "🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>\n\n"
            "📏 Profit Factor: <b>{profit_factor}</b>\n"
            "📐 Sharpe Ratio: <b>{sharpe}</b>\n"
            "📉 Max Drawdown: <b>{max_dd}%</b>\n"
            "🔥 Win Streak: <b>{win_streak}</b>\n"
            "❄️ Loss Streak: <b>{loss_streak}</b>"
        ),
    },

    # ─── Subscription ─────────────────────────────────────
    "sub.choose_plan": {
        "uk": (
            "💎 <b>Тарифні плани BLACK ROOM</b>\n\n"
            "🆓 <b>Free</b> — базові сигнали без точних даних\n"
            "⭐ <b>Pro</b> — повні сигнали + статистика\n"
            "👑 <b>Elite</b> — все з Pro + AI аналітика + пріоритет + портфоліо\n\n"
            "Оберіть план:"
        ),
        "en": (
            "💎 <b>BLACK ROOM Plans</b>\n\n"
            "🆓 <b>Free</b> — basic signals without exact data\n"
            "⭐ <b>Pro</b> — full signals + statistics\n"
            "👑 <b>Elite</b> — everything in Pro + AI analytics + priority + portfolio\n\n"
            "Choose a plan:"
        ),
        "ru": (
            "💎 <b>Тарифные планы BLACK ROOM</b>\n\n"
            "🆓 <b>Free</b> — базовые сигналы без точных данных\n"
            "⭐ <b>Pro</b> — полные сигналы + статистика\n"
            "👑 <b>Elite</b> — всё из Pro + AI аналитика + приоритет + портфолио\n\n"
            "Выберите план:"
        ),
    },
    "sub.payment_created": {
        "uk": "💳 Оплата створена! Перейдіть за посиланням:\n\n{url}\n\nОплата дійсна 60 хвилин.",
        "en": "💳 Payment created! Follow the link:\n\n{url}\n\nPayment valid for 60 minutes.",
        "ru": "💳 Оплата создана! Перейдите по ссылке:\n\n{url}\n\nОплата действительна 60 минут.",
    },
    "sub.payment_success": {
        "uk": "🎉 <b>Оплату підтверджено!</b>\n\nВаш тариф: <b>{tier}</b>\nДійсний до: <b>{expires}</b>",
        "en": "🎉 <b>Payment confirmed!</b>\n\nYour plan: <b>{tier}</b>\nValid until: <b>{expires}</b>",
        "ru": "🎉 <b>Оплата подтверждена!</b>\n\nВаш тариф: <b>{tier}</b>\nДействителен до: <b>{expires}</b>",
    },
    "sub.expired": {
        "uk": "⚠️ Ваша підписка <b>{tier}</b> закінчилась. Продовжіть через /subscribe",
        "en": "⚠️ Your <b>{tier}</b> subscription has expired. Renew via /subscribe",
        "ru": "⚠️ Ваша подписка <b>{tier}</b> истекла. Продлите через /subscribe",
    },

    # ─── Digests ──────────────────────────────────────────
    "digest.daily_title": {
        "uk": "📊 <b>ЩОДЕННИЙ ЗВІТ — {date}</b>",
        "en": "📊 <b>DAILY DIGEST — {date}</b>",
        "ru": "📊 <b>ЕЖЕДНЕВНЫЙ ОТЧЁТ — {date}</b>",
    },
    "digest.weekly_title": {
        "uk": "📊 <b>ТИЖНЕВИЙ ЗВІТ — {date_range}</b>",
        "en": "📊 <b>WEEKLY REPORT — {date_range}</b>",
        "ru": "📊 <b>НЕДЕЛЬНЫЙ ОТЧЁТ — {date_range}</b>",
    },

    # ─── Help ─────────────────────────────────────────────
    "help.text": {
        "uk": (
            "❓ <b>Допомога BLACK ROOM</b>\n\n"
            "🤖 Це AI-система торгових сигналів, яка аналізує ринок 24/7.\n\n"
            "<b>Команди:</b>\n"
            "/start — головне меню\n"
            "/signals — активні сигнали\n"
            "/stats — статистика\n"
            "/subscribe — тарифи\n"
            "/settings — налаштування\n"
            "/help — ця довідка\n\n"
            "📡 Сигнали надходять прямо в бот з кнопками деталей.\n"
            "📊 Дайджести та аналітика публікуються в каналах."
        ),
        "en": (
            "❓ <b>BLACK ROOM Help</b>\n\n"
            "🤖 This is an AI trading signal system analyzing the market 24/7.\n\n"
            "<b>Commands:</b>\n"
            "/start — main menu\n"
            "/signals — active signals\n"
            "/stats — statistics\n"
            "/subscribe — plans\n"
            "/settings — settings\n"
            "/help — this help\n\n"
            "📡 Signals are delivered directly to bot with detail buttons.\n"
            "📊 Digests and analytics are posted to channels."
        ),
        "ru": (
            "❓ <b>Помощь BLACK ROOM</b>\n\n"
            "🤖 Это AI-система торговых сигналов, анализирующая рынок 24/7.\n\n"
            "<b>Команды:</b>\n"
            "/start — главное меню\n"
            "/signals — активные сигналы\n"
            "/stats — статистика\n"
            "/subscribe — тарифы\n"
            "/settings — настройки\n"
            "/help — эта справка\n\n"
            "📡 Сигналы приходят прямо в бот с кнопками деталей.\n"
            "📊 Дайджесты и аналитика публикуются в каналах."
        ),
    },

    # ─── Errors ───────────────────────────────────────────
    "error.generic": {
        "uk": "❌ Сталася помилка. Спробуйте пізніше.",
        "en": "❌ An error occurred. Please try again later.",
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
    },
    "error.not_subscribed": {
        "uk": "🔒 Ця функція доступна лише для підписників {tier}+",
        "en": "🔒 This feature is available for {tier}+ subscribers only",
        "ru": "🔒 Эта функция доступна только для подписчиков {tier}+",
    },
    "error.banned": {
        "uk": "🚫 Ваш акаунт заблоковано.",
        "en": "🚫 Your account has been banned.",
        "ru": "🚫 Ваш аккаунт заблокирован.",
    },

    # ─── Admin panel ──────────────────────────────────────
    "start": {
        "uk": "🚀 <b>Привіт, {name}!</b>\n\nЛаскаво просимо до BLACK ROOM — найпотужнішої AI-системи торгових сигналів.\n\nОберіть дію:",
        "en": "🚀 <b>Hi, {name}!</b>\n\nWelcome to BLACK ROOM — the most powerful AI trading signal system.\n\nChoose an action:",
        "ru": "🚀 <b>Привет, {name}!</b>\n\nДобро пожаловать в BLACK ROOM — самую мощную AI-систему торговых сигналов.\n\nВыберите действие:",
    },
    "main_menu": {
        "uk": "📊 <b>BLACK ROOM</b> — Головне меню\n\nОберіть дію:",
        "en": "📊 <b>BLACK ROOM</b> — Main Menu\n\nChoose an action:",
        "ru": "📊 <b>BLACK ROOM</b> — Главное меню\n\nВыберите действие:",
    },
    "language_changed": {
        "uk": "✅ Мову змінено на <b>Українську</b>",
        "en": "✅ Language changed to <b>English</b>",
        "ru": "✅ Язык изменён на <b>Русский</b>",
    },
    "help": {
        "uk": "❓ <b>Допомога</b>\n\n🤖 AI-система аналізує ринок 24/7 і генерує сигнали.\n\n/start — меню\n/menu — меню\n/signals — сигнали\n/stats — статистика\n/subscribe — підписка\n/settings — налаштування",
        "en": "❓ <b>Help</b>\n\n🤖 AI system analyzes the market 24/7 and generates signals.\n\n/start — menu\n/menu — menu\n/signals — signals\n/stats — statistics\n/subscribe — subscription\n/settings — settings",
        "ru": "❓ <b>Помощь</b>\n\n🤖 AI-система анализирует рынок 24/7 и генерирует сигналы.\n\n/start — меню\n/menu — меню\n/signals — сигналы\n/stats — статистика\n/subscribe — подписка\n/settings — настройки",
    },
    "signals_menu": {
        "uk": "📡 <b>Сигнали</b>\n\nОберіть категорію:",
        "en": "📡 <b>Signals</b>\n\nChoose a category:",
        "ru": "📡 <b>Сигналы</b>\n\nВыберите категорию:",
    },
    "no_active_signals": {
        "uk": "📭 Наразі немає активних сигналів. Скоро з'являться нові!",
        "en": "📭 No active signals right now. New ones coming soon!",
        "ru": "📭 Сейчас нет активных сигналов. Скоро появятся новые!",
    },
    "active_signals_header": {
        "uk": "🟢 <b>Активні сигнали:</b>",
        "en": "🟢 <b>Active Signals:</b>",
        "ru": "🟢 <b>Активные сигналы:</b>",
    },
    "no_signal_history": {
        "uk": "📭 Ще немає історії сигналів.",
        "en": "📭 No signal history yet.",
        "ru": "📭 История сигналов пока пуста.",
    },
    "signal_history_header": {
        "uk": "📜 <b>Історія сигналів:</b>",
        "en": "📜 <b>Signal History:</b>",
        "ru": "📜 <b>История сигналов:</b>",
    },
    "tracked_signals_header": {
        "uk": "📌 <b>Відстежувані сигнали:</b>",
        "en": "📌 <b>Tracked Signals:</b>",
        "ru": "📌 <b>Отслеживаемые сигналы:</b>",
    },
    "no_tracked_signals": {
        "uk": "📭 Ви ще не відстежуєте жодного сигналу.\nНатисніть «Використати» на сигналі, щоб почати відстеження.",
        "en": "📭 You're not tracking any signals yet.\nTap \"Use Signal\" on a signal to start tracking.",
        "ru": "📭 Вы ещё не отслеживаете ни одного сигнала.\nНажмите «Использовать» на сигнале, чтобы начать отслеживание.",
    },
    "signal_stats_header": {
        "uk": "📊 <b>Статистика сигналів</b>",
        "en": "📊 <b>Signal Stats</b>",
        "ru": "📊 <b>Статистика сигналов</b>",
    },
    "confidence": {"uk": "Впевненість", "en": "Confidence", "ru": "Уверенность"},
    "upgrade_to_see": {
        "uk": "Оновіть тариф для повних деталей → /subscribe",
        "en": "Upgrade your plan for full details → /subscribe",
        "ru": "Улучшите план для полных деталей → /subscribe",
    },
    "stats_menu": {
        "uk": "📈 <b>Статистика</b>\n\nОберіть період:",
        "en": "📈 <b>Statistics</b>\n\nChoose period:",
        "ru": "📈 <b>Статистика</b>\n\nВыберите период:",
    },
    "loading": {"uk": "⏳ Завантаження...", "en": "⏳ Loading...", "ru": "⏳ Загрузка..."},
    "error_generic": {"uk": "❌ Помилка. Спробуйте пізніше.", "en": "❌ Error. Try again later.", "ru": "❌ Ошибка. Попробуйте позже."},
    "no_data_for_heatmap": {
        "uk": "📭 Недостатньо даних для хітмапу.",
        "en": "📭 Not enough data for heatmap.",
        "ru": "📭 Недостаточно данных для тепловой карты.",
    },
    "heatmap_caption": {
        "uk": "🗺️ Хітмап продуктивності сигналів",
        "en": "🗺️ Signal Performance Heatmap",
        "ru": "🗺️ Тепловая карта результатов сигналов",
    },
    "subscription_info": {
        "uk": "💎 <b>Підписка</b>\n\nВаш тариф: <b>{current_tier}</b>\n\nОберіть план:",
        "en": "💎 <b>Subscription</b>\n\nYour plan: <b>{current_tier}</b>\n\nChoose a plan:",
        "ru": "💎 <b>Подписка</b>\n\nВаш тариф: <b>{current_tier}</b>\n\nВыберите план:",
    },
    "tier_pro_desc": {
        "uk": "⭐ <b>Pro</b>\n\n✅ Повні сигнали з TP/SL\n✅ Статистика\n✅ Щоденний дайджест\n\nОберіть тривалість:",
        "en": "⭐ <b>Pro</b>\n\n✅ Full signals with TP/SL\n✅ Statistics\n✅ Daily digest\n\nChoose duration:",
        "ru": "⭐ <b>Pro</b>\n\n✅ Полные сигналы с TP/SL\n✅ Статистика\n✅ Ежедневный дайджест\n\nВыберите продолжительность:",
    },
    "tier_elite_desc": {
        "uk": (
            "👑 <b>Elite</b>\n\n"
            "✅ Все з Pro\n"
            "✅ 🧠 AI пояснення до кожного сигналу\n"
            "✅ 📊 Мультитаймфрейм аналіз\n"
            "✅ 🎯 Пріоритетні сигнали раніше за всіх\n"
            "✅ 💼 Симуляція портфоліо ($1K/$5K/$10K)\n"
            "✅ 🔍 Кореляційний аналіз активів\n"
            "✅ ⚡ Ексклюзивний контент\n\n"
            "Оберіть тривалість:"
        ),
        "en": (
            "👑 <b>Elite</b>\n\n"
            "✅ Everything in Pro\n"
            "✅ 🧠 AI reasoning for each signal\n"
            "✅ 📊 Multi-timeframe analysis\n"
            "✅ 🎯 Priority signals before everyone\n"
            "✅ 💼 Portfolio simulation ($1K/$5K/$10K)\n"
            "✅ 🔍 Asset correlation analysis\n"
            "✅ ⚡ Exclusive content\n\n"
            "Choose duration:"
        ),
        "ru": (
            "👑 <b>Elite</b>\n\n"
            "✅ Всё из Pro\n"
            "✅ 🧠 AI обоснование каждого сигнала\n"
            "✅ 📊 Мультитаймфрейм анализ\n"
            "✅ 🎯 Приоритетные сигналы раньше всех\n"
            "✅ 💼 Симуляция портфолио ($1K/$5K/$10K)\n"
            "✅ 🔍 Корреляционный анализ активов\n"
            "✅ ⚡ Эксклюзивный контент\n\n"
            "Выберите продолжительность:"
        ),
    },
    "payment_created": {
        "uk": "💳 Оплата створена: <b>${amount} {currency}</b>\n\nНатисніть кнопку для оплати:",
        "en": "💳 Payment created: <b>${amount} {currency}</b>\n\nClick the button to pay:",
        "ru": "💳 Оплата создана: <b>${amount} {currency}</b>\n\nНажмите кнопку для оплаты:",
    },
    "payment_error": {
        "uk": "❌ Не вдалось створити оплату. Спробуйте пізніше.",
        "en": "❌ Failed to create payment. Try again later.",
        "ru": "❌ Не удалось создать оплату. Попробуйте позже.",
    },
    "payment_success": {
        "uk": "🎉 <b>Оплату підтверджено!</b>\n\nВаш тариф активовано. Дякуємо!",
        "en": "🎉 <b>Payment confirmed!</b>\n\nYour plan is now active. Thank you!",
        "ru": "🎉 <b>Оплата подтверждена!</b>\n\nВаш тариф активирован. Спасибо!",
    },
    "payment_pending": {
        "uk": "⏳ Оплата ще обробляється. Зачекайте кілька хвилин.",
        "en": "⏳ Payment is still processing. Wait a few minutes.",
        "ru": "⏳ Оплата ещё обрабатывается. Подождите несколько минут.",
    },
    "payment_expired": {
        "uk": "⏰ Час оплати вичерпано. Створіть нову.",
        "en": "⏰ Payment expired. Create a new one.",
        "ru": "⏰ Время оплаты истекло. Создайте новую.",
    },
    "my_subscription": {
        "uk": "📋 <b>Ваша підписка</b>\n\nТариф: <b>{tier}</b>\nДійсна до: <b>{expires}</b>",
        "en": "📋 <b>Your Subscription</b>\n\nPlan: <b>{tier}</b>\nValid until: <b>{expires}</b>",
        "ru": "📋 <b>Ваша подписка</b>\n\nТариф: <b>{tier}</b>\nДействительна до: <b>{expires}</b>",
    },
    "settings": {
        "uk": "⚙️ <b>Налаштування</b>\n\nВаш тариф: <b>{tier}</b>",
        "en": "⚙️ <b>Settings</b>\n\nYour plan: <b>{tier}</b>",
        "ru": "⚙️ <b>Настройки</b>\n\nВаш тариф: <b>{tier}</b>",
    },
    "coming_soon": {"uk": "🔜 Скоро буде!", "en": "🔜 Coming soon!", "ru": "🔜 Скоро будет!"},
    "signal_full": {
        "uk": "📡 <b>{coin}</b> {direction}\n\n📍 Entry: ${entry}\n🎯 TP1: ${tp1}\n🛑 SL: ${sl}\n💪 Впевненість: {confidence}%",
        "en": "📡 <b>{coin}</b> {direction}\n\n📍 Entry: ${entry}\n🎯 TP1: ${tp1}\n🛑 SL: ${sl}\n💪 Confidence: {confidence}%",
        "ru": "📡 <b>{coin}</b> {direction}\n\n📍 Вход: ${entry}\n🎯 TP1: ${tp1}\n🛑 SL: ${sl}\n💪 Уверенность: {confidence}%",
    },
    "signal_teaser": {
        "uk": "📡 <b>{coin}</b> — 🔒 Повні деталі для Pro/Elite → /subscribe",
        "en": "📡 <b>{coin}</b> — 🔒 Full details for Pro/Elite → /subscribe",
        "ru": "📡 <b>{coin}</b> — 🔒 Полные детали для Pro/Elite → /subscribe",
    },
    # FREE channel: delayed teaser with minimal info and CTA
    "signal_free_channel": {
        "uk": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 Сигнал був актуальний раніше\n"
            "🎯 Результат: <b>{result}</b>\n\n"
            "🔒 <i>Отримуйте сигнали в реальному часі з Pro/Elite</i>\n"
            "💎 @{bot_username} → /subscribe"
        ),
        "en": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 Signal was active earlier\n"
            "🎯 Result: <b>{result}</b>\n\n"
            "🔒 <i>Get real-time signals with Pro/Elite</i>\n"
            "💎 @{bot_username} → /subscribe"
        ),
        "ru": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 Сигнал был актуален ранее\n"
            "🎯 Результат: <b>{result}</b>\n\n"
            "🔒 <i>Получайте сигналы в реальном времени с Pro/Elite</i>\n"
            "💎 @{bot_username} → /subscribe"
        ),
    },
    # Elite-exclusive: signal with AI reasoning
    "signal_elite": {
        "uk": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "📍 Entry: ${entry}\n"
            "🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}\n"
            "🛑 SL: ${sl}\n"
            "⚡ Плече: x{leverage}\n"
            "💪 Впевненість: {confidence}%\n\n"
            "🧠 <b>AI Аналіз:</b>\n<i>{reasoning}</i>\n\n"
            "📊 Кореляція з BTC: {btc_corr}\n"
            "📏 R:R — {rr}"
        ),
        "en": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "📍 Entry: ${entry}\n"
            "🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}\n"
            "🛑 SL: ${sl}\n"
            "⚡ Leverage: x{leverage}\n"
            "💪 Confidence: {confidence}%\n\n"
            "🧠 <b>AI Analysis:</b>\n<i>{reasoning}</i>\n\n"
            "📊 BTC Correlation: {btc_corr}\n"
            "📏 R:R — {rr}"
        ),
        "ru": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "📍 Вход: ${entry}\n"
            "🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}\n"
            "🛑 SL: ${sl}\n"
            "⚡ Плечо: x{leverage}\n"
            "💪 Уверенность: {confidence}%\n\n"
            "🧠 <b>AI Анализ:</b>\n<i>{reasoning}</i>\n\n"
            "📊 Корреляция с BTC: {btc_corr}\n"
            "📏 R:R — {rr}"
        ),
    },
    "digest_daily_caption": {
        "uk": "📊 Щоденний дайджест BLACK ROOM",
        "en": "📊 BLACK ROOM Daily Digest",
        "ru": "📊 Ежедневный дайджест BLACK ROOM",
    },
    "digest_weekly_caption": {
        "uk": "📊 Тижневий дайджест BLACK ROOM",
        "en": "📊 BLACK ROOM Weekly Digest",
        "ru": "📊 Недельный дайджест BLACK ROOM",
    },

    # ─── Portfolio simulation (digest) ────────────────────
    "portfolio_header": {
        "uk": "💼 <b>Симуляція портфоліо</b>",
        "en": "💼 <b>Portfolio Simulation</b>",
        "ru": "💼 <b>Симуляция портфолио</b>",
    },
    "portfolio_row": {
        "uk": "Стартовий: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
        "en": "Starting: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
        "ru": "Стартовый: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
    },

    # ─── Button labels ────────────────────────────────────
    "btn_signals": {"uk": "📡 Сигнали", "en": "📡 Signals", "ru": "📡 Сигналы"},
    "btn_stats": {"uk": "📈 Статистика", "en": "📈 Statistics", "ru": "📈 Статистика"},
    "btn_subscription": {"uk": "💎 Підписка", "en": "💎 Subscribe", "ru": "💎 Подписка"},
    "btn_settings": {"uk": "⚙️ Налаштування", "en": "⚙️ Settings", "ru": "⚙️ Настройки"},
    "btn_help": {"uk": "❓ Допомога", "en": "❓ Help", "ru": "❓ Помощь"},
    "btn_back": {"uk": "Назад", "en": "Back", "ru": "Назад"},
    "btn_active_signals": {"uk": "Активні сигнали", "en": "Active Signals", "ru": "Активные сигналы"},
    "btn_tracked_signals": {"uk": "Відстежувані", "en": "Tracked", "ru": "Отслеживаемые"},
    "btn_signal_history": {"uk": "Історія", "en": "History", "ru": "История"},
    "btn_signal_stats": {"uk": "Стата сигналів", "en": "Signal Stats", "ru": "Стата сигналов"},
    # Reply keyboard labels (visible text at bottom of chat)
    "rk_signals": {"uk": "📡 Сигнали", "en": "📡 Signals", "ru": "📡 Сигналы"},
    "rk_stats": {"uk": "📈 Статистика", "en": "📈 Stats", "ru": "📈 Статистика"},
    "rk_wallets": {"uk": "💰 Гаманці", "en": "💰 Wallets", "ru": "💰 Кошельки"},
    "rk_settings": {"uk": "⚙️ Налаштування", "en": "⚙️ Settings", "ru": "⚙️ Настройки"},
    "rk_subscription": {"uk": "💎 Підписка", "en": "💎 Subscribe", "ru": "💎 Подписка"},
    "rk_help": {"uk": "❓ Допомога", "en": "❓ Help", "ru": "❓ Помощь"},
    "rk_alerts": {"uk": "🔔 Алерти", "en": "🔔 Alerts", "ru": "🔔 Алерты"},
    "rk_watchlist": {"uk": "👁 Вотчліст", "en": "👁 Watchlist", "ru": "👁 Вотчлист"},
    "rk_back": {"uk": "◀️ Назад", "en": "◀️ Back", "ru": "◀️ Назад"},
    # Reply keyboard — Signals submenu
    "rk_active_signals": {"uk": "📡 Активні", "en": "📡 Active", "ru": "📡 Активные"},
    "rk_tracked_signals": {"uk": "📌 Відстежувані", "en": "📌 Tracked", "ru": "📌 Отслеживаемые"},
    "rk_signal_history": {"uk": "📜 Історія", "en": "📜 History", "ru": "📜 История"},
    "rk_signal_stats": {"uk": "📊 Стата", "en": "📊 Stats", "ru": "📊 Стата"},
    # Reply keyboard — Stats period buttons (merged into signals submenu)
    "rk_stats_24h": {"uk": "📊 24h", "en": "📊 24h", "ru": "📊 24h"},
    "rk_stats_7d": {"uk": "📊 7д", "en": "📊 7d", "ru": "📊 7д"},
    "rk_stats_30d": {"uk": "📊 30д", "en": "📊 30d", "ru": "📊 30д"},
    "rk_stats_all": {"uk": "📊 Весь час", "en": "📊 All time", "ru": "📊 Всё время"},
    "rk_heatmap": {"uk": "🔥 Хітмап", "en": "🔥 Heatmap", "ru": "🔥 Тепловая"},
    # Reply keyboard — Alerts submenu
    "rk_create_alert": {"uk": "➕ Створити", "en": "➕ Create", "ru": "➕ Создать"},
    "rk_my_alerts": {"uk": "📋 Мої алерти", "en": "📋 My Alerts", "ru": "📋 Мои алерты"},
    # Reply keyboard — Watchlist submenu
    "rk_add_watchlist": {"uk": "➕ Додати монету", "en": "➕ Add coin", "ru": "➕ Добавить монету"},
    # Reply keyboard — Wallets submenu
    "rk_my_wallets": {"uk": "💰 Мої гаманці", "en": "💰 My Wallets", "ru": "💰 Мои кошельки"},
    "rk_add_wallet": {"uk": "➕ Додати", "en": "➕ Add", "ru": "➕ Добавить"},
    # Reply keyboard — Subscription submenu
    "rk_sub_pro": {"uk": "⭐ Pro", "en": "⭐ Pro", "ru": "⭐ Pro"},
    "rk_sub_elite": {"uk": "💎 Elite", "en": "💎 Elite", "ru": "💎 Elite"},
    "rk_my_sub": {"uk": "📋 Моя підписка", "en": "📋 My Sub", "ru": "📋 Моя подписка"},
    # Reply keyboard — Settings submenu
    "rk_language": {"uk": "🌐 Мова", "en": "🌐 Language", "ru": "🌐 Язык"},
    "rk_notifications": {"uk": "🔔 Сповіщення", "en": "🔔 Notifications", "ru": "🔔 Уведомления"},
    "rk_api_key": {"uk": "🔑 API ключ", "en": "🔑 API Key", "ru": "🔑 API ключ"},
    "btn_all_time": {"uk": "За весь час", "en": "All time", "ru": "За всё время"},
    "btn_heatmap": {"uk": "Хітмап", "en": "Heatmap", "ru": "Тепловая карта"},
    "btn_cleanup_signals": {"uk": "🗑 Очистити сигнали", "en": "🗑 Cleanup Signals", "ru": "🗑 Очистить сигналы"},
    "btn_cleanup_stopped": {"uk": "🛑 Стоплосс", "en": "🛑 Stopped", "ru": "🛑 Стоплосс"},
    "btn_cleanup_expired": {"uk": "⏰ Протерміновані", "en": "⏰ Expired", "ru": "⏰ Просроченные"},
    "btn_cleanup_closed": {"uk": "📋 Закриті", "en": "📋 Closed", "ru": "📋 Закрытые"},
    "btn_cleanup_all_old": {"uk": "🗑 Всі закриті", "en": "🗑 All Closed", "ru": "🗑 Все закрытые"},
    "btn_confirm_yes": {"uk": "✅ Так, видалити", "en": "✅ Yes, delete", "ru": "✅ Да, удалить"},
    "btn_confirm_no": {"uk": "❌ Скасувати", "en": "❌ Cancel", "ru": "❌ Отмена"},
    "cleanup_menu": {
        "uk": "🗑 <b>Очистити сигнали</b>\n\nВидалити старі закриті сигнали з бази.\nОберіть що видалити:",
        "en": "🗑 <b>Cleanup Signals</b>\n\nDelete old closed signals from the database.\nChoose what to delete:",
        "ru": "🗑 <b>Очистить сигналы</b>\n\nУдалить старые закрытые сигналы из базы.\nВыберите что удалить:",
    },
    "cleanup_confirm": {
        "uk": "⚠️ Ви впевнені? Буде видалено <b>{count}</b> сигналів зі статусом: <b>{status}</b>\n\nЦю дію неможливо скасувати!",
        "en": "⚠️ Are you sure? <b>{count}</b> signals with status <b>{status}</b> will be deleted.\n\nThis cannot be undone!",
        "ru": "⚠️ Вы уверены? Будет удалено <b>{count}</b> сигналов со статусом: <b>{status}</b>\n\nЭто действие нельзя отменить!",
    },
    "cleanup_done": {
        "uk": "✅ Видалено <b>{count}</b> сигналів.",
        "en": "✅ Deleted <b>{count}</b> signals.",
        "ru": "✅ Удалено <b>{count}</b> сигналов.",
    },
    "cleanup_nothing": {
        "uk": "ℹ️ Немає сигналів для видалення.",
        "en": "ℹ️ No signals to delete.",
        "ru": "ℹ️ Нет сигналов для удаления.",
    },
    "btn_my_subscription": {"uk": "Моя підписка", "en": "My subscription", "ru": "Моя подписка"},
    "btn_pay": {"uk": "Оплатити", "en": "Pay", "ru": "Оплатить"},
    "btn_check_payment": {"uk": "Перевірити оплату", "en": "Check payment", "ru": "Проверить оплату"},
    "btn_cancel": {"uk": "Скасувати", "en": "Cancel", "ru": "Отменить"},
    "btn_language": {"uk": "Мова", "en": "Language", "ru": "Язык"},
    "btn_notifications": {"uk": "Сповіщення", "en": "Notifications", "ru": "Уведомления"},
    "btn_api_key": {"uk": "API ключ", "en": "API Key", "ru": "API ключ"},
    "btn_generate_key": {"uk": "Створити ключ", "en": "Generate Key", "ru": "Создать ключ"},
    "btn_regenerate_key": {"uk": "Перегенерувати", "en": "Regenerate", "ru": "Перегенерировать"},
    "btn_revoke_key": {"uk": "Відкликати ключ", "en": "Revoke Key", "ru": "Отозвать ключ"},
    "api_key_none": {
        "uk": "🔑 <b>API ключ для додатку</b>\n\nУ вас поки немає ключа.\nСтворіть його, щоб підключити десктоп-додаток BLACK ROOM.",
        "en": "🔑 <b>API Key for App</b>\n\nYou don't have a key yet.\nGenerate one to connect the BLACK ROOM desktop app.",
        "ru": "🔑 <b>API ключ для приложения</b>\n\nУ вас пока нет ключа.\nСоздайте его, чтобы подключить десктоп-приложение BLACK ROOM.",
    },
    "api_key_info": {
        "uk": "🔑 <b>Ваш API ключ</b>\n\nКлюч: <code>{prefix}••••••••</code>\nСтворено: {created}\nОстаннє використання: {last_used}\n\n⚠️ Не діліться ключем з іншими!",
        "en": "🔑 <b>Your API Key</b>\n\nKey: <code>{prefix}••••••••</code>\nCreated: {created}\nLast used: {last_used}\n\n⚠️ Never share your key with others!",
        "ru": "🔑 <b>Ваш API ключ</b>\n\nКлюч: <code>{prefix}••••••••</code>\nСоздан: {created}\nПоследнее использование: {last_used}\n\n⚠️ Не делитесь ключом с другими!",
    },
    "api_key_created": {
        "uk": "✅ <b>Ключ створено!</b>\n\n<code>{api_key}</code>\n\n⚠️ Скопіюйте його зараз — він більше не буде показаний!\nВставте його в десктоп-додатку BLACK ROOM.",
        "en": "✅ <b>Key Generated!</b>\n\n<code>{api_key}</code>\n\n⚠️ Copy it now — it won't be shown again!\nPaste it in the BLACK ROOM desktop app.",
        "ru": "✅ <b>Ключ создан!</b>\n\n<code>{api_key}</code>\n\n⚠️ Скопируйте его сейчас — он больше не будет показан!\nВставьте его в десктоп-приложении BLACK ROOM.",
    },
    "api_key_revoked": {
        "uk": "🗑 Ключ відкликано. Десктоп-додаток більше не матиме доступу.",
        "en": "🗑 Key revoked. Desktop app will no longer have access.",
        "ru": "🗑 Ключ отозван. Десктоп-приложение больше не будет иметь доступа.",
    },

    # ─── Stats labels ─────────────────────────────────────
    "total_signals": {"uk": "Всього сигналів", "en": "Total signals", "ru": "Всего сигналов"},
    "wins": {"uk": "Прибуткових", "en": "Wins", "ru": "Прибыльных"},
    "losses": {"uk": "Збиткових", "en": "Losses", "ru": "Убыточных"},
    "active": {"uk": "Активних", "en": "Active", "ru": "Активных"},
    "total_pnl": {"uk": "Загальний PnL", "en": "Total PnL", "ru": "Общий PnL"},
    "avg_win": {"uk": "Середній виграш", "en": "Avg win", "ru": "Средний профит"},
    "avg_loss": {"uk": "Середній збиток", "en": "Avg loss", "ru": "Средний убыток"},
    "win_streak": {"uk": "Серія перемог", "en": "Win streak", "ru": "Серия побед"},
    "loss_streak": {"uk": "Серія поразок", "en": "Loss streak", "ru": "Серия проигрышей"},
    "avg_holding": {"uk": "Середній час", "en": "Avg time", "ru": "Среднее время"},
    "total": {"uk": "Всього", "en": "Total", "ru": "Всего"},
    "best_trade": {"uk": "Найкращий трейд", "en": "Best trade", "ru": "Лучший трейд"},
    "worst_trade": {"uk": "Найгірший трейд", "en": "Worst trade", "ru": "Худший трейд"},
    "no_wallets": {"uk": "💼 У вас немає гаманців. Додайте через ➕.", "en": "💼 No wallets yet. Add one.", "ru": "💼 Кошельков нет. Добавьте через ➕."},
    "my_wallets_header": {"uk": "Мої гаманці", "en": "My Wallets", "ru": "Мои кошельки"},
    "wallet_add_prompt": {"uk": "📝 Надішліть адресу гаманця:", "en": "📝 Send your wallet address:", "ru": "📝 Отправьте адрес кошелька:"},
    "no_data": {"uk": "📊 Немає даних за цей період.", "en": "📊 No data for this period.", "ru": "📊 Нет данных за этот период."},
    "no_api_key": {"uk": "Ключ не створено. Натисніть кнопку нижче.", "en": "No key created yet. Press below.", "ru": "Ключ не создан. Нажмите ниже."},
    "api_key_active": {"uk": "✅ Ключ активний", "en": "✅ Key is active", "ru": "✅ Ключ активен"},
    "expires": {"uk": "Діє до", "en": "Expires", "ru": "Действителен до"},
    "tier": {"uk": "Тариф", "en": "Tier", "ru": "Тариф"},

    # ─── Admin panel ──────────────────────────────────────
    "admin_panel_title": {
        "uk": "🔧 <b>Адмін-панель</b>",
        "en": "🔧 <b>Admin Panel</b>",
        "ru": "🔧 <b>Админ-панель</b>",
    },
    "admin_access_denied": {
        "uk": "⛔ Доступ заборонено",
        "en": "⛔ Access denied",
        "ru": "⛔ Доступ запрещён",
    },
    "admin_stats_title": {
        "uk": "🔧 <b>Статистика системи</b>",
        "en": "🔧 <b>System Stats</b>",
        "ru": "🔧 <b>Статистика системы</b>",
    },
    "admin_users_title": {
        "uk": "👥 <b>Останні користувачі</b>",
        "en": "👥 <b>Recent Users</b>",
        "ru": "👥 <b>Последние пользователи</b>",
    },
    "admin_ai_title": {
        "uk": "🧠 <b>Стан AI системи</b>",
        "en": "🧠 <b>AI System Health</b>",
        "ru": "🧠 <b>Состояние AI системы</b>",
    },
    "admin_ai_error": {
        "uk": "❌ Помилка перевірки AI: {error}",
        "en": "❌ AI health check failed: {error}",
        "ru": "❌ Ошибка проверки AI: {error}",
    },
    "admin_scan_started": {
        "uk": "🔄 Сканування запущено...",
        "en": "🔄 Scan started...",
        "ru": "🔄 Сканирование запущено...",
    },
    "admin_scan_complete": {
        "uk": "✅ Сканування завершено. Знайдено <b>{count}</b> нових сигналів.",
        "en": "✅ Scan complete. Found <b>{count}</b> new signals.",
        "ru": "✅ Сканирование завершено. Найдено <b>{count}</b> новых сигналов.",
    },
    "admin_scan_error": {
        "uk": "❌ Помилка сканування: {error}",
        "en": "❌ Scan error: {error}",
        "ru": "❌ Ошибка сканирования: {error}",
    },
    "admin_broadcast_title": {
        "uk": "📨 <b>Розсилка</b>\n\nНадішліть /broadcast &lt;повідомлення&gt; для розсилки всім користувачам.",
        "en": "📨 <b>Broadcast</b>\n\nSend /broadcast &lt;message&gt; to broadcast to all users.",
        "ru": "📨 <b>Рассылка</b>\n\nОтправьте /broadcast &lt;сообщение&gt; для рассылки всем пользователям.",
    },
    "admin_total_users": {"uk": "Всього користувачів", "en": "Total users", "ru": "Всего пользователей"},
    "admin_active_signals": {"uk": "Активних сигналів", "en": "Active signals", "ru": "Активных сигналов"},
    "admin_ai_health": {"uk": "Стан AI", "en": "AI Health", "ru": "Состояние AI"},
    "admin_ai_unavailable": {"uk": "недоступний", "en": "unavailable", "ru": "недоступен"},
    "admin_win_rate": {"uk": "Вінрейт", "en": "Win Rate", "ru": "Винрейт"},
    "admin_min_confidence": {"uk": "Мін. впевненість", "en": "Min Confidence", "ru": "Мин. уверенность"},

    # ─── Admin buttons ────────────────────────────────────
    "admin_btn_stats": {"uk": "📊 Статистика", "en": "📊 System Stats", "ru": "📊 Статистика"},
    "admin_btn_users": {"uk": "👥 Користувачі", "en": "👥 Users", "ru": "👥 Пользователи"},
    "admin_btn_scan": {"uk": "📡 Сканувати", "en": "📡 Force Scan", "ru": "📡 Сканировать"},
    "admin_btn_ai": {"uk": "🧠 AI Стан", "en": "🧠 AI Health", "ru": "🧠 AI Состояние"},
    "admin_btn_broadcast": {"uk": "📨 Розсилка", "en": "📨 Broadcast", "ru": "📨 Рассылка"},

    # ─── Choose language ──────────────────────────────────
    "choose_language": {
        "uk": "🌐 Оберіть мову:",
        "en": "🌐 Choose language:",
        "ru": "🌐 Выберите язык:",
    },

    # ─── Alerts ───────────────────────────────────────────
    "alerts_menu": {
        "uk": "🔔 <b>Алерти</b>\n\nАктивних: <b>{active}</b> / {limit}\n\nОберіть дію:",
        "en": "🔔 <b>Alerts</b>\n\nActive: <b>{active}</b> / {limit}\n\nChoose an action:",
        "ru": "🔔 <b>Алерты</b>\n\nАктивных: <b>{active}</b> / {limit}\n\nВыберите действие:",
    },
    "alerts_empty": {
        "uk": "📭 У вас немає алертів.\n\nНатисніть <b>➕ Створити</b> щоб додати перший!",
        "en": "📭 You have no alerts.\n\nTap <b>➕ Create</b> to add your first!",
        "ru": "📭 У вас нет алертов.\n\nНажмите <b>➕ Создать</b> чтобы добавить первый!",
    },
    "alerts_list_header": {
        "uk": "📋 <b>Ваші алерти:</b>\n",
        "en": "📋 <b>Your alerts:</b>\n",
        "ru": "📋 <b>Ваши алерты:</b>\n",
    },
    "alert_list_row": {
        "uk": "{status} <b>{coin}</b> — {type_name} {params_str}",
        "en": "{status} <b>{coin}</b> — {type_name} {params_str}",
        "ru": "{status} <b>{coin}</b> — {type_name} {params_str}",
    },
    "alert_choose_coin": {
        "uk": "🪙 Введіть символ монети (наприклад <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
        "en": "🪙 Enter coin symbol (e.g. <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
        "ru": "🪙 Введите символ монеты (например <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
    },
    "alert_choose_type": {
        "uk": "📋 Обрано: <b>{coin}</b>\n\nОберіть тип алерту:",
        "en": "📋 Selected: <b>{coin}</b>\n\nChoose alert type:",
        "ru": "📋 Выбрано: <b>{coin}</b>\n\nВыберите тип алерта:",
    },
    "alert_enter_price": {
        "uk": "💰 Введіть ціну (USD):",
        "en": "💰 Enter price (USD):",
        "ru": "💰 Введите цену (USD):",
    },
    "alert_enter_percent": {
        "uk": "📊 Введіть порогове значення у %:",
        "en": "📊 Enter threshold in %:",
        "ru": "📊 Введите пороговое значение в %:",
    },
    "alert_enter_range": {
        "uk": "📏 Введіть діапазон через пробіл: <code>мін макс</code>\n(наприклад <code>60000 70000</code>):",
        "en": "📏 Enter range separated by space: <code>min max</code>\n(e.g. <code>60000 70000</code>):",
        "ru": "📏 Введите диапазон через пробел: <code>мин макс</code>\n(например <code>60000 70000</code>):",
    },
    "alert_enter_rsi": {
        "uk": "📈 Введіть рівень RSI (1-99):",
        "en": "📈 Enter RSI level (1-99):",
        "ru": "📈 Введите уровень RSI (1-99):",
    },
    "alert_enter_funding": {
        "uk": "💸 Введіть порогове значення funding rate (наприклад <code>0.1</code>):",
        "en": "💸 Enter funding rate threshold (e.g. <code>0.1</code>):",
        "ru": "💸 Введите пороговое значение funding rate (например <code>0.1</code>):",
    },
    "alert_created": {
        "uk": "✅ Алерт створено!\n\n🪙 <b>{coin}</b>\n📋 {type_name}\n📌 {params_str}\n\nВи отримаєте сповіщення, коли умова буде виконана.",
        "en": "✅ Alert created!\n\n🪙 <b>{coin}</b>\n📋 {type_name}\n📌 {params_str}\n\nYou'll be notified when the condition is met.",
        "ru": "✅ Алерт создан!\n\n🪙 <b>{coin}</b>\n📋 {type_name}\n📌 {params_str}\n\nВы получите уведомление, когда условие будет выполнено.",
    },
    "alert_limit_reached": {
        "uk": "🔒 Досягнуто ліміт алертів (<b>{limit}</b>).\n\nОновіть тариф для більше алертів → /subscribe",
        "en": "🔒 Alert limit reached (<b>{limit}</b>).\n\nUpgrade your plan for more alerts → /subscribe",
        "ru": "🔒 Достигнут лимит алертов (<b>{limit}</b>).\n\nУлучшите тариф для бо́льшего числа алертов → /subscribe",
    },
    "alert_type_locked": {
        "uk": "🔒 Цей тип алерту доступний з тарифу <b>{tier}</b>+\n\n💎 /subscribe",
        "en": "🔒 This alert type is available from <b>{tier}</b>+ plan\n\n💎 /subscribe",
        "ru": "🔒 Этот тип алерта доступен с тарифа <b>{tier}</b>+\n\n💎 /subscribe",
    },
    "alert_deleted": {
        "uk": "🗑 Алерт видалено.",
        "en": "🗑 Alert deleted.",
        "ru": "🗑 Алерт удалён.",
    },
    "alert_detail": {
        "uk": (
            "🔔 <b>Алерт #{alert_id}</b>\n\n"
            "🪙 Монета: <b>{coin}</b>\n"
            "📋 Тип: {type_name}\n"
            "📌 Параметри: {params_str}\n"
            "📊 Статус: {status}\n"
            "🔁 Спрацювань: {triggered_count}\n"
            "⏱ Кулдаун: {cooldown} хв"
        ),
        "en": (
            "🔔 <b>Alert #{alert_id}</b>\n\n"
            "🪙 Coin: <b>{coin}</b>\n"
            "📋 Type: {type_name}\n"
            "📌 Parameters: {params_str}\n"
            "📊 Status: {status}\n"
            "🔁 Triggers: {triggered_count}\n"
            "⏱ Cooldown: {cooldown} min"
        ),
        "ru": (
            "🔔 <b>Алерт #{alert_id}</b>\n\n"
            "🪙 Монета: <b>{coin}</b>\n"
            "📋 Тип: {type_name}\n"
            "📌 Параметры: {params_str}\n"
            "📊 Статус: {status}\n"
            "🔁 Срабатываний: {triggered_count}\n"
            "⏱ Кулдаун: {cooldown} мин"
        ),
    },
    "alert_invalid_input": {
        "uk": "❌ Невірне значення. Спробуйте ще.",
        "en": "❌ Invalid value. Try again.",
        "ru": "❌ Неверное значение. Попробуйте снова.",
    },
    "alert_coin_not_found": {
        "uk": "❌ Монету <b>{coin}</b> не знайдено. Перевірте символ.",
        "en": "❌ Coin <b>{coin}</b> not found. Check the symbol.",
        "ru": "❌ Монета <b>{coin}</b> не найдена. Проверьте символ.",
    },

    # ─── Alert type names ─────────────────────────────────
    "alert.type_price_above": {"uk": "📈 Ціна вище", "en": "📈 Price above", "ru": "📈 Цена выше"},
    "alert.type_price_below": {"uk": "📉 Ціна нижче", "en": "📉 Price below", "ru": "📉 Цена ниже"},
    "alert.type_change_1h": {"uk": "⏱ Зміна за 1г", "en": "⏱ 1h change", "ru": "⏱ Изменение за 1ч"},
    "alert.type_change_24h": {"uk": "📅 Зміна за 24г", "en": "📅 24h change", "ru": "📅 Изменение за 24ч"},
    "alert.type_volume_spike": {"uk": "📊 Сплеск обсягу", "en": "📊 Volume spike", "ru": "📊 Всплеск объёма"},
    "alert.type_rsi_overbought": {"uk": "🔴 RSI перекуплено", "en": "🔴 RSI overbought", "ru": "🔴 RSI перекуплен"},
    "alert.type_rsi_oversold": {"uk": "🟢 RSI перепродано", "en": "🟢 RSI oversold", "ru": "🟢 RSI перепродан"},
    "alert.type_macd_cross": {"uk": "✖️ MACD перетин", "en": "✖️ MACD cross", "ru": "✖️ MACD пересечение"},
    "alert.type_bb_breakout": {"uk": "💥 BB пробій", "en": "💥 BB breakout", "ru": "💥 BB пробой"},
    "alert.type_new_ath": {"uk": "🏔 Новий ATH", "en": "🏔 New ATH", "ru": "🏔 Новый ATH"},
    "alert.type_new_atl": {"uk": "🕳 Новий ATL", "en": "🕳 New ATL", "ru": "🕳 Новый ATL"},
    "alert.type_funding_rate": {"uk": "💸 Funding Rate", "en": "💸 Funding Rate", "ru": "💸 Funding Rate"},
    "alert.type_correlation_break": {"uk": "🔗 Кореляція", "en": "🔗 Correlation", "ru": "🔗 Корреляция"},
    "alert.type_support_hit": {"uk": "🛡 Підтримка", "en": "🛡 Support hit", "ru": "🛡 Поддержка"},
    "alert.type_resistance_hit": {"uk": "🧱 Опір", "en": "🧱 Resistance hit", "ru": "🧱 Сопротивление"},
    "alert.type_custom_range": {"uk": "📏 Діапазон", "en": "📏 Custom range", "ru": "📏 Диапазон"},

    # ─── Alert trigger notification messages ──────────────
    "alert.triggered_header": {
        "uk": "🔔 <b>АЛЕРТ СПРАЦЮВАВ!</b>",
        "en": "🔔 <b>ALERT TRIGGERED!</b>",
        "ru": "🔔 <b>АЛЕРТ СРАБОТАЛ!</b>",
    },
    "alert.price_hit_body": {
        "uk": "🪙 <b>{coin}</b> досяг {target}\n💰 Поточна ціна: {price}",
        "en": "🪙 <b>{coin}</b> reached {target}\n💰 Current price: {price}",
        "ru": "🪙 <b>{coin}</b> достиг {target}\n💰 Текущая цена: {price}",
    },
    "alert.change_body": {
        "uk": "🪙 <b>{coin}</b> змінився на {change}",
        "en": "🪙 <b>{coin}</b> changed by {change}",
        "ru": "🪙 <b>{coin}</b> изменился на {change}",
    },
    "alert.rsi_body": {
        "uk": "🪙 <b>{coin}</b> — RSI: {rsi}",
        "en": "🪙 <b>{coin}</b> — RSI: {rsi}",
        "ru": "🪙 <b>{coin}</b> — RSI: {rsi}",
    },
    "alert.bb_body": {
        "uk": "🪙 <b>{coin}</b> пробив Bollinger Band ({direction})\n💰 Ціна: {price}",
        "en": "🪙 <b>{coin}</b> broke Bollinger Band ({direction})\n💰 Price: {price}",
        "ru": "🪙 <b>{coin}</b> пробил Bollinger Band ({direction})\n💰 Цена: {price}",
    },
    "alert.funding_body": {
        "uk": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
        "en": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
        "ru": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
    },
    "alert.level_body": {
        "uk": "🪙 <b>{coin}</b> біля рівня {level}\n💰 Ціна: {price}",
        "en": "🪙 <b>{coin}</b> near level {level}\n💰 Price: {price}",
        "ru": "🪙 <b>{coin}</b> у уровня {level}\n💰 Цена: {price}",
    },
    "alert.macd_body": {
        "uk": "🪙 <b>{coin}</b> — MACD перетин: {cross}",
        "en": "🪙 <b>{coin}</b> — MACD cross: {cross}",
        "ru": "🪙 <b>{coin}</b> — MACD пересечение: {cross}",
    },
    "alert.ath_body": {
        "uk": "🪙 <b>{coin}</b> 🚀 Новий ATH!\n💰 Ціна: {price} (попередній: {ath})",
        "en": "🪙 <b>{coin}</b> 🚀 New ATH!\n💰 Price: {price} (previous: {ath})",
        "ru": "🪙 <b>{coin}</b> 🚀 Новый ATH!\n💰 Цена: {price} (предыдущий: {ath})",
    },
    "alert.atl_body": {
        "uk": "🪙 <b>{coin}</b> 📉 Новий ATL!\n💰 Ціна: {price} (попередній: {atl})",
        "en": "🪙 <b>{coin}</b> 📉 New ATL!\n💰 Price: {price} (previous: {atl})",
        "ru": "🪙 <b>{coin}</b> 📉 Новый ATL!\n💰 Цена: {price} (предыдущий: {atl})",
    },
    "alert.generic_body": {
        "uk": "🪙 <b>{coin}</b>\n💰 Ціна: {price}",
        "en": "🪙 <b>{coin}</b>\n💰 Price: {price}",
        "ru": "🪙 <b>{coin}</b>\n💰 Цена: {price}",
    },

    # ─── Alert button labels ──────────────────────────────
    "btn_alerts": {"uk": "🔔 Алерти", "en": "🔔 Alerts", "ru": "🔔 Алерты"},
    "btn_watchlist": {"uk": "⭐ Обране", "en": "⭐ Watchlist", "ru": "⭐ Избранное"},
    "btn_create_alert": {"uk": "➕ Створити", "en": "➕ Create", "ru": "➕ Создать"},
    "btn_my_alerts": {"uk": "📋 Мої алерти", "en": "📋 My alerts", "ru": "📋 Мои алерты"},
    "btn_delete_alert": {"uk": "🗑 Видалити", "en": "🗑 Delete", "ru": "🗑 Удалить"},
    "btn_toggle_alert": {"uk": "⏸ Пауза / ▶️ Увімк.", "en": "⏸ Pause / ▶️ Enable", "ru": "⏸ Пауза / ▶️ Вкл."},

    # ─── Watchlist ────────────────────────────────────────
    "watchlist_menu": {
        "uk": "⭐ <b>Обране</b>\n\nВаші відстежувані монети:",
        "en": "⭐ <b>Watchlist</b>\n\nYour tracked coins:",
        "ru": "⭐ <b>Избранное</b>\n\nВаши отслеживаемые монеты:",
    },
    "watchlist_empty": {
        "uk": "📭 Список обраного порожній.\n\nДодайте монету кнопкою <b>➕ Додати</b>.",
        "en": "📭 Watchlist is empty.\n\nAdd a coin with <b>➕ Add</b> button.",
        "ru": "📭 Избранное пусто.\n\nДобавьте монету кнопкой <b>➕ Добавить</b>.",
    },
    "watchlist_add_prompt": {
        "uk": "🪙 Введіть символ монети для додавання (наприклад <code>BTC</code>):",
        "en": "🪙 Enter coin symbol to add (e.g. <code>BTC</code>):",
        "ru": "🪙 Введите символ монеты для добавления (например <code>BTC</code>):",
    },
    "watchlist_added": {
        "uk": "✅ <b>{coin}</b> додано до обраного!",
        "en": "✅ <b>{coin}</b> added to watchlist!",
        "ru": "✅ <b>{coin}</b> добавлен в избранное!",
    },
    "watchlist_removed": {
        "uk": "🗑 <b>{coin}</b> видалено з обраного.",
        "en": "🗑 <b>{coin}</b> removed from watchlist.",
        "ru": "🗑 <b>{coin}</b> удалён из избранного.",
    },
    "watchlist_already_exists": {
        "uk": "⚠️ <b>{coin}</b> вже в обраному.",
        "en": "⚠️ <b>{coin}</b> is already in watchlist.",
        "ru": "⚠️ <b>{coin}</b> уже в избранном.",
    },
    "watchlist_row": {
        "uk": "• <b>{coin}</b> — ${price} ({change_24h}%)",
        "en": "• <b>{coin}</b> — ${price} ({change_24h}%)",
        "ru": "• <b>{coin}</b> — ${price} ({change_24h}%)",
    },
    "btn_add_watchlist": {"uk": "➕ Додати", "en": "➕ Add", "ru": "➕ Добавить"},
    "btn_remove_watchlist": {"uk": "🗑 Видалити", "en": "🗑 Remove", "ru": "🗑 Удалить"},

    # ─── Alert status labels ─────────────────────────────
    "alert_status_active": {"uk": "🟢 Активний", "en": "🟢 Active", "ru": "🟢 Активен"},
    "alert_status_paused": {"uk": "⏸ Пауза", "en": "⏸ Paused", "ru": "⏸ Пауза"},
    "alert_status_triggered": {"uk": "✅ Спрацював", "en": "✅ Triggered", "ru": "✅ Сработал"},

    # ─── Stats extra labels ───────────────────────────────
    "win_rate": {"uk": "Вінрейт", "en": "Win Rate", "ru": "Винрейт"},
    "tp1_rate": {"uk": "TP1 Rate", "en": "TP1 Rate", "ru": "TP1 Rate"},
    "tp2_rate": {"uk": "TP2 Rate", "en": "TP2 Rate", "ru": "TP2 Rate"},
    "tp3_rate": {"uk": "TP3 Rate", "en": "TP3 Rate", "ru": "TP3 Rate"},
    "profit_factor": {"uk": "Profit Factor", "en": "Profit Factor", "ru": "Profit Factor"},
    "sharpe_ratio": {"uk": "Sharpe", "en": "Sharpe", "ru": "Sharpe"},
    "sortino_ratio": {"uk": "Sortino", "en": "Sortino", "ru": "Sortino"},
    "max_drawdown": {"uk": "Макс. просадка", "en": "Max DD", "ru": "Макс. просадка"},
    "longs_label": {"uk": "Лонги", "en": "Longs", "ru": "Лонги"},
    "shorts_label": {"uk": "Шорти", "en": "Shorts", "ru": "Шорты"},

    # ─── Duration labels ──────────────────────────────────
    "month_short": {"uk": "міс", "en": "mo", "ru": "мес"},

    # ─── Wallet Tracker ──────────────────────────────────
    "btn_wallets": {
        "uk": "💼 Гаманці",
        "en": "💼 Wallets",
        "ru": "💼 Кошельки",
    },
    "btn_my_wallets": {
        "uk": "Мої гаманці",
        "en": "My Wallets",
        "ru": "Мои кошельки",
    },
    "btn_add_wallet": {
        "uk": "Додати гаманець",
        "en": "Add Wallet",
        "ru": "Добавить кошелёк",
    },
    "btn_wallet_portfolio": {
        "uk": "Портфель",
        "en": "Portfolio",
        "ru": "Портфель",
    },
    "btn_wallet_txs": {
        "uk": "Транзакції",
        "en": "Transactions",
        "ru": "Транзакции",
    },
    "btn_wallet_analysis": {
        "uk": "AI Аналітика",
        "en": "AI Analytics",
        "ru": "AI Аналитика",
    },
    "btn_wallet_remove": {
        "uk": "Видалити",
        "en": "Remove",
        "ru": "Удалить",
    },
    "wallet_menu": {
        "uk": "💼 <b>Трекінг гаманців</b>\n\nВідстежуйте свої блокчейн-гаманці в реальному часі.\nАктивних: {count}/{limit}",
        "en": "💼 <b>Wallet Tracker</b>\n\nTrack your blockchain wallets in real-time.\nActive: {count}/{limit}",
        "ru": "💼 <b>Трекинг кошельков</b>\n\nОтслеживайте свои блокчейн-кошельки в реальном времени.\nАктивных: {count}/{limit}",
    },
    "wallet_empty": {
        "uk": "У вас ще немає відстежуваних гаманців.\nНатисніть ➕ щоб додати.",
        "en": "You have no tracked wallets yet.\nPress ➕ to add one.",
        "ru": "У вас пока нет отслеживаемых кошельков.\nНажмите ➕ чтобы добавить.",
    },
    "wallet_list_header": {
        "uk": "📋 <b>Ваші гаманці</b> ({count}):",
        "en": "📋 <b>Your wallets</b> ({count}):",
        "ru": "📋 <b>Ваши кошельки</b> ({count}):",
    },
    "wallet_limit_reached": {
        "uk": "⚠️ Досягнуто ліміт {limit} гаманців (тір {tier}).\nОновіть підписку для більше.",
        "en": "⚠️ Wallet limit reached ({limit}, tier {tier}).\nUpgrade for more.",
        "ru": "⚠️ Лимит {limit} кошельков (тир {tier}).\nОбновите подписку.",
    },
    "wallet_enter_address": {
        "uk": "📍 Введіть адресу гаманця:\n\nПідтримуються: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron",
        "en": "📍 Enter wallet address:\n\nSupported: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron",
        "ru": "📍 Введите адрес кошелька:\n\nПоддерживаются: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron",
    },
    "wallet_invalid_address": {
        "uk": "❌ Невірний формат адреси. Спробуйте ще раз.",
        "en": "❌ Invalid address format. Try again.",
        "ru": "❌ Неверный формат адреса. Попробуйте снова.",
    },
    "wallet_unknown_chain": {
        "uk": "❌ Не вдалося визначити мережу. Перевірте адресу.",
        "en": "❌ Could not detect chain. Check the address.",
        "ru": "❌ Не удалось определить сеть. Проверьте адрес.",
    },
    "wallet_select_chain": {
        "uk": "🔗 Оберіть мережу для цієї EVM адреси:",
        "en": "🔗 Select chain for this EVM address:",
        "ru": "🔗 Выберите сеть для этого EVM адреса:",
    },
    "wallet_invalid_chain": {
        "uk": "❌ Невірна мережа.",
        "en": "❌ Invalid chain.",
        "ru": "❌ Неверная сеть.",
    },
    "wallet_enter_label": {
        "uk": "🏷 Введіть назву для гаманця (або <b>-</b> щоб пропустити):",
        "en": "🏷 Enter a label for the wallet (or <b>-</b> to skip):",
        "ru": "🏷 Введите название кошелька (или <b>-</b> чтобы пропустить):",
    },
    "wallet_added": {
        "uk": "✅ Гаманець <b>{label}</b> [{chain}] додано!\nПерше сканування почнеться автоматично.",
        "en": "✅ Wallet <b>{label}</b> [{chain}] added!\nFirst scan will start automatically.",
        "ru": "✅ Кошелёк <b>{label}</b> [{chain}] добавлен!\nПервое сканирование начнётся автоматически.",
    },
    "wallet_removed": {
        "uk": "🗑 Гаманець видалено.",
        "en": "🗑 Wallet removed.",
        "ru": "🗑 Кошелёк удалён.",
    },
    "wallet_not_found": {
        "uk": "❌ Гаманець не знайдено.",
        "en": "❌ Wallet not found.",
        "ru": "❌ Кошелёк не найден.",
    },
    "wallet_err_unknown_chain": {
        "uk": "❌ Не вдалося визначити мережу.",
        "en": "❌ Could not detect chain.",
        "ru": "❌ Не удалось определить сеть.",
    },
    "wallet_err_user_not_found": {
        "uk": "❌ Користувача не знайдено.",
        "en": "❌ User not found.",
        "ru": "❌ Пользователь не найден.",
    },
    "wallet_err_limit_reached": {
        "uk": "⚠️ Досягнуто ліміт гаманців. Оновіть підписку.",
        "en": "⚠️ Wallet limit reached. Upgrade your subscription.",
        "ru": "⚠️ Лимит кошельков. Обновите подписку.",
    },
    "wallet_err_already_tracked": {
        "uk": "ℹ️ Цей гаманець вже відстежується.",
        "en": "ℹ️ This wallet is already tracked.",
        "ru": "ℹ️ Этот кошелёк уже отслеживается.",
    },
    "wallet_error": {
        "uk": "❌ Помилка. Спробуйте ще раз.",
        "en": "❌ Error. Try again.",
        "ru": "❌ Ошибка. Попробуйте снова.",
    },
    "wallet_portfolio_empty": {
        "uk": "📊 Портфель порожній — токенів не знайдено.",
        "en": "📊 Portfolio empty — no tokens found.",
        "ru": "📊 Портфель пуст — токенов не найдено.",
    },
    "wallet_pro_required": {
        "uk": "🔒 Ця функція доступна з PRO підписки.",
        "en": "🔒 This feature requires PRO subscription.",
        "ru": "🔒 Эта функция доступна с PRO подписки.",
    },
    "wallet_no_txs": {
        "uk": "📝 Транзакцій поки не знайдено.",
        "en": "📝 No transactions found yet.",
        "ru": "📝 Транзакции пока не найдены.",
    },
    "wallet_analyzing": {
        "uk": "🤖 Аналізую портфель...",
        "en": "🤖 Analyzing portfolio...",
        "ru": "🤖 Анализирую портфель...",
    },
    "wallet_analysis_failed": {
        "uk": "❌ Не вдалося згенерувати аналітику. Спробуйте пізніше.",
        "en": "❌ Failed to generate analysis. Try later.",
        "ru": "❌ Не удалось сгенерировать аналитику. Попробуйте позже.",
    },

    # ─── Signal DM Delivery ───────────────────────────────
    "signal_dm_caption": {
        "uk": (
            "📡 <b>Новий сигнал!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | 💪 {confidence}%\n\n"
            "Натисніть кнопки нижче для деталей."
        ),
        "en": (
            "📡 <b>New Signal!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | 💪 {confidence}%\n\n"
            "Tap buttons below for details."
        ),
        "ru": (
            "📡 <b>Новый сигнал!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | 💪 {confidence}%\n\n"
            "Нажмите кнопки ниже для деталей."
        ),
    },
    "signal_dm_caption_free": {
        "uk": (
            "📡 <b>Новий сигнал!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "🎯 Потенціал: +{potential}%\n\n"
            "🔒 Точні рівні доступні на Pro/Elite"
        ),
        "en": (
            "📡 <b>New Signal!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "🎯 Potential: +{potential}%\n\n"
            "🔒 Exact levels available on Pro/Elite"
        ),
        "ru": (
            "📡 <b>Новый сигнал!</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "🎯 Потенциал: +{potential}%\n\n"
            "🔒 Точные уровни доступны на Pro/Elite"
        ),
    },
    "signal_dm_detail": {
        "uk": (
            "🔍 <b>Деталі сигналу #{signal_id}</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Вхід: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 AI Впевненість: {confidence}%\n"
            "⚡ Плече: x{leverage}"
        ),
        "en": (
            "🔍 <b>Signal Details #{signal_id}</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Entry: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 AI Confidence: {confidence}%\n"
            "⚡ Leverage: x{leverage}"
        ),
        "ru": (
            "🔍 <b>Детали сигнала #{signal_id}</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Вход: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 Уверенность AI: {confidence}%\n"
            "⚡ Плечо: x{leverage}"
        ),
    },
    "signal_dm_detail_elite": {
        "uk": (
            "👑 <b>Сигнал #{signal_id} — Elite</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Вхід: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 AI Впевненість: {confidence}%\n"
            "⚡ Плече: x{leverage}\n\n"
            "🧠 <b>AI Аналіз:</b>\n<i>{reasoning}</i>"
        ),
        "en": (
            "👑 <b>Signal #{signal_id} — Elite</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Entry: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 AI Confidence: {confidence}%\n"
            "⚡ Leverage: x{leverage}\n\n"
            "🧠 <b>AI Analysis:</b>\n<i>{reasoning}</i>"
        ),
        "ru": (
            "👑 <b>Сигнал #{signal_id} — Elite</b>\n\n"
            "🪙 <b>{coin}</b> {direction}\n"
            "📊 {exchange} | ⏰ {timeframe}\n\n"
            "▫️ Вход: <code>${entry}</code>\n"
            "🎯 TP1: <code>${tp1}</code> ({tp1_pct})\n"
            "🎯 TP2: <code>${tp2}</code>\n"
            "🎯 TP3: <code>${tp3}</code>\n"
            "🛑 SL: <code>${sl}</code> ({sl_pct})\n\n"
            "📏 R:R — {rr}\n"
            "💪 Уверенность AI: {confidence}%\n"
            "⚡ Плечо: x{leverage}\n\n"
            "🧠 <b>AI Анализ:</b>\n<i>{reasoning}</i>"
        ),
    },

    # Signal interaction responses
    "signal_activated": {
        "uk": "✅ <b>Сигнал активовано!</b>\n\nВи будете отримувати оновлення по цьому сигналу (TP/SL хіти).",
        "en": "✅ <b>Signal activated!</b>\n\nYou will receive updates for this signal (TP/SL hits).",
        "ru": "✅ <b>Сигнал активирован!</b>\n\nВы будете получать обновления по этому сигналу (TP/SL хиты).",
    },
    "signal_already_activated": {
        "uk": "ℹ️ Ви вже відстежуєте цей сигнал.",
        "en": "ℹ️ You're already tracking this signal.",
        "ru": "ℹ️ Вы уже отслеживаете этот сигнал.",
    },
    "signal_not_found": {
        "uk": "❌ Сигнал не знайдено або вже закрито.",
        "en": "❌ Signal not found or already closed.",
        "ru": "❌ Сигнал не найден или уже закрыт.",
    },
    "signal_dismissed": {
        "uk": "🗑 Сповіщення видалено.",
        "en": "🗑 Notification dismissed.",
        "ru": "🗑 Уведомление удалено.",
    },

    # Signal update notifications (sent to users who activated)
    "signal_update_tp_caption": {
        "uk": "🎯 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n💰 PnL: {pnl}\n\n📊 SL переміщено для захисту прибутку.",
        "en": "🎯 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n💰 PnL: {pnl}\n\n📊 SL moved to protect profits.",
        "ru": "🎯 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n💰 PnL: {pnl}\n\n📊 SL перемещён для защиты прибыли.",
    },
    "signal_update_final_caption": {
        "uk": "🏁 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n📊 Результат: {pnl}",
        "en": "🏁 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n📊 Result: {pnl}",
        "ru": "🏁 <b>{header}</b>\n\n🪙 {coin} #{signal_id}\n📊 Результат: {pnl}",
    },

    # Missed signal reminders
    "missed_signals_reminder": {
        "uk": (
            "⏰ <b>Пропущені сигнали</b>\n\n"
            "Ви пропустили <b>{count}</b> сигналів за останні години.\n"
            "Перегляньте активні сигнали, щоб не втратити можливість!"
        ),
        "en": (
            "⏰ <b>Missed Signals</b>\n\n"
            "You missed <b>{count}</b> signals in recent hours.\n"
            "Check active signals to not miss opportunities!"
        ),
        "ru": (
            "⏰ <b>Пропущенные сигналы</b>\n\n"
            "Вы пропустили <b>{count}</b> сигналов за последние часы.\n"
            "Просмотрите активные сигналы, чтобы не упустить возможность!"
        ),
    },

    # FREE channel delayed signal
    "channel_missed_signal": {
        "uk": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 Цей сигнал вже був відпрацьований\n"
            "🎯 Результат: <b>{result}</b>\n\n"
            "🔒 <i>Отримуйте сигнали в реальному часі з Pro/Elite</i>\n"
            "💎 @blackroomapp_bot → /subscribe"
        ),
        "en": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 This signal has already been played\n"
            "🎯 Result: <b>{result}</b>\n\n"
            "🔒 <i>Get real-time signals with Pro/Elite</i>\n"
            "💎 @blackroomapp_bot → /subscribe"
        ),
        "ru": (
            "📡 <b>{coin}</b> {direction}\n\n"
            "🕐 Этот сигнал уже был отработан\n"
            "🎯 Результат: <b>{result}</b>\n\n"
            "🔒 <i>Получайте сигналы в реальном времени с Pro/Elite</i>\n"
            "💎 @blackroomapp_bot → /subscribe"
        ),
    },

    # Button labels for signal notifications
    "btn_view_details": {"uk": "🔍 Деталі", "en": "🔍 Details", "ru": "🔍 Детали"},
    "btn_use_signal": {"uk": "✅ Використати", "en": "✅ Use Signal", "ru": "✅ Использовать"},
    "btn_dismiss": {"uk": "🗑 Приховати", "en": "🗑 Dismiss", "ru": "🗑 Скрыть"},
    "btn_subscribe_pro": {"uk": "💎 Підписатись", "en": "💎 Subscribe", "ru": "💎 Подписаться"},
    "btn_view_signal": {"uk": "📡 Переглянути", "en": "📡 View Signal", "ru": "📡 Просмотреть"},
    "btn_view_active": {"uk": "📡 Активні сигнали", "en": "📡 Active Signals", "ru": "📡 Активные сигналы"},

    "month_short": {"uk": "міс", "en": "mo", "ru": "мес"},
}


def t(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Get localized text by key and language, with placeholder formatting."""
    entry = _TEXTS.get(key)
    if entry is None:
        return f"[missing: {key}]"
    text = entry.get(lang, entry.get("en", f"[no lang: {key}]"))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def get_all_keys() -> list[str]:
    """Return all localization keys."""
    return list(_TEXTS.keys())
