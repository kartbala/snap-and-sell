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
