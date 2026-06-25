"""
Trilingual localization system (Ukrainian / English / Russian / Arabic).
Every user-facing string goes through this module.
"""

from typing import Any

_TEXTS: dict[str, dict[str, str]] = {
    "start.welcome": {
        "uk": (
            """🚀 <b>Ласкаво просимо до BLACK ROOM!</b>

Найпотужніша AI-система торгових сигналів для криптовалют.

Оберіть мову / Choose your language:"""
        ),
        "en": (
            """🚀 <b>Welcome to BLACK ROOM!</b>

The most powerful AI-powered crypto trading signal system.

Choose your language:"""
        ),
        "ru": (
            """🚀 <b>Добро пожаловать в BLACK ROOM!</b>

Самая мощная AI-система торговых сигналов для криптовалют.

Выберите язык:"""
        ),
        "ar": (
            """🚀 <b>مرحبًا بك في BLACK ROOM!</b>

أقوى نظام إشارات تداول العملات المشفرة المدعوم بالذكاء الاصطناعي.

اختر لغتك:"""
        ),
    },
    "start.language_set": {
        "uk": "✅ Мову встановлено: <b>Українська</b>",
        "en": "✅ Language set: <b>English</b>",
        "ru": "✅ Язык установлен: <b>Русский</b>",
        "ar": "✅ لغة محددة: <b>الإنجليزية</b>",
    },
    "start.main_menu": {
        "uk": (
            """📊 <b>BLACK ROOM</b> — Головне меню

Ваш тариф: <b>{tier}</b>
Активних сигналів: <b>{active_signals}</b>

Оберіть дію:"""
        ),
        "en": (
            """📊 <b>BLACK ROOM</b> — Main Menu

Your plan: <b>{tier}</b>
Active signals: <b>{active_signals}</b>

Choose an action:"""
        ),
        "ru": (
            """📊 <b>BLACK ROOM</b> — Главное меню

Ваш тариф: <b>{tier}</b>
Активных сигналов: <b>{active_signals}</b>

Выберите действие:"""
        ),
        "ar": (
            """📊 <b>الغرفة السوداء</b> — القائمة الرئيسية

خطةك: <b>{tier}</b>
الإشارات النشطة: <b>{active_signals}</b>

اختر إجراء:"""
        ),
    },
    "tier.free": {
        "uk": "🆓 Free",
        "en": "🆓 Free",
        "ru": "🆓 Free",
        "ar": "🆓 Free",
    },
    "tier.pro": {
        "uk": "⭐ Pro",
        "en": "⭐ Pro",
        "ru": "⭐ Pro",
        "ar": "⭐ Pro",
    },
    "tier.elite": {
        "uk": "👑 Elite",
        "en": "👑 Elite",
        "ru": "👑 Elite",
        "ar": "👑 Elite",
    },
    "signal.new_title": {
        "uk": "🔔 <b>НОВИЙ СИГНАЛ</b>",
        "en": "🔔 <b>NEW SIGNAL</b>",
        "ru": "🔔 <b>НОВЫЙ СИГНАЛ</b>",
        "ar": "🔔 <b>إشارة جديدة</b>",
    },
    "signal.direction_long": {
        "uk": "🟢 LONG",
        "en": "🟢 LONG",
        "ru": "🟢 LONG",
        "ar": "🟢 LONG",
    },
    "signal.direction_short": {
        "uk": "🔴 SHORT",
        "en": "🔴 SHORT",
        "ru": "🔴 SHORT",
        "ar": "🔴 SHORT",
    },
    "signal.body": {
        "uk": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b> ({coin_name})
📊 Біржа: {exchange} | Пара: {pair}
⏰ Таймфрейм: {timeframe}

▫️ Вхід: <code>{entry_price}</code>
🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)
🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)
🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)
🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)

📏 R:R — {risk_reward}
🧠 Впевненість AI: {confidence}%
⚡ Плече: x{leverage}

📝 <i>{reasoning}</i>

🆔 #{signal_id}"""
        ),
        "en": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b> ({coin_name})
📊 Exchange: {exchange} | Pair: {pair}
⏰ Timeframe: {timeframe}

▫️ Entry: <code>{entry_price}</code>
🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)
🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)
🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)
🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)

📏 R:R — {risk_reward}
🧠 AI Confidence: {confidence}%
⚡ Leverage: x{leverage}

📝 <i>{reasoning}</i>

🆔 #{signal_id}"""
        ),
        "ru": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b> ({coin_name})
📊 Биржа: {exchange} | Пара: {pair}
⏰ Таймфрейм: {timeframe}

▫️ Вход: <code>{entry_price}</code>
🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)
🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)
🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)
🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)

📏 R:R — {risk_reward}
🧠 Уверенность AI: {confidence}%
⚡ Плечо: x{leverage}

📝 <i>{reasoning}</i>

🆔 #{signal_id}"""
        ),
        "ar": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b> ({coin_name})
📊 البورصة: {exchange} | الزوج: {pair}
⏰ الإطار الزمني: {timeframe}

▫️ الدخول: <code>{entry_price}</code>
🎯 TP1: <code>{tp1}</code> ({tp1_pct}%)
🎯 TP2: <code>{tp2}</code> ({tp2_pct}%)
🎯 TP3: <code>{tp3}</code> ({tp3_pct}%)
🛑 SL: <code>{stop_loss}</code> ({sl_pct}%)

📏 R:R — {risk_reward}
🧠 ثقة الذكاء الاصطناعي: {confidence}%
⚡ الرافعة المالية: x{leverage}

📝 <i>{reasoning}</i>

🆔 #{signal_id}"""
        ),
    },
    "signal.body_free": {
        "uk": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b>
📊 Біржа: {exchange}

▫️ Зона входу: ~{entry_approx}
🎯 Потенціал: +{potential}%
🧠 AI Впевненість: {confidence}%

🔒 <i>Точні TP/SL та деталі доступні на тарифах Pro/Elite</i>

💎 /subscribe — отримати повний доступ

🆔 #{signal_id}"""
        ),
        "en": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b>
📊 Exchange: {exchange}

▫️ Entry zone: ~{entry_approx}
🎯 Potential: +{potential}%
🧠 AI Confidence: {confidence}%

🔒 <i>Exact TP/SL and details available on Pro/Elite plans</i>

💎 /subscribe — get full access

🆔 #{signal_id}"""
        ),
        "ru": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b>
📊 Биржа: {exchange}

▫️ Зона входа: ~{entry_approx}
🎯 Потенциал: +{potential}%
🧠 Уверенность AI: {confidence}%

🔒 <i>Точные TP/SL и детали доступны на тарифах Pro/Elite</i>

💎 /subscribe — получить полный доступ

