// Detail views — three variants. Modal-style overlays.
// Each one is paired with a layout variation but shares the same data shape.

// Common photo carousel (handles 0..N photos with arrow keys + dots).
function PhotoCarousel({ item, height = 480 }) {
  const photos = SnapAndSell.photosFor(item);
  const [idx, setIdx] = React.useState(0);
  const total = Math.max(photos.length, 1);

  React.useEffect(() => {
    function onKey(e) {
      if (e.key === 'ArrowRight') setIdx(i => (i + 1) % total);
      if (e.key === 'ArrowLeft') setIdx(i => (i - 1 + total) % total);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [total]);

  return (
    <div style={{ position: 'relative', width: '100%', height, background: '#0a0a0a' }}>
      <Placeholder item={item} tall photo={photos[idx]} label={`${idx + 1} / ${total}`} />
      {total > 1 && (
        <>
          <button aria-label="previous photo" onClick={() => setIdx((idx - 1 + total) % total)} style={navBtn('left')}>‹</button>
          <button aria-label="next photo" onClick={() => setIdx((idx + 1) % total)} style={navBtn('right')}>›</button>
          <div style={{
            position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
            display: 'flex', gap: 6,
          }}>
            {Array.from({ length: total }).map((_, i) => (
              <span key={i} style={{
                width: 18, height: 3,
                background: i === idx ? '#fff' : 'rgba(255,255,255,0.3)',
              }} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
function navBtn(side) {
  return {
    position: 'absolute', top: '50%', transform: 'translateY(-50%)',
    [side]: 16, width: 44, height: 44, borderRadius: 0,
    background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)',
    fontSize: 24, lineHeight: 1, cursor: 'pointer',
  };
}

// ─── Modal shell ──────────────────────────────────────────────────────
function Modal({ open, onClose, children, accent = '#CEFF00' }) {
  React.useEffect(() => {
    if (!open) return;
    function esc(e) { if (e.key === 'Escape') onClose(); }
    window.addEventListener('keydown', esc);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', esc);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.92)', zIndex: 100,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
      overflowY: 'auto', padding: '40px 20px',
      animation: 'fade-in 0.18s ease',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#000', maxWidth: 1100, width: '100%',
        border: '1px solid #27272a', position: 'relative',
      }}>
        <button onClick={onClose} aria-label="close" style={{
          position: 'absolute', top: 16, right: 16, zIndex: 10,
          background: '#000', color: '#fff', border: '1px solid #27272a',
          width: 40, height: 40, fontSize: 18, cursor: 'pointer', borderRadius: 0,
        }}>✕</button>
        {children}
      </div>
    </div>
  );
}

// ─── Variant 1: Editorial Detail (split, classic) ─────────────────────
function DetailEditorial({ item, onClose, accent }) {
  if (!item) return null;
  const offer = SnapAndSell.offerLine(item);
  return (
    <Modal open={!!item} onClose={onClose} accent={accent}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: 0 }}>
        <PhotoCarousel item={item} height={620} />
        <div style={{ padding: '56px 48px', color: '#fff' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <HeatTag item={item} accent={accent} />
            <Countdown item={item} accent={accent} />
          </div>
          <div style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
            color: '#666', letterSpacing: '0.18em', marginBottom: 12,
          }}>
            ID·{String(item.id).padStart(3, '0')} / {item.category.toUpperCase()} / {item.condition.toUpperCase()}
          </div>
          <h2 style={{
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 44, lineHeight: 0.95,
            letterSpacing: '-0.01em', textTransform: 'uppercase', margin: '0 0 24px',
            color: '#fff',
          }}>{item.title}</h2>
          <div style={{ marginBottom: 24 }}>
            <PriceBlock item={item} size="lg" accent={accent} />
            {offer && (
              <div style={{
                marginTop: 8, fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                fontSize: 12, color: '#888', letterSpacing: '0.06em',
              }}>
                Reasonable offers from {SnapAndSell.money(offer.min)} considered ({offer.pct}% off ask)
              </div>
            )}
          </div>
          <pre style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontSize: 16, lineHeight: 1.65,
            color: '#d4d4d8', whiteSpace: 'pre-wrap', margin: '0 0 32px',
            maxHeight: 280, overflowY: 'auto',
          }}>{item.description}</pre>
          <SpecsTable item={item} />
          <div style={{ marginTop: 28 }}>
            <ContactCTA item={item} variant="primary" accent={accent} />
            <div style={{
              marginTop: 10, fontFamily: 'JetBrains Mono, ui-monospace, monospace',
              fontSize: 13, color: '#666', letterSpacing: '0.1em', textAlign: 'center',
            }}>
              CASH · ZELLE · VENMO  /  PICKUP ONLY · SW DC
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}

// ─── Variant 2: Stark Full-Bleed Detail ────────────────────────────────
function DetailStark({ item, onClose, accent }) {
  if (!item) return null;
  const offer = SnapAndSell.offerLine(item);
  return (
    <Modal open={!!item} onClose={onClose} accent={accent}>
      <div style={{ position: 'relative' }}>
        <PhotoCarousel item={item} height={560} />
        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 0,
          padding: '32px 48px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.95), rgba(0,0,0,0))',
        }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <HeatTag item={item} accent={accent} />
            <Countdown item={item} accent={accent} />
          </div>
          <h2 style={{
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 64, lineHeight: 0.9,
            letterSpacing: '-0.01em', textTransform: 'uppercase', margin: 0, color: '#fff',
            textShadow: '0 2px 24px rgba(0,0,0,0.6)',
          }}>{SnapAndSell.shortTitle(item)}</h2>
        </div>
      </div>
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 380px', gap: 0,
        borderTop: '1px solid #27272a',
      }}>
        <div style={{ padding: '40px 48px', color: '#d4d4d8' }}>
          <div style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
            color: '#666', letterSpacing: '0.18em', marginBottom: 20,
            display: 'flex', gap: 18, flexWrap: 'wrap',
          }}>
            <span>ID·{String(item.id).padStart(3, '0')}</span>
            <span>{item.category.toUpperCase()}</span>
            <span>COND · {item.condition.toUpperCase()}</span>
            <span>SW DC</span>
          </div>
          <h3 style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 700, fontSize: 18,
            color: '#fff', margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>Full title</h3>
          <p style={{ margin: '0 0 28px', fontSize: 16, lineHeight: 1.5 }}>{item.title}</p>
          <h3 style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontWeight: 700, fontSize: 18,
            color: '#fff', margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>Details</h3>
          <pre style={{
            fontFamily: 'Inter, system-ui, sans-serif', fontSize: 16, lineHeight: 1.65,
            color: '#d4d4d8', whiteSpace: 'pre-wrap', margin: 0,
          }}>{item.description}</pre>
        </div>
        <aside style={{
          background: '#0a0a0a', padding: '40px 32px', borderLeft: '1px solid #27272a',
          color: '#fff',
        }}>
          <div style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
            color: '#666', letterSpacing: '0.18em', marginBottom: 8,
          }}>ASK</div>
          <div style={{
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 56, lineHeight: 1,
            color: '#fff', marginBottom: 20,
          }}>{SnapAndSell.money(item.asking_price)}</div>
          {offer && (
            <div style={{
              padding: 14, border: '1px solid #27272a', marginBottom: 20,
              fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
              color: '#888', lineHeight: 1.6,
            }}>
              <div style={{ color: accent, marginBottom: 4 }}>OFFER FLOOR</div>
              <div style={{ color: '#fff', fontSize: 18 }}>{SnapAndSell.money(offer.min)}</div>
              <div>Won't go below this. {offer.pct}% off ask.</div>
            </div>
          )}
          <SpecsTable item={item} compact />
          <div style={{ marginTop: 24 }}>
            <ContactCTA item={item} variant={item.pricing_strategy === 'fire_sale' ? 'accent' : 'primary'} accent={accent} />
            <div style={{
              marginTop: 12, fontFamily: 'JetBrains Mono, ui-monospace, monospace',
              fontSize: 12, color: '#666', letterSpacing: '0.14em', textAlign: 'center', lineHeight: 1.5,
            }}>
              CASH · ZELLE · VENMO<br/>PICKUP ONLY · SW DC
            </div>
          </div>
        </aside>
      </div>
    </Modal>
  );
}

