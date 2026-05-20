import { useState } from "react";
import SSIcon from "./SSIcon";
import { fmtPrice } from "../ssUtils";

const SMS_NUMBER = "+12026846252";

function smsHref(item) {
  const body = `Hi! Interested in "${item.title}" at ${fmtPrice(item.current_price ?? item.asking_price)}.`;
  return `sms:${SMS_NUMBER}?&body=${encodeURIComponent(body)}`;
}

export default function OfferForm({ item }) {
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const currentPrice = Number(item.current_price ?? item.asking_price);
  const suggested = Math.round(currentPrice * 0.85);

  const reset = () => {
    setResult(null);
    setError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    const offer = parseFloat(amount);
    if (!offer || !name.trim() || !phone.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/offers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          listing_id: item.id,
          buyer_name: name.trim(),
          buyer_phone: phone.trim(),
          buyer_email: null,
          offer_amount: offer,
          message: msg.trim() || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult({ decision: data.decision, message: data.message, amount: offer });
      } else {
        setError("Something went wrong. Try again.");
      }
    } catch {
      setError("Could not connect. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    if (result.decision === "accepted") {
      return (
        <div className="ss-result accepted">
          <span className="ic"><SSIcon name="check" size={26} stroke={2.5} /></span>
          <div className="body">
            <strong>Accepted — {fmtPrice(result.amount)}</strong>
            {result.message || "I'll text you in a minute to set up pickup."}
            <small>Reply within 24h or the offer releases.</small>
          </div>
        </div>
      );
    }
    if (result.decision === "rejected") {
      return (
        <div className="ss-result rejected">
          <span className="ic"><SSIcon name="x" size={26} stroke={2.5} /></span>
          <div className="body">
            <strong>Below my floor</strong>
            {result.message || `${fmtPrice(result.amount)} is too low. Try closer to ${fmtPrice(Math.round(currentPrice * 0.85))}.`}
            <small>
              <button type="button" className="link" onClick={reset}>
                Make another offer
              </button>
            </small>
          </div>
        </div>
      );
    }
    return (
      <div className="ss-result pending">
        <span className="ic"><SSIcon name="review" size={26} stroke={2.5} /></span>
        <div className="body">
          <strong>I'll review and get back</strong>
          {result.message || `${fmtPrice(result.amount)} is in range but I want to think. You'll hear from me within a few hours.`}
          <small>No need to do anything — I have your number.</small>
        </div>
      </div>
    );
  }

  if (!open) {
    return (
      <div className="ss-offer-buttons">
        <a href={smsHref(item)} className="ss-btn ss-btn-secondary">
          <SSIcon name="sms" size={20} stroke={2} /> Text me
        </a>
        <button type="button" className="ss-btn ss-btn-primary" onClick={() => setOpen(true)}>
          Make an offer
        </button>
      </div>
    );
  }

  return (
    <form className="ss-offer-form" onSubmit={submit}>
      <div>
        <label className="ss-label" htmlFor="off-amt">Your offer</label>
        <div style={{ position: "relative" }}>
          <span
            style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              fontSize: 17,
              fontWeight: 600,
              color: "var(--ink-3)",
            }}
          >
            $
          </span>
          <input
            id="off-amt"
            className="ss-input"
            inputMode="decimal"
            type="text"
            value={amount}
            onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))}
            placeholder={String(suggested)}
            style={{ paddingLeft: 28 }}
            required
          />
        </div>
      </div>
      <div>
        <label className="ss-label" htmlFor="off-name">Your name</label>
        <input
          id="off-name"
          className="ss-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="So I know who I'm talking to"
          required
        />
      </div>
      <div>
        <label className="ss-label" htmlFor="off-phone">Phone</label>
        <input
          id="off-phone"
          className="ss-input"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="(202) 555-1234"
          required
        />
      </div>
      <div>
        <label className="ss-label" htmlFor="off-msg">
          Message <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>· optional</span>
        </label>
        <textarea
          id="off-msg"
          className="ss-input ss-textarea"
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          placeholder="When you can pick up, anything else."
        />
      </div>
      {error && (
        <p style={{ margin: 0, color: "#b8231c", fontWeight: 600, fontSize: 14 }}>{error}</p>
      )}
      <div className="actions">
        <button type="button" className="ss-btn ss-btn-secondary" onClick={() => setOpen(false)}>
          Cancel
        </button>
        <button type="submit" className="ss-btn ss-btn-primary" disabled={submitting}>
          {submitting ? "Sending..." : "Send offer"}
        </button>
      </div>
    </form>
  );
}
