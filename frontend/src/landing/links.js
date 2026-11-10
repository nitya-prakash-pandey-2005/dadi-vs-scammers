// Every outbound link on the landing page lives here, so the lead can swap in the real video / product URLs in one place.
const GH = "https://github.com/nitya-prakash-pandey-2005";
export const REPO_URL = `${GH}/dadi-vs-scammers`;
// the 3-minute video: until the final link is known, point at the README (it carries the video link)
export const VIDEO_URL = `${REPO_URL}#readme`;

// live demos (Vercel) and their GitHub repos
export const DADI_URL = "https://dadi-vs-scammers.vercel.app/";
export const PUKAAR_URL = "https://pukaar-snowy.vercel.app/";
export const PUKAAR_REPO = `${GH}/pukaar`;
export const AWAAZ_URL = "https://apni-awaaz-kappa.vercel.app/";
export const AWAAZ_REPO = `${GH}/apni-awaaz`;
export const APP_HREF = "#/app?play=1"; // demo build: the recorded call starts on arrival (pages/CallRoom.jsx)
