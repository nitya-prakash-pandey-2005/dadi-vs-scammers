// "#/" is the product landing page; everything under "#/app" is the app (with its shell and the demo banner).
import { useRoute } from "./lib/router";
import Landing from "./landing/Landing";
import App from "./App";

export default function Root() {
  const { path } = useRoute();
  return path === "/" || path === "" ? <Landing /> : <App />;
}
