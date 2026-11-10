// Product landing page (route "#/"). The app itself lives at "#/app/...".
// Every number and claim here comes from the README / docs/test-log.md; animation is anime.js v4.
import { Fragment, useEffect, useRef } from "react";
import { animate, createTimeline, stagger, svg, utils } from "animejs";
import {
  ArrowRight, AudioLines, CirclePlay, ExternalLink, FileLock2, Fingerprint, Github, MessageSquareWarning,
  Network, PhoneCall, ShieldCheck, Target, Users, Check, Minus,
} from "lucide-react";
import { countUp, onceVisible, reducedMotion, revealOnScroll } from "../motion";
import { APP_HREF, AWAAZ_URL, PUKAAR_URL, REPO_URL, VIDEO_URL } from "./links";
import Pipeline from "./Pipeline";
import "../landing.css";

const SRC = {
  mha2024: "https://inc42.com/?p=523954",
  seniors: "https://newsable.asianetnews.com/india/senior-citizens-women-lost-rs-7-769-crore-to-cyber-fraud-in-2025-articleshow-u9oad8w",
  oswal: "https://scroll.in/latest/1073888/2-arrested-for-duping-industrialist-sp-oswal-of-rs-7-crore-by-posing-as-officers-of-central-agencies",
};

const FEATURES = [
  { icon: PhoneCall, tone: "pink", title: "Live call in 5 code-mixed languages", img: "f-live",
    text: "Dadi, Paati, Thakuma, Ajji and Ammamma speak Hinglish, Tanglish, Benglish, Kanglish and Tenglish. Prisma v3.0 hears him; Timbre v3.0 answers, and she really coughs." },
  { icon: Target, tone: "violet", title: "Mission + live intel", img: "f-intel",
    text: "Give her a goal: UPI ID, bank account + IFSC, WhatsApp number. She plays along until he says where the money goes, and every ID is extracted as he speaks." },
  { icon: FileLock2, tone: "cyan", title: "Complaint + SHA-256 evidence", img: "f-report",
    text: "One click drafts the complaint for cybercrime.gov.in, 1930 and Chakshu. Each call is recorded in two tracks and sealed with SHA-256 in an evidence ZIP." },
  { icon: Fingerprint, tone: "pink", title: "She remembers a voice", img: "f-voice",
    text: "About 8 s in, Gnani's voice-cloning embedding fingerprints the caller. A repeat scammer gets teased in character, and the war room shows the earlier call." },
  { icon: Network, tone: "violet", title: "Scam Ring Radar", img: "f-rings",
    text: "Calls that share a mule ID or the same voice are linked: two “different officers” with different scripts turn out to be one gang." },
  { icon: ShieldCheck, tone: "green", title: "Guardian mode", img: "f-guardian",
    text: "Protects a real elder on her own call: a rule-based risk score (0–100, no LLM), and Timbre calmly warns her in her language at 40 and at 70." },
  { icon: Users, tone: "amber", title: "Family hand-off", img: "f-family",
    text: "At peak pressure Dadi passes the phone to grandson Bunty, who “tries to pay” and makes the scammer spell the UPI ID, account and IFSC." },
  { icon: MessageSquareWarning, tone: "cyan", title: "Message checker", img: "f-check",
    text: "Paste an SMS, WhatsApp or “notice” in any script: verdict, red flags, IDs, the true fact, and a Dadi reply that baits the sender." },
];

const MEASURED = [
  { to: 156, unit: "ms", label: "Prisma v3.0 streaming: final transcript after end of speech", note: "smoke test, 10 Nov" },
  { to: 0.65, decimals: 2, unit: "s", label: "Timbre v3.0 streaming: first audio chunk", note: "measured live" },
  { to: 0.956, decimals: 3, unit: "", label: "Live repeat-caller voice match, mid-call", note: "same voice 0.93–0.96 · others ≤ 0.78" },
  { to: 0, unit: "", label: "Persona breaks in arena calls through 10 dB call-centre noise", note: "8 Nov" },
  { to: 256, unit: "", label: "Automated tests, all passing with fakes", note: "uv run python -m pytest -q" },
];

