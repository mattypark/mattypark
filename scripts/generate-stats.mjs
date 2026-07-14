/**
 * Renders the profile's stat cards as static SVGs committed into this repo.
 *
 * Why static: every hosted stats service (github-readme-stats and friends) is a live
 * third-party endpoint that eventually 503s — the shared instance is down right now.
 * These are generated in CI and served from the repo itself, so they cannot break.
 *
 *   node scripts/generate-stats.mjs           fetch fresh, render, save snapshot
 *   node scripts/generate-stats.mjs --cached  render from the last snapshot
 *
 * GITHUB_TOKEN raises the API limit from 60/hr to 5,000/hr. CI always sets it.
 */

import { writeFileSync, readFileSync, mkdirSync, existsSync } from 'node:fs';

const USER = process.env.PROFILE_USER || 'mattypark';
const TZ_OFFSET = -4; // America/New_York (EDT). GitHub stamps events in UTC.
const OUT = 'assets';
const SNAPSHOT = `${OUT}/stats-data.json`;

// Old-money monochrome: warm ivory ink on near-black, hairline rules, no accent colour.
const INK = '#F2EFE8';
const DIM = '#7E7B75';
const FAINT = '#413F3B';
const HAIR = '#2B2926';
const RAMP = ['#F2EFE8', '#CFCBC2', '#ACA89F', '#89857D', '#66635C', '#4A4841', '#333029'];

const MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace";
const SERIF = "Georgia, 'Iowan Old Style', 'Times New Roman', serif";

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Letterspaced small caps. SVG collapses runs of whitespace, so the gap between
// words has to be non-breaking or "WHEN I COMMIT" renders as "WHENICOMMIT".
const spaced = (s) =>
  s
    .split(' ')
    .map((word) => word.split('').join(' '))
    .join('\u00A0\u00A0\u00A0');

const hourLabel = (h) =>
  h === 0 ? 'midnight' : h === 12 ? 'noon' : h < 12 ? `${h}am` : `${h - 12}pm`;

