export default function MarketplaceCard({ listing, onMakeOffer, animationDelay = 0 }) {
  return (
    <div
      className="card animate-in"
      style={{
        animationDelay: `${animationDelay * 0.08}s`,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
      }}
      onClick={() => onMakeOffer(listing)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onMakeOffer(listing)}
      aria-label={`${listing.title} - $${Number(listing.current_price ?? listing.asking_price).toFixed(2)}`}
    >
      {/* Photo */}
      <div className="photo-placeholder" style={{ marginBottom: "var(--space-md)" }}>
        {listing.photos?.[0] ? (
          <img src={listing.photos[0]} alt={listing.title} />
        ) : (
          <span aria-hidden="true" style={{ fontSize: 56 }}>&#128247;</span>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <h3
          style={{
            fontSize: "var(--text-lg)",
            marginBottom: "var(--space-xs)",
            lineHeight: 1.3,
          }}
        >
          {listing.title}
        </h3>

        {listing.description && (
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "var(--text-sm)",
              marginBottom: "var(--space-md)",
              flex: 1,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {listing.description}
          </p>
        )}

        {listing.price_comps && (() => {
          try {
            const comps = JSON.parse(listing.price_comps);
            if (comps.length === 0) return null;
            const prices = comps.map(c => c.price).filter(Boolean);
            const min = Math.min(...prices);
            const max = Math.max(...prices);
            return (
              <p style={{
                fontSize: "14px",
                color: "var(--text-muted)",
                marginBottom: "var(--space-sm)",
              }}>
                Similar: ${min.toFixed(0)}&ndash;${max.toFixed(0)}
              </p>
            );
          } catch { return null; }
        })()}

        {/* Bottom row: price + condition */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: "auto",
            gap: "var(--space-sm)",
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-sm)" }}>
            <span className="price" style={{ color: "var(--accent-teal)" }}>
              ${listing.current_price != null
                ? Number(listing.current_price).toFixed(2)
                : listing.asking_price != null
                ? Number(listing.asking_price).toFixed(2)
                : "---"}
            </span>
            {listing.current_price != null &&
              listing.asking_price != null &&
              listing.current_price < listing.asking_price && (
              <span style={{
                textDecoration: "line-through",
                color: "var(--text-muted)",
                fontSize: "var(--text-sm)",
              }}>
                ${Number(listing.asking_price).toFixed(2)}
              </span>
            )}
          </div>

          {listing.condition && (
            <span
              className="badge badge-active"
              style={{ fontSize: 14 }}
            >
              {listing.condition}
            </span>
          )}
        </div>
      </div>

      {/* Bottom bar: expiry + tap hint */}
      <div
        style={{
          marginTop: "var(--space-md)",
          textAlign: "center",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          paddingTop: "var(--space-sm)",
        }}
      >
        {listing.days_remaining != null && listing.days_remaining <= 5 && (
          <div style={{
            marginBottom: 4,
            padding: "4px 12px",
            background: listing.days_remaining <= 2
              ? "rgba(233, 69, 96, 0.2)" : "rgba(245, 166, 35, 0.15)",
            color: listing.days_remaining <= 2
              ? "var(--accent-coral)" : "var(--accent-amber)",
            borderRadius: "100px",
            fontSize: "15px",
            fontWeight: 700,
            display: "inline-block",
          }}>
            {listing.days_remaining === 0
              ? "Last day!"
              : `${listing.days_remaining} day${listing.days_remaining !== 1 ? "s" : ""} left`}
          </div>
        )}
        {listing.days_remaining != null && listing.days_remaining > 5 && (
          <p style={{
            fontSize: "14px",
            color: "var(--text-muted)",
            marginBottom: 4,
          }}>
            {listing.days_remaining} days remaining
          </p>
        )}
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Tap to make an offer
        </p>
      </div>
    </div>
  );
}
