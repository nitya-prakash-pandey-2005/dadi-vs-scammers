// A download link to the API. In the demo build it points to the static snapshot, or shows the button disabled
// with a tooltip when the snapshot has no copy of that file.
import { NOT_IN_DEMO, apiHref } from "../demo";

export default function ApiLink({ href, className = "btn", children, ...rest }) {
  const url = apiHref(href);
  if (url) return <a className={className} href={url} {...rest}>{children}</a>;
  return (
    <span className="api-link-off" title={NOT_IN_DEMO}>
      <button type="button" className={className} disabled aria-label={`${typeof children === "string" ? children : "Download"} (not in this demo)`}>{children}</button>
    </span>
  );
}