// ─── Variant 3: Dossier / Terminal Detail ──────────────────────────────
function DetailDossier({ item, onClose, accent }) {
  if (!item) return null;
  const offer = SnapAndSell.offerLine(item);
  return (
    <Modal open={!!item} onClose={onClose} accent={accent}>
      <div style={{
        padding: '20px 28px', borderBottom: '1px solid #27272a',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
        color: '#888', letterSpacing: '0.16em', display: 'flex', justifyContent: 'space-between',
      }}>
        <span>{`> DOSSIER / ID·${String(item.id).padStart(3, '0')}`}</span>
        <span style={{ color: accent }}>● ACTIVE</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 420px', gap: 0 }}>
        <div style={{ padding: '40px 40px 0' }}>
          <div style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
            color: '#666', letterSpacing: '0.18em', marginBottom: 14,
          }}>
            FILE / {item.category.toUpperCase()}
          </div>
          <h2 style={{
            fontFamily: 'Anton, Impact, sans-serif', fontSize: 52, lineHeight: 0.9,
            letterSpacing: '-0.01em', textTransform: 'uppercase', margin: '0 0 28px',
            color: '#fff',
          }}>{item.title}</h2>
          <PhotoCarousel item={item} height={420} />
          <div style={{ padding: '32px 0' }}>
            <h3 style={{
              fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
              color: accent, letterSpacing: '0.18em', margin: '0 0 14px',
            }}>// DESCRIPTION</h3>
            <pre style={{
              fontFamily: 'Inter, system-ui, sans-serif', fontSize: 16, lineHeight: 1.65,
              color: '#d4d4d8', whiteSpace: 'pre-wrap', margin: 0,
            }}>{item.description}</pre>
          </div>
        </div>
        <aside style={{
          background: '#0a0a0a', borderLeft: '1px solid #27272a',
          padding: 32, color: '#fff',
          fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 12,
          alignSelf: 'start', position: 'sticky', top: 0,
        }}>
          <div style={{ marginBottom: 20 }}>
            <HeatTag item={item} accent={accent} />
            <span style={{ marginLeft: 8 }}><Countdown item={item} accent={accent} /></span>
          </div>
          <DossierRow k="ASKING" v={SnapAndSell.money(item.asking_price)} big accent={accent} />
          <DossierRow k="MIN OFFER" v={SnapAndSell.money(item.min_price)} accent={accent} />
          <DossierRow k="STRATEGY" v={item.pricing_strategy.replace('_', ' ').toUpperCase()} accent={accent} />
          <DossierRow k="CONDITION" v={item.condition.toUpperCase()} accent={accent} />
          <DossierRow k="CATEGORY" v={item.category.toUpperCase()} accent={accent} />
          <DossierRow k="LOCATION" v="SW DC" accent={accent} />
          <DossierRow k="PICKUP" v={item.pickup_type.toUpperCase()} accent={accent} />
          <DossierRow k="DEADLINE" v={item.deadline} accent={accent} />
          <DossierRow k="LISTED" v={(item.created_at || '').slice(0, 10)} accent={accent} />
          <div style={{ marginTop: 24 }}>
            <ContactCTA item={item} variant="accent" accent={accent} />
            <div style={{
              marginTop: 12, fontSize: 12, color: '#666', letterSpacing: '0.14em',
              textAlign: 'center', lineHeight: 1.5,
            }}>
              CASH · ZELLE · VENMO<br/>PICKUP · SW DC
            </div>
          </div>
        </aside>
      </div>
    </Modal>
  );
}