const COMPARE = [
  { name: "Apate.ai", where: "Australia · CommBank, TPG", does: "AI bots hold long scam calls and extract intelligence for banks", lang: "English accents incl. Indian", india: "For Australian banks; no Indian reporting channels", yes: false },
  { name: "O2 “Daisy”", where: "UK · Nov 2024", does: "AI granny that wastes scammers' time", lang: "UK English", india: "No (a publicity campaign, not a product)", yes: false },
  { name: "Truecaller Assistant", where: "India", does: "Screens calls for you, with a transcript", lang: "English, Hindi, Hinglish", india: "No: it screens, it does not bait", yes: false },
  { name: "Dadi vs Scammers", where: "India · built on Gnani AI", does: "Baits in code-mix, extracts UPI IDs and accounts live, drafts the complaint, seals the recording, recognises repeat voices", lang: "Hinglish, Tanglish, Benglish, Kanglish, Tenglish", india: "Yes", yes: true, us: true },
];

function Mark({ size = 36 }) {
  return <img src="/icons/mark.svg" width={size} height={size} alt="" className="l-mark" />;
}

function Headline() {
  const lines = [["Don't", "block", "scammers."], ["Route", "them", "to", "Dadi."]];
  return (
    <h1 className="l-h1" aria-label="Don't block scammers. Route them to Dadi.">
      {lines.map((ws, li) => (
        <span className="l-line" key={li} aria-hidden="true">
          {ws.map((w, i) => (
            <Fragment key={i}><span className="l-w"><span className={w === "Dadi." ? "l-grad" : ""}>{w}</span></span>{i < ws.length - 1 ? " " : ""}</Fragment>
          ))}
        </span>
      ))}
    </h1>
  );
}

function Wave({ bars = 44 }) {
  return (
    <div className="l-wave" aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => <i key={i} />)}
    </div>
  );
}

