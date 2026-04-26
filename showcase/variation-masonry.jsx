// Variation B: Stark Masonry
// Uneven masonry tiles. Hero takes a 2-col span. Hover lifts the title up
// and slides reveal a quick-view CTA bar at the bottom.

function StarkMasonry({ items, accent, density, soldOverride, onOpen }) {
  const [filter, setFilter] = React.useState('ALL');
  const [sort, setSort] = React.useState('urgency');
  const list = applyFilterSort(items, filter, sort);

  // Assign uneven heights deterministically based on price tier.
  function tileHeight(item, isHero) {
    if (isHero) return density === 'tight' ? 460 : 540;
    const p = item.asking_price;
    if (p >= 300) return density === 'tight' ? 380 : 440;
    if (p >= 150) return density === 'tight' ? 320 : 360;
    return density === 'tight' ? 260 : 300;
  }
  function tileSpan(item, i) {
    if (i === 0) return 2;
    if (item.asking_price >= 350 && i % 5 === 0) return 2;
    return 1;
  }

  return (
    <div style={{ background: '#000', minHeight: '100%', color: '#fff' }}>
      <Header items={items} accent={accent} title="MOVING SALE" />
      <FilterBar items={items} filter={filter} setFilter={setFilter}
        sort={sort} setSort={setSort} accent={accent}
        density={density} setDensity={() => {}} showDensity={false} />
      <div style={{
        display: 'grid',
        gridTemplateColumns: density === 'tight' ? 'repeat(4, 1fr)' : 'repeat(3, 1fr)',
        gap: 1, background: '#27272a', padding: 1,
      }}>
        {list.map((item, i) => {
          const sold = soldOverride?.[item.id] ?? (item.status === 'sold');
          const span = tileSpan(item, i);
          return (
            <StarkTile
              key={item.id} item={item} accent={accent}
              height={tileHeight(item, i === 0)}
              span={span} hero={i === 0} sold={sold}
              onOpen={() => onOpen(item)}
            />
          );
        })}
      </div>
      <Footer accent={accent} />
    </div>
  );
}

function StarkTile({ item, accent, height, span, hero, sold, onOpen }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        all: 'unset', position: 'relative', display: 'block',
        gridColumn: `span ${span}`, height, background: '#000',
        cursor: 'pointer', overflow: 'hidden', width: '100%', boxSizing: 'border-box',
      }}
    >
      <div style={{
        position: 'absolute', inset: 0,
        transform: hover ? 'scale(1.04)' : 'scale(1)',
        transition: 'transform 0.4s',
      }}>
        <Placeholder item={item} tall={hero} photo={SnapAndSell.photosFor(item)[0]} />
      </div>

      {/* gradient bottom */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.2) 50%, rgba(0,0,0,0) 70%)',
      }} />

      {/* top tags */}
      <div style={{ position: 'absolute', top: 16, left: 16, right: 16,
        display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <HeatTag item={item} accent={accent} />
          <Countdown item={item} accent={accent} compact />
        </div>
        <span style={{
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 12, color: 'rgba(255,255,255,0.6)', letterSpacing: '0.14em',
        }}>ID·{String(item.id).padStart(3, '0')}</span>
      </div>

      {/* bottom block */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0, padding: 20,
        transform: hover ? 'translateY(-44px)' : 'translateY(0)',
        transition: 'transform 0.22s',
      }}>
        <div style={{
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 12, color: 'rgba(255,255,255,0.55)', letterSpacing: '0.16em',
          marginBottom: 6,
        }}>{item.category.toUpperCase()}</div>
        <div style={{
          fontFamily: 'Anton, Impact, sans-serif',
          fontSize: hero ? 44 : (span === 2 ? 36 : 24),
          lineHeight: 0.92, letterSpacing: '-0.005em', textTransform: 'uppercase',
          color: '#fff', marginBottom: 10,
          textShadow: '0 2px 16px rgba(0,0,0,0.6)',
          overflow: 'hidden', display: '-webkit-box',
          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
        }}>{SnapAndSell.shortTitle(item)}</div>
        <PriceBlock item={item} size={hero ? 'lg' : 'md'} accent={accent} />
      </div>

      {/* hover CTA bar */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: '#fff', color: '#000', padding: '14px 20px',
        fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 900,
        fontSize: 12, letterSpacing: '0.18em', textTransform: 'uppercase',
        display: 'flex', justifyContent: 'space-between',
        transform: hover ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 0.22s',
      }}>
        <span>OPEN DETAIL</span><span>→</span>
      </div>

      {sold && <SoldOverlay />}
    </button>
  );
}

window.StarkMasonry = StarkMasonry;
