import { Link } from "react-router-dom";

export default function FriendsCard({ listing }) {
  const sold = listing.status === "sold";
  const photo = (listing.photos || [])[0];

  const Body = (
    <>
      <div className="thumb">
        {photo ? (
          <img src={photo} alt="" loading="lazy" />
        ) : (
          <div style={{ color: "var(--ink-3)", fontSize: 12 }}>no photo</div>
        )}
        {sold && (
          <>
            <div className="ss-sold-veil" aria-hidden="true" />
            <div className="ss-sold-banner">CLAIMED</div>
          </>
        )}
      </div>
      <h3 className="title">{listing.title}</h3>
      {listing.condition && (
        <div className="price-row">
          <span className="ss-pill">{listing.condition} condition</span>
        </div>
      )}
    </>
  );

  if (sold) {
    return (
      <div
        className="ss-card ss-card--sold"
        aria-label={`${listing.title} (claimed)`}
        aria-disabled="true"
      >
        {Body}
      </div>
    );
  }

  return (
    <Link to={`/friends/item/${listing.id}`} className="ss-card" aria-label={listing.title}>
      {Body}
    </Link>
  );
}
