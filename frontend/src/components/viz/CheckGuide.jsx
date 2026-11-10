// Context for the message checker while no result is shown: the red flags it looks for and the true facts.
import { BookOpenCheck, Flag } from "lucide-react";
import { Card } from "../../ui";
import { RED_FLAG_LABELS } from "../../lib/labels";

export default function CheckGuide() {
  return (
    <div className="grid g2">
      <Card icon={Flag} title="Red flags Dadi looks for">
        <ul className="side-list">{Object.values(RED_FLAG_LABELS).map((l) => <li key={l}>{l}</li>)}</ul>
      </Card>
      <Card icon={BookOpenCheck} title="The true facts">
        <ul className="side-list">
          <li>&ldquo;No investigative agency will ever contact you by phone or video call for enquiries&rdquo; (the Prime Minister, Mann Ki Baat, 27 Oct 2024).</li>
          <li>There is no such thing as a &ldquo;digital arrest&rdquo; or a &ldquo;safe account&rdquo;.</li>
          <li>Never share an OTP, PIN or CVV, and never install a screen-sharing app for a caller.</li>
          <li>Lost money? Call <a href="tel:1930">1930</a> at once, or report on <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">cybercrime.gov.in</a>.</li>
        </ul>
      </Card>
    </div>
  );
}
