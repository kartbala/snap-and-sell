// Shared visual primitives used across all 3 variations.
// Loaded as Babel JSX. Exports onto window at the bottom.

// ─── Category-typed striped placeholder ────────────────────────────────
// Looks intentional, never broken. Volt accent only on a single corner tag.
function Placeholder({ item, tall, photo, label }) {
  // If a real photo url was supplied, show it instead.
  if (photo) {
    return (
      <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>
        <img src={photo} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(1.05)' }} />
        {label && (
          <div style={{
            position: 'absolute', top: 12, left: 12, color: '#fff',
            fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12, letterSpacing: '0.1em',
            background: 'rgba(0,0,0,0.6)', padding: '3px 6px',
          }}>{label}</div>
        )}
      </div>
    );
  }
  const code = SnapAndSell.shortCode(item);
  const cat = item.category.toUpperCase();
  // Diagonal stripes via repeating-linear-gradient on zinc-950.
  const stripes = `repeating-linear-gradient(135deg, #0a0a0a 0 14px, #111 14px 28px)`;
  return (
    <div style={{
      position: 'relative', width: '100%', height: '100%', background: stripes,
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      padding: 14, fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      color: 'rgba(255,255,255,0.4)', overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, letterSpacing: '0.18em' }}>
        <span>{cat}</span>
        <span>NO IMG</span>
      </div>
      <div style={{
        fontFamily: 'Anton, Impact, sans-serif', fontSize: tall ? 84 : 56, lineHeight: 0.85,
        color: 'rgba(255,255,255,0.18)', letterSpacing: '-0.02em', textTransform: 'uppercase',
      }}>{code}</div>
      <div style={{ fontSize: 12, letterSpacing: '0.18em', color: 'rgba(255,255,255,0.32)' }}>
        ID·{String(item.id).padStart(3, '0')}
      </div>
    </div>
  );
}

// ─── Volt countdown badge ──────────────────────────────────────────────
function Countdown({ item, compact, accent = '#CEFF00' }) {
  const now = SnapAndSell.useToday();
  const days = SnapAndSell.daysUntil(item.deadline, now);
  if (days == null) return null;
  const past = days < 0;
  const urgent = days <= 14;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: compact ? 12 : 13, letterSpacing: '0.1em',
      color: urgent ? '#000' : (past ? '#888' : '#fff'),
      background: urgent ? accent : 'transparent',
      padding: compact ? '2px 6px' : '4px 8px',
      border: urgent ? 'none' : '1px solid #27272a',
      whiteSpace: 'nowrap',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: 0,
        background: urgent ? '#000' : accent,
        animation: urgent ? 'volt-pulse 1.6s ease-in-out infinite' : 'none',
      }} />
      {past ? 'PAST DUE' : `${days}D LEFT`}
    </span>
  );
}

// ─── Price block ───────────────────────────────────────────────────────
function PriceBlock({ item, size = 'md', accent = '#CEFF00' }) {
  const offer = SnapAndSell.offerLine(item);
  const savings = SnapAndSell.savingsLine(item);
  const isFire = item.pricing_strategy === 'fire_sale';
  const fontSize = size === 'lg' ? 32 : size === 'sm' ? 18 : 22;
  const metaSize = size === 'lg' ? 14 : 13;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{
          fontFamily: 'Anton, Impact, sans-serif',
          fontSize, lineHeight: 1, color: '#fff', letterSpacing: '-0.01em',
        }}>
          {SnapAndSell.money(item.asking_price)}
        </span>
        {savings && (
          <span style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            fontSize: metaSize, letterSpacing: '0.06em',
            color: '#666', textDecoration: 'line-through',
          }}>
            {SnapAndSell.money(savings.orig)}
          </span>
        )}
        {savings && (
          <span style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            fontSize: metaSize, letterSpacing: '0.12em', fontWeight: 700,
            color: '#000', background: accent, padding: '2px 7px',
          }}>
            {savings.pct}% OFF
          </span>
        )}
        {offer && isFire && (
          <span style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            fontSize: 12, letterSpacing: '0.12em', color: accent,
          }}>
            OBO ↓ {SnapAndSell.money(offer.min)}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Assembled badge ───────────────────────────────────────────────────
// Universal selling point: every item is already assembled and in use.
// No flat-pack, no allen wrenches, no missing screws.
function AssembledBadge({ size = 'md' }) {
  const fontSize = size === 'sm' ? 11 : 12;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize, letterSpacing: '0.16em', fontWeight: 600,
      padding: '3px 8px',
      background: 'transparent', color: '#fff',
      border: '1px solid #fff',
      whiteSpace: 'nowrap',
    }}>
      <span style={{
        width: 6, height: 6, background: '#CEFF00', display: 'inline-block',
      }} />
      ASSEMBLED
    </span>
  );
}

// ─── Heat tag ──────────────────────────────────────────────────────────
function HeatTag({ item, accent = '#CEFF00' }) {
  const h = SnapAndSell.heat(item);
  const colors = {
    hot: { bg: accent, fg: '#000' },
    warm: { bg: 'transparent', fg: '#fff', border: '#fff' },
    cool: { bg: 'transparent', fg: '#666', border: '#27272a' },
  }[h.tone];
  return (
    <span style={{
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: 12, letterSpacing: '0.16em', fontWeight: 600,
      padding: '3px 7px',
      background: colors.bg, color: colors.fg,
      border: colors.border ? `1px solid ${colors.border}` : 'none',
      whiteSpace: 'nowrap',
    }}>{h.label}</span>
  );
}

