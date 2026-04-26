// Variation C: Dossier / Terminal
// Metadata-forward file cards with a cross-haired top-left ID stamp,
// dashed dividers, and dense monospace specs. Hover reveals a scanline.

function DossierGrid({ items, accent, density, soldOverride, onOpen }) {
  const [filter, setFilter] = React.useState('ALL');
  const [sort, setSort] = React.useState('urgency');
  const list = applyFilterSort(items, filter, sort);
  const cols = density === 'tight' ? 4 : 3;

  return (
    <div style={{ background: '#000', minHeight: '100%', color: '#fff' }}>
      <Header items={items} accent={accent} title="MOVING SALE" subtitle="DOSSIER" terminal />
      <FilterBar items={items} filter={filter} setFilter={setFilter}
        sort={sort} setSort={setSort} accent={accent}
        density={density} setDensity={() => {}} showDensity={false} />

      {/* terminal status strip */}
      <div style={{
        padding: '10px 32px', borderBottom: '1px solid #27272a',
        background: '#000', fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        fontSize: 13, color: '#666', letterSpacing: '0.14em',
        display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
      }}>
        <span>{`> ${list.length} ACTIVE / ${items.filter(i => i.pricing_strategy === 'fire_sale').length} FIRE SALE`}</span>
        <span style={{ color: accent }}>● LIVE FEED</span>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 24, padding: 32,
      }}>
        {list.map(item => {
          const sold = soldOverride?.[item.id] ?? (item.status === 'sold');
          return (
            <DossierCard
              key={item.id} item={item} accent={accent} sold={sold}
              onOpen={() => onOpen(item)}
            />
          );
        })}
      </div>
      <Footer accent={accent} />
    </div>
  );
}

function DossierCard({ item, accent, sold, onOpen }) {
  const [hover, setHover] = React.useState(false);
  const offer = SnapAndSell.offerLine(item);
  return (
    <button
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        all: 'unset', display: 'block', cursor: 'pointer',
        background: '#0a0a0a',
        border: '1px solid ' + (hover ? accent : '#27272a'),
        position: 'relative', transition: 'border-color 0.15s',
        boxSizing: 'border-box', width: '100%',
      }}
    >
      {/* corner crosshair */}
      <CornerMark accent={hover ? accent : '#27272a'} />

      {/* image */}
      <div style={{ position: 'relative', height: 220, borderBottom: '1px solid #27272a', overflow: 'hidden' }}>
        <Placeholder item={item} photo={SnapAndSell.photosFor(item)[0]} />
        {/* scanline on hover */}
        {hover && (
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: `linear-gradient(to bottom, transparent 0%, ${accent}22 50%, transparent 100%)`,
            backgroundSize: '100% 8px',
            animation: 'scanline 1.6s linear infinite',
          }} />
        )}
        {sold && <SoldOverlay />}
      </div>

      {/* dossier header line */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px dashed #27272a',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
        color: '#666', letterSpacing: '0.16em',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span>FILE · ID·{String(item.id).padStart(3, '0')}</span>
        <span>{item.category.toUpperCase()}</span>
      </div>

      <div style={{ padding: 18 }}>
        {/* tags */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
          <HeatTag item={item} accent={accent} />
        </div>

        {/* title */}
        <div style={{
          fontFamily: 'Anton, Impact, sans-serif', fontSize: 24, lineHeight: 0.95,
          letterSpacing: '-0.005em', textTransform: 'uppercase', color: '#fff',
          marginBottom: 14, minHeight: 46,
          overflow: 'hidden', display: '-webkit-box',
          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
        }}>{SnapAndSell.shortTitle(item)}</div>

        {/* price + offer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
          padding: '12px 0', borderTop: '1px dashed #27272a', borderBottom: '1px dashed #27272a',
          marginBottom: 14,
        }}>
          <div>
            <div style={{
              fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
              color: '#666', letterSpacing: '0.16em', marginBottom: 2,
            }}>ASK</div>
            <PriceBlock item={item} size="md" accent={accent} />
          </div>
          {offer && (
            <div style={{ textAlign: 'right' }}>
              <div style={{
                fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
                color: '#666', letterSpacing: '0.16em', marginBottom: 2,
              }}>FLOOR</div>
              <div style={{
                fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 14,
                color: accent,
              }}>{SnapAndSell.money(offer.min)}</div>
            </div>
          )}
        </div>

        {/* spec lines */}
        <div style={{
          fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
          color: '#888', lineHeight: 1.7,
        }}>
          <DRow k="cond" v={item.condition.toUpperCase()} />
          <DRow k="loc" v={item.location.toUpperCase()} />
          <DRow k="pickup" v={item.pickup_type.toUpperCase()} />
        </div>

        {/* CTA */}
        <div style={{
          marginTop: 16, padding: '12px 14px',
          background: hover ? accent : '#000',
          border: '1px solid ' + (hover ? accent : '#27272a'),
          color: hover ? '#000' : '#fff',
          fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 900,
          fontSize: 13, letterSpacing: '0.18em', textTransform: 'uppercase',
          display: 'flex', justifyContent: 'space-between', transition: 'all 0.15s',
        }}>
          <span>OPEN FILE</span><span>→</span>
        </div>
      </div>
    </button>
  );
}

function DRow({ k, v }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: '#555' }}>{k.padEnd(8, '·')}</span>
      <span style={{ color: '#ccc' }}>{v}</span>
    </div>
  );
}

function CornerMark({ accent }) {
  const sz = 12, w = 1.5;
  return (
    <>
      {[
        { top: 0, left: 0, borderTop: `${w}px solid ${accent}`, borderLeft: `${w}px solid ${accent}` },
        { top: 0, right: 0, borderTop: `${w}px solid ${accent}`, borderRight: `${w}px solid ${accent}` },
        { bottom: 0, left: 0, borderBottom: `${w}px solid ${accent}`, borderLeft: `${w}px solid ${accent}` },
        { bottom: 0, right: 0, borderBottom: `${w}px solid ${accent}`, borderRight: `${w}px solid ${accent}` },
      ].map((s, i) => (
        <span key={i} style={{
          position: 'absolute', width: sz, height: sz, ...s, pointerEvents: 'none', zIndex: 2,
        }} />
      ))}
    </>
  );
}

window.DossierGrid = DossierGrid;
