// Renders a spoken line, showing Timbre audio tags (<coughs>, <sigh>…) as quiet stage directions.
const TAG = /<([^<>]{1,24})>/g;

export default function SpeechText({ text = "" }) {
  const parts = [];
  let last = 0;
  let m;
  TAG.lastIndex = 0;
  while ((m = TAG.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(<span className="sfx" key={m.index}>{m[1]}</span>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}