// ─── Sold overlay ──────────────────────────────────────────────────────
function SoldOverlay() {
  return (
    <div style={{
      position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 5,
    }}>
      <span style={{
        fontFamily: 'Anton, Impact, sans-serif', fontSize: 56,
        color: '#fff', letterSpacing: '0.04em',
        border: '4px solid #fff', padding: '6px 18px',
        transform: 'rotate(-8deg)',
      }}>SOLD</span>
    </div>
  );
}

// ─── Contact CTA (DM to purchase) ──────────────────────────────────────
function ContactCTA({ item, variant = 'primary', accent = '#CEFF00', onClick }) {
  const styles = {
    primary: { background: '#fff', color: '#000', border: 'none' },
    accent: { background: accent, color: '#000', border: 'none' },
    ghost: { background: 'transparent', color: '#fff', border: '1px solid #fff' },
  }[variant];
  return (
    <button
      onClick={onClick}
      style={{
        ...styles,
        fontFamily: 'Inter, system-ui, sans-serif',
        fontWeight: 900, fontSize: 13, letterSpacing: '0.14em',
        textTransform: 'uppercase', padding: '14px 22px',
        cursor: 'pointer', borderRadius: 0, width: '100%',
        transition: 'transform 0.06s',
      }}
      onMouseDown={e => e.currentTarget.style.transform = 'translateY(1px)'}
      onMouseUp={e => e.currentTarget.style.transform = 'translateY(0)'}
      onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
    >
      DM TO PURCHASE →
    </button>
  );
}

// ─── Filter / Sort bar (shared) ────────────────────────────────────────
function FilterBar({ items, filter, setFilter, sort, setSort, accent = '#CEFF00', density, setDensity, showDensity }) {
  const cats = ['ALL', ...Array.from(new Set(items.map(i => i.category)))];
  const sorts = [
    ['urgency', 'URGENCY'],
    ['price_desc', 'PRICE ↓'],
    ['price_asc', 'PRICE ↑'],
    ['newest', 'NEWEST'],
  ];
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 16, padding: '20px 32px',
      borderTop: '1px solid #27272a', borderBottom: '1px solid #27272a',
      background: '#000',
    }}>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {cats.map(c => {
          const active = filter === c;
          return (
            <button key={c} onClick={() => setFilter(c)} style={{
              fontFamily: 'JetBrains Mono, ui-monospace, monospace',
              fontSize: 13, letterSpacing: '0.14em', textTransform: 'uppercase',
              padding: '8px 14px', border: '1px solid ' + (active ? accent : '#27272a'),
              background: active ? accent : 'transparent',
              color: active ? '#000' : '#fff',
              cursor: 'pointer', borderRadius: 0,
            }}>{c}</button>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        {showDensity && (
          <div style={{ display: 'flex', gap: 0, border: '1px solid #27272a' }}>
            {['tight', 'comfy'].map(d => (
              <button key={d} onClick={() => setDensity(d)} style={{
                fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                fontSize: 13, letterSpacing: '0.14em', textTransform: 'uppercase',
                padding: '8px 12px', border: 'none',
                background: density === d ? '#fff' : 'transparent',
                color: density === d ? '#000' : '#fff', cursor: 'pointer',
              }}>{d}</button>
            ))}
          </div>
        )}
        <select value={sort} onChange={e => setSort(e.target.value)} style={{
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 13, letterSpacing: '0.14em', textTransform: 'uppercase',
          background: 'transparent', color: '#fff', border: '1px solid #27272a',
          padding: '8px 28px 8px 14px', borderRadius: 0,
          appearance: 'none',
          backgroundImage: "url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2210%22 height=%226%22 viewBox=%220 0 10 6%22 fill=%22none%22%3E%3Cpath d=%22M1 1l4 4 4-4%22 stroke=%22white%22 stroke-width=%221.5%22/%3E%3C/svg%3E')",
          backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center',
        }}>
          {sorts.map(([v, l]) => <option key={v} value={v} style={{ background: '#000' }}>SORT: {l}</option>)}
        </select>
      </div>
    </div>
  );
}

// Apply filter + sort to list. Featured items always pin to the top so the
// masonry layout gives them the hero tile, regardless of which sort is active.
function applyFilterSort(items, filter, sort) {
  let out = filter === 'ALL' ? items : items.filter(i => i.category === filter);
  switch (sort) {
    case 'price_desc': out = [...out].sort((a, b) => b.asking_price - a.asking_price); break;
    case 'price_asc': out = [...out].sort((a, b) => a.asking_price - b.asking_price); break;
    case 'newest': out = [...out].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); break;
    case 'urgency':
    default:
      out = [...out].sort((a, b) => {
        const rank = { fire_sale: 0, aggressive: 1, hold: 2 };
        return (rank[a.pricing_strategy] ?? 3) - (rank[b.pricing_strategy] ?? 3) || b.asking_price - a.asking_price;
      });
  }
  const featured = out.filter(i => i._featured);
  const rest = out.filter(i => !i._featured);
  return [...featured, ...rest];
}

Object.assign(window, {
  Placeholder, Countdown, PriceBlock, HeatTag, SoldOverlay,
  ContactCTA, FilterBar, applyFilterSort, AssembledBadge,
});
