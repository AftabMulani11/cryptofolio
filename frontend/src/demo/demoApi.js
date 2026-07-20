/* eslint-disable */
/**
 * CryptoFolio — Demo Mode
 *
 * Free, static demo for GitHub Pages: mocks the Flask/JWT backend in the
 * browser (auth, portfolio, dashboard, profile — persisted to localStorage)
 * while using Binance's free public REST API for live market data, exactly
 * like the real backend's websocket worker does.
 * Enabled only when REACT_APP_DEMO=true.
 *
 * Demo login (prefilled in the banner): demo / demo123
 */

const LS_KEY = "cryptofolio_demo_v1";
const BINANCE = "https://api.binance.com/api/v3";

const SYMBOL_MAP = {
  BTC: "Bitcoin", ETH: "Ethereum", USDT: "Tether", BNB: "Binance Coin",
  SOL: "Solana", USDC: "USDC", XRP: "Ripple", DOGE: "Dogecoin",
  ADA: "Cardano", AVAX: "Avalanche", SHIB: "Shiba Inu", DOT: "Polkadot",
};

// Static fallback prices if Binance is unreachable
const FALLBACK = {
  BTC: { close: 65000, change: 2.5 }, ETH: { close: 3100, change: -1.2 },
  SOL: { close: 150, change: 4.1 }, BNB: { close: 590, change: 0.8 },
  XRP: { close: 0.52, change: -0.5 }, DOGE: { close: 0.12, change: 1.9 },
  ADA: { close: 0.45, change: -2.1 }, DOT: { close: 6.8, change: 0.4 },
};

// ---------- live market data (free public Binance REST) ----------
let tickerCache = { at: 0, data: {} };

async function liveTickers() {
  if (Date.now() - tickerCache.at < 5000) return tickerCache.data;
  try {
    const res = await fetch(`${BINANCE}/ticker/24hr`);
    if (!res.ok) throw new Error("binance http " + res.status);
    const list = await res.json();
    const data = {};
    for (const t of list) {
      if (!t.symbol.endsWith("USDT")) continue;
      data[t.symbol.toLowerCase()] = {
        symbol: t.symbol,
        close: parseFloat(t.lastPrice),
        change: parseFloat(t.priceChangePercent),
        high: parseFloat(t.highPrice),
        low: parseFloat(t.lowPrice),
        volume: parseFloat(t.quoteVolume),
      };
    }
    tickerCache = { at: Date.now(), data };
    return data;
  } catch (e) {
    const data = {};
    for (const [sym, v] of Object.entries(FALLBACK)) {
      data[`${sym.toLowerCase()}usdt`] = { symbol: `${sym}USDT`, close: v.close, change: v.change, high: v.close * 1.03, low: v.close * 0.97, volume: 1e9 };
    }
    return data;
  }
}

// ---------- persistent demo store ----------
function seedStore() {
  const day = (off) => {
    const d = new Date();
    d.setDate(d.getDate() - off);
    return d.toISOString().split("T")[0];
  };
  const tx = (id, type, coin, symbol, amount, price, off) => ({
    tx_id: String(Date.now() - off * 86400000 - id),
    type, coin, symbol,
    amount: String(amount), price: String(price),
    date: day(off), timestamp: Date.now() - off * 86400000,
  });
  return {
    user: {
      username: "demo", password: "demo123", name: "Demo User",
      email: "demo@cryptofolio.app", join_date: day(210),
    },
    transactions: [
      tx(1, "buy", "Bitcoin", "BTC", 0.08, 51200, 180),
      tx(2, "buy", "Ethereum", "ETH", 1.5, 2650, 150),
      tx(3, "buy", "Solana", "SOL", 12, 98, 120),
      tx(4, "buy", "Bitcoin", "BTC", 0.04, 58900, 90),
      tx(5, "sell", "Solana", "SOL", 4, 145, 45),
      tx(6, "buy", "Dogecoin", "DOGE", 5000, 0.095, 30),
      tx(7, "buy", "Cardano", "ADA", 800, 0.41, 14),
    ],
  };
}

function loadStore() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  const s = seedStore();
  saveStore(s);
  return s;
}
function saveStore(s) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch (e) {}
}