async function gh(path) {
  const headers = { 'User-Agent': `${USER}-profile-stats`, Accept: 'application/vnd.github+json' };
  if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;

  const res = await fetch(`https://api.github.com${path}`, { headers });
  if (!res.ok) throw new Error(`GitHub ${res.status} on ${path}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

/** Everything the cards need, flattened — so a snapshot can stand in for the API. */
async function collect() {
  const profile = await gh(`/users/${USER}`);

  const repos = [];
  for (let page = 1; page <= 5; page++) {
    const batch = await gh(`/users/${USER}/repos?per_page=100&page=${page}&type=owner`);
    repos.push(...batch);
    if (batch.length < 100) break;
  }
  const original = repos.filter((r) => !r.fork);

  const bytes = {};
  for (const repo of original) {
    const langs = await gh(`/repos/${USER}/${repo.name}/languages`);
    for (const [name, size] of Object.entries(langs)) bytes[name] = (bytes[name] || 0) + size;
  }

  // The events feed is the only public source of commit *hours*. It reaches back ~90
  // days, which is the honest window for "when do I ship".
  const events = [];
  for (let page = 1; page <= 3; page++) {
    const batch = await gh(`/users/${USER}/events/public?per_page=100&page=${page}`);
    events.push(...batch);
    if (batch.length < 100) break;
  }
  const pushes = events.filter((e) => e.type === 'PushEvent').map((e) => e.created_at);

  // Bucket pushes into local hour × weekday, Monday-first — the way a week is lived.
  const utcGrid = Array.from({ length: 7 }, () => Array(24).fill(0));
  const hours = Array(24).fill(0);
  for (const stamp of pushes) {
    const d = new Date(stamp);
    let hour = d.getUTCHours() + TZ_OFFSET;
    let day = d.getUTCDay();
    if (hour < 0) {
      hour += 24;
      day = (day + 6) % 7;
    }
    utcGrid[day][hour]++;
    hours[hour]++;
  }
  const grid = [1, 2, 3, 4, 5, 6, 0].map((i) => utcGrid[i]);

  const lateNight = [22, 23, 0, 1, 2].reduce((sum, h) => sum + hours[h], 0);

  return {
    generatedAt: new Date().toISOString(),
    followers: profile.followers,
    publicRepos: repos.length,
    originalRepos: original.length,
    bytes,
    grid,
    hours,
    pushCount: pushes.length,
    peakHour: hours.indexOf(Math.max(...hours)),
    lateShare: pushes.length ? Math.round((lateNight / pushes.length) * 100) : 0,
  };
}

const shell = (w, h, label, body) => `<svg
  xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 ${w} ${h}" width="${w}" height="${h}"
  role="img" aria-label="${esc(label)}"
  font-family="${MONO}"
>
  <defs>
    <radialGradient id="bg" cx="50%" cy="40%" r="80%">
      <stop offset="0%" stop-color="#141414" />
      <stop offset="100%" stop-color="#080808" />
    </radialGradient>
    <style>
      .ink { fill: ${INK} } .dim { fill: ${DIM} } .faint { fill: ${FAINT} }
      .serif { font-family: ${SERIF} }
      .rise { opacity: 0; animation: rise .8s cubic-bezier(.16,1,.3,1) forwards }
      @keyframes rise { from { opacity: 0; transform: translateY(5px) } to { opacity: 1; transform: none } }
      .frame {
        fill: none; stroke: ${HAIR}; stroke-width: 1;
        stroke-dasharray: ${2 * (w + h)}; stroke-dashoffset: ${2 * (w + h)};
        animation: draw 1.2s cubic-bezier(.16,1,.3,1) forwards;
      }
      @keyframes draw { to { stroke-dashoffset: 0 } }
    </style>
  </defs>
  <rect x="1" y="1" width="${w - 2}" height="${h - 2}" rx="7" fill="url(#bg)" />
  <rect class="frame" x="1" y="1" width="${w - 2}" height="${h - 2}" rx="7" />
${body}
</svg>
`;

/** Donut of language share, drawn arc by arc, with percentages and hard counts. */
function languagesCard(s) {
  const W = 880;
  const H = 320;

  const total = Object.values(s.bytes).reduce((a, b) => a + b, 0);
  const ranked = Object.entries(s.bytes).sort((a, b) => b[1] - a[1]);
  const top = ranked.slice(0, 6);
  const rest = ranked.slice(6).reduce((sum, [, v]) => sum + v, 0);
  const slices = rest > 0 ? [...top, ['Other', rest]] : top;

  const cx = 138;
  const cy = 176;
  const r = 74;
  const circumference = 2 * Math.PI * r;

  let offset = 0;
  const arcs = slices
    .map(([, size], i) => {
      const len = (size / total) * circumference;
      // Each arc parks at its own start angle via a negative dashoffset, then grows.
      const arc = `
    <circle
      cx="${cx}" cy="${cy}" r="${r}" fill="none"
      stroke="${RAMP[i % RAMP.length]}" stroke-width="19"
      stroke-dasharray="0 ${circumference.toFixed(2)}"
      stroke-dashoffset="${(-offset).toFixed(2)}"
      transform="rotate(-90 ${cx} ${cy})"
    >
      <animate attributeName="stroke-dasharray"
        from="0 ${circumference.toFixed(2)}"
        to="${Math.max(len - 2.5, 0).toFixed(2)} ${(circumference - len + 2.5).toFixed(2)}"
        dur="0.75s" begin="${(0.55 + i * 0.15).toFixed(2)}s"
        calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1" fill="freeze" />
    </circle>`;
      offset += len;
      return arc;
    })
    .join('');

  const legend = slices
    .map(([name, size], i) => {
      const y = 118 + i * 27;
      return `
    <g class="rise" style="animation-delay:${(0.9 + i * 0.09).toFixed(2)}s">
      <rect x="266" y="${y - 9}" width="10" height="10" fill="${RAMP[i % RAMP.length]}" />
      <text class="ink" x="290" y="${y}" font-size="14">${esc(name)}</text>
      <text class="dim" x="470" y="${y}" font-size="14" text-anchor="end">${((size / total) * 100).toFixed(1)}%</text>
    </g>`;
    })
    .join('');

  const numbers = [
    [s.originalRepos, 'original repos'],
    [s.publicRepos, 'public repos'],
    [ranked.length, 'languages'],
    [s.pushCount, 'pushes · 90d'],
  ]
    .map(([value, label], i) => {
      const y = 112 + i * 48;
      return `
    <g class="rise" style="animation-delay:${(1.15 + i * 0.1).toFixed(2)}s">
      <text class="ink serif" x="560" y="${y}" font-size="30">${value}</text>
      <text class="dim" x="648" y="${y}" font-size="13">${esc(label)}</text>
      <line x1="560" y1="${y + 14}" x2="840" y2="${y + 14}" stroke="${HAIR}" />
    </g>`;
    })
    .join('');

  const lead = ((top[0][1] / total) * 100).toFixed(0);

  const body = `
  <text class="serif faint rise" x="40" y="44" font-size="11" letter-spacing="3.2" style="animation-delay:.45s">${spaced('LANGUAGES')}</text>
  <text class="dim rise" x="40" y="68" font-size="12.5" style="animation-delay:.5s">by bytes written across ${s.originalRepos} original repositories</text>
  <line x1="40" y1="86" x2="840" y2="86" stroke="${HAIR}" />
${arcs}
  <text class="ink serif rise" x="${cx}" y="${cy - 2}" font-size="26" text-anchor="middle" style="animation-delay:1.55s">${lead}%</text>
  <text class="dim rise" x="${cx}" y="${cy + 20}" font-size="11.5" text-anchor="middle" style="animation-delay:1.6s">${esc(top[0][0])}</text>
${legend}
${numbers}`;

  const label = `Languages by bytes: ${top.map(([n, v]) => `${n} ${((v / total) * 100).toFixed(0)}%`).join(', ')}. ${s.originalRepos} original repositories, ${ranked.length} languages.`;
  return shell(W, H, label, body);
}

/** 7×24 matrix of when pushes actually land. GitHub shows the days; nobody shows the hours. */
function rhythmCard(s) {
  const W = 880;
  const H = 376;

  const x0 = 74;
  const y0 = 122;
  const cell = 29;
  const box = 21;
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
  const peak = Math.max(1, ...s.grid.flat());

  const rows = s.grid
    .map((row, d) => {
      const cells = row
        .map((count, h) => {
          const x = x0 + h * cell;
          const y = y0 + d * cell;
          const delay = (0.7 + h * 0.022 + d * 0.03).toFixed(2);

          if (!count) {
            return `<rect class="rise" x="${x}" y="${y}" width="${box}" height="${box}" rx="2" fill="none" stroke="${FAINT}" style="animation-delay:${delay}s" />`;
          }
          const weight = 0.3 + 0.7 * (count / peak);
          return `<rect class="rise" x="${x}" y="${y}" width="${box}" height="${box}" rx="2" fill="${INK}" fill-opacity="${weight.toFixed(2)}" style="animation-delay:${delay}s"><title>${days[d]} ${String(h).padStart(2, '0')}:00 — ${count} push${count > 1 ? 'es' : ''}</title></rect>`;
        })
        .join('\n      ');

      return `
    <g>
      <text class="serif faint" x="56" y="${y0 + d * cell + 15}" font-size="9.5" letter-spacing="1.4" text-anchor="end">${days[d]}</text>
      ${cells}
    </g>`;
    })
    .join('');

  const ticks = [0, 6, 12, 18, 23]
    .map((h) => {
      const label = h === 0 ? '12a' : h === 12 ? '12p' : h < 12 ? `${h}a` : `${h - 12}p`;
      return `<text class="faint" x="${x0 + h * cell + box / 2}" y="${y0 - 14}" font-size="10" text-anchor="middle">${label}</text>`;
    })
    .join('\n  ');

  // Hairline through the busiest hour of the day.
  const peakX = x0 + s.peakHour * cell + box / 2;
  const footY = y0 + 7 * cell + 40;

  const body = `
  <text class="serif faint rise" x="40" y="44" font-size="11" letter-spacing="3.2" style="animation-delay:.45s">${spaced('WHEN I COMMIT')}</text>
  <text class="dim rise" x="40" y="68" font-size="12.5" style="animation-delay:.5s">${s.pushCount} pushes · last 90 days · America/New_York</text>
  <line x1="40" y1="86" x2="840" y2="86" stroke="${HAIR}" />
  ${ticks}
${rows}
  <g class="rise" style="animation-delay:2.3s">
    <line x1="${peakX}" y1="${y0 - 8}" x2="${peakX}" y2="${y0 + 7 * cell + 6}" stroke="${INK}" stroke-width="1" stroke-dasharray="2 3" opacity="0.45" />
    <line x1="40" y1="${footY - 24}" x2="840" y2="${footY - 24}" stroke="${HAIR}" />
    <text class="ink" x="40" y="${footY}" font-size="13.5">${s.lateShare}% of my pushes land between 10pm and 3am.</text>
    <text class="faint" x="840" y="${footY}" font-size="12" text-anchor="end">busiest hour · ${hourLabel(s.peakHour)}</text>
  </g>`;

  const label = `Commit rhythm: ${s.pushCount} pushes over 90 days, busiest hour ${hourLabel(s.peakHour)}, ${s.lateShare}% between 10pm and 3am.`;
  return shell(W, H, label, body);
}

// --- run ---------------------------------------------------------------------

const useCache = process.argv.includes('--cached');
let snapshot;

if (useCache) {
  if (!existsSync(SNAPSHOT)) throw new Error(`No snapshot at ${SNAPSHOT} — run without --cached first.`);
  snapshot = JSON.parse(readFileSync(SNAPSHOT, 'utf8'));
  console.log(`using snapshot from ${snapshot.generatedAt}`);
} else {
  snapshot = await collect();
}

mkdirSync(OUT, { recursive: true });
writeFileSync(SNAPSHOT, JSON.stringify(snapshot, null, 2));
writeFileSync(`${OUT}/languages.svg`, languagesCard(snapshot));
writeFileSync(`${OUT}/rhythm.svg`, rhythmCard(snapshot));

console.log(`languages.svg — ${Object.keys(snapshot.bytes).length} languages, ${snapshot.originalRepos} original repos`);
console.log(`rhythm.svg    — ${snapshot.pushCount} pushes, peak ${hourLabel(snapshot.peakHour)}, ${snapshot.lateShare}% late-night`);
