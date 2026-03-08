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
      aria-label={`${listing.title} - $${Number(listing.asking_price).toFixed(2)}`}
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
          <span className="price" style={{ color: "var(--accent-teal)" }}>
            ${Number(listing.asking_price).toFixed(2)}
          </span>

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
        {listing.days_remaining != null && (
          <p
            style={{
              fontSize: "14px",
              color: listing.days_remaining <= 5 ? "var(--accent-coral)" : "var(--text-muted)",
              fontWeight: listing.days_remaining <= 5 ? 700 : 400,
              marginBottom: 4,
            }}
          >
            {listing.days_remaining <= 5
              ? `Only ${listing.days_remaining} day${listing.days_remaining !== 1 ? "s" : ""} left!`
              : `${listing.days_remaining} days remaining`}
          </p>
        )}
        <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Tap to make an offer
        </p>
      </div>
    </div>
  );
}
