import { useEffect } from "react";
import SSIcon from "./SSIcon";

export default function Lightbox({ photos, index, onClose, onIndex }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onIndex(Math.min(photos.length - 1, index + 1));
      if (e.key === "ArrowLeft") onIndex(Math.max(0, index - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, photos.length, onClose, onIndex]);

  return (
    <div className="ss-lightbox">
      <div className="lb-bar">
        <span>{index + 1} / {photos.length}</span>
        <button type="button" onClick={onClose} aria-label="Close">
          <SSIcon name="x" size={22} stroke={2.2} />
        </button>
      </div>
      <div className="lb-img" onClick={onClose}>
        <img src={photos[index]} alt="" />
      </div>
      {photos.length > 1 && (
        <div className="lb-thumbs">
          {photos.map((p, i) => (
            <button
              key={i}
              className={"lb-thumb" + (i === index ? " active" : "")}
              onClick={() => onIndex(i)}
              aria-label={`Photo ${i + 1}`}
            >
              <img src={p} alt="" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
