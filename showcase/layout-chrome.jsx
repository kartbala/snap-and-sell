// Shared Header + Footer used by all three variations.
function Header({ items, accent, title, subtitle, terminal }) {
  const now = SnapAndSell.useToday();
  const days = SnapAndSell.daysUntil('2026-06-01', now);
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
            {' '}Sabbatical to the Netherlands.
            {' '}Pickup in SW DC -- address shared after payment. Cash, Zelle, or Venmo.
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
          }}>{days} days</div>
          <div style={{ marginTop: 6, color: '#fff' }}>UNTIL JUN 01 / 2026</div>
        </div>
      </div>
    </header>
  );
}

function Faq({ accent }) {
  const qa = [
    ['How do I buy something?',
     'Hit the EMAIL SELLER button on the item. It opens a pre-filled email to kartbala@gmail.com with the item name. First buyer with confirmed payment gets it.'],
    ['How do I pay?',
     'Venmo, Zelle, or cash, at pickup. No checks. No PayPal goods-and-services. No holds without payment.'],
    ['Can you deliver?',
     'No. Pickup is in SW DC -- exact address shared after payment. We will help you to the elevator and lobby. Bring a friend for anything heavy.'],
    ['Can I reserve something?',
     'Once you have paid, it is yours. We do not hold items for unpaid promises.'],
    ['Are prices negotiable?',
     'Most items, yes. Email an offer with the item name.'],
    ['Can I see it before I buy?',
     'Yes, email to schedule a look. Especially worth it for couches, dining tables, and anything with dimensions you need to verify.'],
    ['Will it fit through my door?',
     'Every listing shows W x D x H. Measure your hallway and doorways first. The FRIHETEN sectional comes apart into three pieces if needed.'],
    ['When does the sale end?',
     'Final pickups by May 30, 2026. Anything unsold is donated.'],
  ];
  return (
    <section style={{
      borderTop: '1px solid #27272a', padding: '56px 32px',
      fontFamily: 'Inter, system-ui, sans-serif',
      maxWidth: 920, margin: '0 auto', boxSizing: 'border-box',
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        fontSize: 12, color: accent, letterSpacing: '0.22em', marginBottom: 12,
      }}>HOW THIS WORKS</div>
      <h2 style={{
        fontFamily: 'Anton, Impact, sans-serif',
        fontSize: 'clamp(36px, 5vw, 56px)', lineHeight: 0.9,
        letterSpacing: '-0.01em', textTransform: 'uppercase',
        color: '#fff', margin: '0 0 32px',
      }}>Logistics &amp; FAQ</h2>
      <dl style={{ margin: 0, color: '#ddd', fontSize: 16, lineHeight: 1.55 }}>
        {qa.map(([q, a]) => (
          <div key={q} style={{ marginBottom: 22 }}>
            <dt style={{ color: '#fff', fontWeight: 700, marginBottom: 4 }}>{q}</dt>
            <dd style={{ margin: 0, color: '#aaa' }}>{a}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Footer({ accent }) {
  return (
    <>
      <Faq accent={accent} />
      <footer style={{
        borderTop: '1px solid #27272a', padding: '40px 32px',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 13,
        color: '#666', letterSpacing: '0.14em',
        display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
      }}>
        <span>EVERYTHING MUST GO · DEADLINE 2026·06·01</span>
        <span>SW DC · PICKUP ONLY · CASH · ZELLE · VENMO</span>
      </footer>
    </>
  );
}

Object.assign(window, { Header, Footer, Faq });
