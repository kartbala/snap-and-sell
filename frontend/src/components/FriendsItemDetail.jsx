import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import SSIcon from "./SSIcon";
import Lightbox from "./Lightbox";
import { SALE_HEADER } from "../ssUtils";

function MobileCarousel({ photos, onZoom }) {
  const [active, setActive] = useState(0);
  const ref = useRef(null);
  const onScroll = () => {
    if (!ref.current) return;
    const w = ref.current.clientWidth;
    setActive(Math.round(ref.current.scrollLeft / w));
  };
  return (
    <div className="ss-carousel">
      <div className="slides" ref={ref} onScroll={onScroll}>
        {photos.map((p, i) => (
          <div className="slide" key={i}>
            <img src={p} alt="" onClick={() => onZoom(i)} />
          </div>
        ))}
      </div>
      {photos.length > 1 && (
        <div className="dots">
          {photos.map((_, i) => (
            <span key={i} className={"dot" + (i === active ? " active" : "")} />
          ))}
        </div>
      )}
    </div>
  );
}

function DesktopGallery({ photos, onZoom }) {
  const [active, setActive] = useState(0);
  return (
    <div className="ss-desktop-gallery">
      <div className="thumbs">
        {photos.slice(0, 6).map((p, i) => (
          <button
            key={i}
            className={"thumb-btn" + (i === active ? " active" : "")}
            onClick={() => setActive(i)}
            aria-label={`Photo ${i + 1}`}
          >
            <img src={p} alt="" />
          </button>
        ))}
      </div>
      <div className="main" onClick={() => onZoom(active)}>
        <img src={photos[active]} alt="" />
      </div>
    </div>
  );
}

function DetailBody({ item }) {
  const sold = item.status === "sold";
  const smsBody = encodeURIComponent(`Claiming "${item.title}" from the friends list.`);
  return (
    <>
      <h1 className="ss-detail-title">{item.title}</h1>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {item.condition && <span className="ss-pill">{item.condition} condition</span>}
        {item.category && <span className="ss-pill">{String(item.category).replace(/-/g, " ")}</span>}
      </div>
      {item.description && <p className="ss-desc">{item.description}</p>}
      {!sold && (
        <div className="ss-loc">
          <SSIcon name="pin" size={20} />
          <span>
            {item.location || "DC"}
            {item.pickup_type === "home" ? " · home pickup" : " · public meetup"}
          </span>
        </div>
      )}
      {sold ? (
        <p className="ss-paynote">Already claimed.</p>
      ) : (
        <>
          <a
            className="btn btn-primary"
            href={`sms:${SALE_HEADER.sms}?&body=${smsBody}`}
            style={{ display: "inline-block", marginTop: 16 }}
          >
            Text to claim
          </a>
          <p className="ss-paynote">
            Friends &amp; family — take what you need. Just text so I know it's spoken for.
          </p>
        </>
      )}
    </>
  );
}

export default function FriendsItemDetail() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [missing, setMissing] = useState(false);
  const [lbIndex, setLbIndex] = useState(0);
  const [lbOpen, setLbOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia("(min-width: 900px)").matches : false,
  );

  useEffect(() => {
    const mql = window.matchMedia("(min-width: 900px)");
    const handler = (e) => setIsDesktop(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setMissing(false);
    (async () => {
      try {
        const res = await fetch("/api/friends-marketplace");
        if (!alive) return;
        if (!res.ok) {
          setMissing(true);
          return;
        }
        const all = await res.json();
        const found = all.find((it) => String(it.id) === String(id));
        if (!found) {
          setMissing(true);
          return;
        }
        setItem(found);
      } catch {
        setMissing(true);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="ss-scope">
        <div className="ss-empty">Loading...</div>
      </div>
    );
  }
  if (missing || !item) {
    return (
      <div className="ss-scope">
        <div className="ss-empty">
          That item isn't available.<br />
          <Link to="/friends" style={{ textDecoration: "underline", fontWeight: 600 }}>
            Back to friends &amp; family
          </Link>
        </div>
      </div>
    );
  }

  const photos = item.photos && item.photos.length ? item.photos : [];

  return (
    <div className="ss-scope ss-detail-page">
      {isDesktop ? (
        <>
          <header className="ss-topbar" style={{ padding: "16px 40px" }}>
            <h1 style={{ fontSize: 17 }}>
              <Link to="/friends" style={{ color: "inherit" }}>
                {SALE_HEADER.title} — friends &amp; family
              </Link>
            </h1>
          </header>
          <div className="ss-detail-desktop">
            {photos.length > 0 && (
              <DesktopGallery
                photos={photos}
                onZoom={(i) => {
                  setLbIndex(i);
                  setLbOpen(true);
                }}
              />
            )}
            <div className="content">
              <DetailBody item={item} />
            </div>
          </div>
        </>
      ) : (
        <>
          <div style={{ padding: "8px 4px 0" }}>
            <Link to="/friends" className="ss-back" aria-label="Back to all items">
              <SSIcon name="chev-l" size={16} stroke={2.4} /> All items
            </Link>
          </div>
          {photos.length > 0 && (
            <MobileCarousel
              photos={photos}
              onZoom={(i) => {
                setLbIndex(i);
                setLbOpen(true);
              }}
            />
          )}
          <div className="ss-detail-body">
            <DetailBody item={item} />
          </div>
        </>
      )}

      {lbOpen && photos.length > 0 && (
        <Lightbox
          photos={photos}
          index={lbIndex}
          onClose={() => setLbOpen(false)}
          onIndex={setLbIndex}
        />
      )}
    </div>
  );
}
