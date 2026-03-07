import { useState, useEffect, useCallback } from "react";
import ListingCard from "./ListingCard";

const TABS = ["draft", "active", "sold"];
const TAB_LABELS = { draft: "Drafts", active: "Active", sold: "Sold" };

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("draft");
  const [listings, setListings] = useState([]);
  const [allListings, setAllListings] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);

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

      {/* Toolbar for drafts */}
      {activeTab === "draft" && listings.length > 0 && (
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
          <button
            className="btn btn-success"
            disabled={selected.size === 0}
            onClick={handleBatchApprove}
          >
            Approve Selected ({selected.size})
          </button>
        </div>
      )}

      {/* Listings grid */}
      {loading ? (
        <div className="empty-state">
          <p style={{ animation: "fadeIn 0.5s ease infinite alternate" }}>Loading...</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="empty-state animate-in">
          <div className="icon">
            {activeTab === "draft" ? "&#128221;" : activeTab === "active" ? "&#128722;" : "&#127881;"}
          </div>
          <h3>
            {activeTab === "draft"
              ? "No drafts yet"
              : activeTab === "active"
              ? "No active listings"
              : "No sold items yet"}
          </h3>
          <p>
            {activeTab === "draft"
              ? "Use Gemini to scan your photos and create listings"
              : activeTab === "active"
              ? "Approve some drafts to start selling"
              : "Sold items will appear here"}
          </p>
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
              showCheckbox={activeTab === "draft"}
              animationDelay={i}
            />
          ))}
        </div>
      )}
    </div>
  );
}
