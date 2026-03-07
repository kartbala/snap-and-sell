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

      {/* Tap hint */}
      <div
        style={{
          marginTop: "var(--space-md)",
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: "var(--text-sm)",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          paddingTop: "var(--space-sm)",
        }}
      >
        Tap to make an offer
      </div>
    </div>
  );
}
