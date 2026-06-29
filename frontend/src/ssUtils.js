export function fmtPrice(n) {
  if (n == null) return "";
  const num = Number(n);
  if (Number.isInteger(num)) return `$${num}`;
  return `$${num.toFixed(num % 1 ? 2 : 0).replace(/\.00$/, "")}`;
}

export function todayPrice(item) {
  return item.current_price ?? item.asking_price;
}

export function isDiscounted(item) {
  const op = Number(item.original_price);
  const tp = Number(todayPrice(item));
  return Boolean(op) && Boolean(tp) && op > tp;
}

export function isUrgent(item) {
  return item.days_remaining != null && item.days_remaining <= 7;
}

export function retailDiscount(item) {
  const op = Number(item.original_price);
  const tp = Number(todayPrice(item));
  if (!op || !tp || op <= tp) return null;
  return Math.round((1 - tp / op) * 100);
}

export const SALE_HEADER = {
  title: "Karthik's moving sale",
  blurb: "70 items · DC pickup · ends June 3",
  sms: "+12026846252",
  smsDisplay: "202-684-6252",
};

// --- Lightweight click/view tracking ---------------------------------------
// Fire-and-forget beacon to /api/events. Never throws, never blocks the UI.
// session_id is a random per-browser token (funnel dedup only, not identity).

function sessionId() {
  try {
    let id = localStorage.getItem("ss_sid");
    if (!id) {
      id = (crypto?.randomUUID?.() ?? String(Math.random()).slice(2));
      localStorage.setItem("ss_sid", id);
    }
    return id;
  } catch {
    return null; // private mode / storage blocked -- still send, just unkeyed
  }
}

export function track(eventType, { listingId = null, target = null } = {}) {
  const body = JSON.stringify({
    event_type: eventType,
    listing_id: listingId,
    target,
    session_id: sessionId(),
  });
  try {
    // sendBeacon survives navigation (key for outbound payment/share clicks).
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/events", new Blob([body], { type: "application/json" }));
      return;
    }
  } catch { /* fall through to fetch */ }
  fetch("/api/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {});
}
