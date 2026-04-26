// Variation A: Editorial Index
// Numbered list/grid hybrid. Items present as catalog entries with a leading
// 2-digit index, large display title, inline metadata, and a small image.
// Hover slides the image rightward and reveals a CTA.

function EditorialIndex({ items, accent, density, soldOverride, onOpen }) {
  const [filter, setFilter] = React.useState('ALL');
  const [sort, setSort] = React.useState('urgency');
  const list = applyFilterSort(items, filter, sort);
  const tight = density === 'tight';

  return (
    <div style={{ background: '#000', minHeight: '100%', color: '#fff' }}>
      <Header items={items} accent={accent} title="MOVING SALE" subtitle="EDITORIAL INDEX" />
      <FilterBar items={items} filter={filter} setFilter={setFilter}
        sort={sort} setSort={setSort} accent={accent}
        density={density} setDensity={() => {}} showDensity={false} />
      <div>
        {list.map((item, i) => {
          const sold = soldOverride?.[item.id] ?? (item.status === 'sold');
          return (
            <EditorialRow
              key={item.id} item={item} idx={i + 1} accent={accent}
              tight={tight} sold={sold} onOpen={() => onOpen(item)}
            />
          );
        })}
      </div>
      <Footer accent={accent} />
    </div>
  );
}

function EditorialRow({ item, idx, accent, tight, sold, onOpen }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        all: 'unset', display: 'block', width: '100%', cursor: 'pointer',
        borderBottom: '1px solid #27272a',
      }}
    >
      <div style={{
        display: 'grid',
        gridTemplateColumns: '80px 1fr 220px 200px',
        alignItems: 'center', gap: 32,
        padding: tight ? '20px 32px' : '36px 32px',
        background: hover ? '#0a0a0a' : 'transparent',
        transition: 'background 0.15s',
        position: 'relative',
        opacity: sold ? 0.45 : 1,
      }}>
        <span style={{
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 14, color: '#666', letterSpacing: '0.14em',
        }}>{String(idx).padStart(2, '0')}.</span>

        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
            <HeatTag item={item} accent={accent} />
            <Countdown item={item} accent={accent} compact />
            <span style={{
              fontFamily: 'JetBrains Mono, ui-monospace, monospace',
              fontSize: 12, color: '#666', letterSpacing: '0.14em',
              padding: '3px 7px', border: '1px solid #27272a',
            }}>{item.category.toUpperCase()}</span>
          </div>
          <div style={{
            fontFamily: 'Anton, Impact, sans-serif',
            fontSize: tight ? 26 : 36, lineHeight: 0.95,
            letterSpacing: '-0.005em', textTransform: 'uppercase',
            color: '#fff', marginBottom: 6,
            transform: hover ? 'translateX(8px)' : 'translateX(0)',
            transition: 'transform 0.18s',
          }}>{SnapAndSell.shortTitle(item)}</div>
          <div style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontSize: 14,
            color: '#888', maxWidth: '60ch',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{item.title}</div>
        </div>

        <div style={{
          width: '100%', height: tight ? 80 : 120, position: 'relative',
          overflow: 'hidden',
        }}>
          <Placeholder item={item} photo={SnapAndSell.photosFor(item)[0]} />
        </div>

        <div style={{ textAlign: 'right' }}>
          <PriceBlock item={item} size="lg" accent={accent} />
          <div style={{
            marginTop: 8, fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            fontSize: 13, color: hover ? accent : '#666', letterSpacing: '0.14em',
            transition: 'color 0.15s',
          }}>VIEW DETAILS →</div>
        </div>

        {sold && (
          <span style={{
            position: 'absolute', top: 16, right: 32,
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 18,
            color: '#fff', letterSpacing: '0.1em',
            border: '2px solid #fff', padding: '2px 10px', transform: 'rotate(-6deg)',
          }}>SOLD</span>
        )}
      </div>
    </button>
  );
}

window.EditorialIndex = EditorialIndex;
