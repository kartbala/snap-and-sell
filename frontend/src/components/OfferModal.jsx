import { useState } from "react";

const RESULT_ICONS = {
  accepted: "\u2705",
  rejected: "\u274C",
  pending: "\u23F3",
};
const RESULT_TITLES = {
  accepted: "Offer Accepted!",
  rejected: "Offer Declined",
  pending: "Under Review",
};

export default function OfferModal({ listing, onClose }) {
  const [form, setForm] = useState({
    buyer_name: "",
    buyer_phone: "",
    buyer_email: "",
    offer_amount: "",
    message: "",
  });
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch("/api/offers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          listing_id: listing.id,
          buyer_name: form.buyer_name,
          buyer_phone: form.buyer_phone,
          buyer_email: form.buyer_email || null,
          offer_amount: parseFloat(form.offer_amount),
          message: form.message || null,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } catch {
      setError("Could not connect. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit =
    form.buyer_name.trim() &&
    form.buyer_phone.trim() &&
    parseFloat(form.offer_amount) > 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ marginBottom: "var(--space-xs)" }}>Make an Offer</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-sm)", marginBottom: "var(--space-lg)" }}>
              {listing.title} &mdash;{" "}
              <span style={{ color: "var(--accent-teal)", fontWeight: 600 }}>
                ${Number(listing.asking_price).toFixed(2)}
              </span>
            </p>
          </div>
          <button
            className="btn btn-ghost"
            onClick={onClose}
            style={{ minWidth: "auto", padding: "8px 14px", fontSize: "var(--text-lg)" }}
            aria-label="Close"
          >
            &#10005;
          </button>
        </div>

        {result ? (
          /* ---- Result display ---- */
          <div className={`offer-result result-${result.decision}`}>
            <div style={{ fontSize: 56, marginBottom: "var(--space-sm)" }}>
              {RESULT_ICONS[result.decision]}
            </div>
            <h3>{RESULT_TITLES[result.decision]}</h3>
            <p>{result.message}</p>
            <button
              className="btn btn-ghost"
              onClick={onClose}
              style={{ marginTop: "var(--space-lg)" }}
            >
              Close
            </button>
          </div>
        ) : (
          /* ---- Form ---- */
          <form onSubmit={handleSubmit}>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
              <div>
                <label htmlFor="buyer_name">Your Name *</label>
                <input
                  id="buyer_name"
                  name="buyer_name"
                  type="text"
                  placeholder="Your full name"
                  value={form.buyer_name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div>
                <label htmlFor="buyer_phone">Phone Number *</label>
                <input
                  id="buyer_phone"
                  name="buyer_phone"
                  type="tel"
                  placeholder="(202) 555-1234"
                  value={form.buyer_phone}
                  onChange={handleChange}
                  required
                />
              </div>

              <div>
                <label htmlFor="buyer_email">Email (optional)</label>
                <input
                  id="buyer_email"
                  name="buyer_email"
                  type="email"
                  placeholder="you@example.com"
                  value={form.buyer_email}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label htmlFor="offer_amount">Your Offer *</label>
                <div style={{ position: "relative" }}>
                  <span
                    style={{
                      position: "absolute",
                      left: 16,
                      top: "50%",
                      transform: "translateY(-50%)",
                      color: "var(--text-muted)",
                      fontSize: "var(--text-lg)",
                      fontWeight: 700,
                    }}
                  >
                    $
                  </span>
                  <input
                    id="offer_amount"
                    name="offer_amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0.00"
                    value={form.offer_amount}
                    onChange={handleChange}
                    required
                    style={{ paddingLeft: 36 }}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="message">Message (optional)</label>
                <textarea
                  id="message"
                  name="message"
                  rows={3}
                  placeholder="Any notes for the seller..."
                  value={form.message}
                  onChange={handleChange}
                  style={{ resize: "vertical", minHeight: 80 }}
                />
              </div>

              {error && (
                <p style={{ color: "var(--accent-coral)", fontWeight: 600 }}>
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={!canSubmit || submitting}
                style={{ width: "100%", fontSize: "var(--text-lg)", padding: "var(--space-md)" }}
              >
                {submitting ? "Submitting..." : "Submit Offer"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
