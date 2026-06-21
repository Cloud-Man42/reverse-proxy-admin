# Proxy Setup Manual — In a Cloud Gateway

This guide explains how to create and manage reverse proxy applications in the Admin UI, and **why** each step works the way it does. It matches the behaviour of the current codebase (nginx site files, Let's Encrypt integration, traffic flow tests, and safe reload workflow).

> **Note:** All company names, hostnames, IP addresses, and account names in this manual are **fictional examples** (RFC 5737 documentation addresses and `example.com` domains). Replace them with your own environment.

### Fictional reference environment (Acme Labs)

| Role | Example value |
|------|----------------|
| Public WAN IP | `203.0.113.10` |
| Reverse proxy (LAN) | `10.0.0.5` |
| Web app backend | `10.0.0.40:3000` |
| API backend | `10.0.0.41:8080` |
| Backend on another VLAN | `10.0.1.15:4000` |
| Public domains | `portal.example.com`, `calendar.example.com` |
| Proxy app slugs | `portal-app`, `calendar-app` |
| Admin UI URL | `https://10.0.0.5:8443` |

---

## Table of contents

1. [What you are configuring](#1-what-you-are-configuring)
2. [Prerequisites](#2-prerequisites)
3. [How traffic flows (and why it matters)](#3-how-traffic-flows-and-why-it-matters)
4. [Access the Admin UI](#4-access-the-admin-ui)
5. [Step-by-step: create your first proxy](#5-step-by-step-create-your-first-proxy)
6. [Form fields reference](#6-form-fields-reference)
7. [HTTPS and certificates](#7-https-and-certificates)
8. [Traffic flow test](#8-traffic-flow-test)
9. [Traffic debug (after save)](#9-traffic-debug-after-save)
10. [Managing existing proxies](#10-managing-existing-proxies)
11. [Multi-route applications](#11-multi-route-applications)
12. [What happens when you click Save](#12-what-happens-when-you-click-save)
13. [Worked examples](#13-worked-examples)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. What you are configuring

Each **proxy app** in the Admin UI represents **one nginx virtual host** (one file in `/etc/nginx/sites-available/<name>.conf`) that:

- Listens on **port 80** (and **443** when HTTPS is enabled) for one or more **domain names**
- Terminates TLS when **Force HTTPS** is on and a Let's Encrypt certificate exists
- Forwards requests to one or more **upstream backends** (IP + port + protocol)
- Writes a dedicated **access log** at `/var/log/nginx/proxy-<name>.log` for traffic debugging

The Admin UI does **not** replace your firewall or DNS. It generates nginx configuration, validates it, reloads nginx safely, and helps you verify connectivity **from the reverse proxy server itself**.

---

## 2. Prerequisites

Before creating a proxy that must be reachable from the internet:

| Requirement | Why |
|-------------|-----|
| **DNS** — public A/AAAA record points to your WAN IP | Browsers and Let's Encrypt reach you via the domain name, not the internal LAN IP of the proxy |
| **Router/NAT** — TCP **80** and **443** forwarded to the proxy host | HTTP challenges and HTTPS traffic must reach nginx on the proxy machine |
| **Upstream reachable from the proxy** | The flow test opens a TCP connection **from the proxy server** to `target_host:target_port`. If the backend is on another VLAN/subnet without routing, the test fails even if your laptop can reach the backend |
| **Admin UI access** — typically `https://<proxy-lan-ip>:8443` | The UI is intended for internal/VPN use only |
| **Permissions** — your user needs **Create** / **Edit** / **Read** as appropriate | Non-admin users may be read-only |

Optional but recommended:

- Set `CERTBOT_EMAIL` in `/etc/nginx-admin/env` (or `.env` in Docker) before issuing certificates
- Set `SERVER_PUBLIC_IP` in the environment so the network map and traffic path summary show your public IP

---

## 3. How traffic flows (and why it matters)

For a typical public web app with Force HTTPS enabled:

```text
Internet client
    → DNS resolves portal.example.com to 203.0.113.10 (public IP)
    → Edge firewall / NAT (port 443 forwarded)
    → Nginx on reverse proxy host (10.0.0.5)
        → TLS terminated using /etc/letsencrypt/live/portal.example.com/
        → proxy_pass to https://10.0.0.40:3000
    → Backend application
```

**Why the upstream IP must be reachable from the proxy**

Nginx runs on the **reverse proxy host**. When it forwards a request, it opens a **new connection** from that machine to `target_host:target_port`. The Admin UI's **upstream connectivity** check uses the same logic: a TCP connect from the server running the admin API (co-located with nginx in production).

**Why Force HTTPS requires a certificate first**

With **Redirect HTTP to HTTPS** enabled, nginx generates:

1. A port **80** server block that returns `301` to `https://$host$request_uri`
2. A port **443** server block with `ssl_certificate` pointing at Let's Encrypt files

If no certificate exists, nginx would serve HTTPS with missing/invalid cert paths. The application **blocks saving** Force HTTPS until a cert is present for the primary domain (first domain in the list).

**Why port 80 must be open for new certificates**

Let's Encrypt HTTP-01 validation (via the certbot nginx plugin) must reach your server on **port 80**. After issuance, automatic renewal runs twice daily via `certbot-renew.timer` (native install) or cron (Docker).

---

## 4. Access the Admin UI

1. Open **`https://10.0.0.5:8443`** (or your proxy host) from an allowed network (see `ALLOWED_IPS` in env).
2. Log in with the administrator account configured during installation. Change the default password under **Users** before production use.
3. Use the sidebar:
   - **Dashboard** — overview and network map
   - **Proxies** — list, create, edit apps
   - **Certificates** — issue/renew Let's Encrypt certs
   - **Logs** — nginx error/access logs

User roles:

| Permission | Can do |
|------------|--------|
| Read | View proxies, run flow tests, traffic debug, config test |
| Create | Create new proxy apps |
| Edit | Update, enable/disable, delete proxies |

---

## 5. Step-by-step: create your first proxy

### Step 1 — Plan the app

Decide:

- **App name** — internal slug (e.g. `portal-app`). Becomes the config filename: `portal-app.conf`
- **Domain(s)** — what users type in the browser (e.g. `portal.example.com`)
- **Backend** — IP, port, and protocol nginx should use **from the proxy server** (e.g. `10.0.0.40`, `3000`, `https`)

### Step 2 — Issue a certificate (if using HTTPS)

Skip only if you serve plain HTTP on port 80 with Force HTTPS **off**.

1. Go to **Certificates**.
2. Enter the **exact domain** (e.g. `portal.example.com`).
3. Enter a valid contact email (e.g. `ops@acme-labs.net`) or rely on `CERTBOT_EMAIL` in env.
4. Click **Issue**.
5. Wait for success. Certbot modifies nginx and stores files under `/etc/letsencrypt/live/<domain>/`.

**Why before the proxy:** Saving with Force HTTPS checks that `fullchain.pem` exists for the primary domain.

### Step 3 — Create the proxy

1. Go to **Proxies** → **Create app**.
2. Fill in the form (see [Form fields reference](#6-form-fields-reference)).
3. Click **Test traffic flow** (recommended before save).
4. Fix any failed checks.
5. Click **Save**.

### Step 4 — Verify

1. From an external network (mobile off Wi‑Fi), open `https://portal.example.com/`.
2. On the proxy edit page, open **Traffic debug** and confirm your client IP appears in `/var/log/nginx/proxy-portal-app.log`.

---

## 6. Form fields reference

### App name

- **Format:** lowercase letters, numbers, hyphens only (`a-z`, `0-9`, `-`)
- **Used for:** config file name, htpasswd file name, per-app access log name
- **Cannot be changed casually:** renaming creates a new config file and removes the old one (with backup + rollback on failure)

### Domains (comma separated)

- **Example:** `portal.example.com` or `app.example.com, www.example.com`
- **First domain** is the **primary** domain: used for SSL certificate path when Force HTTPS is on
- **Validation:** real domain syntax; wildcard `*.example.com` supported
- **Why comma separated:** nginx `server_name` accepts multiple hostnames in one app

### Upstream routes

Each route maps a **path prefix** on the public domain to a **backend**.

| Field | Meaning | Why |
|-------|---------|-----|
| **Path prefix** | URL path on the public domain, e.g. `/` or `/api` | Becomes nginx `location` block |
| **Protocol** | `http` or `https` to backend | Sets `proxy_pass` scheme; use `https` if the backend speaks TLS |
| **Target host** | IPv4/IPv6 address | Hostname is **not** accepted — avoids DNS ambiguity on the proxy server |
| **Target port** | 1–65535 | Backend listen port |
| **WebSocket** | Enable upgrade headers | Required for WS apps (Socket.IO, etc.); adds `Upgrade` and `Connection` headers |

**Path matching rules:**

- `/` catches the whole site (location `/` with `proxy_pass` to upstream root)
- `/api` matches `/api/...` (prefix location)
- Each path prefix must be **unique** within one app
- Longer paths are sorted first in generated config so specific routes win over `/`

### Max body size

- Optional nginx `client_max_body_size` (e.g. `50m`)
- **Why:** default nginx limit is 1 MB — uploads fail without raising this

### Redirect HTTP to HTTPS (Force HTTPS)

- Adds port 80 redirect + port 443 SSL server block
- **Requires** existing Let's Encrypt cert for primary domain
- Uses standard Let's Encrypt nginx SSL snippets (`options-ssl-nginx.conf`, `ssl-dhparams.pem`)

### Enabled

- **On:** symlink in `sites-enabled` — nginx loads the site
- **Off:** config file remains but site is disabled (no symlink) — useful for maintenance without deleting

### Basic auth

- Adds nginx `auth_basic` using `/etc/nginx/.htpasswd/<app-name>.htpasswd`
- A username and password must be supplied **on save** when enabling basic auth (e.g. user `staging-viewer` — use your own values)
- **Why:** extra layer before traffic hits the backend (not a substitute for app login)

---

## 7. HTTPS and certificates

### Issuing (Admin UI → Certificates)

Certbot runs with the nginx plugin:

```text
certbot --nginx -d portal.example.com --non-interactive --agree-tos -m ops@acme-labs.net
```

It inserts temporary validation locations, obtains the cert, and updates nginx.

### Saving a proxy with Force HTTPS

The backend verifies:

```text
/etc/letsencrypt/live/<primary-domain>/fullchain.pem exists
```

If missing, save is rejected with a clear error.

### Automatic renewal

On native install, `certbot-renew.timer` runs `deploy/certbot-renew.sh` twice daily. After renewal, a deploy hook runs `nginx -s reload` / `systemctl reload nginx`.

You can also manually renew from **Certificates** or run:

```bash
sudo bash /opt/reverse-proxy-admin/deploy/certbot-renew.sh
```

---

## 8. Traffic flow test

Click **Test traffic flow** on the create/edit form **before** saving. It runs five checks:

| Check | What it does | Why |
|-------|--------------|-----|
| **Input validation** | Confirms domains/routes parsed | Ensures the draft payload is structurally valid |
| **Nginx syntax** | Renders config to a temp tree and runs `nginx -t` | Catches broken nginx before touching production config |
| **Upstream connectivity** | TCP connect from **proxy server** to each `target_host:target_port` | Proves nginx *can* reach backends — most common failure is wrong subnet or firewall |
| **SSL readiness** | If Force HTTPS: cert exists for primary domain | Prevents enabling HTTPS without cert files |
| **Traffic path** | Summary: Internet → Firewall → Nginx → domain → routes | Informational; marked failed if any critical check above failed |

**Important:** Passing the flow test does **not** guarantee DNS or router forwarding are correct — only that nginx config and upstream TCP from the proxy are OK. External access still requires DNS + NAT.

---

## 9. Traffic debug (after save)

Available on the **edit** page only.

Reads the tail of `/var/log/nginx/proxy-<app-name>.log` in a pipe-delimited format:

```text
client_ip|time|host|request|status|bytes|x-forwarded-for|user-agent
```

**Why it exists:** confirms real requests hit **this** nginx vhost (vs. router, wrong host, or DNS pointing elsewhere).

If you test from the internet and see **no lines**, traffic is not reaching nginx — check DNS and port forwarding first.

---

## 10. Managing existing proxies

From **Proxies** list:

| Action | Effect |
|--------|--------|
| **Edit** | Change domains, routes, HTTPS, auth, etc. |
| **Enable / Disable** | Toggle symlink in `sites-enabled` without deleting config |
| **Test** | Runs global `nginx -t` on the whole server |
| **Delete** | Removes config, disables site, reloads nginx (with backup + rollback on failure) |

Dashboard **Network map** shows Internet → Firewall → Nginx → your apps → upstreams. Click an app node to edit it.

---

## 11. Multi-route applications

One domain can split traffic by path:

| Path prefix | Backend | Use case |
|-------------|---------|----------|
| `/` | `http://10.0.0.40:3000` | Main web UI |
| `/api` | `http://10.0.0.41:8080` | API server |

**Why one app instead of two:** same `server_name`, shared TLS cert, single access log and admin entry.

**Ordering:** longer prefixes (e.g. `/api`) are generated before `/` so nginx matches the most specific location first.

---

## 12. What happens when you click Save

This safe workflow is why misconfiguration rarely takes nginx down:

1. **Validate** input (domains, IPs, unique paths, Force HTTPS + cert)
2. **Backup** existing config if updating
3. **Write** `/etc/nginx/sites-available/<name>.conf` (and htpasswd if needed)
4. **Enable symlink** if `Enabled` is checked
5. **Run `nginx -t`** — if it fails, **restore backup** and abort
6. **Reload nginx** — if reload fails, error returned to UI
7. **Audit log** records who changed what

Renaming an app is a special case: new file created, old file removed, with full rollback if any step fails.

---

## 13. Worked examples

### Example A — Public HTTPS web app (Acme Labs portal)

**Goal:** `https://portal.example.com` → application on `10.0.0.40:3000`

1. DNS: `portal.example.com` → `203.0.113.10` (public IP)  
2. Router: forward 80/443 → `10.0.0.5` (proxy)  
3. **Certificates:** issue for `portal.example.com`  
4. **Create proxy:**
   - Name: `portal-app`
   - Domains: `portal.example.com`
   - Route: `/` → `https` → `10.0.0.40` → `3000`
   - Force HTTPS: **on**
   - Enabled: **on**
5. Test traffic flow → Save  
6. Verify externally + traffic debug log

**Why HTTPS to backend:** Some frameworks serve TLS locally; nginx connects to the backend over HTTPS and presents the public Let's Encrypt cert to browsers.

### Example B — HTTP internal tool (no public TLS)

**Goal:** `http://tools.internal.example` on LAN only

1. Create proxy with Force HTTPS **off**
2. Route `/` → `http` → `10.0.0.50` → `8080`
3. No certificate required
4. Ensure internal DNS or hosts file resolves on LAN only

### Example C — Backend on another subnet

**Problem:** Backend at `10.0.1.15:4000` (VLAN 30), proxy at `10.0.0.5` (VLAN 20) — flow test fails.

**Fix options:**

- Add router/firewall routing between VLAN 20 and VLAN 30, **or**
- Give the backend an address on `10.0.0.x`, **or**
- Move backend to same subnet as proxy

The Admin UI cannot fix network routing; it only reports that the proxy cannot open TCP to the upstream.

---

## 14. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| **upstream_connectivity failed** | Proxy cannot TCP-connect to backend | Ping/`nc -zv` from proxy host; fix routing or upstream IP |
| **ssl_readiness failed** | Force HTTPS on without cert | Issue cert on **Certificates** page first |
| **Cannot save Force HTTPS** | Same as above | Issue cert, then save |
| **Flow test passes, browser cannot connect** | DNS or NAT | Check public DNS, router port forward to proxy LAN IP |
| **No traffic debug lines from internet** | Traffic never hits nginx | Same as above; also check router not answering port 80 itself |
| **502 Bad Gateway** | Backend down or wrong protocol/port | Verify backend listens; try `curl` from proxy with same scheme |
| **Certbot issue fails** | Port 80 not reachable from internet | Fix NAT; ensure nothing else owns port 80 on WAN |
| **Save failed: nginx -t** | Invalid generated config | Rare — check error detail; report if bug |
| **Basic auth save failed** | Username/password empty | Both required when basic auth enabled |

### Useful server commands

```bash
# Flow diagnostics for an existing app
sudo bash /opt/reverse-proxy-admin/deploy/diagnose-flow.sh portal-app portal.example.com

# Test upstream from proxy
nc -zv 10.0.0.40 3000

# Watch app access log
sudo tail -f /var/log/nginx/proxy-portal-app.log

# Global nginx test
sudo nginx -t
```

---

## Quick checklist

Before going live with a new public HTTPS app:

- [ ] DNS A record → public IP (e.g. `203.0.113.10`)  
- [ ] Router forwards **80** and **443** → reverse proxy host (e.g. `10.0.0.5`)  
- [ ] Certificate issued for primary domain  
- [ ] Upstream IP reachable **from proxy server** (flow test green)  
- [ ] Force HTTPS enabled after cert exists  
- [ ] External browser test succeeds  
- [ ] Traffic debug shows client requests  

---

*This manual describes In a Cloud Gateway. Replace all fictional example values with your own infrastructure before use.*
