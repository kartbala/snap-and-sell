import { useState } from "react";

export default function ListingCard({
  listing,
  selected,
  onToggleSelect,
  onUpdate,
  showCheckbox = false,
  animationDelay = 0,
}) {
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState("");

  const startEdit = (field, value) => {
    setEditing(field);
    setEditValue(value ?? "");
  };

  const commitEdit = () => {
    if (editing && editValue !== (listing[editing] ?? "")) {
      const val = ["asking_price", "min_price"].includes(editing)
        ? parseFloat(editValue) || 0
        : editValue;
      onUpdate(listing.id, { [editing]: val });
    }
    setEditing(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") commitEdit();
    if (e.key === "Escape") setEditing(null);
  };

  const badgeClass = `badge badge-${listing.status}`;

  return (
    <div
      className="card animate-in"
      style={{ animationDelay: `${animationDelay * 0.06}s` }}
    >
      {/* Top row: checkbox + badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "var(--space-md)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-sm)" }}>
          {showCheckbox && (
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggleSelect(listing.id)}
              aria-label={`Select ${listing.title}`}
            />
          )}
          <span className={badgeClass}>{listing.status}</span>
        </div>
        {listing.offer_count > 0 && (
          <span
            style={{
              background: "rgba(233, 69, 96, 0.15)",
              color: "var(--accent-coral)",
              padding: "4px 12px",
              borderRadius: "100px",
              fontSize: "15px",
              fontWeight: 700,
            }}
          >
            {listing.offer_count} offer{listing.offer_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Photo */}
      <div className="photo-placeholder" style={{ marginBottom: "var(--space-md)" }}>
        {listing.photos?.[0] ? (
          <img src={listing.photos[0]} alt={listing.title} />
        ) : (
          <span aria-hidden="true">&#128247;</span>
        )}
      </div>

      {/* Title */}
      {editing === "title" ? (
        <input
          className="editable-field"
          style={{ fontSize: "var(--text-lg)", fontWeight: 700, width: "100%", marginBottom: "var(--space-sm)" }}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
          autoFocus
        />
      ) : (
        <h3
          onClick={() => listing.status === "draft" && startEdit("title", listing.title)}
          style={{
            fontSize: "var(--text-lg)",
            marginBottom: "var(--space-sm)",
            cursor: listing.status === "draft" ? "text" : "default",
          }}
          title={listing.status === "draft" ? "Click to edit" : undefined}
        >
          {listing.title}
        </h3>
      )}

      {/* Description */}
      {editing === "description" ? (
        <textarea
          className="editable-field"
          style={{ fontSize: "var(--text-sm)", width: "100%", minHeight: 80, marginBottom: "var(--space-md)" }}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
          autoFocus
        />
      ) : (
        <p
          onClick={() => listing.status === "draft" && startEdit("description", listing.description)}
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--text-sm)",
            marginBottom: "var(--space-md)",
            cursor: listing.status === "draft" ? "text" : "default",
            minHeight: 28,
          }}
          title={listing.status === "draft" ? "Click to edit" : undefined}
        >
          {listing.description || (listing.status === "draft" ? "Click to add description..." : "")}
        </p>
      )}

      {/* Prices */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-lg)",
          alignItems: "baseline",
          flexWrap: "wrap",
        }}
      >
        <div>
          <label style={{ marginBottom: 2 }}>Asking</label>
          {editing === "asking_price" ? (
            <input
              className="editable-field price"
              style={{ width: 140 }}
              type="number"
              step="0.01"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={handleKeyDown}
              autoFocus
            />
          ) : (
            <div
              className="price"
              onClick={() => listing.status === "draft" && startEdit("asking_price", listing.asking_price)}
              style={{ cursor: listing.status === "draft" ? "text" : "default" }}
              title={listing.status === "draft" ? "Click to edit" : undefined}
            >
              {listing.asking_price != null
                ? `$${Number(listing.asking_price).toFixed(2)}`
                : "---"}
            </div>
          )}
        </div>

        <div>
          <label style={{ marginBottom: 2 }}>Min</label>
          {editing === "min_price" ? (
            <input
              className="editable-field price-small"
              style={{ width: 120 }}
              type="number"
              step="0.01"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={handleKeyDown}
              autoFocus
            />
          ) : (
            <div
              className="price-small"
              style={{
                color: "var(--text-muted)",
                cursor: listing.status === "draft" ? "text" : "default",
              }}
              onClick={() => listing.status === "draft" && startEdit("min_price", listing.min_price)}
              title={listing.status === "draft" ? "Click to edit" : undefined}
            >
              {listing.min_price != null
                ? `$${Number(listing.min_price).toFixed(2)}`
                : "---"}
            </div>
          )}
        </div>
      </div>

      {/* Category + Condition */}
      {(listing.category || listing.condition) && (
        <div
          style={{
            display: "flex",
            gap: "var(--space-sm)",
            marginTop: "var(--space-md)",
            flexWrap: "wrap",
          }}
        >
          {listing.category && (
            <span
              style={{
                background: "rgba(255,255,255,0.06)",
                padding: "4px 12px",
                borderRadius: "100px",
                fontSize: "15px",
                color: "var(--text-secondary)",
              }}
            >
              {listing.category}
            </span>
          )}
          {listing.condition && (
            <span
              style={{
                background: "rgba(255,255,255,0.06)",
                padding: "4px 12px",
                borderRadius: "100px",
                fontSize: "15px",
                color: "var(--text-secondary)",
              }}
            >
              {listing.condition}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
