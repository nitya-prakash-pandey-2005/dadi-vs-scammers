// Slim, honest banner on every page of the demo build.
import "./demo.css";
import { ArrowUpRight, Radio } from "lucide-react";
import { RECORDED_ON, REPO_URL } from "./index.js";

export default function DemoBanner() {
  return (
    <div className="demo-banner" role="note">
      <Radio size={15} className="flex-none demo-banner-icon" aria-hidden="true" />
      <span className="grow">
        <b>Interactive demo</b>
        <span className="long">: replays real calls recorded on Gnani's live servers on {RECORDED_ON} (synthetic scammer, fake IDs). Run it locally with your own keys for live calls.</span>
        <span className="short">: replays real calls recorded on Gnani, {RECORDED_ON}. Fake IDs.</span>
      </span>
      <a className="demo-banner-link" href={REPO_URL} target="_blank" rel="noreferrer">
        GitHub <ArrowUpRight size={14} aria-hidden="true" />
      </a>
    </div>
  );
}
