// Shared Header + Footer used by all three variations.
function Header({ items, accent, title, subtitle, terminal }) {
  const now = SnapAndSell.useToday();
  const days = SnapAndSell.daysUntil('2026-06-01', now);
  const fireCount = items.filter(i => i.pricing_strategy === 'fire_sale').length;
  return (
    <header style={{
      borderBottom: '1px solid #27272a', background: '#000',
    }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        padding: '36px 32px 28px', flexWrap: 'wrap', gap: 16,
      }}>
        <div>
          <div style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            fontSize: 12, color: accent, letterSpacing: '0.22em', marginBottom: 8,
          }}>
            {terminal ? '> ' : ''}{subtitle}
          </div>
          <h1 style={{
            fontFamily: 'Anton, Impact, sans-serif',
            fontSize: 'clamp(48px, 7vw, 96px)', lineHeight: 0.85,
            letterSpacing: '-0.015em', textTransform: 'uppercase',
            color: '#fff', margin: 0,
          }}>{title}</h1>
          <p style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontSize: 16,
            color: '#888', margin: '14px 0 0', maxWidth: 580, lineHeight: 1.5,
          }}>
            Everything must go before <strong style={{ color: '#fff' }}>June 1, 2026</strong>.
            {' '}Sabbatical to the Netherlands.{' '}
            <strong style={{ color: '#fff' }}>Every item is already assembled</strong>{' '}
            -- no flat-pack, no allen wrenches, no missing screws.
            {' '}Pickup only · SW DC · Cash, Zelle, or Venmo.
          </p>
        </div>
        <div style={{
          padding: 20, border: '1px solid #27272a', minWidth: 220,
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 13, color: '#888', letterSpacing: '0.14em',
        }}>
          <div style={{ marginBottom: 6 }}>DEADLINE</div>
          <div style={{
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 56, color: accent,
            lineHeight: 0.9, letterSpacing: '-0.01em',
          }}>{days}D</div>
          <div style={{ marginTop: 6, color: '#fff' }}>UNTIL JUN 01 / 2026</div>
          <div style={{
            marginTop: 14, paddingTop: 12, borderTop: '1px dashed #27272a',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>FIRE SALE</span>
            <span style={{ color: accent }}>{fireCount} / {items.length}</span>
          </div>
          <div style={{
            marginTop: 8,
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>ASSEMBLED</span>
            <span style={{ color: accent }}>ALL / {items.length}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Footer({ accent }) {
  return (
    <footer style={{
      borderTop: '1px solid #27272a', padding: '40px 32px',
      fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
      color: '#666', letterSpacing: '0.14em',
      display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
    }}>
      <span>EVERYTHING MUST GO · DEADLINE 2026·06·01</span>
      <span>SW DC · PICKUP ONLY · CASH · ZELLE · VENMO</span>
    </footer>
  );
}

Object.assign(window, { Header, Footer });
