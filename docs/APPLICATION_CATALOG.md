# Application Catalog

The Application Catalog is a YAML-backed library of 100+ self-hosted application templates. Each template ships recommended nginx proxy settings, optional optimized presets, and a guided 7-step wizard to create proxy hosts safely.

## Overview

- **Source of truth:** `backend/catalog/` (groups + per-group template YAML files)
- **Runtime loader:** `CatalogService` validates YAML at startup and indexes templates in memory
- **Legacy compatibility:** `GET /api/templates/legacy` returns the original array shape; slug aliases (e.g. `proxmox` → `proxmox-ve`) remain valid
- **Safe creation:** Wizard `create-proxy` endpoints call the same `ProxyService.create_proxy()` pipeline as manual proxy creation (backup → write → `nginx -t` → reload or rollback)

## Directory layout

```
backend/catalog/
  groups.yaml
  templates/
    infrastructure.yaml
    monitoring.yaml
    ...
```

Each YAML file contains a `templates:` list. Every entry validates against the `ApplicationTemplate` Pydantic model in `backend/app/schemas/catalog.py`.

## Template fields

| Field | Purpose |
|-------|---------|
| `slug` | Unique identifier used in URLs and API paths |
| `name`, `description`, `long_description` | Display metadata |
| `group`, `category` | Catalog grouping |
| `tags` | Search/filter tags |
| `availability_level` | `free`, `pro`, or `enterprise` (UI badge only — no payment gating) |
| `optimized` | Marks templates with richer nginx presets (timeouts, headers, HSTS) |
| `default_upstream_protocol`, `default_upstream_port` | Wizard defaults |
| `websocket_support`, `large_upload_support` | Feature flags |
| `recommended_*` | Suggested body size, timeouts, headers |
| `security_headers`, `security_notes` | Wizard step 5 guidance |
| `slug_aliases` | Legacy slug compatibility |
| `documentation_url`, `health_check_path` | Wizard review hints |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/templates/groups` | List catalog groups with counts |
| GET | `/api/templates` | Filtered/paginated catalog list |
| GET | `/api/templates/legacy` | Legacy array response for older clients |
| GET | `/api/templates/{slug}` | Full template detail |
| POST | `/api/templates/{slug}/preview` | Render nginx config preview |
| POST | `/api/templates/{slug}/create-proxy` | Create proxy via safe pipeline |

### List filters

Query parameters: `q`, `group`, `tag`, `availability_level`, `optimized`, `websocket`, `large_upload`, `https_upstream`, `page`, `page_size`.

## Frontend routes

| Route | Page |
|-------|------|
| `/templates` | Application catalog home (groups + search) |
| `/templates/groups/:groupSlug` | Templates in a group |
| `/templates/:slug` | Template detail |
| `/templates/:slug/wizard` | 7-step setup wizard |
| `/proxies/new?template={slug}` | Redirects to wizard step 3 (upstream) |

## Wizard steps

1. **Overview** — Confirm template
2. **Domain** — Public hostname
3. **Upstream** — Host, port, protocol
4. **Options** — WebSocket, HTTPS redirect, uploads, HSTS, headers
5. **Recommended** — Review suggested settings and security notes
6. **Preview** — `POST .../preview` nginx config
7. **Create** — `POST .../create-proxy` with nginx test result

## Adding a template

1. Choose the appropriate group file under `backend/catalog/templates/` (or add a new file).
2. Add a YAML entry under `templates:` matching the schema.
3. Run backend tests: `pytest backend/tests/test_catalog_schema.py backend/tests/test_catalog_service.py`
4. Restart the backend (catalog is loaded at startup).

Example:

```yaml
templates:
  - slug: my-app
    name: My App
    description: Short summary for catalog cards
    group: monitoring-observability
    category: Monitoring
    availability_level: free
    optimized: false
    default_upstream_protocol: http
    default_upstream_port: 8080
    websocket_support: false
    large_upload_support: false
    http_to_https_redirect_default: true
    tags: [self-hosted]
```

## Validation rules

- Slugs must pass `validate_slug`
- Header names/values are validated (unsafe injection patterns rejected)
- Timeout strings must match `^\d+[sm]?$` when set
- Duplicate slugs across YAML files fail schema tests

## Testing checklist

- [ ] `pytest backend/tests/test_catalog_*.py backend/tests/test_template_*.py`
- [ ] `npm run test -- TemplateWizardPage`
- [ ] Browse `/templates`, filter by optimized, open wizard, preview, create (staging)
- [ ] Legacy link `/proxies/new?template=proxmox` resolves alias and opens wizard