function Hero() {
  const root = useRef(null);
  useEffect(() => {
    const el = root.current;
    if (!el) return undefined;
    const bars = el.querySelectorAll(".l-wave i");
    if (reducedMotion()) { el.classList.add("is-in"); return undefined; }
    const anims = [];
    // gradient mesh drifts slowly (transform only)
    el.querySelectorAll(".l-blob").forEach((b, i) => {
      anims.push(animate(b, {
        translateX: [0, [60, -70, 50, -40][i]], translateY: [0, [-40, 50, 30, -60][i]], scale: [1, [1.15, 0.9, 1.2, 1.1][i]],
        duration: 9000 + i * 2200, ease: "inOutSine", loop: true, alternate: true,
      }));
    });
    // live voice waveform: each bar breathes on its own random keyframes
    bars.forEach((b, i) => {
      const base = 0.25 + 0.55 * Math.abs(Math.sin(i * 0.42));
      const ks = Array.from({ length: 4 }, () => ({ to: Math.min(1, Math.max(0.12, base * utils.random(0.35, 1.5, 2))) }));
      anims.push(animate(b, { scaleY: ks, duration: utils.random(1300, 2100), ease: "inOutSine", loop: true, alternate: true, delay: i * 18 }));
    });
    const tl = createTimeline({ defaults: { ease: "outExpo" } })
      .add(".l-hero .l-eyebrow", { opacity: [0, 1], translateY: [14, 0], duration: 700 }, 80)
      .add(".l-hero .l-w > span", { translateY: ["108%", "0%"], opacity: [0, 1], duration: 1100, delay: stagger(70) }, 160)
      .add(".l-hero .l-sub", { opacity: [0, 1], translateY: [18, 0], duration: 900 }, 620)
      .add(".l-hero .l-live", { opacity: [0, 1], translateY: [14, 0], duration: 800 }, 760)
      .add(".l-hero .l-cta > *", { opacity: [0, 1], translateY: [16, 0], duration: 800, delay: stagger(90) }, 860)
      .add(".l-hero .l-shot", { opacity: [0, 1], translateY: [60, 0], scale: [0.94, 1], duration: 1500 }, 420)
      .add(".l-hero .l-chip", { opacity: [0, 1], scale: [0.6, 1], duration: 900, delay: stagger(160), ease: "outBack(1.6)" }, 1200);
    el.classList.add("is-in");
    anims.push(tl);
    // the screenshot floats gently once it has landed
    const fl = el.querySelector(".l-float");
    if (fl) anims.push(animate(fl, { translateY: [-6, 8], duration: 4200, ease: "inOutSine", loop: true, alternate: true }));
    return () => anims.forEach((a) => a.pause());
  }, []);

  return (
    <header className="l-hero" ref={root}>
      <div className="l-mesh" aria-hidden="true">
        <span className="l-blob b1" /><span className="l-blob b2" /><span className="l-blob b3" /><span className="l-blob b4" />
        <span className="l-gridbg" />
      </div>
      <div className="l-wrap l-hero-grid">
        <div className="l-hero-copy">
          <div className="l-eyebrow"><span className="l-dot" />Built on Gnani AI · Prisma v3.0 + Timbre v3.0</div>
          <Headline />
          <p className="l-sub">
            An AI grandmother answers scam calls in five Indian code-mixed languages, wastes the scammer's time,
            gets his mule UPI IDs and bank accounts, drafts the complaint for 1930, seals the recording as evidence,
            and never forgets a voice.
          </p>
          <div className="l-live">
            <span className="l-live-tag"><AudioLines size={15} /> Dadi is on the line</span>
            <Wave />
          </div>
          <div className="l-cta">
            <a className="l-btn primary" href={APP_HREF}>Try the live demo <ArrowRight size={17} /></a>
            <a className="l-btn" href={VIDEO_URL} target="_blank" rel="noreferrer"><CirclePlay size={17} /> Watch the 3-minute video</a>
          </div>
        </div>
        <div className="l-hero-art">
          <div className="l-float">
            <figure className="l-shot">
              <div className="l-chrome" aria-hidden="true"><i /><i /><i /><span>dadi-vs-scammers · war room</span></div>
              <img src="/landing/warroom.webp" width="1280" height="800" alt="The war room during a live scam call: transcript, tactic, extracted UPI ID and mission status" fetchpriority="high" />
            </figure>
            <span className="l-chip c1"><Fingerprint size={14} /> Voice match 0.956</span>
            <span className="l-chip c2"><FileLock2 size={14} /> Sealed · SHA-256</span>
            <span className="l-chip c3"><Check size={14} /> Mission: UPI ID captured</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function useReveal(opts) {
  const ref = useRef(null);
  useEffect(() => revealOnScroll(ref.current, "[data-reveal]", opts), []); // eslint-disable-line react-hooks/exhaustive-deps
  return ref;
}

function useCounts() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    return onceVisible(el, () => {
      el.querySelectorAll("[data-count]").forEach((n, i) => {
        const to = Number(n.dataset.count), d = Number(n.dataset.dec || 0);
        countUp(n, to, { decimals: d, duration: 1800, delay: i * 120 });
      });
    });
  }, []);
  return ref;
}

