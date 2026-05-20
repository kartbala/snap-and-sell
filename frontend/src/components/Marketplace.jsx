import { useState, useEffect } from "react";
import MarketplaceCard from "./MarketplaceCard";
import { SALE_HEADER } from "../ssUtils";

export default function Marketplace() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/marketplace");
        if (res.ok) setListings(await res.json());
      } catch {
        /* backend unreachable */
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const count = listings.length;
  const blurb = count
    ? `${count} item${count === 1 ? "" : "s"} · DC pickup · ends June 3`
    : SALE_HEADER.blurb;

  return (
    <div className="ss-scope">
      <header className="ss-topbar">
        <h1>{SALE_HEADER.title}</h1>
        <p>{blurb}</p>
      </header>

      {loading ? (
        <div className="ss-empty">Loading...</div>
      ) : listings.length === 0 ? (
        <div className="ss-empty">Nothing listed right now. Check back soon.</div>
      ) : (
        <div className="ss-grid">
          {listings.map((listing) => (
            <MarketplaceCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}

      <footer className="ss-footer">
        Questions? Text <a href={`sms:${SALE_HEADER.sms}`}>{SALE_HEADER.smsDisplay}</a>
      </footer>
    </div>
  );
}
