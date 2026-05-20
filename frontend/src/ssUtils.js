export function fmtPrice(n) {
  if (n == null) return "";
  const num = Number(n);
  if (Number.isInteger(num)) return `$${num}`;
  return `$${num.toFixed(num % 1 ? 2 : 0).replace(/\.00$/, "")}`;
}

export function isDiscounted(item) {
  return (
    item.asking_price != null &&
    item.current_price != null &&
    Number(item.current_price) < Number(item.asking_price)
  );
}

export function isUrgent(item) {
  return item.days_remaining != null && item.days_remaining <= 7;
}

export function retailDiscount(item) {
  const op = Number(item.original_price);
  const ap = Number(item.asking_price);
  if (!op || !ap || op <= ap) return null;
  return Math.round((1 - ap / op) * 100);
}

export const SALE_HEADER = {
  title: "Karthik's moving sale",
  blurb: "70 items · DC pickup · ends June 3",
  sms: "+12026846252",
  smsDisplay: "202-684-6252",
};
