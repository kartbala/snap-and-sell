import { Link } from "react-router-dom";
import SSIcon from "./SSIcon";
import { fmtPrice, isDiscounted, isUrgent } from "../ssUtils";

export default function MarketplaceCard({ listing }) {
  const discounted = isDiscounted(listing);
  const urgent = isUrgent(listing);
  const sold = listing.status === "sold";
  const photo = (listing.photos || [])[0];
  const isMeetup = listing.pickup_type === "meetup";

  const Body = (
    <>
      <div className="thumb">
        {photo ? (
          <img src={photo} alt="" loading="lazy" />
        ) : (
          <div style={{ color: "var(--ink-3)", fontSize: 12 }}>no photo</div>
        )}
        <div className="badges">
          {!sold && (
            <span className="ss-badge pickup">
              <SSIcon name={isMeetup ? "meetup" : "home"} size={11} stroke={2.2} />
              {isMeetup ? "meetup" : "pickup"}
            </span>
          )}
          {!sold && urgent && (
            <span className="ss-badge urgent">{listing.days_remaining}d left</span>
          )}
        </div>
        {sold && (
          <>
            <div className="ss-sold-veil" aria-hidden="true" />
            <div className="ss-sold-banner">SOLD</div>
          </>
        )}
      </div>
      <h3 className="title">{listing.title}</h3>
      <div className="price-row">
        <span className={"price" + (discounted && !sold ? "" : " no-discount")}>
          {fmtPrice(listing.current_price ?? listing.asking_price)}
        </span>
        {discounted && !sold && (
          <span className="strike">{fmtPrice(listing.asking_price)}</span>
        )}
      </div>
    </>
  );

  if (sold) {
    return (
      <div
        className="ss-card ss-card--sold"
        aria-label={`${listing.title} (sold)`}
        aria-disabled="true"
      >
        {Body}
      </div>
    );
  }

  return (
    <Link to={`/item/${listing.id}`} className="ss-card" aria-label={listing.title}>
      {Body}
    </Link>
  );
}
