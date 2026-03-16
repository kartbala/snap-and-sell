import { useState, useEffect, useCallback } from "react";
import ListingCard from "./ListingCard";

const TABS = ["draft", "active", "sold", "donate", "store"];
const TAB_LABELS = {
  draft: "Drafts",
  active: "Active",
  sold: "Sold",
  donate: "Donate",
  store: "Store",
};
const EMPTY_MESSAGES = {
  draft: { icon: "&#128221;", title: "No drafts yet", sub: "Use Gemini to scan your photos and create listings" },
  active: { icon: "&#128722;", title: "No active listings", sub: "Approve some drafts to start selling" },
  sold: { icon: "&#127881;", title: "No sold items yet", sub: "Sold items will appear here" },
  donate: { icon: "&#127873;", title: "No items for donation", sub: "Items past deadline without action go here" },
  store: { icon: "&#128230;", title: "No stored items", sub: "High-value keepers go here" },
};

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("draft");
  const [listings, setListings] = useState([]);
  const [allListings, setAllListings] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [notifCount, setNotifCount] = useState(0);

  const fetchListings = useCallback(async () => {
    try {
      const res = await fetch("/api/listings");
      if (res.ok) {
        const data = await res.json();
        setAllListings(data);
      }
    } catch {
      // backend may not be running
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  useEffect(() => {
    const loadNotifs = async () => {
      try {
        const res = await fetch("/api/notifications/count");
        if (res.ok) {
          const data = await res.json();
          setNotifCount(data.unsent);
        }
      } catch {}
    };
    loadNotifs();
  }, [allListings]);

  useEffect(() => {
    setListings(allListings.filter((l) => l.status === activeTab));
    setSelected(new Set());
  }, [activeTab, allListings]);

  const tabCounts = {};
  for (const tab of TABS) {
    tabCounts[tab] = allListings.filter((l) => l.status === tab).length;
  }

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === listings.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(listings.map((l) => l.id)));
    }
  };

  const handleUpdate = async (id, updates) => {
    try {
      const res = await fetch(`/api/listings/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (res.ok) fetchListings();
    } catch {
      // silently fail for MVP
    }
  };

  const handleBatchApprove = async () => {
    if (selected.size === 0) return;
    try {
      const res = await fetch("/api/listings/batch-approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: [...selected] }),
      });
      if (res.ok) {
        setSelected(new Set());
        fetchListings();
      }
    } catch {
      // silently fail
    }
  };

  const handleBatchStatus = async (newStatus) => {
    if (selected.size === 0) return;
    try {
      const res = await fetch("/api/listings/batch-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: [...selected], status: newStatus }),
      });
      if (res.ok) {
        setSelected(new Set());
        fetchListings();
      }
    } catch {}
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`/api/listings/${id}`, { method: "DELETE" });
      if (res.ok) fetchListings();
    } catch {
      // silently fail
    }
  };

  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1>My Listings</h1>
        <p className="subtitle">Review, edit, and approve items for sale</p>
        {notifCount > 0 && (
          <div
            style={{
              marginTop: "var(--space-sm)",
              padding: "var(--space-sm) var(--space-md)",
              background: "rgba(233, 69, 96, 0.15)",
              border: "1px solid rgba(233, 69, 96, 0.3)",
              borderRadius: "var(--radius-md)",
              color: "var(--accent-coral)",
              fontWeight: 700,
              fontSize: "var(--text-base)",
            }}
          >
            {notifCount} new offer{notifCount !== 1 ? "s" : ""} — check your email or run notifications
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
            <span className="count">{tabCounts[tab]}</span>
          </button>
        ))}
      </div>

      {/* Toolbar for drafts and active */}
      {(activeTab === "draft" || activeTab === "active") && listings.length > 0 && (
        <div className="toolbar animate-in" style={{ animationDelay: "0.1s" }}>
          <div className="toolbar-left">
            <button className="btn btn-ghost" onClick={selectAll}>
              {selected.size === listings.length ? "Deselect All" : "Select All"}
            </button>
            {selected.size > 0 && (
              <span style={{ color: "var(--text-secondary)", fontSize: "var(--text-sm)" }}>
                {selected.size} selected
              </span>
            )}
          </div>
          {activeTab === "draft" && (
            <button
              className="btn btn-success"
              disabled={selected.size === 0}
              onClick={handleBatchApprove}
            >
              Approve Selected ({selected.size})
            </button>
          )}
          {activeTab === "active" && selected.size > 0 && (
            <>
              <button className="btn btn-ghost" onClick={() => handleBatchStatus("donate")}>
                Donate ({selected.size})
              </button>
              <button className="btn btn-ghost" onClick={() => handleBatchStatus("store")}>
                Store ({selected.size})
              </button>
            </>
          )}
        </div>
      )}

      {/* Listings grid */}
      {loading ? (
        <div className="empty-state">
          <p style={{ animation: "fadeIn 0.5s ease infinite alternate" }}>Loading...</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="empty-state animate-in">
          <div className="icon" dangerouslySetInnerHTML={{ __html: (EMPTY_MESSAGES[activeTab] || EMPTY_MESSAGES.draft).icon }} />
          <h3>{(EMPTY_MESSAGES[activeTab] || EMPTY_MESSAGES.draft).title}</h3>
          <p>{(EMPTY_MESSAGES[activeTab] || EMPTY_MESSAGES.draft).sub}</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {listings.map((listing, i) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              selected={selected.has(listing.id)}
              onToggleSelect={toggleSelect}
              onUpdate={handleUpdate}
              showCheckbox={activeTab === "draft" || activeTab === "active"}
              animationDelay={i}
            />
          ))}
        </div>
      )}
    </div>
  );
}