function Problem() {
  const reveal = useReveal();
  const counts = useCounts();
  const set = (el) => { reveal.current = el; counts.current = el; };
  return (
    <section className="l-sec l-problem" id="problem" ref={set}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>The problem</p>
        <h2 className="l-h2" data-reveal>Blocking a scam call costs him nothing. <span className="l-dim">He just dials the next number.</span></h2>
        <div className="l-stats">
          <a className="l-stat" data-reveal href={SRC.mha2024} target="_blank" rel="noreferrer">
            <div className="l-stat-v"><small>₹</small><span data-count="22845">22,845</span><small> crore</small></div>
            <div className="l-stat-l">lost by Indians to cyber fraud in 2024, three times 2023</div>
            <div className="l-src">MHA reply in the Lok Sabha, via Inc42 <ExternalLink size={12} /></div>
          </a>
          <a className="l-stat" data-reveal href={SRC.seniors} target="_blank" rel="noreferrer">
            <div className="l-stat-v"><span data-count="103488">1,03,488</span></div>
            <div className="l-stat-l">senior citizens reported losing <b>₹4,005 crore</b> in 2025: about 4% of complainants, roughly 18% of the money</div>
            <div className="l-src">MHA's Rajya Sabha reply, via ANI <ExternalLink size={12} /></div>
          </a>
          <a className="l-stat" data-reveal href={SRC.oswal} target="_blank" rel="noreferrer">
            <div className="l-stat-v"><small>₹</small><span data-count="7">7</span><small> crore</small></div>
            <div className="l-stat-l">taken from industrialist S.P. Oswal by fake &ldquo;CBI officers&rdquo; who held him on Skype for two days (Ludhiana, Aug 2024)</div>
            <div className="l-src">Scroll <ExternalLink size={12} /></div>
          </a>
        </div>
        <p className="l-lede" data-reveal><b>Routing the call to Dadi costs him real time</b> that would have gone to a real victim. And every scam ends with &ldquo;send the money here&rdquo;. Dadi plays along until he says where.</p>
      </div>
    </section>
  );
}

