import { useState, useEffect } from "react";
import FriendsCard from "./FriendsCard";
import { SALE_HEADER } from "../ssUtils";

export default function Friends() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/friends-marketplace");
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
  const addrRank = (loc) => (loc === "800 4th St SW" ? 0 : 1);
  const sortActive = (a, b) => {
    const ar = addrRank(a.location);
    const br = addrRank(b.location);
    if (ar !== br) return ar - br;
    const ab = a.bulky ? 1 : 0;
    const bb = b.bulky ? 1 : 0;
    if (ab !== bb) return bb - ab;
    return a.title.localeCompare(b.title);
  };
  const ordered = [...active.sort(sortActive), ...sold];
  const count = active.length;
  const blurb = listings.length
    ? `${count} available${sold.length ? ` · ${sold.length} claimed` : ""} · DC pickup · friends & family`
    : "Friends & family preview";

  return (
    <div className="ss-scope">
      <header className="ss-topbar">
        <h1>Karthik &amp; Ashton — friends &amp; family</h1>
        <p>{blurb}</p>
        <p style={{ marginTop: 8, fontSize: 14, opacity: 0.85 }}>
          See something you want? Text{" "}
          <a href={`sms:${SALE_HEADER.sms}`}>{SALE_HEADER.smsDisplay}</a> and it's yours.
        </p>
      </header>

      {loading ? (
        <div className="ss-empty">Loading...</div>
      ) : listings.length === 0 ? (
        <div className="ss-empty">Nothing listed right now.</div>
      ) : (
        <div className="ss-grid">
          {ordered.map((listing) => (
            <FriendsCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}

      <footer className="ss-footer">
        Questions? Text <a href={`sms:${SALE_HEADER.sms}`}>{SALE_HEADER.smsDisplay}</a>
      </footer>
    </div>
  );
}
