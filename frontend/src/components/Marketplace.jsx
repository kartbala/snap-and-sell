import { useState, useEffect } from "react";
import MarketplaceCard from "./MarketplaceCard";
import OfferModal from "./OfferModal";

export default function Marketplace() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [offerListing, setOfferListing] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/marketplace");
        if (res.ok) setListings(await res.json());
      } catch {
        // backend may not be running
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="page-container">
      {/* Hero header */}
      <div
        className="page-header animate-in"
        style={{ textAlign: "center", marginBottom: "var(--space-2xl)" }}
      >
        <h1
          style={{
            fontSize: "var(--text-3xl)",
            background: "linear-gradient(135deg, var(--accent-coral) 0%, var(--accent-amber) 50%, var(--accent-teal) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            marginBottom: "var(--space-sm)",
          }}
        >
          Snap & Sell
        </h1>
        <p className="subtitle" style={{ maxWidth: 480, margin: "0 auto" }}>
          Quality local items in DC &mdash; tap any item to make an offer
        </p>
      </div>

      {/* Listings */}
      {loading ? (
        <div className="empty-state">
          <p>Loading items...</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="empty-state animate-in">
          <div className="icon">&#128722;</div>
          <h3>No items available right now</h3>
          <p>Check back soon for new listings</p>
        </div>
      ) : (
        <>
          <p
            className="animate-in"
            style={{
              color: "var(--text-muted)",
              marginBottom: "var(--space-lg)",
              fontSize: "var(--text-sm)",
              animationDelay: "0.1s",
            }}
          >
            {listings.length} item{listings.length !== 1 ? "s" : ""} available
          </p>
          <div className="grid grid-3">
            {listings.map((listing, i) => (
              <MarketplaceCard
                key={listing.id}
                listing={listing}
                onMakeOffer={setOfferListing}
                animationDelay={i}
              />
            ))}
          </div>
        </>
      )}

      {/* Offer modal */}
      {offerListing && (
        <OfferModal
          listing={offerListing}
          onClose={() => setOfferListing(null)}
        />
      )}
    </div>
  );
}
