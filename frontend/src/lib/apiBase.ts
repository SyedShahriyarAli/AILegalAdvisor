/**
 * API URL helper for dev/prod.
 *
 * While running `vite dev`, requests intentionally stay **same-origin** (`/api/...`)
 * so Vite proxies to Flask. That avoids Chromium treating calls from `localhost:5173`
 * to `127.0.0.1:5000` as cross-origin (CORS / private-network quirks), which often shows up in DevTools as
 * "Provisional headers" with no clear POST body until the browser drops the request.
 *
 * Production builds use `VITE_API_BASE_URL` (must match where the SPA is served from).
 */
export function apiBase(): string {
  if (import.meta.env.DEV) {
    return '';
  }
  const raw = import.meta.env.VITE_API_BASE_URL;
  if (typeof raw !== 'string') {
    return '';
  }
  return raw.replace(/^\ufeff/, '').trim().replace(/\/$/, '');
}

export function apiUrl(path: string): string {
  const base = apiBase();
  const p = path.startsWith('/') ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

/** Turn backend-relative paths (e.g. `/api/pdf?...`) into absolute URLs when `VITE_API_BASE_URL` is set. */
export function resolveApiHref(href: string | undefined | null): string | undefined {
  if (href == null || href === '') return undefined;
  const h = href.trim();
  if (h.startsWith('http://') || h.startsWith('https://')) return h;
  return apiUrl(h.startsWith('/') ? h.slice(1) : h);
}