🆔 #{signal_id}"""
        ),
        "ar": (
            """{direction_icon}

🪙 <b>{coin_symbol}</b>
📊 البورصة: {exchange}

▫️ منطقة الدخول: ~{entry_approx}
🎯 الإمكانية: +{potential}%
🧠 ثقة الذكاء الاصطناعي: {confidence}%

🔒 <i>TP/SL الدقيق والتفاصيل متاحة في خطط Pro/Elite</i>

💎 /subscribe — احصل على وصول كامل

🆔 #{signal_id}"""
        ),
    },
    "signal.tp1_hit": {
        "uk": (
            """✅ <b>TP1 ДОСЯГНУТО!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибуток: +{pnl}%"""
        ),
        "en": (
            """✅ <b>TP1 HIT!</b>

🪙 {coin_symbol} #{signal_id}
💰 Profit: +{pnl}%"""
        ),
        "ru": (
            """✅ <b>TP1 ДОСТИГНУТ!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибыль: +{pnl}%"""
        ),
        "ar": (
            """✅ <b>TP1 تحقق!</b>

🪙 {coin_symbol} #{signal_id}
💰 الربح: +{pnl}%"""
        ),
    },
    "signal.tp2_hit": {
        "uk": (
            """✅✅ <b>TP2 ДОСЯГНУТО!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибуток: +{pnl}%"""
        ),
        "en": (
            """✅✅ <b>TP2 HIT!</b>

🪙 {coin_symbol} #{signal_id}
💰 Profit: +{pnl}%"""
        ),
        "ru": (
            """✅✅ <b>TP2 ДОСТИГНУТ!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибыль: +{pnl}%"""
        ),
        "ar": (
            """✅✅ <b>TP2 HIT!</b>

🪙 {coin_symbol} #{signal_id}
💰 Profit: +{pnl}%"""
        ),
    },
    "signal.tp3_hit": {
        "uk": (
            """✅✅✅ <b>TP3 ДОСЯГНУТО!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибуток: +{pnl}%
🏆 Повна перемога!"""
        ),
        "en": (
            """✅✅✅ <b>TP3 HIT!</b>

🪙 {coin_symbol} #{signal_id}
💰 Profit: +{pnl}%
🏆 Full win!"""
        ),
        "ru": (
            """✅✅✅ <b>TP3 ДОСТИГНУТ!</b>

🪙 {coin_symbol} #{signal_id}
💰 Прибыль: +{pnl}%
🏆 Полная победа!"""
        ),
        "ar": (
            """✅✅✅ <b>TP3 HIT!</b>

🪙 {coin_symbol} #{signal_id}
💰 Profit: +{pnl}%
🏆 فوز كامل!"""
        ),
    },
    "signal.sl_hit": {
        "uk": (
            """🛑 <b>СТОП-ЛОСС</b>

🪙 {coin_symbol} #{signal_id}
📉 Збиток: {pnl}%"""
        ),
        "en": (
            """🛑 <b>STOP LOSS HIT</b>

🪙 {coin_symbol} #{signal_id}
📉 Loss: {pnl}%"""
        ),
        "ru": (
            """🛑 <b>СТОП-ЛОСС</b>

🪙 {coin_symbol} #{signal_id}
📉 Убыток: {pnl}%"""
        ),
        "ar": (
            """🛑 <b>تم تفعيل وقف الخسارة</b>

🪙 {coin_symbol} #{signal_id}
📉 خسارة: {pnl}%"""
        ),
    },
    "signal.closed": {
        "uk": (
            """🔒 <b>СИГНАЛ ЗАКРИТО</b>

🪙 {coin_symbol} #{signal_id}
📊 Результат: {pnl}%"""
        ),
        "en": (
            """🔒 <b>SIGNAL CLOSED</b>

🪙 {coin_symbol} #{signal_id}
📊 Result: {pnl}%"""
        ),
        "ru": (
            """🔒 <b>СИГНАЛ ЗАКРЫТ</b>

🪙 {coin_symbol} #{signal_id}
📊 Результат: {pnl}%"""
        ),
        "ar": (
            """🔒 <b>الإشارة مغلقة</b>

🪙 {coin_symbol} #{signal_id}
📊 النتيجة: {pnl}%"""
        ),
    },
    "stats.title": {
        "uk": "📈 <b>СТАТИСТИКА BLACK ROOM</b>",
        "en": "📈 <b>BLACK ROOM STATISTICS</b>",
        "ru": "📈 <b>СТАТИСТИКА BLACK ROOM</b>",
        "ar": "📈 <b>إحصائيات الغرفة السوداء</b>",
    },
    "stats.body": {
        "uk": (
            """📅 Період: <b>{period}</b>

📊 Всього сигналів: <b>{total}</b>
✅ Прибуткових: <b>{wins}</b> ({win_rate}%)
❌ Збиткових: <b>{losses}</b>
⏳ Активних: <b>{active}</b>

💰 Середній прибуток: <b>+{avg_win}%</b>
📉 Середній збиток: <b>{avg_loss}%</b>
📊 Загальний PnL: <b>{total_pnl}%</b>

🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>
🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>
🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>

📏 Profit Factor: <b>{profit_factor}</b>
📐 Sharpe Ratio: <b>{sharpe}</b>
📉 Max Drawdown: <b>{max_dd}%</b>
🔥 Win Streak: <b>{win_streak}</b>
❄️ Loss Streak: <b>{loss_streak}</b>"""
        ),
        "en": (
            """📅 Period: <b>{period}</b>

📊 Total signals: <b>{total}</b>
✅ Winning: <b>{wins}</b> ({win_rate}%)
❌ Losing: <b>{losses}</b>
⏳ Active: <b>{active}</b>

💰 Avg win: <b>+{avg_win}%</b>
📉 Avg loss: <b>{avg_loss}%</b>
📊 Total PnL: <b>{total_pnl}%</b>

🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>
🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>
🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>

📏 Profit Factor: <b>{profit_factor}</b>
📐 Sharpe Ratio: <b>{sharpe}</b>
📉 Max Drawdown: <b>{max_dd}%</b>
🔥 Win Streak: <b>{win_streak}</b>
❄️ Loss Streak: <b>{loss_streak}</b>"""
        ),
        "ru": (
            """📅 Период: <b>{period}</b>

📊 Всего сигналов: <b>{total}</b>
✅ Прибыльных: <b>{wins}</b> ({win_rate}%)
❌ Убыточных: <b>{losses}</b>
⏳ Активных: <b>{active}</b>

💰 Средний профит: <b>+{avg_win}%</b>
📉 Средний убыток: <b>{avg_loss}%</b>
📊 Общий PnL: <b>{total_pnl}%</b>

🎯 TP1 Hit Rate: <b>{tp1_rate}%</b>
🎯 TP2 Hit Rate: <b>{tp2_rate}%</b>
🎯 TP3 Hit Rate: <b>{tp3_rate}%</b>

📏 Profit Factor: <b>{profit_factor}</b>
📐 Sharpe Ratio: <b>{sharpe}</b>
📉 Max Drawdown: <b>{max_dd}%</b>
🔥 Win Streak: <b>{win_streak}</b>
❄️ Loss Streak: <b>{loss_streak}</b>"""
        ),
        "ar": (
            """📅 الفترة: <b>{period}</b>

📊 إجمالي الإشارات: <b>{total}</b>
✅ الفائز: <b>{wins}</b> ({win_rate}%)
❌ الخاسر: <b>{losses}</b>
⏳ النشط: <b>{active}</b>

💰 متوسط الربح: <b>+{avg_win}%</b>
📉 متوسط الخسارة: <b>{avg_loss}%</b>
📊 إجمالي الربح والخسارة: <b>{total_pnl}%</b>

🎯 معدل ضربات TP1: <b>{tp1_rate}%</b>
🎯 معدل ضربات TP2: <b>{tp2_rate}%</b>
🎯 معدل ضربات TP3: <b>{tp3_rate}%</b>

📏 عامل الربح: <b>{profit_factor}</b>
📐 نسبة شاربي: <b>{sharpe}</b>
📉 أقصى انخفاض: <b>{max_dd}%</b>
🔥 سلسلة انتصارات: <b>{win_streak}</b>
❄️ سلسلة خسائر: <b>{loss_streak}</b>"""
        ),
    },
    "sub.choose_plan": {
        "uk": (
            """💎 <b>Тарифні плани BLACK ROOM</b>

🆓 <b>Free</b> — базові сигнали без точних даних
⭐ <b>Pro</b> — повні сигнали + статистика
👑 <b>Elite</b> — все з Pro + AI аналітика + пріоритет + портфоліо

Оберіть план:"""
        ),
        "en": (
            """💎 <b>BLACK ROOM Plans</b>

🆓 <b>Free</b> — basic signals without exact data
⭐ <b>Pro</b> — full signals + statistics
👑 <b>Elite</b> — everything in Pro + AI analytics + priority + portfolio

Choose a plan:"""
        ),
        "ru": (
            """💎 <b>Тарифные планы BLACK ROOM</b>

🆓 <b>Free</b> — базовые сигналы без точных данных
⭐ <b>Pro</b> — полные сигналы + статистика
👑 <b>Elite</b> — всё из Pro + AI аналитика + приоритет + портфолио

Выберите план:"""
        ),
        "ar": (
            """💎 <b>خطط الغرفة السوداء</b>

🆓 <b>مجاني</b> — إشارات أساسية بدون بيانات دقيقة
⭐ <b>محترف</b> — إشارات كاملة + إحصائيات
👑 <b>نخبة</b> — كل شيء في المحترف + تحليلات الذكاء الاصطناعي + أولوية + محفظة

اختر خطة:"""
        ),
    },
    "sub.payment_created": {
        "uk": (
            """💳 Оплата створена! Перейдіть за посиланням:

{url}

Оплата дійсна 60 хвилин."""
        ),
        "en": (
            """💳 Payment created! Follow the link:

{url}

Payment valid for 60 minutes."""
        ),
        "ru": (
            """💳 Оплата создана! Перейдите по ссылке:

{url}

Оплата действительна 60 минут."""
        ),
        "ar": (
            """💳 تم إنشاء الدفع! اتبع الرابط:

{url}

الدفع صالح لمدة 60 دقيقة."""
        ),
    },
    "sub.payment_success": {
        "uk": (
            """🎉 <b>Оплату підтверджено!</b>

Ваш тариф: <b>{tier}</b>
Дійсний до: <b>{expires}</b>"""
        ),
        "en": (
            """🎉 <b>Payment confirmed!</b>

Your plan: <b>{tier}</b>
Valid until: <b>{expires}</b>"""
        ),
        "ru": (
            """🎉 <b>Оплата подтверждена!</b>

Ваш тариф: <b>{tier}</b>
Действителен до: <b>{expires}</b>"""
        ),
        "ar": (
            """🎉 <b>تم تأكيد الدفع!</b>

خطتك: <b>{tier}</b>
صالح حتى: <b>{expires}</b>"""
        ),
    },
    "sub.expired": {
        "uk": "⚠️ Ваша підписка <b>{tier}</b> закінчилась. Продовжіть через /subscribe",
        "en": "⚠️ Your <b>{tier}</b> subscription has expired. Renew via /subscribe",
        "ru": "⚠️ Ваша подписка <b>{tier}</b> истекла. Продлите через /subscribe",
        "ar": "⚠️ اشتراكك <b>{tier}</b> قد انتهى. قم بالتجديد عبر /subscribe",
    },
    "digest.daily_title": {
        "uk": "📊 <b>ЩОДЕННИЙ ЗВІТ — {date}</b>",
        "en": "📊 <b>DAILY DIGEST — {date}</b>",
        "ru": "📊 <b>ЕЖЕДНЕВНЫЙ ОТЧЁТ — {date}</b>",
        "ar": "📊 <b>ملخص يومي — {date}</b>",
    },
    "digest.weekly_title": {
        "uk": "📊 <b>ТИЖНЕВИЙ ЗВІТ — {date_range}</b>",
        "en": "📊 <b>WEEKLY REPORT — {date_range}</b>",
        "ru": "📊 <b>НЕДЕЛЬНЫЙ ОТЧЁТ — {date_range}</b>",
        "ar": "📊 <b>التقرير الأسبوعي — {date_range}</b>",
    },
    "help.text": {
        "uk": (
            """❓ <b>Допомога BLACK ROOM</b>

🤖 Це AI-система торгових сигналів, яка аналізує ринок 24/7.

<b>Команди:</b>
/start — головне меню
/signals — активні сигнали
/stats — статистика
/subscribe — тарифи
/settings — налаштування
/help — ця довідка

📡 Сигнали надходять прямо в бот з кнопками деталей.
📊 Дайджести та аналітика публікуються в каналах."""
        ),
        "en": (
            """❓ <b>BLACK ROOM Help</b>

🤖 This is an AI trading signal system analyzing the market 24/7.

<b>Commands:</b>
/start — main menu
/signals — active signals
/stats — statistics
/subscribe — plans
/settings — settings
/help — this help

📡 Signals are delivered directly to bot with detail buttons.
📊 Digests and analytics are posted to channels."""
        ),
        "ru": (
            """❓ <b>Помощь BLACK ROOM</b>

🤖 Это AI-система торговых сигналов, анализирующая рынок 24/7.

<b>Команды:</b>
/start — главное меню
/signals — активные сигналы
/stats — статистика
/subscribe — тарифы
/settings — настройки
/help — эта справка

📡 Сигналы приходят прямо в бот с кнопками деталей.
📊 Дайджесты и аналитика публикуются в каналах."""
        ),
        "ar": (
            """❓ <b>مساعدة الغرفة السوداء</b>

🤖 هذا نظام إشارات تداول بالذكاء الاصطناعي يقوم بتحليل السوق على مدار الساعة.

<b>الأوامر:</b>
/start — القائمة الرئيسية
/signals — الإشارات النشطة
/stats — الإحصائيات
/subscribe — الخطط
/settings — الإعدادات
/help — هذه المساعدة

📡 يتم توصيل الإشارات مباشرة إلى البوت مع أزرار تفصيلية.
📊 يتم نشر الملخصات والتحليلات في القنوات."""
        ),
    },
    "error.generic": {
        "uk": "❌ Сталася помилка. Спробуйте пізніше.",
        "en": "❌ An error occurred. Please try again later.",
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
        "ar": "❌ حدث خطأ. يرجى المحاولة مرة أخرى لاحقًا.",
    },
    "error.not_subscribed": {
        "uk": "🔒 Ця функція доступна лише для підписників {tier}+",
        "en": "🔒 This feature is available for {tier}+ subscribers only",
        "ru": "🔒 Эта функция доступна только для подписчиков {tier}+",
        "ar": "🔒 هذه الميزة متاحة فقط للمشتركين في {tier}+",
    },
    "error.banned": {
        "uk": "🚫 Ваш акаунт заблоковано.",
        "en": "🚫 Your account has been banned.",
        "ru": "🚫 Ваш аккаунт заблокирован.",
        "ar": "🚫 تم حظر حسابك.",
    },
    "start": {
        "uk": (
            """🚀 <b>Привіт, {name}!</b>

Ласкаво просимо до BLACK ROOM — найпотужнішої AI-системи торгових сигналів.

Оберіть дію:"""
        ),
        "en": (
            """🚀 <b>Hi, {name}!</b>

Welcome to BLACK ROOM — the most powerful AI trading signal system.

Choose an action:"""
        ),
        "ru": (
            """🚀 <b>Привет, {name}!</b>

Добро пожаловать в BLACK ROOM — самую мощную AI-систему торговых сигналов.

Выберите действие:"""
        ),
        "ar": (
            """🚀 <b>مرحبًا، {name}!</b>

مرحبًا بك في BLACK ROOM — أقوى نظام إشارات تداول بالذكاء الاصطناعي.

اختر إجراء:"""
        ),
    },
    "main_menu": {
        "uk": (
            """📊 <b>BLACK ROOM</b> — Головне меню

Оберіть дію:"""
        ),
        "en": (
            """📊 <b>BLACK ROOM</b> — Main Menu

Choose an action:"""
        ),
        "ru": (
            """📊 <b>BLACK ROOM</b> — Главное меню

Выберите действие:"""
        ),
        "ar": (
            """📊 <b>الغرفة السوداء</b> — القائمة الرئيسية

اختر إجراء:"""
        ),
    },
    "language_changed": {
        "uk": "✅ Мову змінено на <b>Українську</b>",
        "en": "✅ Language changed to <b>English</b>",
        "ru": "✅ Язык изменён на <b>Русский</b>",
        "ar": "✅ تم تغيير اللغة إلى <b>الإنجليزية</b>",
    },
    "help": {
        "uk": (
            """❓ <b>Допомога</b>

🤖 AI-система аналізує ринок 24/7 і генерує сигнали.

/start — меню
/menu — меню
/signals — сигнали
/stats — статистика
/subscribe — підписка
/settings — налаштування"""
        ),
        "en": (
            """❓ <b>Help</b>

🤖 AI system analyzes the market 24/7 and generates signals.

/start — menu
/menu — menu
/signals — signals
/stats — statistics
/subscribe — subscription
/settings — settings"""
        ),
        "ru": (
            """❓ <b>Помощь</b>

🤖 AI-система анализирует рынок 24/7 и генерирует сигналы.

/start — меню
/menu — меню
/signals — сигналы
/stats — статистика
/subscribe — подписка
/settings — настройки"""
        ),
        "ar": (
            """❓ <b>مساعدة</b>

🤖 يقوم نظام الذكاء الاصطناعي بتحليل السوق على مدار الساعة طوال أيام الأسبوع ويولد إشارات.

/start — القائمة
/menu — القائمة
/signals — الإشارات
/stats — الإحصائيات
/subscribe — الاشتراك
/settings — الإعدادات"""
        ),
    },
    "signals_menu": {
        "uk": (
            """📡 <b>Сигнали</b>

Оберіть категорію:"""
        ),
        "en": (
            """📡 <b>Signals</b>

Choose a category:"""
        ),
        "ru": (
            """📡 <b>Сигналы</b>

Выберите категорию:"""
        ),
        "ar": (
            """📡 <b>الإشارات</b>

اختر فئة:"""
        ),
    },
    "no_active_signals": {
        "uk": "📭 Наразі немає активних сигналів. Скоро з'являться нові!",
        "en": "📭 No active signals right now. New ones coming soon!",
        "ru": "📭 Сейчас нет активных сигналов. Скоро появятся новые!",
        "ar": "📭 لا توجد إشارات نشطة في الوقت الحالي. إشارات جديدة قادمة قريبًا!",
    },
    "active_signals_header": {
        "uk": "🟢 <b>Активні сигнали:</b>",
        "en": "🟢 <b>Active Signals:</b>",
        "ru": "🟢 <b>Активные сигналы:</b>",
        "ar": "🟢 <b>الإشارات النشطة:</b>",
    },
    "no_signal_history": {
        "uk": "📭 Ще немає історії сигналів.",
        "en": "📭 No signal history yet.",
        "ru": "📭 История сигналов пока пуста.",
        "ar": "📭 لا توجد تاريخ إشارة بعد.",
    },
    "signal_history_header": {
        "uk": "📜 <b>Історія сигналів:</b>",
        "en": "📜 <b>Signal History:</b>",
        "ru": "📜 <b>История сигналов:</b>",
        "ar": "📜 <b>تاريخ الإشارة:</b>",
    },
    "tracked_signals_header": {
        "uk": "📌 <b>Відстежувані сигнали:</b>",
        "en": "📌 <b>Tracked Signals:</b>",
        "ru": "📌 <b>Отслеживаемые сигналы:</b>",
        "ar": "📌 <b>الإشارات المتعقبة:</b>",
    },
    "no_tracked_signals": {
        "uk": (
            """📭 Ви ще не відстежуєте жодного сигналу.
Натисніть «Використати» на сигналі, щоб почати відстеження."""
        ),
        "en": (
            """📭 You're not tracking any signals yet.
Tap \"Use Signal\" on a signal to start tracking."""
        ),
        "ru": (
            """📭 Вы ещё не отслеживаете ни одного сигнала.
Нажмите «Использовать» на сигнале, чтобы начать отслеживание."""
        ),
        "ar": (
            """📭 أنت لا تتعقب أي إشارات بعد.
اضغط على \"استخدام الإشارة\" على إشارة لبدء التعقب."""
        ),
    },
    "signal_stats_header": {
        "uk": "📊 <b>Статистика сигналів</b>",
        "en": "📊 <b>Signal Stats</b>",
        "ru": "📊 <b>Статистика сигналов</b>",
        "ar": "📊 <b>إحصائيات الإشارة</b>",
    },
    "confidence": {
        "uk": "Впевненість",
        "en": "Confidence",
        "ru": "Уверенность",
        "ar": "ثقة",
    },
    "upgrade_to_see": {
        "uk": "Оновіть тариф для повних деталей → /subscribe",
        "en": "Upgrade your plan for full details → /subscribe",
        "ru": "Улучшите план для полных деталей → /subscribe",
        "ar": "قم بترقية خطتك للحصول على التفاصيل الكاملة → /subscribe",
    },
    "stats_menu": {
        "uk": (
            """📈 <b>Статистика</b>

Оберіть період:"""
        ),
        "en": (
            """📈 <b>Statistics</b>

Choose period:"""
        ),
        "ru": (
            """📈 <b>Статистика</b>

Выберите период:"""
        ),
        "ar": (
            """📈 <b>الإحصائيات</b>

اختر الفترة:"""
        ),
    },
    "loading": {
        "uk": "⏳ Завантаження...",
        "en": "⏳ Loading...",
        "ru": "⏳ Загрузка...",
        "ar": "⏳ جار التحميل...",
    },
    "error_generic": {
        "uk": "❌ Помилка. Спробуйте пізніше.",
        "en": "❌ Error. Try again later.",
        "ru": "❌ Ошибка. Попробуйте позже.",
        "ar": "❌ خطأ. حاول مرة أخرى لاحقًا.",
    },
    "no_data_for_heatmap": {
        "uk": "📭 Недостатньо даних для хітмапу.",
        "en": "📭 Not enough data for heatmap.",
        "ru": "📭 Недостаточно данных для тепловой карты.",
        "ar": "📭 ليس هناك بيانات كافية لخريطة الحرارة.",
    },
    "heatmap_caption": {
        "uk": "🗺️ Хітмап продуктивності сигналів",
        "en": "🗺️ Signal Performance Heatmap",
        "ru": "🗺️ Тепловая карта результатов сигналов",
        "ar": "🗺️ خريطة حرارة أداء الإشارة",
    },
    "subscription_info": {
        "uk": (
            """💎 <b>Підписка</b>

Ваш тариф: <b>{current_tier}</b>

Оберіть план:"""
        ),
        "en": (
            """💎 <b>Subscription</b>

Your plan: <b>{current_tier}</b>

Choose a plan:"""
        ),
        "ru": (
            """💎 <b>Подписка</b>

Ваш тариф: <b>{current_tier}</b>

Выберите план:"""
        ),
        "ar": (
            """💎 <b>الاشتراك</b>

خطةك: <b>{current_tier}</b>

اختر خطة:"""
        ),
    },
    "tier_pro_desc": {
        "uk": (
            """⭐ <b>Pro</b>

✅ Повні сигнали з TP/SL
✅ Статистика
✅ Щоденний дайджест

Оберіть тривалість:"""
        ),
        "en": (
            """⭐ <b>Pro</b>

✅ Full signals with TP/SL
✅ Statistics
✅ Daily digest

Choose duration:"""
        ),
        "ru": (
            """⭐ <b>Pro</b>

✅ Полные сигналы с TP/SL
✅ Статистика
✅ Ежедневный дайджест

Выберите продолжительность:"""
        ),
        "ar": (
            """⭐ <b>محترف</b>

✅ إشارات كاملة مع TP/SL  
✅ إحصائيات  
✅ ملخص يومي  

اختر المدة:"""
        ),
    },
    "tier_elite_desc": {
        "uk": (
            """👑 <b>Elite</b>

✅ Все з Pro
✅ 🧠 AI пояснення до кожного сигналу
✅ 📊 Мультитаймфрейм аналіз
✅ 🎯 Пріоритетні сигнали раніше за всіх
✅ 💼 Симуляція портфоліо ($1K/$5K/$10K)
✅ 🔍 Кореляційний аналіз активів
✅ ⚡ Ексклюзивний контент

Оберіть тривалість:"""
        ),
        "en": (
            """👑 <b>Elite</b>

✅ Everything in Pro
✅ 🧠 AI reasoning for each signal
✅ 📊 Multi-timeframe analysis
✅ 🎯 Priority signals before everyone
✅ 💼 Portfolio simulation ($1K/$5K/$10K)
✅ 🔍 Asset correlation analysis
✅ ⚡ Exclusive content

Choose duration:"""
        ),
        "ru": (
            """👑 <b>Elite</b>

✅ Всё из Pro
✅ 🧠 AI обоснование каждого сигнала
✅ 📊 Мультитаймфрейм анализ
✅ 🎯 Приоритетные сигналы раньше всех
✅ 💼 Симуляция портфолио ($1K/$5K/$10K)
✅ 🔍 Корреляционный анализ активов
✅ ⚡ Эксклюзивный контент

Выберите продолжительность:"""
        ),
        "ar": (
            """👑 <b>النخبة</b>

✅ كل شيء في برو
✅ 🧠 reasoning الذكاء الاصطناعي لكل إشارة
✅ 📊 تحليل متعدد الأطر الزمنية
✅ 🎯 إشارات ذات أولوية قبل الجميع
✅ 💼 محاكاة المحفظة ($1K/$5K/$10K)
✅ 🔍 تحليل ارتباط الأصول
✅ ⚡ محتوى حصري

اختر المدة:"""
        ),
    },
    "payment_created": {
        "uk": (
            """💳 Оплата створена: <b>${amount} {currency}</b>

Натисніть кнопку для оплати:"""
        ),
        "en": (
            """💳 Payment created: <b>${amount} {currency}</b>

Click the button to pay:"""
        ),
        "ru": (
            """💳 Оплата создана: <b>${amount} {currency}</b>

Нажмите кнопку для оплаты:"""
        ),
        "ar": (
            """💳 تم إنشاء الدفع: <b>${amount} {currency}</b>

انقر على الزر للدفع:"""
        ),
    },
    "payment_error": {
        "uk": "❌ Не вдалось створити оплату. Спробуйте пізніше.",
        "en": "❌ Failed to create payment. Try again later.",
        "ru": "❌ Не удалось создать оплату. Попробуйте позже.",
        "ar": "❌ فشل في إنشاء الدفع. حاول مرة أخرى لاحقًا.",
    },
    "payment_success": {
        "uk": (
            """🎉 <b>Оплату підтверджено!</b>

Ваш тариф активовано. Дякуємо!"""
        ),
        "en": (
            """🎉 <b>Payment confirmed!</b>

Your plan is now active. Thank you!"""
        ),
        "ru": (
            """🎉 <b>Оплата подтверждена!</b>

Ваш тариф активирован. Спасибо!"""
        ),
        "ar": (
            """🎉 <b>تم تأكيد الدفع!</b>

خطة الاشتراك الخاصة بك نشطة الآن. شكرًا لك!"""
        ),
    },
    "payment_pending": {
        "uk": "⏳ Оплата ще обробляється. Зачекайте кілька хвилин.",
        "en": "⏳ Payment is still processing. Wait a few minutes.",
        "ru": "⏳ Оплата ещё обрабатывается. Подождите несколько минут.",
        "ar": "⏳ الدفع لا يزال قيد المعالجة. انتظر بضع دقائق.",
    },
    "payment_expired": {
        "uk": "⏰ Час оплати вичерпано. Створіть нову.",
        "en": "⏰ Payment expired. Create a new one.",
        "ru": "⏰ Время оплаты истекло. Создайте новую.",
        "ar": "⏰ انتهت صلاحية الدفع. أنشئ واحدة جديدة.",
    },
    "my_subscription": {
        "uk": (
            """📋 <b>Ваша підписка</b>

Тариф: <b>{tier}</b>
Дійсна до: <b>{expires}</b>"""
        ),
        "en": (
            """📋 <b>Your Subscription</b>

Plan: <b>{tier}</b>
Valid until: <b>{expires}</b>"""
        ),
        "ru": (
            """📋 <b>Ваша подписка</b>

Тариф: <b>{tier}</b>
Действительна до: <b>{expires}</b>"""
        ),
        "ar": (
            """📋 <b>اشتراكك</b>

الخطة: <b>{tier}</b>
صالح حتى: <b>{expires}</b>"""
        ),
    },
    "settings": {
        "uk": (
            """⚙️ <b>Налаштування</b>

Ваш тариф: <b>{tier}</b>"""
        ),
        "en": (
            """⚙️ <b>Settings</b>

Your plan: <b>{tier}</b>"""
        ),
        "ru": (
            """⚙️ <b>Настройки</b>

Ваш тариф: <b>{tier}</b>"""
        ),
        "ar": (
            """⚙️ <b>الإعدادات</b>

خطةك: <b>{tier}</b>"""
        ),
    },
    "coming_soon": {
        "uk": "🔜 Скоро буде!",
        "en": "🔜 Coming soon!",
        "ru": "🔜 Скоро будет!",
        "ar": "🔜 قريباً!",
    },
    "signal_full": {
        "uk": (
            """📡 <b>{coin}</b> {direction}

📍 Entry: ${entry}
🎯 TP1: ${tp1}
🛑 SL: ${sl}
💪 Впевненість: {confidence}%"""
        ),
        "en": (
            """📡 <b>{coin}</b> {direction}

📍 Entry: ${entry}
🎯 TP1: ${tp1}
🛑 SL: ${sl}
💪 Confidence: {confidence}%"""
        ),
        "ru": (
            """📡 <b>{coin}</b> {direction}

📍 Вход: ${entry}
🎯 TP1: ${tp1}
🛑 SL: ${sl}
💪 Уверенность: {confidence}%"""
        ),
        "ar": (
            """📡 <b>{coin}</b> {direction}

📍 الدخول: ${entry}
🎯 TP1: ${tp1}
🛑 SL: ${sl}
💪 الثقة: {confidence}%"""
        ),
    },
    "signal_teaser": {
        "uk": "📡 <b>{coin}</b> — 🔒 Повні деталі для Pro/Elite → /subscribe",
        "en": "📡 <b>{coin}</b> — 🔒 Full details for Pro/Elite → /subscribe",
        "ru": "📡 <b>{coin}</b> — 🔒 Полные детали для Pro/Elite → /subscribe",
        "ar": "📡 <b>{coin}</b> — 🔒 التفاصيل الكاملة للمحترفين/النخبة → /subscribe",
    },
    "signal_free_channel": {
        "uk": (
            """📡 <b>{coin}</b> {direction}

🕐 Сигнал був актуальний раніше
🎯 Результат: <b>{result}</b>

🔒 <i>Отримуйте сигнали в реальному часі з Pro/Elite</i>
💎 @{bot_username} → /subscribe"""
        ),
        "en": (
            """📡 <b>{coin}</b> {direction}

🕐 Signal was active earlier
🎯 Result: <b>{result}</b>

🔒 <i>Get real-time signals with Pro/Elite</i>
💎 @{bot_username} → /subscribe"""
        ),
        "ru": (
            """📡 <b>{coin}</b> {direction}

🕐 Сигнал был актуален ранее
🎯 Результат: <b>{result}</b>

🔒 <i>Получайте сигналы в реальном времени с Pro/Elite</i>
💎 @{bot_username} → /subscribe"""
        ),
        "ar": (
            """📡 <b>{coin}</b> {direction}

🕐 كانت الإشارة نشطة في وقت سابق
🎯 النتيجة: <b>{result}</b>

🔒 <i>احصل على إشارات في الوقت الحقيقي مع Pro/Elite</i>
💎 @{bot_username} → /subscribe"""
        ),
    },
    "signal_elite": {
        "uk": (
            """📡 <b>{coin}</b> {direction}

📍 Entry: ${entry}
🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}
🛑 SL: ${sl}
⚡ Плече: x{leverage}
💪 Впевненість: {confidence}%

🧠 <b>AI Аналіз:</b>
<i>{reasoning}</i>

📊 Кореляція з BTC: {btc_corr}
📏 R:R — {rr}"""
        ),
        "en": (
            """📡 <b>{coin}</b> {direction}

📍 Entry: ${entry}
🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}
🛑 SL: ${sl}
⚡ Leverage: x{leverage}
💪 Confidence: {confidence}%

🧠 <b>AI Analysis:</b>
<i>{reasoning}</i>

📊 BTC Correlation: {btc_corr}
📏 R:R — {rr}"""
        ),
        "ru": (
            """📡 <b>{coin}</b> {direction}

📍 Вход: ${entry}
🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}
🛑 SL: ${sl}
⚡ Плечо: x{leverage}
💪 Уверенность: {confidence}%

🧠 <b>AI Анализ:</b>
<i>{reasoning}</i>

📊 Корреляция с BTC: {btc_corr}
📏 R:R — {rr}"""
        ),
        "ar": (
            """📡 <b>{coin}</b> {direction}

📍 الدخول: ${entry}
🎯 TP1: ${tp1} | TP2: ${tp2} | TP3: ${tp3}
🛑 SL: ${sl}
⚡ الرافعة المالية: x{leverage}
💪 الثقة: {confidence}%

🧠 <b>تحليل الذكاء الاصطناعي:</b>
<i>{reasoning}</i>

📊 ارتباط BTC: {btc_corr}
📏 R:R — {rr}"""
        ),
    },
    "digest_daily_caption": {
        "uk": "📊 Щоденний дайджест BLACK ROOM",
        "en": "📊 BLACK ROOM Daily Digest",
        "ru": "📊 Ежедневный дайджест BLACK ROOM",
        "ar": "📊 ملخص يومي للغرفة السوداء",
    },
    "digest_weekly_caption": {
        "uk": "📊 Тижневий дайджест BLACK ROOM",
        "en": "📊 BLACK ROOM Weekly Digest",
        "ru": "📊 Недельный дайджест BLACK ROOM",
        "ar": "📊 ملخص أسبوعي للغرفة السوداء",
    },
    "portfolio_header": {
        "uk": "💼 <b>Симуляція портфоліо</b>",
        "en": "💼 <b>Portfolio Simulation</b>",
        "ru": "💼 <b>Симуляция портфолио</b>",
        "ar": "💼 <b>محاكاة المحفظة</b>",
    },
    "portfolio_row": {
        "uk": "Стартовий: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
        "en": "Starting: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
        "ru": "Стартовый: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
        "ar": "بدءًا: <b>${start}</b> → <b>${end}</b> ({pnl}%)",
    },
    "btn_signals": {
        "uk": "📡 Сигнали",
        "en": "📡 Signals",
        "ru": "📡 Сигналы",
        "ar": "📡 إشارات",
    },
    "btn_stats": {
        "uk": "📈 Статистика",
        "en": "📈 Statistics",
        "ru": "📈 Статистика",
        "ar": "📈 الإحصائيات",
    },
    "btn_subscription": {
        "uk": "💎 Підписка",
        "en": "💎 Subscribe",
        "ru": "💎 Подписка",
        "ar": "💎 اشترك",
    },
    "btn_settings": {
        "uk": "⚙️ Налаштування",
        "en": "⚙️ Settings",
        "ru": "⚙️ Настройки",
        "ar": "⚙️ الإعدادات",
    },
    "btn_help": {
        "uk": "❓ Допомога",
        "en": "❓ Help",
        "ru": "❓ Помощь",
        "ar": "❓ مساعدة",
    },
    "btn_back": {
        "uk": "Назад",
        "en": "Back",
        "ru": "Назад",
        "ar": "عودة",
    },
    "btn_active_signals": {
        "uk": "Активні сигнали",
        "en": "Active Signals",
        "ru": "Активные сигналы",
        "ar": "النشرات النشطة",
    },
    "btn_tracked_signals": {
        "uk": "Відстежувані",
        "en": "Tracked",
        "ru": "Отслеживаемые",
        "ar": "تم تتبعه",
    },
    "btn_signal_history": {
        "uk": "Історія",
        "en": "History",
        "ru": "История",
        "ar": "تاريخ",
    },
    "btn_signal_stats": {
        "uk": "Стата сигналів",
        "en": "Signal Stats",
        "ru": "Стата сигналов",
        "ar": "إحصائيات الإشارة",
    },
    "rk_signals": {
        "uk": "📡 Сигнали",
        "en": "📡 Signals",
        "ru": "📡 Сигналы",
        "ar": "📡 إشارات",
    },
    "rk_stats": {
        "uk": "📈 Статистика",
        "en": "📈 Stats",
        "ru": "📈 Статистика",
        "ar": "📈 إحصائيات",
    },
    "rk_wallets": {
        "uk": "💰 Гаманці",
        "en": "💰 Wallets",
        "ru": "💰 Кошельки",
        "ar": "💰 المحافظ",
    },
    "rk_settings": {
        "uk": "⚙️ Налаштування",
        "en": "⚙️ Settings",
        "ru": "⚙️ Настройки",
        "ar": "⚙️ الإعدادات",
    },
    "rk_subscription": {
        "uk": "💎 Підписка",
        "en": "💎 Subscribe",
        "ru": "💎 Подписка",
        "ar": "💎 اشترك",
    },
    "rk_help": {
        "uk": "❓ Допомога",
        "en": "❓ Help",
        "ru": "❓ Помощь",
        "ar": "❓ مساعدة",
    },
    "rk_alerts": {
        "uk": "🔔 Алерти",
        "en": "🔔 Alerts",
        "ru": "🔔 Алерты",
        "ar": "🔔 تنبيهات",
    },
    "rk_watchlist": {
        "uk": "👁 Вотчліст",
        "en": "👁 Watchlist",
        "ru": "👁 Вотчлист",
        "ar": "👁 قائمة المراقبة",
    },
    "rk_back": {
        "uk": "◀️ Назад",
        "en": "◀️ Back",
        "ru": "◀️ Назад",
        "ar": "◀️ العودة",
    },
    "rk_active_signals": {
        "uk": "📡 Активні",
        "en": "📡 Active",
        "ru": "📡 Активные",
        "ar": "📡 نشط",
    },
    "rk_tracked_signals": {
        "uk": "📌 Відстежувані",
        "en": "📌 Tracked",
        "ru": "📌 Отслеживаемые",
        "ar": "📌 تم تتبعه",
    },
    "rk_signal_history": {
        "uk": "📜 Історія",
        "en": "📜 History",
        "ru": "📜 История",
        "ar": "📜 التاريخ",
    },
    "rk_signal_stats": {
        "uk": "📊 Стата",
        "en": "📊 Stats",
        "ru": "📊 Стата",
        "ar": "📊 إحصائيات",
    },
    "rk_stats_24h": {
        "uk": "📊 24h",
        "en": "📊 24h",
        "ru": "📊 24h",
        "ar": "📊 ٢٤ ساعة",
    },
    "rk_stats_7d": {
        "uk": "📊 7д",
        "en": "📊 7d",
        "ru": "📊 7д",
        "ar": "📊 7d",
    },
    "rk_stats_30d": {
        "uk": "📊 30д",
        "en": "📊 30d",
        "ru": "📊 30д",
        "ar": "📊 30يوم",
    },
    "rk_stats_all": {
        "uk": "📊 Весь час",
        "en": "📊 All time",
        "ru": "📊 Всё время",
        "ar": "📊 كل الوقت",
    },
    "rk_heatmap": {
        "uk": "🔥 Хітмап",
        "en": "🔥 Heatmap",
        "ru": "🔥 Тепловая",
        "ar": "🔥 خريطة الحرارة",
    },
    "rk_create_alert": {
        "uk": "➕ Створити",
        "en": "➕ Create",
        "ru": "➕ Создать",
        "ar": "➕ إنشاء",
    },
    "rk_my_alerts": {
        "uk": "📋 Мої алерти",
        "en": "📋 My Alerts",
        "ru": "📋 Мои алерты",
        "ar": "📋 تنبيهاتى",
    },
    "rk_add_watchlist": {
        "uk": "➕ Додати монету",
        "en": "➕ Add coin",
        "ru": "➕ Добавить монету",
        "ar": "➕ أضف عملة",
    },
    "rk_my_wallets": {
        "uk": "💰 Мої гаманці",
        "en": "💰 My Wallets",
        "ru": "💰 Мои кошельки",
        "ar": "💰 محفظتي",
    },
    "rk_add_wallet": {
        "uk": "➕ Додати",
        "en": "➕ Add",
        "ru": "➕ Добавить",
        "ar": "➕ أضف",
    },
    "rk_sub_pro": {
        "uk": "⭐ Pro",
        "en": "⭐ Pro",
        "ru": "⭐ Pro",
        "ar": "⭐ Pro",
    },
    "rk_sub_elite": {
        "uk": "💎 Elite",
        "en": "💎 Elite",
        "ru": "💎 Elite",
        "ar": "💎 النخبة",
    },
    "rk_my_sub": {
        "uk": "📋 Моя підписка",
        "en": "📋 My Sub",
        "ru": "📋 Моя подписка",
        "ar": "📋 اشتراكي",
    },
    "rk_language": {
        "uk": "🌐 Мова",
        "en": "🌐 Language",
        "ru": "🌐 Язык",
        "ar": "🌐 لغة",
    },
    "rk_notifications": {
        "uk": "🔔 Сповіщення",
        "en": "🔔 Notifications",
        "ru": "🔔 Уведомления",
        "ar": "🔔 الإشعارات",
    },
    "rk_api_key": {
        "uk": "🔑 API ключ",
        "en": "🔑 API Key",
        "ru": "🔑 API ключ",
        "ar": "🔑 مفتاح API",
    },
    "btn_all_time": {
        "uk": "За весь час",
        "en": "All time",
        "ru": "За всё время",
        "ar": "كل الوقت",
    },
    "btn_heatmap": {
        "uk": "Хітмап",
        "en": "Heatmap",
        "ru": "Тепловая карта",
        "ar": "خريطة الحرارة",
    },
    "btn_cleanup_signals": {
        "uk": "🗑 Очистити сигнали",
        "en": "🗑 Cleanup Signals",
        "ru": "🗑 Очистить сигналы",
        "ar": "🗑 إشارات التنظيف",
    },
    "btn_cleanup_stopped": {
        "uk": "🛑 Стоплосс",
        "en": "🛑 Stopped",
        "ru": "🛑 Стоплосс",
        "ar": "🛑 توقف",
    },
    "btn_cleanup_expired": {
        "uk": "⏰ Протерміновані",
        "en": "⏰ Expired",
        "ru": "⏰ Просроченные",
        "ar": "⏰ منتهية الصلاحية",
    },
    "btn_cleanup_closed": {
        "uk": "📋 Закриті",
        "en": "📋 Closed",
        "ru": "📋 Закрытые",
        "ar": "📋 مغلق",
    },
    "btn_cleanup_all_old": {
        "uk": "🗑 Всі закриті",
        "en": "🗑 All Closed",
        "ru": "🗑 Все закрытые",
        "ar": "🗑 جميع المغلقة",
    },
    "btn_confirm_yes": {
        "uk": "✅ Так, видалити",
        "en": "✅ Yes, delete",
        "ru": "✅ Да, удалить",
        "ar": "✅ نعم، احذف",
    },
    "btn_confirm_no": {
        "uk": "❌ Скасувати",
        "en": "❌ Cancel",
        "ru": "❌ Отмена",
        "ar": "❌ إلغاء",
    },
    "cleanup_menu": {
        "uk": (
            """🗑 <b>Очистити сигнали</b>

Видалити старі закриті сигнали з бази.
Оберіть що видалити:"""
        ),
        "en": (
            """🗑 <b>Cleanup Signals</b>

Delete old closed signals from the database.
Choose what to delete:"""
        ),
        "ru": (
            """🗑 <b>Очистить сигналы</b>

Удалить старые закрытые сигналы из базы.
Выберите что удалить:"""
        ),
        "ar": (
            """🗑 <b>إشارات التنظيف</b>

احذف الإشارات المغلقة القديمة من قاعدة البيانات.
اختر ما تريد حذفه:"""
        ),
    },
    "cleanup_confirm": {
        "uk": (
            """⚠️ Ви впевнені? Буде видалено <b>{count}</b> сигналів зі статусом: <b>{status}</b>

Цю дію неможливо скасувати!"""
        ),
        "en": (
            """⚠️ Are you sure? <b>{count}</b> signals with status <b>{status}</b> will be deleted.

This cannot be undone!"""
        ),
        "ru": (
            """⚠️ Вы уверены? Будет удалено <b>{count}</b> сигналов со статусом: <b>{status}</b>

Это действие нельзя отменить!"""
        ),
        "ar": (
            """⚠️ هل أنت متأكد؟ سيتم حذف <b>{count}</b> إشارات بحالة <b>{status}</b>.

لا يمكن التراجع عن هذا!"""
        ),
    },
    "cleanup_done": {
        "uk": "✅ Видалено <b>{count}</b> сигналів.",
        "en": "✅ Deleted <b>{count}</b> signals.",
        "ru": "✅ Удалено <b>{count}</b> сигналов.",
        "ar": "✅ تم حذف <b>{count}</b> إشارات.",
    },
    "cleanup_nothing": {
        "uk": "ℹ️ Немає сигналів для видалення.",
        "en": "ℹ️ No signals to delete.",
        "ru": "ℹ️ Нет сигналов для удаления.",
        "ar": "ℹ️ لا توجد إشارات للحذف.",
    },
    "btn_my_subscription": {
        "uk": "Моя підписка",
        "en": "My subscription",
        "ru": "Моя подписка",
        "ar": "اشتراكي",
    },
    "btn_pay": {
        "uk": "Оплатити",
        "en": "Pay",
        "ru": "Оплатить",
        "ar": "دفع",
    },
    "btn_check_payment": {
        "uk": "Перевірити оплату",
        "en": "Check payment",
        "ru": "Проверить оплату",
        "ar": "تحقق من الدفع",
    },
    "btn_cancel": {
        "uk": "Скасувати",
        "en": "Cancel",
        "ru": "Отменить",
        "ar": "إلغاء",
    },
    "btn_language": {
        "uk": "Мова",
        "en": "Language",
        "ru": "Язык",
        "ar": "لغة",
    },
    "btn_notifications": {
        "uk": "Сповіщення",
        "en": "Notifications",
        "ru": "Уведомления",
        "ar": "الإشعارات",
    },
    "btn_api_key": {
        "uk": "API ключ",
        "en": "API Key",
        "ru": "API ключ",
        "ar": "مفتاح API",
    },
    "btn_generate_key": {
        "uk": "Створити ключ",
        "en": "Generate Key",
        "ru": "Создать ключ",
        "ar": "إنشاء مفتاح",
    },
    "btn_regenerate_key": {
        "uk": "Перегенерувати",
        "en": "Regenerate",
        "ru": "Перегенерировать",
        "ar": "تجديد",
    },
    "btn_revoke_key": {
        "uk": "Відкликати ключ",
        "en": "Revoke Key",
        "ru": "Отозвать ключ",
        "ar": "إلغاء المفتاح",
    },
    "api_key_none": {
        "uk": (
            """🔑 <b>API ключ для додатку</b>

У вас поки немає ключа.
Створіть його, щоб підключити десктоп-додаток BLACK ROOM."""
        ),
        "en": (
            """🔑 <b>API Key for App</b>

You don't have a key yet.
Generate one to connect the BLACK ROOM desktop app."""
        ),
        "ru": (
            """🔑 <b>API ключ для приложения</b>

У вас пока нет ключа.
Создайте его, чтобы подключить десктоп-приложение BLACK ROOM."""
        ),
        "ar": (
            """🔑 <b>مفتاح API للتطبيق</b>

ليس لديك مفتاح بعد.
قم بإنشاء واحد للاتصال بتطبيق BLACK ROOM لسطح المكتب."""
        ),
    },
    "api_key_info": {
        "uk": (
            """🔑 <b>Ваш API ключ</b>

Ключ: <code>{prefix}••••••••</code>
Створено: {created}
Останнє використання: {last_used}

⚠️ Не діліться ключем з іншими!"""
        ),
        "en": (
            """🔑 <b>Your API Key</b>

Key: <code>{prefix}••••••••</code>
Created: {created}
Last used: {last_used}

⚠️ Never share your key with others!"""
        ),
        "ru": (
            """🔑 <b>Ваш API ключ</b>

Ключ: <code>{prefix}••••••••</code>
Создан: {created}
Последнее использование: {last_used}

⚠️ Не делитесь ключом с другими!"""
        ),
        "ar": (
            """🔑 <b>مفتاح API الخاص بك</b>

المفتاح: <code>{prefix}••••••••</code>
تم إنشاؤه: {created}
آخر استخدام: {last_used}

⚠️ لا تشارك مفتاحك مع الآخرين!"""
        ),
    },
    "api_key_created": {
        "uk": (
            """✅ <b>Ключ створено!</b>

<code>{api_key}</code>

⚠️ Скопіюйте його зараз — він більше не буде показаний!
Вставте його в десктоп-додатку BLACK ROOM."""
        ),
        "en": (
            """✅ <b>Key Generated!</b>

<code>{api_key}</code>

⚠️ Copy it now — it won't be shown again!
Paste it in the BLACK ROOM desktop app."""
        ),
        "ru": (
            """✅ <b>Ключ создан!</b>

<code>{api_key}</code>

⚠️ Скопируйте его сейчас — он больше не будет показан!
Вставьте его в десктоп-приложении BLACK ROOM."""
        ),
        "ar": (
            """✅ <b>تم إنشاء المفتاح!</b>

<code>{api_key}</code>

⚠️ انسخه الآن — لن يتم عرضه مرة أخرى!
الصقه في تطبيق BLACK ROOM لسطح المكتب."""
        ),
    },
    "api_key_revoked": {
        "uk": "🗑 Ключ відкликано. Десктоп-додаток більше не матиме доступу.",
        "en": "🗑 Key revoked. Desktop app will no longer have access.",
        "ru": "🗑 Ключ отозван. Десктоп-приложение больше не будет иметь доступа.",
        "ar": "🗑 تم إلغاء المفتاح. لن يتمكن تطبيق سطح المكتب من الوصول بعد الآن.",
    },
    "total_signals": {
        "uk": "Всього сигналів",
        "en": "Total signals",
        "ru": "Всего сигналов",
        "ar": "إجمالي الإشارات",
    },
    "wins": {
        "uk": "Прибуткових",
        "en": "Wins",
        "ru": "Прибыльных",
        "ar": "الانتصارات",
    },
    "losses": {
        "uk": "Збиткових",
        "en": "Losses",
        "ru": "Убыточных",
        "ar": "الخسائر",
    },
    "active": {
        "uk": "Активних",
        "en": "Active",
        "ru": "Активных",
        "ar": "نشط",
    },
    "total_pnl": {
        "uk": "Загальний PnL",
        "en": "Total PnL",
        "ru": "Общий PnL",
        "ar": "إجمالي الأرباح والخسائر",
    },
    "avg_win": {
        "uk": "Середній виграш",
        "en": "Avg win",
        "ru": "Средний профит",
        "ar": "متوسط الربح",
    },
    "avg_loss": {
        "uk": "Середній збиток",
        "en": "Avg loss",
        "ru": "Средний убыток",
        "ar": "متوسط الخسارة",
    },
    "win_streak": {
        "uk": "Серія перемог",
        "en": "Win streak",
        "ru": "Серия побед",
        "ar": "سلسلة انتصارات",
    },
    "loss_streak": {
        "uk": "Серія поразок",
        "en": "Loss streak",
        "ru": "Серия проигрышей",
        "ar": "سلسلة خسائر",
    },
    "avg_holding": {
        "uk": "Середній час",
        "en": "Avg time",
        "ru": "Среднее время",
        "ar": "متوسط الوقت",
    },
    "total": {
        "uk": "Всього",
        "en": "Total",
        "ru": "Всего",
        "ar": "إجمالي",
    },
    "best_trade": {
        "uk": "Найкращий трейд",
        "en": "Best trade",
        "ru": "Лучший трейд",
        "ar": "أفضل صفقة",
    },
    "worst_trade": {
        "uk": "Найгірший трейд",
        "en": "Worst trade",
        "ru": "Худший трейд",
        "ar": "أسوأ صفقة",
    },
    "no_wallets": {
        "uk": "💼 У вас немає гаманців. Додайте через ➕.",
        "en": "💼 No wallets yet. Add one.",
        "ru": "💼 Кошельков нет. Добавьте через ➕.",
        "ar": "💼 لا توجد محافظ بعد. أضف واحدة.",
    },
    "my_wallets_header": {
        "uk": "Мої гаманці",
        "en": "My Wallets",
        "ru": "Мои кошельки",
        "ar": "محافظي",
    },
    "wallet_add_prompt": {
        "uk": "📝 Надішліть адресу гаманця:",
        "en": "📝 Send your wallet address:",
        "ru": "📝 Отправьте адрес кошелька:",
        "ar": "📝 أرسل عنوان محفظتك:",
    },
    "no_data": {
        "uk": "📊 Немає даних за цей період.",
        "en": "📊 No data for this period.",
        "ru": "📊 Нет данных за этот период.",
        "ar": "📊 لا توجد بيانات لهذه الفترة.",
    },
    "no_api_key": {
        "uk": "Ключ не створено. Натисніть кнопку нижче.",
        "en": "No key created yet. Press below.",
        "ru": "Ключ не создан. Нажмите ниже.",
        "ar": "لا مفتاح تم إنشاؤه بعد. اضغط أدناه.",
    },
    "api_key_active": {
        "uk": "✅ Ключ активний",
        "en": "✅ Key is active",
        "ru": "✅ Ключ активен",
        "ar": "✅ المفتاح نشط",
    },
    "expires": {
        "uk": "Діє до",
        "en": "Expires",
        "ru": "Действителен до",
        "ar": "تنتهي صلاحيتها",
    },
    "tier": {
        "uk": "Тариф",
        "en": "Tier",
        "ru": "Тариф",
        "ar": "طبقة",
    },
    "admin_panel_title": {
        "uk": "🔧 <b>Адмін-панель</b>",
        "en": "🔧 <b>Admin Panel</b>",
        "ru": "🔧 <b>Админ-панель</b>",
        "ar": "🔧 <b>لوحة الإدارة</b>",
    },
    "admin_access_denied": {
        "uk": "⛔ Доступ заборонено",
        "en": "⛔ Access denied",
        "ru": "⛔ Доступ запрещён",
        "ar": "⛔ الوصول مرفوض",
    },
    "admin_stats_title": {
        "uk": "🔧 <b>Статистика системи</b>",
        "en": "🔧 <b>System Stats</b>",
        "ru": "🔧 <b>Статистика системы</b>",
        "ar": "🔧 <b>إحصائيات النظام</b>",
    },
    "admin_users_title": {
        "uk": "👥 <b>Останні користувачі</b>",
        "en": "👥 <b>Recent Users</b>",
        "ru": "👥 <b>Последние пользователи</b>",
        "ar": "👥 <b>المستخدمون الجدد</b>",
    },
    "admin_ai_title": {
        "uk": "🧠 <b>Стан AI системи</b>",
        "en": "🧠 <b>AI System Health</b>",
        "ru": "🧠 <b>Состояние AI системы</b>",
        "ar": "🧠 <b>صحة نظام الذكاء الاصطناعي</b>",
    },
    "admin_ai_error": {
        "uk": "❌ Помилка перевірки AI: {error}",
        "en": "❌ AI health check failed: {error}",
        "ru": "❌ Ошибка проверки AI: {error}",
        "ar": "❌ فحص صحة الذكاء الاصطناعي فشل: {error}",
    },
    "admin_scan_started": {
        "uk": "🔄 Сканування запущено...",
        "en": "🔄 Scan started...",
        "ru": "🔄 Сканирование запущено...",
        "ar": "🔄 بدأ الفحص...",
    },
    "admin_scan_complete": {
        "uk": "✅ Сканування завершено. Знайдено <b>{count}</b> нових сигналів.",
        "en": "✅ Scan complete. Found <b>{count}</b> new signals.",
        "ru": "✅ Сканирование завершено. Найдено <b>{count}</b> новых сигналов.",
        "ar": "✅ تم الانتهاء من الفحص. تم العثور على <b>{count}</b> إشارات جديدة.",
    },
    "admin_scan_error": {
        "uk": "❌ Помилка сканування: {error}",
        "en": "❌ Scan error: {error}",
        "ru": "❌ Ошибка сканирования: {error}",
        "ar": "❌ خطأ في المسح: {error}",
    },
    "admin_broadcast_title": {
        "uk": (
            """📨 <b>Розсилка</b>

Надішліть /broadcast &lt;повідомлення&gt; для розсилки всім користувачам."""
        ),
        "en": (
            """📨 <b>Broadcast</b>

Send /broadcast &lt;message&gt; to broadcast to all users."""
        ),
        "ru": (
            """📨 <b>Рассылка</b>

Отправьте /broadcast &lt;сообщение&gt; для рассылки всем пользователям."""
        ),
        "ar": (
            """📨 <b>بث</b>

أرسل /broadcast &lt;رسالة&gt; للبث إلى جميع المستخدمين."""
        ),
    },
    "admin_total_users": {
        "uk": "Всього користувачів",
        "en": "Total users",
        "ru": "Всего пользователей",
        "ar": "إجمالي المستخدمين",
    },
    "admin_active_signals": {
        "uk": "Активних сигналів",
        "en": "Active signals",
        "ru": "Активных сигналов",
        "ar": "الإشارات النشطة",
    },
    "admin_ai_health": {
        "uk": "Стан AI",
        "en": "AI Health",
        "ru": "Состояние AI",
        "ar": "الصحة الذكية",
    },
    "admin_ai_unavailable": {
        "uk": "недоступний",
        "en": "unavailable",
        "ru": "недоступен",
        "ar": "غير متوفر",
    },
    "admin_win_rate": {
        "uk": "Вінрейт",
        "en": "Win Rate",
        "ru": "Винрейт",
        "ar": "نسبة الفوز",
    },
    "admin_min_confidence": {
        "uk": "Мін. впевненість",
        "en": "Min Confidence",
        "ru": "Мин. уверенность",
        "ar": "ثقة الحد الأدنى",
    },
    "admin_btn_stats": {
        "uk": "📊 Статистика",
        "en": "📊 System Stats",
        "ru": "📊 Статистика",
        "ar": "📊 إحصائيات النظام",
    },
    "admin_btn_users": {
        "uk": "👥 Користувачі",
        "en": "👥 Users",
        "ru": "👥 Пользователи",
        "ar": "👥 المستخدمون",
    },
    "admin_btn_scan": {
        "uk": "📡 Сканувати",
        "en": "📡 Force Scan",
        "ru": "📡 Сканировать",
        "ar": "📡 فحص القوة",
    },
    "admin_btn_ai": {
        "uk": "🧠 AI Стан",
        "en": "🧠 AI Health",
        "ru": "🧠 AI Состояние",
        "ar": "🧠 الذكاء الاصطناعي للصحة",
    },
    "admin_btn_broadcast": {
        "uk": "📨 Розсилка",
        "en": "📨 Broadcast",
        "ru": "📨 Рассылка",
        "ar": "📨 بث",
    },
    "choose_language": {
        "uk": "🌐 Оберіть мову:",
        "en": "🌐 Choose language:",
        "ru": "🌐 Выберите язык:",
        "ar": "🌐 اختر اللغة:",
    },
    "alerts_menu": {
        "uk": (
            """🔔 <b>Алерти</b>

Активних: <b>{active}</b> / {limit}

Оберіть дію:"""
        ),
        "en": (
            """🔔 <b>Alerts</b>

Active: <b>{active}</b> / {limit}

Choose an action:"""
        ),
        "ru": (
            """🔔 <b>Алерты</b>

Активных: <b>{active}</b> / {limit}

Выберите действие:"""
        ),
        "ar": (
            """🔔 <b>تنبيهات</b>

نشط: <b>{active}</b> / {limit}

اختر إجراء:"""
        ),
    },
    "alerts_empty": {
        "uk": (
            """📭 У вас немає алертів.

Натисніть <b>➕ Створити</b> щоб додати перший!"""
        ),
        "en": (
            """📭 You have no alerts.

Tap <b>➕ Create</b> to add your first!"""
        ),
        "ru": (
            """📭 У вас нет алертов.

Нажмите <b>➕ Создать</b> чтобы добавить первый!"""
        ),
        "ar": (
            """📭 ليس لديك أي تنبيهات.

اضغط على <b>➕ إنشاء</b> لإضافة أول واحدة!"""
        ),
    },
    "alerts_list_header": {
        "uk": (
            """📋 <b>Ваші алерти:</b>
"""
        ),
        "en": (
            """📋 <b>Your alerts:</b>
"""
        ),
        "ru": (
            """📋 <b>Ваши алерты:</b>
"""
        ),
        "ar": "📋 <b>تنبيهاتك:</b>",
    },
    "alert_list_row": {
        "uk": "{status} <b>{coin}</b> — {type_name} {params_str}",
        "en": "{status} <b>{coin}</b> — {type_name} {params_str}",
        "ru": "{status} <b>{coin}</b> — {type_name} {params_str}",
        "ar": "{status} <b>{coin}</b> — {type_name} {params_str}",
    },
    "alert_choose_coin": {
        "uk": "🪙 Введіть символ монети (наприклад <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
        "en": "🪙 Enter coin symbol (e.g. <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
        "ru": "🪙 Введите символ монеты (например <code>BTC</code>, <code>ETH</code>, <code>SOL</code>):",
        "ar": "🪙 أدخل رمز العملة (مثل <code>BTC</code>، <code>ETH</code>، <code>SOL</code>):",
    },
    "alert_choose_type": {
        "uk": (
            """📋 Обрано: <b>{coin}</b>

Оберіть тип алерту:"""
        ),
        "en": (
            """📋 Selected: <b>{coin}</b>

Choose alert type:"""
        ),
        "ru": (
            """📋 Выбрано: <b>{coin}</b>

Выберите тип алерта:"""
        ),
        "ar": (
            """📋 المحدد: <b>{coin}</b>

اختر نوع التنبيه:"""
        ),
    },
    "alert_enter_price": {
        "uk": "💰 Введіть ціну (USD):",
        "en": "💰 Enter price (USD):",
        "ru": "💰 Введите цену (USD):",
        "ar": "💰 أدخل السعر (دولار أمريكي):",
    },
    "alert_enter_percent": {
        "uk": "📊 Введіть порогове значення у %:",
        "en": "📊 Enter threshold in %:",
        "ru": "📊 Введите пороговое значение в %:",
        "ar": "📊 أدخل العتبة بالنسبه %:",
    },
    "alert_enter_range": {
        "uk": (
            """📏 Введіть діапазон через пробіл: <code>мін макс</code>
(наприклад <code>60000 70000</code>):"""
        ),
        "en": (
            """📏 Enter range separated by space: <code>min max</code>
(e.g. <code>60000 70000</code>):"""
        ),
        "ru": (
            """📏 Введите диапазон через пробел: <code>мин макс</code>
(например <code>60000 70000</code>):"""
        ),
        "ar": "📏 أدخل النطاق مفصولًا بمسافة: <code>min max</code> (مثل <code>60000 70000</code>):",
    },
    "alert_enter_rsi": {
        "uk": "📈 Введіть рівень RSI (1-99):",
        "en": "📈 Enter RSI level (1-99):",
        "ru": "📈 Введите уровень RSI (1-99):",
        "ar": "📈 أدخل مستوى RSI (1-99):",
    },
    "alert_enter_funding": {
        "uk": "💸 Введіть порогове значення funding rate (наприклад <code>0.1</code>):",
        "en": "💸 Enter funding rate threshold (e.g. <code>0.1</code>):",
        "ru": "💸 Введите пороговое значение funding rate (например <code>0.1</code>):",
        "ar": "💸 أدخل حد معدل التمويل (على سبيل المثال <code>0.1</code>):",
    },
    "alert_created": {
        "uk": (
            """✅ Алерт створено!

🪙 <b>{coin}</b>
📋 {type_name}
📌 {params_str}

Ви отримаєте сповіщення, коли умова буде виконана."""
        ),
        "en": (
            """✅ Alert created!

🪙 <b>{coin}</b>
📋 {type_name}
📌 {params_str}

You'll be notified when the condition is met."""
        ),
        "ru": (
            """✅ Алерт создан!

🪙 <b>{coin}</b>
📋 {type_name}
📌 {params_str}

Вы получите уведомление, когда условие будет выполнено."""
        ),
        "ar": (
            """✅ تم إنشاء التنبيه!

🪙 <b>{coin}</b>
📋 {type_name}
📌 {params_str}

ستتلقى إشعارًا عندما يتم استيفاء الشرط."""
        ),
    },
    "alert_limit_reached": {
        "uk": (
            """🔒 Досягнуто ліміт алертів (<b>{limit}</b>).

Оновіть тариф для більше алертів → /subscribe"""
        ),
        "en": (
            """🔒 Alert limit reached (<b>{limit}</b>).

Upgrade your plan for more alerts → /subscribe"""
        ),
        "ru": (
            """🔒 Достигнут лимит алертов (<b>{limit}</b>).

Улучшите тариф для бо́льшего числа алертов → /subscribe"""
        ),
        "ar": (
            """🔒 تم الوصول إلى حد التنبيهات (<b>{limit}</b>).

قم بترقية خطتك للحصول على المزيد من التنبيهات → /subscribe"""
        ),
    },
    "alert_type_locked": {
        "uk": (
            """🔒 Цей тип алерту доступний з тарифу <b>{tier}</b>+

💎 /subscribe"""
        ),
        "en": (
            """🔒 This alert type is available from <b>{tier}</b>+ plan

💎 /subscribe"""
        ),
        "ru": (
            """🔒 Этот тип алерта доступен с тарифа <b>{tier}</b>+

💎 /subscribe"""
        ),
        "ar": (
            """🔒 هذا النوع من التنبيهات متاح من خطة <b>{tier}</b>+

💎 /subscribe"""
        ),
    },
    "alert_deleted": {
        "uk": "🗑 Алерт видалено.",
        "en": "🗑 Alert deleted.",
        "ru": "🗑 Алерт удалён.",
        "ar": "🗑 تم حذف التنبيه.",
    },
    "alert_detail": {
        "uk": (
            """🔔 <b>Алерт #{alert_id}</b>

🪙 Монета: <b>{coin}</b>
📋 Тип: {type_name}
📌 Параметри: {params_str}
📊 Статус: {status}
🔁 Спрацювань: {triggered_count}
⏱ Кулдаун: {cooldown} хв"""
        ),
        "en": (
            """🔔 <b>Alert #{alert_id}</b>

🪙 Coin: <b>{coin}</b>
📋 Type: {type_name}
📌 Parameters: {params_str}
📊 Status: {status}
🔁 Triggers: {triggered_count}
⏱ Cooldown: {cooldown} min"""
        ),
        "ru": (
            """🔔 <b>Алерт #{alert_id}</b>

🪙 Монета: <b>{coin}</b>
📋 Тип: {type_name}
📌 Параметры: {params_str}
📊 Статус: {status}
🔁 Срабатываний: {triggered_count}
⏱ Кулдаун: {cooldown} мин"""
        ),
        "ar": (
            """🔔 <b>تنبيه #{alert_id}</b>

🪙 العملة: <b>{coin}</b>
📋 النوع: {type_name}
📌 المعلمات: {params_str}
📊 الحالة: {status}
🔁 المحفزات: {triggered_count}
⏱ فترة الانتظار: {cooldown} دقيقة"""
        ),
    },
    "alert_invalid_input": {
        "uk": "❌ Невірне значення. Спробуйте ще.",
        "en": "❌ Invalid value. Try again.",
        "ru": "❌ Неверное значение. Попробуйте снова.",
        "ar": "❌ قيمة غير صالحة. حاول مرة أخرى.",
    },
    "alert_coin_not_found": {
        "uk": "❌ Монету <b>{coin}</b> не знайдено. Перевірте символ.",
        "en": "❌ Coin <b>{coin}</b> not found. Check the symbol.",
        "ru": "❌ Монета <b>{coin}</b> не найдена. Проверьте символ.",
        "ar": "❌ العملة <b>{coin}</b> غير موجودة. تحقق من الرمز.",
    },
    "alert.type_price_above": {
        "uk": "📈 Ціна вище",
        "en": "📈 Price above",
        "ru": "📈 Цена выше",
        "ar": "📈 السعر أعلى",
    },
    "alert.type_price_below": {
        "uk": "📉 Ціна нижче",
        "en": "📉 Price below",
        "ru": "📉 Цена ниже",
        "ar": "📉 السعر أدناه",
    },
    "alert.type_change_1h": {
        "uk": "⏱ Зміна за 1г",
        "en": "⏱ 1h change",
        "ru": "⏱ Изменение за 1ч",
        "ar": "⏱ تغيير 1 ساعة",
    },
    "alert.type_change_24h": {
        "uk": "📅 Зміна за 24г",
        "en": "📅 24h change",
        "ru": "📅 Изменение за 24ч",
        "ar": "📅 تغيير 24 ساعة",
    },
    "alert.type_volume_spike": {
        "uk": "📊 Сплеск обсягу",
        "en": "📊 Volume spike",
        "ru": "📊 Всплеск объёма",
        "ar": "📊 ارتفاع في الحجم",
    },
    "alert.type_rsi_overbought": {
        "uk": "🔴 RSI перекуплено",
        "en": "🔴 RSI overbought",
        "ru": "🔴 RSI перекуплен",
        "ar": "🔴 مؤشر القوة النسبية في منطقة الشراء المفرط",
    },
    "alert.type_rsi_oversold": {
        "uk": "🟢 RSI перепродано",
        "en": "🟢 RSI oversold",
        "ru": "🟢 RSI перепродан",
        "ar": "🟢 RSI مفرط البيع",
    },
    "alert.type_macd_cross": {
        "uk": "✖️ MACD перетин",
        "en": "✖️ MACD cross",
        "ru": "✖️ MACD пересечение",
        "ar": "✖️ تقاطع MACD",
    },
    "alert.type_bb_breakout": {
        "uk": "💥 BB пробій",
        "en": "💥 BB breakout",
        "ru": "💥 BB пробой",
        "ar": "💥 اختراق BB",
    },
    "alert.type_new_ath": {
        "uk": "🏔 Новий ATH",
        "en": "🏔 New ATH",
        "ru": "🏔 Новый ATH",
        "ar": "🏔 ATH جديدة",
    },
    "alert.type_new_atl": {
        "uk": "🕳 Новий ATL",
        "en": "🕳 New ATL",
        "ru": "🕳 Новый ATL",
        "ar": "🕳 نيو ATL",
    },
    "alert.type_funding_rate": {
        "uk": "💸 Funding Rate",
        "en": "💸 Funding Rate",
        "ru": "💸 Funding Rate",
        "ar": "💸 معدل التمويل",
    },
    "alert.type_correlation_break": {
        "uk": "🔗 Кореляція",
        "en": "🔗 Correlation",
        "ru": "🔗 Корреляция",
        "ar": "🔗 الارتباط",
    },
    "alert.type_support_hit": {
        "uk": "🛡 Підтримка",
        "en": "🛡 Support hit",
        "ru": "🛡 Поддержка",
        "ar": "🛡 دعم الضربة",
    },
    "alert.type_resistance_hit": {
        "uk": "🧱 Опір",
        "en": "🧱 Resistance hit",
        "ru": "🧱 Сопротивление",
        "ar": "🧱 مقاومة ضربت",
    },
    "alert.type_custom_range": {
        "uk": "📏 Діапазон",
        "en": "📏 Custom range",
        "ru": "📏 Диапазон",
        "ar": "📏 نطاق مخصص",
    },
    "alert.triggered_header": {
        "uk": "🔔 <b>АЛЕРТ СПРАЦЮВАВ!</b>",
        "en": "🔔 <b>ALERT TRIGGERED!</b>",
        "ru": "🔔 <b>АЛЕРТ СРАБОТАЛ!</b>",
        "ar": "🔔 <b>تم تفعيل التنبيه!</b>",
    },
    "alert.price_hit_body": {
        "uk": (
            """🪙 <b>{coin}</b> досяг {target}
💰 Поточна ціна: {price}"""
        ),
        "en": (
            """🪙 <b>{coin}</b> reached {target}
💰 Current price: {price}"""
        ),
        "ru": (
            """🪙 <b>{coin}</b> достиг {target}
💰 Текущая цена: {price}"""
        ),
        "ar": (
            """🪙 <b>{coin}</b> وصلت إلى {target}  
💰 السعر الحالي: {price}"""
        ),
    },
    "alert.change_body": {
        "uk": "🪙 <b>{coin}</b> змінився на {change}",
        "en": "🪙 <b>{coin}</b> changed by {change}",
        "ru": "🪙 <b>{coin}</b> изменился на {change}",
        "ar": "🪙 <b>{coin}</b> تغير بمقدار {change}",
    },
    "alert.rsi_body": {
        "uk": "🪙 <b>{coin}</b> — RSI: {rsi}",
        "en": "🪙 <b>{coin}</b> — RSI: {rsi}",
        "ru": "🪙 <b>{coin}</b> — RSI: {rsi}",
        "ar": "🪙 <b>{coin}</b> — RSI: {rsi}",
    },
    "alert.bb_body": {
        "uk": (
            """🪙 <b>{coin}</b> пробив Bollinger Band ({direction})
💰 Ціна: {price}"""
        ),
        "en": (
            """🪙 <b>{coin}</b> broke Bollinger Band ({direction})
💰 Price: {price}"""
        ),
        "ru": (
            """🪙 <b>{coin}</b> пробил Bollinger Band ({direction})
💰 Цена: {price}"""
        ),
        "ar": (
            """🪙 <b>{coin}</b> اخترق نطاق بولينجر ({direction})
💰 السعر: {price}"""
        ),
    },
    "alert.funding_body": {
        "uk": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
        "en": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
        "ru": "🪙 <b>{coin}</b> — Funding Rate: {rate}",
        "ar": "🪙 <b>{coin}</b> — معدل التمويل: {rate}",
    },
    "alert.level_body": {
        "uk": (
            """🪙 <b>{coin}</b> біля рівня {level}
💰 Ціна: {price}"""
        ),
        "en": (
            """🪙 <b>{coin}</b> near level {level}
💰 Price: {price}"""
        ),
        "ru": (
            """🪙 <b>{coin}</b> у уровня {level}
💰 Цена: {price}"""
        ),
        "ar": (
            """🪙 <b>{coin}</b> بالقرب من المستوى {level}  
💰 السعر: {price}"""
        ),
    },
    "alert.macd_body": {
        "uk": "🪙 <b>{coin}</b> — MACD перетин: {cross}",
        "en": "🪙 <b>{coin}</b> — MACD cross: {cross}",
        "ru": "🪙 <b>{coin}</b> — MACD пересечение: {cross}",
        "ar": "🪙 <b>{coin}</b> — تقاطع MACD: {cross}",
    },
    "alert.ath_body": {
        "uk": (
            """🪙 <b>{coin}</b> 🚀 Новий ATH!
💰 Ціна: {price} (попередній: {ath})"""
        ),
        "en": (
            """🪙 <b>{coin}</b> 🚀 New ATH!
💰 Price: {price} (previous: {ath})"""
        ),
        "ru": (
            """🪙 <b>{coin}</b> 🚀 Новый ATH!
💰 Цена: {price} (предыдущий: {ath})"""
        ),
        "ar": (
            """🪙 <b>{coin}</b> 🚀 أعلى مستوى تاريخي جديد!
💰 السعر: {price} (السابق: {ath})"""
        ),
    },
    "alert.atl_body": {
        "uk": (
            """🪙 <b>{coin}</b> 📉 Новий ATL!
💰 Ціна: {price} (попередній: {atl})"""
        ),
        "en": (
            """🪙 <b>{coin}</b> 📉 New ATL!
💰 Price: {price} (previous: {atl})"""
        ),
        "ru": (
            """🪙 <b>{coin}</b> 📉 Новый ATL!
💰 Цена: {price} (предыдущий: {atl})"""
        ),
        "ar": (
            """🪙 <b>{coin}</b> 📉 أدنى مستوى تاريخي جديد!
💰 السعر: {price} (السابق: {atl})"""
        ),
    },
    "alert.generic_body": {
        "uk": (
            """🪙 <b>{coin}</b>
💰 Ціна: {price}"""
        ),
        "en": (
            """🪙 <b>{coin}</b>
💰 Price: {price}"""
        ),
        "ru": (
            """🪙 <b>{coin}</b>
💰 Цена: {price}"""
        ),
        "ar": (
            """🪙 <b>{coin}</b>  
💰 السعر: {price}"""
        ),
    },
    "btn_alerts": {
        "uk": "🔔 Алерти",
        "en": "🔔 Alerts",
        "ru": "🔔 Алерты",
        "ar": "🔔 تنبيهات",
    },
    "btn_watchlist": {
        "uk": "⭐ Обране",
        "en": "⭐ Watchlist",
        "ru": "⭐ Избранное",
        "ar": "⭐ قائمة المراقبة",
    },
    "btn_create_alert": {
        "uk": "➕ Створити",
        "en": "➕ Create",
        "ru": "➕ Создать",
        "ar": "➕ إنشاء",
    },
    "btn_my_alerts": {
        "uk": "📋 Мої алерти",
        "en": "📋 My alerts",
        "ru": "📋 Мои алерты",
        "ar": "📋 تنبيهاتى",
    },
    "btn_delete_alert": {
        "uk": "🗑 Видалити",
        "en": "🗑 Delete",
        "ru": "🗑 Удалить",
        "ar": "🗑 حذف",
    },
    "btn_toggle_alert": {
        "uk": "⏸ Пауза / ▶️ Увімк.",
        "en": "⏸ Pause / ▶️ Enable",
        "ru": "⏸ Пауза / ▶️ Вкл.",
        "ar": "⏸ إيقاف / ▶️ تفعيل",
    },
    "watchlist_menu": {
        "uk": (
            """⭐ <b>Обране</b>

Ваші відстежувані монети:"""
        ),
        "en": (
            """⭐ <b>Watchlist</b>

Your tracked coins:"""
        ),
        "ru": (
            """⭐ <b>Избранное</b>

Ваши отслеживаемые монеты:"""
        ),
        "ar": (
            """⭐ <b>قائمة المراقبة</b>

العملات التي تتابعها:"""
        ),
    },
    "watchlist_empty": {
        "uk": (
            """📭 Список обраного порожній.

Додайте монету кнопкою <b>➕ Додати</b>."""
        ),
        "en": (
            """📭 Watchlist is empty.

Add a coin with <b>➕ Add</b> button."""
        ),
        "ru": (
            """📭 Избранное пусто.

Добавьте монету кнопкой <b>➕ Добавить</b>."""
        ),
        "ar": (
            """📭 قائمة المراقبة فارغة.

أضف عملة باستخدام زر <b>➕ إضافة</b>."""
        ),
    },
    "watchlist_add_prompt": {
        "uk": "🪙 Введіть символ монети для додавання (наприклад <code>BTC</code>):",
        "en": "🪙 Enter coin symbol to add (e.g. <code>BTC</code>):",
        "ru": "🪙 Введите символ монеты для добавления (например <code>BTC</code>):",
        "ar": "🪙 أدخل رمز العملة لإضافته (مثل <code>BTC</code>):",
    },
    "watchlist_added": {
        "uk": "✅ <b>{coin}</b> додано до обраного!",
        "en": "✅ <b>{coin}</b> added to watchlist!",
        "ru": "✅ <b>{coin}</b> добавлен в избранное!",
        "ar": "✅ <b>{coin}</b> أضيفت إلى قائمة المراقبة!",
    },
    "watchlist_removed": {
        "uk": "🗑 <b>{coin}</b> видалено з обраного.",
        "en": "🗑 <b>{coin}</b> removed from watchlist.",
        "ru": "🗑 <b>{coin}</b> удалён из избранного.",
        "ar": "🗑 <b>{coin}</b> تمت إزالته من قائمة المراقبة.",
    },
    "watchlist_already_exists": {
        "uk": "⚠️ <b>{coin}</b> вже в обраному.",
        "en": "⚠️ <b>{coin}</b> is already in watchlist.",
        "ru": "⚠️ <b>{coin}</b> уже в избранном.",
        "ar": "⚠️ <b>{coin}</b> موجود بالفعل في قائمة المراقبة.",
    },
    "watchlist_row": {
        "uk": "• <b>{coin}</b> — ${price} ({change_24h}%)",
        "en": "• <b>{coin}</b> — ${price} ({change_24h}%)",
        "ru": "• <b>{coin}</b> — ${price} ({change_24h}%)",
        "ar": "• <b>{coin}</b> — ${price} ({change_24h}%)",
    },
    "btn_add_watchlist": {
        "uk": "➕ Додати",
        "en": "➕ Add",
        "ru": "➕ Добавить",
        "ar": "➕ أضف",
    },
    "btn_remove_watchlist": {
        "uk": "🗑 Видалити",
        "en": "🗑 Remove",
        "ru": "🗑 Удалить",
        "ar": "🗑 إزالة",
    },
    "alert_status_active": {
        "uk": "🟢 Активний",
        "en": "🟢 Active",
        "ru": "🟢 Активен",
        "ar": "🟢 نشط",
    },
    "alert_status_paused": {
        "uk": "⏸ Пауза",
        "en": "⏸ Paused",
        "ru": "⏸ Пауза",
        "ar": "⏸ متوقف",
    },
    "alert_status_triggered": {
        "uk": "✅ Спрацював",
        "en": "✅ Triggered",
        "ru": "✅ Сработал",
        "ar": "✅ تم تفعيله",
    },
    "win_rate": {
        "uk": "Вінрейт",
        "en": "Win Rate",
        "ru": "Винрейт",
        "ar": "نسبة الفوز",
    },
    "tp1_rate": {
        "uk": "TP1 Rate",
        "en": "TP1 Rate",
        "ru": "TP1 Rate",
        "ar": "معدل TP1",
    },
    "tp2_rate": {
        "uk": "TP2 Rate",
        "en": "TP2 Rate",
        "ru": "TP2 Rate",
        "ar": "معدل TP2",
    },
    "tp3_rate": {
        "uk": "TP3 Rate",
        "en": "TP3 Rate",
        "ru": "TP3 Rate",
        "ar": "معدل TP3",
    },
    "profit_factor": {
        "uk": "Profit Factor",
        "en": "Profit Factor",
        "ru": "Profit Factor",
        "ar": "عامل الربح",
    },
    "sharpe_ratio": {
        "uk": "Sharpe",
        "en": "Sharpe",
        "ru": "Sharpe",
        "ar": "شارب",
    },
    "sortino_ratio": {
        "uk": "Sortino",
        "en": "Sortino",
        "ru": "Sortino",
        "ar": "سورتينو",
    },
    "max_drawdown": {
        "uk": "Макс. просадка",
        "en": "Max DD",
        "ru": "Макс. просадка",
        "ar": "ماكس DD",
    },
    "longs_label": {
        "uk": "Лонги",
        "en": "Longs",
        "ru": "Лонги",
        "ar": "طويلات",
    },
    "shorts_label": {
        "uk": "Шорти",
        "en": "Shorts",
        "ru": "Шорты",
        "ar": "شورتات",
    },
    "month_short": {
        "uk": "міс",
        "en": "mo",
        "ru": "мес",
        "ar": "مو",
    },
    "btn_wallets": {
        "uk": "💼 Гаманці",
        "en": "💼 Wallets",
        "ru": "💼 Кошельки",
        "ar": "💼 المحافظ",
    },
    "btn_my_wallets": {
        "uk": "Мої гаманці",
        "en": "My Wallets",
        "ru": "Мои кошельки",
        "ar": "محافظي",
    },
    "btn_add_wallet": {
        "uk": "Додати гаманець",
        "en": "Add Wallet",
        "ru": "Добавить кошелёк",
        "ar": "أضف المحفظة",
    },
    "btn_wallet_portfolio": {
        "uk": "Портфель",
        "en": "Portfolio",
        "ru": "Портфель",
        "ar": "محفظة",
    },
    "btn_wallet_txs": {
        "uk": "Транзакції",
        "en": "Transactions",
        "ru": "Транзакции",
        "ar": "المعاملات",
    },
    "btn_wallet_analysis": {
        "uk": "AI Аналітика",
        "en": "AI Analytics",
        "ru": "AI Аналитика",
        "ar": "تحليلات الذكاء الاصطناعي",
    },
    "btn_wallet_remove": {
        "uk": "Видалити",
        "en": "Remove",
        "ru": "Удалить",
        "ar": "إزالة",
    },
    "wallet_menu": {
        "uk": (
            """💼 <b>Трекінг гаманців</b>

Відстежуйте свої блокчейн-гаманці в реальному часі.
Активних: {count}/{limit}"""
        ),
        "en": (
            """💼 <b>Wallet Tracker</b>

Track your blockchain wallets in real-time.
Active: {count}/{limit}"""
        ),
        "ru": (
            """💼 <b>Трекинг кошельков</b>

Отслеживайте свои блокчейн-кошельки в реальном времени.
Активных: {count}/{limit}"""
        ),
        "ar": (
            """💼 <b>متعقب المحفظة</b>

تتبع محافظك على البلوكشين في الوقت الحقيقي.
نشط: {count}/{limit}"""
        ),
    },
    "wallet_empty": {
        "uk": (
            """У вас ще немає відстежуваних гаманців.
Натисніть ➕ щоб додати."""
        ),
        "en": (
            """You have no tracked wallets yet.
Press ➕ to add one."""
        ),
        "ru": (
            """У вас пока нет отслеживаемых кошельков.
Нажмите ➕ чтобы добавить."""
        ),
        "ar": (
            """ليس لديك أي محافظ متعقبة حتى الآن.  
اضغط على ➕ لإضافة واحدة."""
        ),
    },
    "wallet_list_header": {
        "uk": "📋 <b>Ваші гаманці</b> ({count}):",
        "en": "📋 <b>Your wallets</b> ({count}):",
        "ru": "📋 <b>Ваши кошельки</b> ({count}):",
        "ar": "📋 <b>محافظك</b> ({count}):",
    },
    "wallet_limit_reached": {
        "uk": (
            """⚠️ Досягнуто ліміт {limit} гаманців (тір {tier}).
Оновіть підписку для більше."""
        ),
        "en": (
            """⚠️ Wallet limit reached ({limit}, tier {tier}).
Upgrade for more."""
        ),
        "ru": (
            """⚠️ Лимит {limit} кошельков (тир {tier}).
Обновите подписку."""
        ),
        "ar": "⚠️ تم الوصول إلى حد المحفظة ({limit}, المستوى {tier}). قم بالترقية للمزيد.",
    },
    "wallet_enter_address": {
        "uk": (
            """📍 Введіть адресу гаманця:

Підтримуються: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron"""
        ),
        "en": (
            """📍 Enter wallet address:

Supported: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron"""
        ),
        "ru": (
            """📍 Введите адрес кошелька:

Поддерживаются: Ethereum, BSC, Arbitrum, Base, Polygon, Solana, Tron"""
        ),
        "ar": (
            """📍 أدخل عنوان المحفظة:

مدعوم: إيثيريوم، بي إس سي، أربيتروم، بيس، بوليغون، سولانا، ترون"""
        ),
    },
    "wallet_invalid_address": {
        "uk": "❌ Невірний формат адреси. Спробуйте ще раз.",
        "en": "❌ Invalid address format. Try again.",
        "ru": "❌ Неверный формат адреса. Попробуйте снова.",
        "ar": "❌ تنسيق العنوان غير صالح. حاول مرة أخرى.",
    },
    "wallet_unknown_chain": {
        "uk": "❌ Не вдалося визначити мережу. Перевірте адресу.",
        "en": "❌ Could not detect chain. Check the address.",
        "ru": "❌ Не удалось определить сеть. Проверьте адрес.",
        "ar": "❌ لم يتمكن من اكتشاف السلسلة. تحقق من العنوان.",
    },
    "wallet_select_chain": {
        "uk": "🔗 Оберіть мережу для цієї EVM адреси:",
        "en": "🔗 Select chain for this EVM address:",
        "ru": "🔗 Выберите сеть для этого EVM адреса:",
        "ar": "🔗 اختر سلسلة لهذا عنوان EVM:",
    },
    "wallet_invalid_chain": {
        "uk": "❌ Невірна мережа.",
        "en": "❌ Invalid chain.",
        "ru": "❌ Неверная сеть.",
        "ar": "❌ سلسلة غير صالحة.",
    },
    "wallet_enter_label": {
        "uk": "🏷 Введіть назву для гаманця (або <b>-</b> щоб пропустити):",
        "en": "🏷 Enter a label for the wallet (or <b>-</b> to skip):",
        "ru": "🏷 Введите название кошелька (или <b>-</b> чтобы пропустить):",
        "ar": "🏷 أدخل تسمية للمحفظة (أو <b>-</b> لتخطي):",
    },
    "wallet_added": {
        "uk": (
            """✅ Гаманець <b>{label}</b> [{chain}] додано!
Перше сканування почнеться автоматично."""
        ),
        "en": (
            """✅ Wallet <b>{label}</b> [{chain}] added!
First scan will start automatically."""
        ),
        "ru": (
            """✅ Кошелёк <b>{label}</b> [{chain}] добавлен!
Первое сканирование начнётся автоматически."""
        ),
        "ar": (
            """✅ المحفظة <b>{label}</b> [{chain}] تمت إضافتها!  
سيبدأ الفحص الأول تلقائيًا."""
        ),
    },
    "wallet_removed": {
        "uk": "🗑 Гаманець видалено.",
        "en": "🗑 Wallet removed.",
        "ru": "🗑 Кошелёк удалён.",
        "ar": "🗑 تمت إزالة المحفظة.",
    },
    "wallet_not_found": {
        "uk": "❌ Гаманець не знайдено.",
        "en": "❌ Wallet not found.",
        "ru": "❌ Кошелёк не найден.",
        "ar": "❌ المحفظة غير موجودة.",
    },
    "wallet_err_unknown_chain": {
        "uk": "❌ Не вдалося визначити мережу.",
        "en": "❌ Could not detect chain.",
        "ru": "❌ Не удалось определить сеть.",
        "ar": "❌ لم يتمكن من اكتشاف السلسلة.",
    },
    "wallet_err_user_not_found": {
        "uk": "❌ Користувача не знайдено.",
        "en": "❌ User not found.",
        "ru": "❌ Пользователь не найден.",
        "ar": "❌ المستخدم غير موجود.",
    },
    "wallet_err_limit_reached": {
        "uk": "⚠️ Досягнуто ліміт гаманців. Оновіть підписку.",
        "en": "⚠️ Wallet limit reached. Upgrade your subscription.",
        "ru": "⚠️ Лимит кошельков. Обновите подписку.",
        "ar": "⚠️ تم الوصول إلى حد المحفظة. قم بترقية اشتراكك.",
    },
    "wallet_err_already_tracked": {
        "uk": "ℹ️ Цей гаманець вже відстежується.",
        "en": "ℹ️ This wallet is already tracked.",
        "ru": "ℹ️ Этот кошелёк уже отслеживается.",
        "ar": "ℹ️ هذه المحفظة مُتَتبَّعة بالفعل.",
    },
    "wallet_error": {
        "uk": "❌ Помилка. Спробуйте ще раз.",
        "en": "❌ Error. Try again.",
        "ru": "❌ Ошибка. Попробуйте снова.",
        "ar": "❌ خطأ. حاول مرة أخرى.",
    },
    "wallet_portfolio_empty": {
        "uk": "📊 Портфель порожній — токенів не знайдено.",
        "en": "📊 Portfolio empty — no tokens found.",
        "ru": "📊 Портфель пуст — токенов не найдено.",
        "ar": "📊 المحفظة فارغة — لم يتم العثور على رموز.",
    },
    "wallet_pro_required": {
        "uk": "🔒 Ця функція доступна з PRO підписки.",
        "en": "🔒 This feature requires PRO subscription.",
        "ru": "🔒 Эта функция доступна с PRO подписки.",
        "ar": "🔒 هذه الميزة تتطلب اشتراك PRO.",
    },
    "wallet_no_txs": {
        "uk": "📝 Транзакцій поки не знайдено.",
        "en": "📝 No transactions found yet.",
        "ru": "📝 Транзакции пока не найдены.",
        "ar": "📝 لم يتم العثور على أي معاملات بعد.",
    },
    "wallet_analyzing": {
        "uk": "🤖 Аналізую портфель...",
        "en": "🤖 Analyzing portfolio...",
        "ru": "🤖 Анализирую портфель...",
        "ar": "🤖 تحليل المحفظة...",
    },
    "wallet_analysis_failed": {
        "uk": "❌ Не вдалося згенерувати аналітику. Спробуйте пізніше.",
        "en": "❌ Failed to generate analysis. Try later.",
        "ru": "❌ Не удалось сгенерировать аналитику. Попробуйте позже.",
        "ar": "❌ فشل في توليد التحليل. حاول لاحقًا.",
    },
    "signal_dm_caption": {
        "uk": (
            """📡 <b>Новий сигнал!</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | 💪 {confidence}%

Натисніть кнопки нижче для деталей."""
        ),
        "en": (
            """📡 <b>New Signal!</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | 💪 {confidence}%

Tap buttons below for details."""
        ),
        "ru": (
            """📡 <b>Новый сигнал!</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | 💪 {confidence}%

Нажмите кнопки ниже для деталей."""
        ),
        "ar": (
            """📡 <b>إشارة جديدة!</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | 💪 {confidence}%

اضغط على الأزرار أدناه للحصول على التفاصيل."""
        ),
    },
    "signal_dm_caption_free": {
        "uk": (
            """📡 <b>Новий сигнал!</b>

🪙 <b>{coin}</b> {direction}
🎯 Потенціал: +{potential}%

🔒 Точні рівні доступні на Pro/Elite"""
        ),
        "en": (
            """📡 <b>New Signal!</b>

🪙 <b>{coin}</b> {direction}
🎯 Potential: +{potential}%

🔒 Exact levels available on Pro/Elite"""
        ),
        "ru": (
            """📡 <b>Новый сигнал!</b>

🪙 <b>{coin}</b> {direction}
🎯 Потенциал: +{potential}%

🔒 Точные уровни доступны на Pro/Elite"""
        ),
        "ar": (
            """📡 <b>إشارة جديدة!</b>

🪙 <b>{coin}</b> {direction}
🎯 الإمكانية: +{potential}%

🔒 المستويات الدقيقة متاحة على Pro/Elite"""
        ),
    },
    "signal_dm_detail": {
        "uk": (
            """🔍 <b>Деталі сигналу #{signal_id}</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Вхід: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 AI Впевненість: {confidence}%
⚡ Плече: x{leverage}"""
        ),
        "en": (
            """🔍 <b>Signal Details #{signal_id}</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Entry: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 AI Confidence: {confidence}%
⚡ Leverage: x{leverage}"""
        ),
        "ru": (
            """🔍 <b>Детали сигнала #{signal_id}</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Вход: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 Уверенность AI: {confidence}%
⚡ Плечо: x{leverage}"""
        ),
        "ar": (
            """🔍 <b>تفاصيل الإشارة #{signal_id}</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ الدخول: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 ثقة الذكاء الاصطناعي: {confidence}%
⚡ الرافعة المالية: x{leverage}"""
        ),
    },
    "signal_dm_detail_elite": {
        "uk": (
            """👑 <b>Сигнал #{signal_id} — Elite</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Вхід: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 AI Впевненість: {confidence}%
⚡ Плече: x{leverage}

🧠 <b>AI Аналіз:</b>
<i>{reasoning}</i>"""
        ),
        "en": (
            """👑 <b>Signal #{signal_id} — Elite</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Entry: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 AI Confidence: {confidence}%
⚡ Leverage: x{leverage}

🧠 <b>AI Analysis:</b>
<i>{reasoning}</i>"""
        ),
        "ru": (
            """👑 <b>Сигнал #{signal_id} — Elite</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ Вход: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 Уверенность AI: {confidence}%
⚡ Плечо: x{leverage}

🧠 <b>AI Анализ:</b>
<i>{reasoning}</i>"""
        ),
        "ar": (
            """👑 <b>إشارة #{signal_id} — النخبة</b>

🪙 <b>{coin}</b> {direction}
📊 {exchange} | ⏰ {timeframe}

▫️ الدخول: <code>${entry}</code>
🎯 TP1: <code>${tp1}</code> ({tp1_pct})
🎯 TP2: <code>${tp2}</code>
🎯 TP3: <code>${tp3}</code>
🛑 SL: <code>${sl}</code> ({sl_pct})

📏 R:R — {rr}
💪 ثقة الذكاء الاصطناعي: {confidence}%
⚡ الرافعة المالية: x{leverage}

🧠 <b>تحليل الذكاء الاصطناعي:</b>
<i>{reasoning}</i>"""
        ),
    },
    "signal_activated": {
        "uk": (
            """✅ <b>Сигнал активовано!</b>

Ви будете отримувати оновлення по цьому сигналу (TP/SL хіти)."""
        ),
        "en": (
            """✅ <b>Signal activated!</b>

You will receive updates for this signal (TP/SL hits)."""
        ),
        "ru": (
            """✅ <b>Сигнал активирован!</b>

Вы будете получать обновления по этому сигналу (TP/SL хиты)."""
        ),
        "ar": (
            """✅ <b>تم تفعيل الإشارة!</b>

ستتلقى تحديثات لهذه الإشارة (ضربات TP/SL)."""
        ),
    },
    "signal_already_activated": {
        "uk": "ℹ️ Ви вже відстежуєте цей сигнал.",
        "en": "ℹ️ You're already tracking this signal.",
        "ru": "ℹ️ Вы уже отслеживаете этот сигнал.",
        "ar": "ℹ️ أنت بالفعل تتبع هذه الإشارة.",
    },
    "signal_not_found": {
        "uk": "❌ Сигнал не знайдено або вже закрито.",
        "en": "❌ Signal not found or already closed.",
        "ru": "❌ Сигнал не найден или уже закрыт.",
        "ar": "❌ الإشارة غير موجودة أو مغلقة بالفعل.",
    },
    "signal_dismissed": {
        "uk": "🗑 Сповіщення видалено.",
        "en": "🗑 Notification dismissed.",
        "ru": "🗑 Уведомление удалено.",
        "ar": "🗑 تم dismiss الإشعار.",
    },
    "signal_update_tp_caption": {
        "uk": (
            """🎯 <b>{header}</b>

🪙 {coin} #{signal_id}
💰 PnL: {pnl}

📊 SL переміщено для захисту прибутку."""
        ),
        "en": (
            """🎯 <b>{header}</b>

🪙 {coin} #{signal_id}
💰 PnL: {pnl}

📊 SL moved to protect profits."""
        ),
        "ru": (
            """🎯 <b>{header}</b>

🪙 {coin} #{signal_id}
💰 PnL: {pnl}

📊 SL перемещён для защиты прибыли."""
        ),
        "ar": (
            """🎯 <b>{header}</b>

🪙 {coin} #{signal_id}
💰 PnL: {pnl}

📊 تم نقل SL لحماية الأرباح."""
        ),
    },
    "signal_update_final_caption": {
        "uk": (
            """🏁 <b>{header}</b>

🪙 {coin} #{signal_id}
📊 Результат: {pnl}"""
        ),
        "en": (
            """🏁 <b>{header}</b>

🪙 {coin} #{signal_id}
📊 Result: {pnl}"""
        ),
        "ru": (
            """🏁 <b>{header}</b>

🪙 {coin} #{signal_id}
📊 Результат: {pnl}"""
        ),
        "ar": (
            """🏁 <b>{header}</b>

🪙 {coin} #{signal_id}
📊 النتيجة: {pnl}"""
        ),
    },
    "missed_signals_reminder": {
        "uk": (
            """⏰ <b>Пропущені сигнали</b>

Ви пропустили <b>{count}</b> сигналів за останні години.
Перегляньте активні сигнали, щоб не втратити можливість!"""
        ),
        "en": (
            """⏰ <b>Missed Signals</b>

You missed <b>{count}</b> signals in recent hours.
Check active signals to not miss opportunities!"""
        ),
        "ru": (
            """⏰ <b>Пропущенные сигналы</b>

Вы пропустили <b>{count}</b> сигналов за последние часы.
Просмотрите активные сигналы, чтобы не упустить возможность!"""
        ),
        "ar": (
            """⏰ <b>الإشارات المفقودة</b>

لقد فاتتك <b>{count}</b> إشارات في الساعات الأخيرة.
تحقق من الإشارات النشطة حتى لا تفوت الفرص!"""
        ),
    },
    "channel_missed_signal": {
        "uk": (
            """📡 <b>{coin}</b> {direction}

🕐 Цей сигнал вже був відпрацьований
🎯 Результат: <b>{result}</b>

🔒 <i>Отримуйте сигнали в реальному часі з Pro/Elite</i>
💎 @blackroomapp_bot → /subscribe"""
        ),
        "en": (
            """📡 <b>{coin}</b> {direction}

🕐 This signal has already been played
🎯 Result: <b>{result}</b>

🔒 <i>Get real-time signals with Pro/Elite</i>
💎 @blackroomapp_bot → /subscribe"""
        ),
        "ru": (
            """📡 <b>{coin}</b> {direction}

🕐 Этот сигнал уже был отработан
🎯 Результат: <b>{result}</b>

🔒 <i>Получайте сигналы в реальном времени с Pro/Elite</i>
💎 @blackroomapp_bot → /subscribe"""
        ),
        "ar": (
            """📡 <b>{coin}</b> {direction}

🕐 تم تشغيل هذه الإشارة بالفعل
🎯 النتيجة: <b>{result}</b>

🔒 <i>احصل على إشارات في الوقت الحقيقي مع Pro/Elite</i>
💎 @blackroomapp_bot → /subscribe"""
        ),
    },
    "btn_view_details": {
        "uk": "🔍 Деталі",
        "en": "🔍 Details",
        "ru": "🔍 Детали",
        "ar": "🔍 تفاصيل",
    },
    "btn_use_signal": {
        "uk": "✅ Використати",
        "en": "✅ Use Signal",
        "ru": "✅ Использовать",
        "ar": "✅ استخدم Signal",
    },
    "btn_dismiss": {
        "uk": "🗑 Приховати",
        "en": "🗑 Dismiss",
        "ru": "🗑 Скрыть",
        "ar": "🗑 تجاهل",
    },
    "btn_subscribe_pro": {
        "uk": "💎 Підписатись",
        "en": "💎 Subscribe",
        "ru": "💎 Подписаться",
        "ar": "💎 اشترك",
    },
    "btn_view_signal": {
        "uk": "📡 Переглянути",
        "en": "📡 View Signal",
        "ru": "📡 Просмотреть",
        "ar": "📡 عرض الإشارة",
    },
    "btn_view_active": {
        "uk": "📡 Активні сигнали",
        "en": "📡 Active Signals",
        "ru": "📡 Активные сигналы",
        "ar": "📡 إشارات نشطة",
    },
}
