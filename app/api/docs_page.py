"""
API documentation — interactive HTML page served at root /.
Documents Desktop API (per-user auth) and Public API (no auth).
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BLACK ROOM &mdash; API Documentation</title>
<style>
  :root {
    --bg: #0a0a0f;
    --bg2: #12121a;
    --bg3: #1a1a2e;
    --accent: #6c63ff;
    --accent2: #a29bfe;
    --green: #00e676;
    --red: #ff5252;
    --orange: #ffab40;
    --cyan: #18ffff;
    --text: #e0e0e0;
    --text2: #9e9e9e;
    --border: #2a2a3e;
    --radius: 12px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }

  .header {
    background: linear-gradient(135deg, var(--bg2) 0%, var(--bg3) 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 0 32px;
    text-align: center;
  }
  .header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }
  .header p { color: var(--text2); font-size: 1rem; max-width: 600px; margin: 0 auto; }
  .badge-row { display: flex; gap: 10px; justify-content: center; margin-top: 16px; flex-wrap: wrap; }
  .badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px; font-size: 0.78rem;
    font-weight: 600; border: 1px solid var(--border); background: var(--bg);
  }
  .badge .dot { width: 8px; height: 8px; border-radius: 50%; }
  .badge .dot.green { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .badge .dot.purple { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
  .badge .dot.orange { background: var(--orange); box-shadow: 0 0 6px var(--orange); }
  .badge .dot.cyan { background: var(--cyan); box-shadow: 0 0 6px var(--cyan); }

  .container { max-width: 960px; margin: 0 auto; padding: 32px 20px 60px; }

  .nav-tabs { display: flex; gap: 8px; margin-bottom: 28px; flex-wrap: wrap; }
  .nav-tab {
    padding: 8px 20px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
    cursor: pointer; border: 1px solid var(--border); background: var(--bg2);
    color: var(--text2); transition: all 0.2s;
  }
  .nav-tab:hover { border-color: var(--accent); color: var(--text); }
  .nav-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }

  .tab-content { display: none; }
  .tab-content.active { display: block; }

  .auth-block {
    background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 20px 24px; margin-bottom: 28px;
  }
  .auth-block h3 { font-size: 0.95rem; color: var(--orange); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
  .auth-block code {
    background: var(--bg); padding: 3px 10px; border-radius: 6px; font-size: 0.85rem;
    color: var(--cyan); border: 1px solid var(--border);
  }
  .auth-block p { font-size: 0.88rem; color: var(--text2); margin-top: 6px; }

  .section { margin-bottom: 28px; }
  .section-title {
    font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 14px;
    display: flex; align-items: center; gap: 10px;
  }
  .section-title .icon {
    width: 32px; height: 32px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 1rem;
  }
  .section-title .icon.purple { background: rgba(108, 99, 255, 0.15); }
  .section-title .icon.green  { background: rgba(0, 230, 118, 0.15); }
  .section-title .icon.orange { background: rgba(255, 171, 64, 0.15); }
  .section-title .icon.cyan   { background: rgba(24, 255, 255, 0.15); }
  .section-title .icon.red    { background: rgba(255, 82, 82, 0.15); }

  .endpoint {
    background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius);
    margin-bottom: 10px; overflow: hidden; transition: border-color 0.2s;
  }
  .endpoint:hover { border-color: var(--accent); }
  .endpoint-header {
    padding: 14px 20px; display: flex; align-items: center; gap: 14px;
    cursor: pointer; user-select: none;
  }
  .method {
    font-size: 0.72rem; font-weight: 800; padding: 4px 10px; border-radius: 6px;
    letter-spacing: 0.5px; min-width: 48px; text-align: center;
  }
  .method.get  { background: rgba(0, 230, 118, 0.12); color: var(--green); border: 1px solid rgba(0, 230, 118, 0.25); }
  .method.post { background: rgba(108, 99, 255, 0.12); color: var(--accent2); border: 1px solid rgba(108, 99, 255, 0.25); }
  .method.delete { background: rgba(255, 82, 82, 0.12); color: var(--red); border: 1px solid rgba(255, 82, 82, 0.25); }
  .method.ws { background: rgba(24, 255, 255, 0.12); color: var(--cyan); border: 1px solid rgba(24, 255, 255, 0.25); }
  .path { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.9rem; color: #fff; font-weight: 600; }
  .desc { flex: 1; font-size: 0.82rem; color: var(--text2); text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chevron { color: var(--text2); transition: transform 0.2s; font-size: 0.8rem; }
  .endpoint.open .chevron { transform: rotate(90deg); }
  .tier-badge {
    font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 10px;
    letter-spacing: 0.5px; text-transform: uppercase;
  }
  .tier-badge.free { background: rgba(0,230,118,0.12); color: var(--green); }
  .tier-badge.pro { background: rgba(108,99,255,0.12); color: var(--accent2); }
  .tier-badge.elite { background: rgba(255,171,64,0.12); color: var(--orange); }

  .endpoint-body { display: none; padding: 0 20px 18px; border-top: 1px solid var(--border); }
  .endpoint.open .endpoint-body { display: block; padding-top: 16px; }
  .endpoint-body p { font-size: 0.85rem; color: var(--text2); margin-bottom: 12px; }
  .params-title { font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text2); margin-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
  th { text-align: left; padding: 6px 12px; color: var(--text2); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
  td { padding: 8px 12px; border-bottom: 1px solid rgba(42, 42, 62, 0.5); }
  td code { background: var(--bg); padding: 2px 7px; border-radius: 4px; font-size: 0.8rem; color: var(--cyan); }
  .type-tag { font-size: 0.75rem; color: var(--accent2); font-family: monospace; }
  .required { color: var(--red); font-size: 0.7rem; font-weight: 700; }
  .optional { color: var(--text2); font-size: 0.7rem; }

  .response-block { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-top: 10px; overflow-x: auto; }
  .response-block pre { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.78rem; color: var(--text); white-space: pre; line-height: 1.5; }
  .response-block .key { color: var(--accent2); }
  .response-block .str { color: var(--green); }
  .response-block .num { color: var(--orange); }

  .footer { text-align: center; padding: 32px 20px; color: var(--text2); font-size: 0.8rem; border-top: 1px solid var(--border); }
  .footer a { color: var(--accent2); text-decoration: none; }
  .footer a:hover { text-decoration: underline; }

  @media (max-width: 640px) {
    .header h1 { font-size: 1.6rem; }
    .desc { display: none; }
    .endpoint-header { padding: 12px 14px; gap: 10px; }
  }
</style>
</head>
<body>

<div class="header">
  <h1>&#9679; BLACK ROOM</h1>
  <p>API for Desktop &amp; Mobile apps, websites, and third-party integrations</p>
  <div class="badge-row">
    <div class="badge"><span class="dot green"></span> v2.0</div>
    <div class="badge"><span class="dot purple"></span> Desktop API — 22 endpoints + WS</div>
    <div class="badge"><span class="dot cyan"></span> Public API — 4 endpoints</div>
    <div class="badge"><span class="dot orange"></span> Per-user API Key</div>
  </div>
</div>

<div class="container">

  <div class="nav-tabs">
    <div class="nav-tab active" onclick="switchTab('desktop')">Desktop API</div>
    <div class="nav-tab" onclick="switchTab('public')">Public API</div>
    <div class="nav-tab" onclick="switchTab('websocket')">WebSocket</div>
    <div class="nav-tab" onclick="switchTab('tiers')">Tiers &amp; Limits</div>
  </div>

  <!-- ═══════════════════════════════════════════ -->
  <!-- DESKTOP TAB                                 -->
  <!-- ═══════════════════════════════════════════ -->
  <div id="tab-desktop" class="tab-content active">

    <div class="auth-block">
      <h3>&#x1F512; Authentication</h3>
      <p>All Desktop API endpoints require a per-user API key via header:</p>
      <p style="margin-top:10px"><code>X-API-Key: brk_your_personal_api_key</code></p>
      <p>Generate your key in the Telegram bot: <b>/settings</b> &#8594; <b>API Key</b>. Keys are hashed (SHA-256) — we never store the plain key.</p>
      <p>Requests without a valid key receive <b>401 Unauthorized</b>. Banned/deactivated accounts receive <b>403 Forbidden</b>.</p>
    </div>

    <!-- Profile -->
    <div class="section">
      <div class="section-title"><div class="icon purple">&#x1F464;</div>Profile</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/me</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">User profile, tier, features</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Returns your profile, active subscription, and available features based on tier.</p>
          <div class="response-block"><pre>{
  <span class="key">"id"</span>: <span class="num">42</span>,
  <span class="key">"telegram_id"</span>: <span class="num">123456789</span>,
  <span class="key">"username"</span>: <span class="str">"trader_joe"</span>,
  <span class="key">"tier"</span>: <span class="str">"pro"</span>,
  <span class="key">"subscription"</span>: { <span class="key">"expires_at"</span>: <span class="str">"2026-05-01T00:00:00"</span>, <span class="key">"auto_renew"</span>: <span class="num">true</span> },
  <span class="key">"features"</span>: {
    <span class="key">"signals_full_access"</span>: <span class="num">true</span>,
    <span class="key">"alerts_limit"</span>: <span class="num">20</span>,
    <span class="key">"watchlist_limit"</span>: <span class="num">30</span>,
    <span class="key">"real_time_updates"</span>: <span class="num">true</span>
  }
}</pre></div>
        </div>
      </div>
    </div>

    <!-- System Status -->
    <div class="section">
      <div class="section-title"><div class="icon green">&#x1F4E1;</div>System Status</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/status</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">System health, exchanges, scheduler</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Returns system health: database, Redis, scheduler status, exchange scores, last scan time, active WebSocket connections.</p>
          <div class="response-block"><pre>{
  <span class="key">"db_ok"</span>: <span class="num">true</span>,
  <span class="key">"redis_ok"</span>: <span class="num">true</span>,
  <span class="key">"scheduler_running"</span>: <span class="num">true</span>,
  <span class="key">"scheduler_jobs"</span>: <span class="num">12</span>,
  <span class="key">"last_scan"</span>: <span class="str">"2026-04-03T12:30:00Z"</span>,
  <span class="key">"active_signals"</span>: <span class="num">8</span>,
  <span class="key">"exchanges"</span>: {
    <span class="key">"binance"</span>: { <span class="key">"score"</span>: <span class="num">0.95</span>, <span class="key">"success_rate"</span>: <span class="num">0.99</span> },
    <span class="key">"bybit"</span>: { <span class="key">"score"</span>: <span class="num">0.91</span>, <span class="key">"success_rate"</span>: <span class="num">0.97</span> }
  }
}</pre></div>
        </div>
      </div>
    </div>

    <!-- Signals -->
    <div class="section">
      <div class="section-title"><div class="icon green">&#x1F4C8;</div>Signals</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/signals</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Paginated signals list</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Paginated signals. FREE users see limited details on PRO/ELITE signals. FREE users only see last 7 days of closed signals.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>status</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>active, closed, all</td></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>Filter by coin (e.g. BTC)</td></tr>
            <tr><td><code>direction</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>long / short</td></tr>
            <tr><td><code>page</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Page number (default 1)</td></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-100 (default 20)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/signals/active</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Active signals only</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Returns all currently active signals. Optimized for dashboard view — no pagination needed.</p></div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/signals/{id}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Signal detail + update history</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Full signal with TP/SL levels, AI reasoning, PnL stats, and chronological update history. ELITE users also see <code>factors</code> breakdown (regime, ML gate, indicators, correlation data).</p>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="section">
      <div class="section-title"><div class="icon purple">&#x1F4CA;</div>Stats</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/stats</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Performance: win rate, PnL, user data</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Global performance stats (total signals, win rate, average PnL, total PnL, 30-day count) plus user-specific data (alerts count, watchlist count).</p>
          <div class="response-block"><pre>{
  <span class="key">"global"</span>: {
    <span class="key">"total_signals"</span>: <span class="num">580</span>,
    <span class="key">"win_rate"</span>: <span class="num">68.5</span>,
    <span class="key">"average_pnl"</span>: <span class="num">3.42</span>,
    <span class="key">"total_pnl"</span>: <span class="num">1540.50</span>
  },
  <span class="key">"user"</span>: {
    <span class="key">"tier"</span>: <span class="str">"pro"</span>,
    <span class="key">"alerts_active"</span>: <span class="num">5</span>,
    <span class="key">"watchlist_size"</span>: <span class="num">12</span>
  }
}</pre></div>
        </div>
      </div>
    </div>

    <!-- Market -->
    <div class="section">
      <div class="section-title"><div class="icon cyan">&#x1F4B0;</div>Market Data</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/market</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Top coins by volume with prices</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Top coins ranked by 24h volume. Includes latest price, volume, 1h/24h/7d change, market cap, and logo.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-200 (default 50)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/market/{coin}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Coin detail: multi-exchange prices + history</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Single coin with prices across all exchanges, price history chart data, and active signals for this coin.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>hours</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Price history window, 1-168h (default 24)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/candles/{coin}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">OHLCV candle data for charting</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Historical OHLCV candle data. Tier-gated: FREE (1h+4h, last 24h), PRO (all timeframes, 7 days), ELITE (full history).</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>exchange</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>e.g. binance, bybit</td></tr>
            <tr><td><code>timeframe</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>15m, 1h, 4h, 1d (default 1h)</td></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-1000 (default 200)</td></tr>
            <tr><td><code>from_ts</code></td><td class="type-tag">ISO date</td><td class="optional">opt</td><td>Start date</td></tr>
            <tr><td><code>to_ts</code></td><td class="type-tag">ISO date</td><td class="optional">opt</td><td>End date</td></tr>
          </table>
          <div class="response-block"><pre>{
  <span class="key">"coin"</span>: <span class="str">"BTC"</span>,
  <span class="key">"timeframe"</span>: <span class="str">"1h"</span>,
  <span class="key">"candles"</span>: [
    { <span class="key">"t"</span>: <span class="str">"2026-04-03T00:00:00"</span>, <span class="key">"o"</span>: <span class="num">67500</span>, <span class="key">"h"</span>: <span class="num">68200</span>, <span class="key">"l"</span>: <span class="num">67100</span>, <span class="key">"c"</span>: <span class="num">67900</span>, <span class="key">"v"</span>: <span class="num">1250000</span> }
  ]
}</pre></div>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/candles/{coin}/exchanges</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Available exchanges for a coin</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Returns available exchanges and timeframes with data range for a specific coin.</p></div>
      </div>
    </div>

    <!-- Coins -->
    <div class="section">
      <div class="section-title"><div class="icon orange">&#x1FA99;</div>Coins</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/coins</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Coin list with metadata &amp; logos</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Paginated coin list with logos, market cap, rank. PRO+ gets ATH/ATL, supply data. ELITE gets categories, description, CoinGecko ID.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>search</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>Search by symbol or name</td></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-500 (default 100)</td></tr>
            <tr><td><code>offset</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Pagination offset</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/coins/{symbol}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Detailed coin metadata</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Full coin metadata: logo, name, market cap, rank, supply, ATH/ATL, exchanges where available.</p></div>
      </div>
    </div>

    <!-- AI Analysis -->
    <div class="section">
      <div class="section-title"><div class="icon purple">&#x1F9E0;</div>AI Analysis</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/analysis</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">AI market analysis reports</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>AI-generated market analysis. FREE: today only. PRO: 7 days. ELITE: 90 days + all analysis types.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>analysis_type</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>market_overview, coin_analysis, trend_report</td></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>Filter by coin</td></tr>
            <tr><td><code>days</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-90 (default 7)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/analysis/latest</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Latest daily analysis</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Latest overview, trend report, and coin analyses. FREE users see overview + 3 coin analyses only.</p></div>
      </div>
    </div>

    <!-- News -->
    <div class="section">
      <div class="section-title"><div class="icon cyan">&#x1F4F0;</div>News</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/news</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Crypto news feed</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Latest crypto news with sentiment and importance scoring. FREE: last 24h only. PRO/ELITE: full history.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>Filter by mentioned coin</td></tr>
            <tr><td><code>page</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Page number</td></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-50 (default 20)</td></tr>
          </table>
        </div>
      </div>
    </div>

    <!-- Alerts -->
    <div class="section">
      <div class="section-title"><div class="icon red">&#x1F514;</div>Alerts</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/alerts</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Your active alerts</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Returns your alerts with trigger count, last triggered time, cooldown settings, and tier limit.</p></div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method post">POST</span><span class="path">/desktop/alerts</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Create alert</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Create a price or signal alert. Limits: FREE=3, PRO=20, ELITE=100.</p>
          <div class="params-title">JSON body</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="required">req</td><td>Coin symbol (e.g. BTC)</td></tr>
            <tr><td><code>alert_type</code></td><td class="type-tag">string</td><td class="required">req</td><td>price_above, price_below, new_signal, etc.</td></tr>
            <tr><td><code>params</code></td><td class="type-tag">JSON</td><td class="optional">opt</td><td>Alert parameters</td></tr>
            <tr><td><code>cooldown</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Cooldown minutes (5-1440, default 60)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method delete">DELETE</span><span class="path">/desktop/alerts/{id}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Deactivate alert</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Deactivates the specified alert. Only your own alerts can be deleted.</p></div>
      </div>
    </div>

    <!-- Watchlist -->
    <div class="section">
      <div class="section-title"><div class="icon orange">&#x2B50;</div>Watchlist</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/desktop/watchlist</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Your watched coins with prices</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Returns watched coins with latest prices, 24h change, and volume. Limits: FREE=5, PRO=30, ELITE=100.</p></div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method post">POST</span><span class="path">/desktop/watchlist</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Add coin to watchlist</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <div class="params-title">JSON body</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="required">req</td><td>Coin symbol</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method delete">DELETE</span><span class="path">/desktop/watchlist/{coin}</span>
          <span class="tier-badge free">ALL</span>
          <span class="desc">Remove from watchlist</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body"><p>Removes the coin from your watchlist.</p></div>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════ -->
  <!-- PUBLIC TAB                                  -->
  <!-- ═══════════════════════════════════════════ -->
  <div id="tab-public" class="tab-content">

    <div class="auth-block" style="border-color: var(--green);">
      <h3 style="color: var(--green);">&#x1F513; No Authentication Required</h3>
      <p>Public API endpoints are open to everyone. Designed for marketing websites and third-party integrations.</p>
      <p>All signal data is <b>delayed by 4 hours</b> to protect paying subscribers. Active signals are <b>never</b> exposed.</p>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon green">&#x1F4CA;</div>Public Stats</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/public/stats</span>
          <span class="desc">Aggregate performance for website</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Total signals, win rate, average PnL, total PnL, TP1/2/3 hit rates, total users. Safe for marketing website.</p>
          <div class="response-block"><pre>{
  <span class="key">"total_signals"</span>: <span class="num">580</span>,
  <span class="key">"win_rate"</span>: <span class="num">68.5</span>,
  <span class="key">"avg_pnl_percent"</span>: <span class="num">3.42</span>,
  <span class="key">"total_pnl_percent"</span>: <span class="num">1540.50</span>,
  <span class="key">"tp1_hit_rate"</span>: <span class="num">62.3</span>,
  <span class="key">"tp2_hit_rate"</span>: <span class="num">38.1</span>,
  <span class="key">"tp3_hit_rate"</span>: <span class="num">15.7</span>,
  <span class="key">"total_users"</span>: <span class="num">1580</span>
}</pre></div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon purple">&#x1F4C8;</div>Delayed Signals</div>
      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/public/signals</span>
          <span class="desc">Closed signals (4h delay)</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Recent closed signals delayed by 4 hours. Filter by coin, direction, or result (win/loss).</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>coin</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>Filter by coin</td></tr>
            <tr><td><code>direction</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>long / short</td></tr>
            <tr><td><code>result</code></td><td class="type-tag">string</td><td class="optional">opt</td><td>win, loss, or all</td></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-100 (default 20)</td></tr>
            <tr><td><code>offset</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>Pagination offset</td></tr>
          </table>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon orange">&#x1F3C6;</div>Top Coins &amp; Streaks</div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/public/top-coins</span>
          <span class="desc">Best performing coins by win rate</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Top coins ranked by win rate (minimum 3 closed signals). Returns win/loss counts, avg PnL, best trade.</p>
          <div class="params-title">Query parameters</div>
          <table>
            <tr><th>Param</th><th>Type</th><th></th><th>Description</th></tr>
            <tr><td><code>limit</code></td><td class="type-tag">int</td><td class="optional">opt</td><td>1-50 (default 10)</td></tr>
          </table>
        </div>
      </div>

      <div class="endpoint" onclick="toggle(this)">
        <div class="endpoint-header">
          <span class="method get">GET</span><span class="path">/public/streak</span>
          <span class="desc">Current win/loss streak</span><span class="chevron">&#x25B6;</span>
        </div>
        <div class="endpoint-body">
          <p>Current winning or losing streak, plus last 10 trades summary (wins, losses, avg PnL).</p>
          <div class="response-block"><pre>{
  <span class="key">"current_streak"</span>: <span class="num">5</span>,
  <span class="key">"streak_type"</span>: <span class="str">"win"</span>,
  <span class="key">"last_10_wins"</span>: <span class="num">7</span>,
  <span class="key">"last_10_losses"</span>: <span class="num">3</span>,
  <span class="key">"last_10_avg_pnl"</span>: <span class="num">4.21</span>
}</pre></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════ -->
  <!-- WEBSOCKET TAB                               -->
  <!-- ═══════════════════════════════════════════ -->
  <div id="tab-websocket" class="tab-content">

    <div class="auth-block" style="border-color: var(--cyan);">
      <h3 style="color: var(--cyan);">&#x26A1; WebSocket Protocol</h3>
      <p>Connect to <code>wss://your-domain/desktop/ws</code></p>
      <p>Send an auth message as the <b>first message</b> within 10 seconds:</p>
      <div class="response-block" style="margin-top:10px"><pre>{ <span class="key">"type"</span>: <span class="str">"auth"</span>, <span class="key">"key"</span>: <span class="str">"brk_your_api_key"</span> }</pre></div>
      <p style="margin-top:10px">On success, server responds with:</p>
      <div class="response-block" style="margin-top:6px"><pre>{ <span class="key">"type"</span>: <span class="str">"auth_ok"</span>, <span class="key">"tier"</span>: <span class="str">"pro"</span>, <span class="key">"features"</span>: { ... } }</pre></div>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon green">&#x2B07;&#xFE0F;</div>Server &#8594; Client Messages</div>
      <div class="auth-block" style="border-color: var(--border);">
        <table>
          <tr><th>Type</th><th>When</th><th>Data</th></tr>
          <tr><td><code>signal_new</code></td><td>New signal generated</td><td>signal: {id, coin, direction, entry_price, ...}</td></tr>
          <tr><td><code>signal_update</code></td><td>TP/SL hit, status change</td><td>signal: {id, coin, status, pnl, peak_profit, is_final}</td></tr>
          <tr><td><code>price_alert</code></td><td>User alert triggered</td><td>alert: {coin, type, price, ...}</td></tr>
          <tr><td><code>heartbeat</code></td><td>Every 30 seconds</td><td>ts: ISO timestamp</td></tr>
          <tr><td><code>pong</code></td><td>Response to ping</td><td>ts: ISO timestamp</td></tr>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon purple">&#x2B06;&#xFE0F;</div>Client &#8594; Server Messages</div>
      <div class="auth-block" style="border-color: var(--border);">
        <table>
          <tr><th>Type</th><th>Purpose</th><th>Example</th></tr>
          <tr><td><code>subscribe</code></td><td>Filter updates by coins</td><td><code>{"type":"subscribe","coins":["BTC","ETH"]}</code></td></tr>
          <tr><td><code>ping</code></td><td>Request heartbeat</td><td><code>{"type":"ping"}</code></td></tr>
        </table>
        <p style="margin-top:12px; font-size:0.85rem;">Send an empty <code>coins</code> array to unsubscribe from coin filtering and receive all updates again.</p>
      </div>
    </div>

    <div class="section">
      <div class="section-title"><div class="icon orange">&#x1F6E1;&#xFE0F;</div>Broadcast Rules</div>
      <div class="auth-block" style="border-color: var(--border);">
        <p><b>Tier gating:</b> Signal updates respect the signal's <code>min_tier</code>. If a signal is PRO-only, FREE users will not receive its updates via WebSocket.</p>
        <p style="margin-top:8px"><b>Coin filtering:</b> After sending a <code>subscribe</code> message, you only receive updates for the specified coins. Unfiltered users receive all updates.</p>
        <p style="margin-top:8px"><b>Connection limits:</b> Multiple connections per user are allowed. Each connection shares the same coin filter.</p>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════ -->
  <!-- TIERS TAB                                   -->
  <!-- ═══════════════════════════════════════════ -->
  <div id="tab-tiers" class="tab-content">

    <div class="auth-block" style="border-color: var(--accent);">
      <h3 style="color: var(--accent2);">&#x1F451; Tier Feature Matrix</h3>
      <table style="margin-top:12px">
        <tr><th>Feature</th><th>FREE</th><th>PRO</th><th>ELITE</th></tr>
        <tr><td>Signal coin + direction + confidence</td><td style="color:var(--green)">&#x2705;</td><td style="color:var(--green)">&#x2705;</td><td style="color:var(--green)">&#x2705;</td></tr>
        <tr><td>Full signal details (entry/TP/SL)</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--green)">&#x2705;</td><td style="color:var(--green)">&#x2705;</td></tr>
        <tr><td>AI reasoning &amp; factors</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--green)">&#x2705;</td></tr>
        <tr><td>Signal history</td><td>7 days</td><td>Full</td><td>Full</td></tr>
        <tr><td>Alerts limit</td><td>3</td><td>20</td><td>100</td></tr>
        <tr><td>Watchlist limit</td><td>5</td><td>30</td><td>100</td></tr>
        <tr><td>Real-time WebSocket</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--green)">&#x2705;</td><td style="color:var(--green)">&#x2705;</td></tr>
        <tr><td>Candle data</td><td>1h+4h, 24h</td><td>All TF, 7d</td><td>All TF, full</td></tr>
        <tr><td>News access</td><td>24h</td><td>Full</td><td>Full</td></tr>
        <tr><td>AI analysis</td><td>Today only</td><td>7 days</td><td>90 days</td></tr>
        <tr><td>Coin metadata detail</td><td>Basic</td><td>+ Supply, ATH/ATL</td><td>+ Categories, CoinGecko ID</td></tr>
        <tr><td>Data export</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--red)">&#x274C;</td><td style="color:var(--green)">&#x2705;</td></tr>
      </table>
    </div>

    <div class="auth-block" style="border-color: var(--border);">
      <h3 style="color: var(--text);">&#x1F6E0;&#xFE0F; Rate Limits</h3>
      <table style="margin-top:12px">
        <tr><th>Resource</th><th>Limit</th></tr>
        <tr><td>REST API requests</td><td>60 requests/minute per API key</td></tr>
        <tr><td>WebSocket messages</td><td>10 messages/second per connection</td></tr>
        <tr><td>Signal poll interval</td><td>Recommended: 10s (use WebSocket for real-time)</td></tr>
      </table>
    </div>

    <div class="auth-block" style="border-color: var(--border);">
      <h3 style="color: var(--text);">&#x1F310; Supported Exchanges</h3>
      <p>Data sourced from 8 exchanges via CCXT:</p>
      <div class="badge-row" style="margin-top:12px; justify-content: flex-start;">
        <div class="badge">Binance</div>
        <div class="badge">Bybit</div>
        <div class="badge">OKX</div>
        <div class="badge">KuCoin</div>
        <div class="badge">Gate.io</div>
        <div class="badge">MEXC</div>
        <div class="badge">Bitget</div>
        <div class="badge">HTX</div>
      </div>
    </div>
  </div>

</div>

<div class="footer">
  <p>BLACK ROOM API v2.0 &middot; Powered by FastAPI &middot; <a href="/docs">OpenAPI Docs</a> &middot; <a href="/health">Health Check</a> &middot; <a href="/admin">Admin Panel</a></p>
</div>

<script>
function toggle(el) { el.classList.toggle('open'); }

function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
  document.querySelectorAll('.nav-tab').forEach(function(t) { t.classList.remove('active'); });
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def api_docs_page():
    """Serve the API documentation page."""
    return _HTML
