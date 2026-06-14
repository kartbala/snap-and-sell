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

  const active = listings.filter((l) => l.status !== "sold");
  const sold = listings.filter((l) => l.status === "sold");
  // "Our place" sits above Ashton's mom's place (700 7th St SW).
  const addrRank = (loc) => (loc === "700 7th St SW" ? 1 : 0);
  const ts = (l) => l.created_at || "";
  // Order top-to-bottom: new items first, then our place above mom's place,
  // then bulky above small, then newest first (so old stock like the bikes sinks).
  const sortActive = (a, b) => {
    const an = a.is_new ? 0 : 1;
    const bn = b.is_new ? 0 : 1;
    if (an !== bn) return an - bn;
    const ar = addrRank(a.location);
    const br = addrRank(b.location);
    if (ar !== br) return ar - br;
    const ab = a.bulky ? 0 : 1;
    const bb = b.bulky ? 0 : 1;
    if (ab !== bb) return ab - bb;
    return ts(b).localeCompare(ts(a));
  };
  const ordered = [...active.sort(sortActive), ...sold];
  const count = active.length;
  const blurb = listings.length
    ? `${count} available${sold.length ? ` · ${sold.length} sold` : ""} · DC pickup · ends June 3`
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
          {ordered.map((listing) => (
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
