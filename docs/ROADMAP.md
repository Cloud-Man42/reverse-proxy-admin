# In a Cloud Gateway — Roadmap

## V1 — Core proxy management ✅

- [x] Proxy CRUD with safe nginx write/test/reload/rollback
- [x] Certificate management (Certbot)
- [x] Session auth (Argon2, CSRF, login rate limit, IP allowlist)
- [x] Audit logging
- [x] Log viewer

## V2 — Enterprise operations ✅

- [x] Backend pools and load balancing
- [x] Health monitoring and aggregates
- [x] SMTP notifications and alert recipients
- [x] System resource alerts
- [x] Scheduled status reports
- [x] Traffic analytics

## V3 — Platform extensions ✅

- [x] Per-proxy rate limiting
- [x] Proxy templates
- [x] Config version history and rollback
- [x] API tokens and `/api/v1` Bearer API
- [x] Multi-tenant organizations (backend)

## V4 — Security hardening ✅

- [x] **4.1** IP allow/block lists (global + per-proxy)
- [x] **4.2** Geo blocking (GeoIP2 include snippets)
- [x] **4.3** Threat feeds (HTTP sync + scheduler)
- [x] **4.4** WAF integration (ModSecurity per-proxy settings)
- [x] **4.5** Security events dashboard
- [x] **4.6** Audit export (CSV/JSON) and Security events export

## V5 — Observability platform ✅

- [x] Minute/hour traffic aggregates with status-code JSON
- [x] Request event sampling (live & failed request views)
- [x] NGINX stub_status connection metrics
- [x] Backend metric history
- [x] `/api/metrics/*`, live/failed requests, metric alert CRUD
- [x] Retention cleanup job and metrics settings UI
- [x] Enhanced JSON access logging (`proxy_json`) per proxy
- [x] Analytics & observability UI pages

## Future (post-V5)

- [x] **Application Catalog** — YAML templates, groups, search/filters, wizard, preview/create-proxy API
- [ ] Nginx log ingestion for live rate-limit/geo/WAF block events
- [ ] Automated ModSecurity CRS profile tuning
- [ ] GeoIP database auto-update cron
- [ ] Security event retention policies
- [ ] Frontend org/tenant switcher
