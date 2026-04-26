// Shared data layer + helpers for all variations.
// Always pulls from the prod marketplace endpoint so the showcase shows the
// real listings + uploaded photos no matter where it's served from. Falls back
// to the bundled snapshot if the network is unreachable.
window.SnapAndSell = (function () {
  const API_BASE = 'https://snap-and-sell.onrender.com';
  // /api/marketplace includes a photos array per listing; /api/listings doesn't.
  const API = API_BASE + '/api/marketplace';
  const FALLBACK = 'listings.json';

  // IDs pinned as featured/hero -- always sort to position 0 so the masonry
  // grid puts them in the big hero tile, regardless of urgency/price sort.
  const FEATURED_IDS = new Set([3]); // 3 = IKEA FRIHETEN sleeper sectional

  // For these IDs, prefer the most-recently-uploaded photo over the existing
  // primary. Workaround: backend has no "delete photo" / "set primary"
  // endpoint and redeploying would wipe the Free-tier DB.
  const PHOTO_PREFER_NEWEST = new Set([3]);

  // Cross-listing photo cleanup (no DELETE endpoint): listing 13 (kitchen
  // table set) was uploaded with photos that actually show the bar table
  // and the Branch office chair. Hide those server-side photo ids.
  const PHOTO_HIDE_IDS = { 3: new Set([3]), 13: new Set([10, 13]), 20: new Set([30]), 21: new Set([43]) };

  // Pin a specific server-side photo id to the front (as the visual primary)
  // when the DB primary flag is wrong. 12 = wide MARIEDAMM/BERGMUND shot.
  // 44 = Samsung Freestyle hero side-profile.
  const PHOTO_PIN_FIRST = { 13: 12, 21: 44 };

  // Normalize string fields the design assumes are always present.
  // Local dev DB sometimes has nulls; prod has full SW DC values.
  function normalize(item) {
    return {
      ...item,
      condition: item.condition || 'unknown',
      location: item.location || 'SW DC',
      pickup_type: item.pickup_type || 'home',
      pricing_strategy: item.pricing_strategy || 'hold',
      category: item.category || 'misc',
      _featured: FEATURED_IDS.has(item.id),
    };
  }

  async function loadListings() {
    try {
      const r = await fetch(API);
      if (!r.ok) throw new Error('api ' + r.status);
      const data = await r.json();
      if (Array.isArray(data) && data.length) return data.map(normalize);
      throw new Error('empty');
    } catch (e) {
      const r = await fetch(FALLBACK);
      const data = await r.json();
      return data.map(normalize);
    }
  }

  // Days until deadline (Jun 1 2026). Negative if past.
  function daysUntil(deadline, today = new Date()) {
    if (!deadline) return null;
    const d = new Date(deadline + 'T00:00:00');
    const ms = d - today;
    return Math.ceil(ms / 86400000);
  }

  // Heat label from pricing_strategy + days remaining.
  function heat(item, today) {
    const days = daysUntil(item.deadline, today);
    if (item.pricing_strategy === 'fire_sale') return { label: 'FIRE SALE', tone: 'hot', days };
    if (item.pricing_strategy === 'aggressive') return { label: 'AGGRESSIVE', tone: 'warm', days };
    return { label: 'HOLD', tone: 'cool', days };
  }

  // Offer guidance copy from min_price / asking_price.
  function offerLine(item) {
    if (!item.min_price || !item.asking_price) return null;
    const pct = Math.round(((item.asking_price - item.min_price) / item.asking_price) * 100);
    return { min: item.min_price, ask: item.asking_price, pct };
  }

  // Savings vs original retail. Returns null when no original_price on file
  // or the asking price isn't actually below it.
  function savingsLine(item) {
    const orig = Number(item.original_price);
    const ask = Number(item.asking_price);
    if (!orig || !ask || ask >= orig) return null;
    return { orig, ask, pct: Math.round((1 - ask / orig) * 100) };
  }

  // Category short-code for stamps / placeholders.
  const CAT_CODE = {
    furniture: 'FRN',
    electronics: 'ELC',
    bicycles: 'CYC',
    fitness: 'FIT',
  };

  // Pull a short product code (3-letter brand-ish) from title for placeholders.
  function shortCode(item) {
    const t = item.title.toUpperCase();
    const known = ['IPAD', 'ROOMBA', 'IKEA', 'AOC', 'SAMSUNG', 'URB-E', 'SCHWINN', 'LOVESAC'];
    for (const k of known) if (t.includes(k)) return k.replace('-', '');
    return CAT_CODE[item.category] || 'ITM';
  }

  // First-line title (before " - " or " — " or first comma).
  function shortTitle(item) {
    return item.title.split(/\s[-—]\s/)[0].split(',')[0].trim();
  }

  // Pull photos straight from the marketplace response. Absolutize relative
  // /photos/* paths against the prod host so they resolve regardless of where
  // the showcase HTML is served from.
  function photosFor(item) {
    const p = item && item.photos;
    if (!Array.isArray(p) || !p.length) return [];
    // 1. Drop hidden photo ids (cross-listing duplicates).
    const hide = item && PHOTO_HIDE_IDS[item.id];
    let kept = hide ? p.filter(x => !(x && hide.has(x.id))) : p;
    // 2. PHOTO_PREFER_NEWEST: API lists primary first; prefer last-uploaded.
    if (item && PHOTO_PREFER_NEWEST.has(item.id)) kept = [...kept].reverse();
    // 3. Pin a specific server-side photo id to position 0 if requested.
    const pinId = item && PHOTO_PIN_FIRST[item.id];
    if (pinId != null) {
      const idx = kept.findIndex(x => x && x.id === pinId);
      if (idx > 0) kept = [kept[idx], ...kept.slice(0, idx), ...kept.slice(idx + 1)];
    }
    return kept.map(x => {
      const url = typeof x === 'string' ? x : (x && x.url) || '';
      if (!url) return null;
      if (url.startsWith('http://') || url.startsWith('https://')) return url;
      return API_BASE + (url.startsWith('/') ? url : '/' + url);
    }).filter(Boolean);
  }

  // Format $price.
  function money(n) {
    if (n == null) return '—';
    return '$' + n.toLocaleString('en-US');
  }

  // Live "today" so countdown updates without page reload (granularity: 1 min).
  function useToday() {
    const [now, setNow] = React.useState(() => new Date());
    React.useEffect(() => {
      const id = setInterval(() => setNow(new Date()), 60_000);
      return () => clearInterval(id);
    }, []);
    return now;
  }

  return {
    loadListings, daysUntil, heat, offerLine, savingsLine, shortCode, shortTitle,
    money, photosFor, useToday, CAT_CODE,
  };
})();
