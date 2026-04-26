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
    // PHOTO_PREFER_NEWEST: API returns photos with primary first; we want the
    // most-recently-uploaded one (last in the array) to lead.
    const ordered = item && PHOTO_PREFER_NEWEST.has(item.id) ? [...p].reverse() : p;
    return ordered.map(x => {
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
    loadListings, daysUntil, heat, offerLine, shortCode, shortTitle,
    money, photosFor, useToday, CAT_CODE,
  };
})();