// ---------- portfolio math (mirrors backend operations.py) ----------
function computeStats(transactions, ws) {
  const holdings = {}, buyStats = {};
  let totalInvested = 0, totalSold = 0;
  const sorted = [...transactions].sort((a, b) => Number(a.tx_id) - Number(b.tx_id));
  for (const t of sorted) {
    const amt = parseFloat(t.amount), price = parseFloat(t.price);
    holdings[t.symbol] = holdings[t.symbol] || 0;
    if (t.type === "buy") {
      holdings[t.symbol] += amt;
      totalInvested += amt * price;
      buyStats[t.symbol] = buyStats[t.symbol] || { qty: 0, cost: 0 };
      buyStats[t.symbol].qty += amt;
      buyStats[t.symbol].cost += amt * price;
    } else {
      holdings[t.symbol] -= amt;
      totalSold += amt * price;
    }
  }

  const assets = [];
  let totalBalance = 0;
  for (const [sym, qty] of Object.entries(holdings)) {
    if (qty <= 1e-8) continue;
    const w = ws[`${sym.toLowerCase()}usdt`] || {};
    const price = w.close || 0;
    const value = qty * price;
    totalBalance += value;
    const bs = buyStats[sym];
    const avg = bs && bs.qty > 0 ? bs.cost / bs.qty : 0;
    const costBasis = qty * avg;
    assets.push({
      symbol: sym,
      name: SYMBOL_MAP[sym] || sym,
      price: `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      raw_price: price,
      holdings: qty.toFixed(4),
      value: `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      avg_price: `$${avg.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      allocation: 0,
      change_24h: w.change || 0,
      pnl_percent: costBasis > 0 ? ((value - costBasis) / costBasis) * 100 : 0,
    });
  }
  for (const a of assets) {
    a.allocation = totalBalance > 0 ? (a.raw_price * parseFloat(a.holdings) / totalBalance) * 100 : 0;
  }

  const netProfit = totalBalance + totalSold - totalInvested;
  const profitPercent = totalInvested > 0 ? (netProfit / totalInvested) * 100 : 0;
  let best = null;
  for (const a of assets) if (!best || a.pnl_percent > best.pnl_percent) best = a;

  return {
    assets, totalBalance, totalInvested, totalSold, netProfit, profitPercent,
    bestPerformer: best ? { symbol: best.symbol, pnl_percent: best.pnl_percent } : null,
    tradeCount: transactions.length,
  };
}

const usd = (n) => `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

// ---------- request handler ----------
async function handle(url, opts) {
  const store = loadStore();
  const method = (opts?.method || "GET").toUpperCase();
  let body = {};
  try { body = opts?.body ? JSON.parse(opts.body) : {}; } catch (e) {}
  const u = new URL(url, window.location.origin);
  const path = u.pathname.replace(/^.*?\/api\//, "/api/");
  await new Promise((r) => setTimeout(r, 150 + Math.random() * 200));

  if (path === "/api/login" && method === "POST") {
    if (body.username === store.user.username && body.password === store.user.password) {
      return json({ status: "success", token: "demo-token", username: store.user.username });
    }
    return json({ status: "error", message: "Invalid credentials. Demo login: demo / demo123" }, 401);
  }
  if (path === "/api/signup" && method === "POST") {
    return json({ status: "error", message: "Sign-up is disabled in the demo. Use demo / demo123." }, 400);
  }
  if (path === "/api/password-reset" || path === "/api/password-update") {
    return json({ status: "error", message: "Password changes are disabled in the demo." }, 400);
  }

  if (path === "/api/coins") {
    const ws = await liveTickers();
    const rows = Object.values(ws).sort((a, b) => b.volume - a.volume).slice(0, 100);
    return json(rows.map((c, i) => ({
      rank: i + 1,
      name: SYMBOL_MAP[c.symbol.slice(0, -4)] || c.symbol.slice(0, -4),
      symbol: c.symbol.slice(0, -4),
      price: c.close,
      change_24h: c.change,
      volume: c.volume,
    })));
  }
  if (path === "/api/live-prices") return json(await liveTickers());

  const coinMatch = path.match(/^\/api\/coin\/([^/]+)$/);
  if (coinMatch) {
    const s = coinMatch[1].toUpperCase();
    const ws = await liveTickers();
    const w = ws[`${s.toLowerCase()}usdt`] || {};
    const supply = s === "BTC" ? 19000000 : 1000000000;
    return json({
      name: SYMBOL_MAP[s] || s, symbol: s,
      description: `${SYMBOL_MAP[s] || s} — live market data via Binance public API (demo mode).`,
      current_price: w.close || 0, high_24h: w.high || 0, low_24h: w.low || 0,
      price_change_24h: w.change || 0, market_cap: (w.close || 0) * supply,
      total_volume: w.volume || 0, image: null,
    });
  }

  if (path === "/api/history") {
    const symbol = u.searchParams.get("symbol"), date = u.searchParams.get("date");
    try {
      const ts = new Date(`${date}T00:00:00Z`).getTime();
      const res = await fetch(`${BINANCE}/klines?symbol=${symbol.toUpperCase()}USDT&interval=1d&startTime=${ts}&limit=1`);
      const rows = await res.json();
      return json({ price: parseFloat(rows[0][4]) });
    } catch (e) {
      return json({ price: null });
    }
  }

  const holdMatch = path.match(/^\/api\/holdings\/([^/]+)$/);
  if (holdMatch) {
    const s = holdMatch[1].toUpperCase();
    let total = 0;
    for (const t of store.transactions) {
      if (t.symbol === s) total += (t.type === "buy" ? 1 : -1) * parseFloat(t.amount);
    }
    return json({ holdings: total });
  }

  if (path === "/api/portfolio") {
    if (method === "GET") {
      return json([...store.transactions].sort((a, b) => Number(b.tx_id) - Number(a.tx_id)));
    }
    if (method === "POST") {
      const s = (body.symbol || "UNK").toUpperCase();
      if ((body.type || "buy").toLowerCase() === "sell") {
        let bal = 0;
        for (const t of store.transactions) if (t.symbol === s) bal += (t.type === "buy" ? 1 : -1) * parseFloat(t.amount);
        if (bal - parseFloat(body.amount || 0) < -1e-8) {
          return json({ error: `Insufficient funds. You hold ${bal.toFixed(4)} ${s}.` }, 400);
        }
      }
      store.transactions.push({
        tx_id: String(Date.now()),
        type: (body.type || "buy").toLowerCase(),
        coin: body.coin || SYMBOL_MAP[s] || s,
        symbol: s,
        amount: String(body.amount || 0),
        price: String(body.price || 0),
        date: body.date || new Date().toISOString().split("T")[0],
        timestamp: Date.now(),
      });
      saveStore(store);
      return json({ status: "success" });
    }
    if (method === "PUT") {
      const t = store.transactions.find((x) => x.tx_id === body.tx_id);
      if (!t) return json({ error: "Transaction not found" }, 400);
      Object.assign(t, {
        amount: String(body.amount ?? t.amount),
        price: String(body.price ?? t.price),
        type: (body.type || t.type).toLowerCase(),
        date: body.date || t.date,
      });
      saveStore(store);
      return json({ status: "success" });
    }
  }

  if (path === "/api/dashboard") {
    const stats = computeStats(store.transactions, await liveTickers());
    return json({
      assets: stats.assets,
      totalBalance: usd(stats.totalBalance),
      totalInvested: usd(stats.totalInvested),
      totalSpentLifetime: usd(stats.totalInvested),
      totalRealizedGain: usd(stats.totalSold),
      totalUnrealizedGain: usd(stats.totalBalance - stats.totalInvested + stats.totalSold),
      netProfit: usd(stats.netProfit),
      profitPercent: `${stats.profitPercent >= 0 ? "+" : ""}${stats.profitPercent.toFixed(2)}%`,
      bestPerformer: stats.bestPerformer,
      totalTrades: stats.tradeCount,
      recentTransactions: [...store.transactions].sort((a, b) => Number(b.tx_id) - Number(a.tx_id)).slice(0, 5),
    });
  }

  if (path === "/api/profile") {
    if (method === "GET") {
      const stats = computeStats(store.transactions, await liveTickers());
      return json({
        name: store.user.name,
        email: store.user.email,
        joinDate: store.user.join_date,
        totalValue: usd(stats.totalBalance),
        totalTrades: stats.tradeCount,
        pnl: `${stats.profitPercent >= 0 ? "+" : ""}${stats.profitPercent.toFixed(2)}%`,
      });
    }
    if (method === "PUT") {
      if (body.name) store.user.name = body.name;
      if (body.email) store.user.email = body.email;
      saveStore(store);
      return json({ status: "success" });
    }
  }

  if (path === "/api/export/all-data") {
    return json({ error: "Excel export is disabled in the demo." }, 400);
  }

  return json({ error: "Not found (demo)" }, 404);
}

export function installDemoApi() {
  const realFetch = window.fetch.bind(window);
  window.fetch = (input, opts) => {
    const url = typeof input === "string" ? input : input.url;
    // pass through absolute external calls (Binance etc.); intercept our /api/*
    if (url && url.includes("/api/") && !/^https?:\/\/(?!(localhost|127\.))/.test(url)) {
      return handle(url, opts);
    }
    return realFetch(input, opts);
  };

  const banner = document.createElement("div");
  banner.setAttribute("style", [
    "position:fixed", "bottom:0", "left:0", "right:0", "z-index:99999",
    "background:#1e1b4b", "color:#e0e7ff", "font:12px/1.6 system-ui,sans-serif",
    "padding:6px 12px", "text-align:center",
  ].join(";"));
  banner.innerHTML =
    '📊 <b>Demo mode</b> — portfolio data is sample data stored in your browser; market prices are live from Binance\'s free public API. ' +
    'Login: <b>demo</b> / <b>demo123</b> ' +
    '<button id="cf-demo-reset" style="margin-left:8px;background:#818cf8;color:#1e1b4b;border:0;border-radius:4px;padding:2px 8px;cursor:pointer;font-weight:600">Reset data</button>';
  const attach = () => document.body && document.body.appendChild(banner);
  if (document.body) attach();
  else document.addEventListener("DOMContentLoaded", attach);
  banner.addEventListener("click", (e) => {
    if (e.target && e.target.id === "cf-demo-reset") {
      localStorage.removeItem(LS_KEY);
      window.location.reload();
    }
  });
}
