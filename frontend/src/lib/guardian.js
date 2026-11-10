// Guardian mode risk score, client side: the same rules as backend/dadi/guardian.py, read from the same JSON
// (guardian-rules.json is a byte-identical copy of backend/dadi/data/guardian_rules.json). A pytest runs this file
// with node and checks that it gives exactly the Python scores and reasons. Plain ES module: no imports.

export const LEVELS = ["safe", "caution", "stop"];

export function levelFor(score, rules) {
  const th = rules.thresholds;
  return score >= th.stop ? "stop" : score >= th.caution ? "caution" : "safe";
}

export function normalise(text, rules) {
  return " " + text.toLowerCase().replace(new RegExp(rules.separators, "g"), " ").trim() + " ";
}

// The red flags one utterance raises, in rule order: [[flag key, what was heard], ...]
export function flagsIn(text, rules) {
  const norm = normalise(text, rules);
  const raw = text.toLowerCase();
  const hits = [];
  for (const f of rules.flags) {
    let heard = null;
    const term = f.terms.find((t) => norm.includes(t));
    if (term !== undefined) heard = term.trim();
    else {
      for (const p of f.patterns) {
        const m = raw.match(new RegExp(p));
        if (m) { heard = m[0]; break; }
      }
    }
    if (heard !== null) hits.push([f.key, heard]);
  }
  return hits;
}

// Each flag counts once; diminishing returns: 100 * (1 - prod(1 - w/100)). Reasons carry the points they added.
export function createTracker(rules) {
  const byKey = Object.fromEntries(rules.flags.map((f) => [f.key, f]));
  const t = { remaining: 1, reasons: [], turns: 0 };
  const score = () => Math.round(100 * (1 - t.remaining));
  t.score = score;
  t.level = () => levelFor(score(), rules);
  t.add = (text) => {
    t.turns += 1;
    const fresh = [];
    for (const [key, heard] of flagsIn(text, rules)) {
      if (t.reasons.some((r) => r.flag === key) || !byKey[key]) continue;
      const before = score();
      t.remaining *= 1 - byKey[key].weight / 100;
      const points = score() - before;
      const r = { flag: key, points, heard, turn: t.turns, text: `+${points}: ${byKey[key].reason}` };
      t.reasons.push(r);
      fresh.push(r);
    }
    return fresh;
  };
  return t;
}

// Risk after each utterance (the backend's score_texts gives the same list)
export function scoreTexts(texts, rules) {
  const tr = createTracker(rules);
  return texts.map((text) => {
    tr.add(text);
    return { score: tr.score(), level: tr.level(), reasons: tr.reasons.map((r) => r.text) };
  });
}

export const warningText = (rules, lang, level) => (rules.warnings[lang] || rules.warnings.hi)[level];