function Features() {
  const ref = useReveal({ gap: 60 });
  return (
    <section className="l-sec" id="features" ref={ref}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>What Dadi does</p>
        <h2 className="l-h2" data-reveal>One sweet, slightly deaf grandmother. <span className="l-dim">Eight ways she ruins a scammer's day.</span></h2>
        <div className="l-features">
          {FEATURES.map((f) => (
            <article className={`l-feat t-${f.tone}`} key={f.title} data-reveal>
              <div className="l-thumb"><img src={`/landing/${f.img}.webp`} width="720" height="450" loading="lazy" decoding="async" alt="" /></div>
              <div className="l-feat-body">
                <span className="l-ic"><f.icon size={18} /></span>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function How() {
  const ref = useReveal();
  return (
    <section className="l-sec l-how" id="how" ref={ref}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>How it works</p>
        <h2 className="l-h2" data-reveal>Every word he says goes through Gnani. <span className="l-dim">Every word she says comes back through Gnani.</span></h2>
        <div data-reveal><Pipeline /></div>
        <p className="l-note" data-reveal>Dialogue and extraction run on Groq <code>qwen/qwen3.8-27b</code> in the demo. Evon v3.3 is supported by the same adapter but has no hosted API, so it was not used.</p>
      </div>
    </section>
  );
}

function Results() {
  const reveal = useReveal({ gap: 80 });
  const counts = useCounts();
  const set = (el) => { reveal.current = el; counts.current = el; };
  return (
    <section className="l-sec" id="results" ref={set}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>Measured on Gnani's live servers</p>
        <h2 className="l-h2" data-reveal>Fast enough to feel like a phone call. <span className="l-dim">Stubborn enough to never break character.</span></h2>
        <div className="l-metrics">
          {MEASURED.map((m) => (
            <div className="l-metric" key={m.label} data-reveal>
              <div className="l-metric-v"><span data-count={m.to} data-dec={m.decimals || 0}>{m.to.toFixed(m.decimals || 0)}</span>{m.unit && <small>{m.unit}</small>}</div>
              <div className="l-metric-l">{m.label}</div>
              <div className="l-metric-n">{m.note}</div>
            </div>
          ))}
        </div>
        <p className="l-note" data-reveal>Smoke test 10 Nov 2026: 7/7 Gnani + Groq checks pass. Full numbers and method in <a href={`${REPO_URL}/blob/main/docs/test-log.md`} target="_blank" rel="noreferrer">docs/test-log.md</a>.</p>
      </div>
    </section>
  );
}

function Quote() {
  const ref = useReveal();
  return (
    <section className="l-sec l-quote-sec" ref={ref}>
      <div className="l-wrap">
        <figure className="l-quote" data-reveal>
          <div className="l-quote-head"><Mark size={42} /><div><b>She remembers him</b><span>Live AI-vs-AI test · 10 Nov 2026 · 8 kHz line, 10 dB call-centre noise</span></div><span className="l-match">voice match <b>0.956</b></span></div>
          <blockquote lang="hi">&ldquo;राहुल जी, आपकी आवाज़ में वह पुराना विजय राठौड़ का हुशार-पन है ना? <i>(laughs)</i> तब कहते थे पुलिस वाले हैं, अब SBI वाले? किस्से बदलते रहते हैं, बेटा।&rdquo;</blockquote>
          <figcaption>&ldquo;Rahul ji, your voice has that old cleverness of Vijay Rathore, doesn't it? Back then you said you were police, now SBI? Your stories keep changing, son.&rdquo;</figcaption>
          <p className="l-quote-foot">Call 1: &ldquo;Inspector Vijay Rathore, CBI&rdquo;. Call 2, same voice, new name and new story: &ldquo;Rahul, SBI head office&rdquo;. About 8 seconds in, Gnani's voice-cloning embedding matched the earlier call and Dadi said this, unscripted. The Scam Ring Radar then linked both &ldquo;officers&rdquo; as one caller.</p>
        </figure>
      </div>
    </section>
  );
}

function Compare() {
  const ref = useReveal({ gap: 60 });
  return (
    <section className="l-sec" id="compare" ref={ref}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>How Dadi is different</p>
        <h2 className="l-h2" data-reveal>Others screen, label or entertain. <span className="l-dim">Dadi turns the call into evidence.</span></h2>
        <div className="l-table" role="table" aria-label="Comparison with similar products">
          <div className="l-tr l-th" role="row" data-reveal>
            <span role="columnheader">Product</span><span role="columnheader">What it does</span><span role="columnheader">Languages</span><span role="columnheader">Mule IDs + evidence for India?</span>
          </div>
          {COMPARE.map((r) => (
            <div className={`l-tr ${r.us ? "us" : ""}`} role="row" key={r.name} data-reveal>
              <span role="cell" className="l-td-name"><b>{r.name}</b><small>{r.where}</small></span>
              <span role="cell" data-h="What it does">{r.does}</span>
              <span role="cell" data-h="Languages">{r.lang}</span>
              <span role="cell" data-h="Mule IDs + evidence for India?" className={r.yes ? "yes" : "no"}>{r.yes ? <Check size={15} /> : <Minus size={15} />}{r.india}</span>
            </div>
          ))}
        </div>
        <p className="l-note" data-reveal>To our knowledge, as of Nov 2026, no publicly reported scam-baiting voice agent both converses in Indian code-mixed languages and turns the call into UPI or mule-account identifiers, evidence and a complaint draft for India's reporting channels (cybercrime.gov.in, 1930, Chakshu).</p>
      </div>
    </section>
  );
}

function Engine() {
  const ref = useReveal({ gap: 90 });
  const items = [
    { name: "Dadi vs Scammers", text: "An AI grandmother who baits scam callers and turns the call into mule IDs, evidence and a complaint.", href: REPO_URL, tag: "this site", tone: "pink" },
    { name: "Pukaar", text: "A flood-emergency voice line that answers overflow calls in the caller's language.", href: PUKAAR_URL, tone: "cyan" },
    { name: "Apni Awaaz", text: "Gives people who lost their voice their own voice back.", href: AWAAZ_URL, tone: "violet" },
  ];
  return (
    <section className="l-sec" id="engine" ref={ref}>
      <div className="l-wrap">
        <p className="l-kicker" data-reveal>One engine, three products</p>
        <h2 className="l-h2" data-reveal>The same <code>voice-core</code> on Gnani AI <span className="l-dim">powers all three.</span></h2>
        <div className="l-engine">
          {items.map((p) => (
            <a className={`l-prod t-${p.tone}`} key={p.name} href={p.href} target="_blank" rel="noreferrer" data-reveal>
              <span className="l-prod-top"><b>{p.name}</b>{p.tag ? <em>{p.tag}</em> : <Github size={16} />}</span>
              <span className="l-prod-text">{p.text}</span>
              <span className="l-prod-go">View on GitHub <ArrowRight size={15} /></span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function Closing() {
  const ref = useReveal();
  return (
    <section className="l-sec l-closing" ref={ref}>
      <div className="l-wrap">
        <div className="l-final" data-reveal>
          <Mark size={64} />
          <h2 className="l-h2">Put a scammer on hold. <span className="l-grad">Forever, if Dadi has her way.</span></h2>
          <div className="l-cta center">
            <a className="l-btn primary" href={APP_HREF}>Try the live demo <ArrowRight size={17} /></a>
            <a className="l-btn" href={REPO_URL} target="_blank" rel="noreferrer"><Github size={17} /> Read the code</a>
          </div>
        </div>
      </div>
    </section>
  );
}

function Nav() {
  const ref = useRef(null);
  useEffect(() => {
    const on = () => ref.current && ref.current.classList.toggle("solid", window.scrollY > 12);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  const go = (id) => (e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth" }); };
  return (
    <nav className="l-nav" ref={ref} aria-label="Main">
      <div className="l-wrap l-nav-in">
        <a className="l-brand" href="#/" aria-label="Dadi vs Scammers home"><Mark size={30} /><span>Dadi <em>vs</em> Scammers</span></a>
        <div className="l-links">
          <a href="#problem" onClick={go("problem")}>Problem</a>
          <a href="#features" onClick={go("features")}>Features</a>
          <a href="#how" onClick={go("how")}>How it works</a>
          <a href="#results" onClick={go("results")}>Results</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer"><Github size={15} /> GitHub</a>
        </div>
        <a className="l-btn primary sm" href={APP_HREF}>Live demo <ArrowRight size={15} /></a>
      </div>
    </nav>
  );
}

export default function Landing() {
  useEffect(() => {
    const prev = document.title;
    document.title = "Dadi vs Scammers: an AI grandmother who wastes scammers' time";
    window.scrollTo(0, 0);
    return () => { document.title = prev; };
  }, []);
  return (
    <div className="landing">
      <a className="l-skip" href="#features" onClick={(e) => { e.preventDefault(); document.getElementById("features")?.scrollIntoView(); }}>Skip to content</a>
      <Nav />
      <Hero />
      <main>
        <Problem />
        <Features />
        <How />
        <Results />
        <Quote />
        <Compare />
        <Engine />
        <Closing />
      </main>
      <footer className="l-foot">
        <div className="l-wrap l-foot-in">
          <div className="l-foot-brand"><Mark size={28} /><div><b>Dadi vs Scammers</b><span>Nitya Prakash Pandey · Dilavesh Kanz Nidooli</span></div></div>
          <p className="l-honest">
            <b>About this demo:</b> the live demo is a static replay of calls recorded on Gnani's live servers on 10 Nov 2026: no server,
            no API keys, no microphone. All callers are synthetic and every ID is fake. Run it locally with your own keys for a live call.
          </p>
          <div className="l-foot-row">
            <a href={REPO_URL} target="_blank" rel="noreferrer"><Github size={15} /> GitHub</a>
            <a href={APP_HREF}>Open the app</a>
            <span className="l-tags">#GnaniAI #GreatIndianAIInternshipChallenge</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