function DossierRow({ k, v, big, accent }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '10px 0', borderBottom: '1px dashed #27272a', gap: 12,
    }}>
      <span style={{ color: '#666', letterSpacing: '0.14em' }}>{k}</span>
      <span style={{
        color: '#fff', fontFamily: big ? 'Anton, Impact, sans-serif' : 'inherit',
        fontSize: big ? 24 : 12, letterSpacing: big ? '-0.01em' : '0.04em',
        textAlign: 'right',
      }}>{v}</span>
    </div>
  );
}

// Shared specs table.
function SpecsTable({ item, compact }) {
  const rows = [
    ['Condition', item.condition],
    ['Category', item.category],
    ['Pickup', item.pickup_type + ' / SW DC'],
    ['Deadline', item.deadline],
    ['Strategy', item.pricing_strategy.replace('_', ' ')],
  ];
  return (
    <table style={{
      width: '100%', borderCollapse: 'collapse',
      fontFamily: 'JetBrains Mono, ui-monospace, monospace',
      fontSize: compact ? 11 : 12,
    }}>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <td style={{
              padding: '8px 0', color: '#666', letterSpacing: '0.14em',
              textTransform: 'uppercase', borderBottom: '1px dashed #27272a',
              width: '40%',
            }}>{k}</td>
            <td style={{
              padding: '8px 0', color: '#fff', textAlign: 'right',
              borderBottom: '1px dashed #27272a', textTransform: 'uppercase',
            }}>{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

Object.assign(window, {
  DetailEditorial, DetailStark, DetailDossier, PhotoCarousel, Modal,
});
