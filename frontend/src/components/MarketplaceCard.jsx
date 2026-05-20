import { Link } from "react-router-dom";
import SSIcon from "./SSIcon";
import { fmtPrice, isDiscounted, isUrgent } from "../ssUtils";

export default function MarketplaceCard({ listing }) {
  const discounted = isDiscounted(listing);
  const urgent = isUrgent(listing);
  const photo = (listing.photos || [])[0];
  const isMeetup = listing.pickup_type === "meetup";

  return (
    <Link to={`/item/${listing.id}`} className="ss-card" aria-label={listing.title}>
      <div className="thumb">
        {photo ? (
          <img src={photo} alt="" loading="lazy" />
        ) : (
          <div style={{ color: "var(--ink-3)", fontSize: 12 }}>no photo</div>
        )}
        <div className="badges">
          <span className="ss-badge pickup">
            <SSIcon name={isMeetup ? "meetup" : "home"} size={11} stroke={2.2} />
            {isMeetup ? "meetup" : "pickup"}
          </span>
          {urgent && <span className="ss-badge urgent">{listing.days_remaining}d left</span>}
        </div>
      </div>
      <h3 className="title">{listing.title}</h3>
      <div className="price-row">
        <span className={"price" + (discounted ? "" : " no-discount")}>
          {fmtPrice(listing.current_price ?? listing.asking_price)}
        </span>
        {discounted && <span className="strike">{fmtPrice(listing.asking_price)}</span>}
      </div>
    </Link>
  );
}
