# ⚙️ GitHub Actions Automation — Setup Reference

The automated research workflow already lives on `ITCardo/cardo-intel` (`.github/workflows/daily-refresh.yml`). This doc covers what it needs to run, how to verify it's working, and how to change it.

## What's Here

✅ **GitHub Actions Workflow** — `.github/workflows/daily-refresh.yml`
- Runs weekly, Mondays at 14:00 UTC (configurable), plus a manual "Run workflow" button
- Four jobs in sequence: `determine-brands` → `research-agents` (parallel, one per brand) → `social-listeners` → `publish`

✅ **Python Scripts** — `scripts/` directory
- `research_agent.py` — per-brand research, using Claude with its own web search tool (no external scraping service)
- `social_media_listener.py` — Reddit customer feedback, also via Claude's web search
- `apify_social_listener.py` — real Facebook Group and Instagram posts via Apify, classified by Claude
- `product_expert.py` — synthesizes `product_insights.json` from all research

✅ **Config** — `research/brands.json`
- Add a new competitor by adding one entry here; no code or workflow change needed

---

## Step 1: Add Repository Secrets

Go to `https://github.com/ITCardo/cardo-intel/settings/secrets/actions` → **New repository secret** for each of:

| Secret | Required? | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Required** — nothing runs without it | https://console.anthropic.com → Settings → API Keys |
| `KEEPA_API_KEY` | Optional — Amazon pricing/rank panel stays empty if unset, everything else still works | https://keepa.com → account settings → API |
| `APIFY_API_TOKEN` | Required as the code is currently written — `apify_social_listener.py` exits with an error if this is missing, which blocks the `publish` job too (see Troubleshooting) | https://console.apify.com → Settings → Integrations |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Required once the site is gated behind login (see Step 2) — until this exists, the `publish` job's Azure deploy step just skips itself harmlessly | Azure Portal → your Static Web App resource → Overview → "Manage deployment token" |

There is no Firecrawl key — Firecrawl was replaced by Claude's own server-side web search tool, called directly from the research scripts.

---

## Step 2: Move hosting to Azure Static Web Apps, gated behind Entra ID login

**Status: done.** The dashboard is live at `https://cardo-intel.cardosystems.com/`, hosted on Azure Static Web Apps (resource `cardo-intel-login`, Standard plan — the Free plan can't restrict login to one tenant), behind Entra ID sign-in restricted to assigned Cardo Systems accounts. What it took, for reference and for anyone repeating this elsewhere:

1. **Create the Static Web App** — Azure Portal → Create a resource → Static Web App → Standard plan. For "Deployment details" choose **Other** (not GitHub) — this avoids Azure auto-generating its own competing workflow file; this repo's own `.github/workflows/daily-refresh.yml` already has the deploy step it needs.
2. **Get the deployment token** — resource → Overview → "Manage deployment token" → add it as the `AZURE_STATIC_WEB_APPS_API_TOKEN` secret (Step 1 above).
3. **Register an Entra app** for this login (app registration: "Cardo Intel Dashboard") — Entra admin center → App registrations → New registration. Redirect URI (Web): `https://<your-swa-hostname>.azurestaticapps.net/.auth/login/aad/callback` (shown on the Static Web App's Overview page). Note the Application (client) ID and Directory (tenant) ID, then add a client secret under Certificates & secrets, and grant Microsoft Graph delegated permissions: `email`, `openid`, `profile`, `User.Read` (with admin consent granted). **Also required, easy to miss:** on the same Authentication page, under "Implicit grant and hybrid flows," check **"ID tokens (used for implicit and hybrid flows)."** Without this, sign-in appears to work (you reach the Microsoft screen and pick an account) but silently loops back to the login page — `/.auth/me` stays `{"clientPrincipal": null}` — because Azure Static Web Apps' auth flow requests an `id_token` and Entra rejects it with `AADSTS700054: response_type 'id_token' is not enabled for the application`. That error only surfaces in the browser's Network tab (filter for `auth`, look at the `.auth/login/aad/callback` request), not on screen.
4. **Add those as Static Web App environment variables** (not GitHub secrets — this portal section used to be called "Application settings," now "Environment variables") — resource → Environment variables: `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET`. These names must match `staticwebapp.config.json` at the repo root, which also needs its tenant ID placeholder replaced with the real Directory (tenant) ID from step 3.
5. **Restrict access to actual Cardo employees, not just the tenant** — the tenant restriction in `staticwebapp.config.json` (`openIdIssuer` pinned to the Cardo tenant) is not sufficient on its own: Entra's email one-time-passcode guest sign-in can let an unrecognized email into the tenant as a B2B guest. Close this gap at the Enterprise Application level — Entra admin center → Enterprise applications → **Cardo Intel Dashboard** (auto-created alongside the app registration) → Properties → set **"Assignment required?"** to **Yes** → Save, then under Users and groups, assign only actual Cardo employees. Anyone not explicitly assigned is blocked with `AADSTS50105` right after sign-in, regardless of whether Microsoft let them through the sign-in screen itself.
6. **(Optional) Entra Company Branding** — Entra admin center → Company branding, if not already set up org-wide (Cardo's tenant already has this configured). This puts the Cardo logo/colors on the actual Microsoft sign-in screen itself (affects every Microsoft login at Cardo, not just this dashboard). Separately, `login.html` at the repo root is a Cardo-branded landing page shown *before* that Microsoft screen, with a "Sign in with Microsoft" button.
7. **Add a custom domain on the Azure resource** — Static Web App resource → Custom domains → Add → enter the domain (e.g. `cardo-intel.cardosystems.com`) → choose CNAME validation. Azure gives you a CNAME target (the `<swa-hostname>.azurestaticapps.net` hostname) to create in DNS *first* — Azure's validation checks for that record and will fail with "CNAME Record is invalid" if it doesn't exist yet or hasn't propagated.
8. **Point the domain at Azure in Cloudflare DNS** — edit the existing `cardo-intel` CNAME record, changing its target from `itcardo.github.io` to the Static Web App's `<swa-hostname>.azurestaticapps.net` hostname. Set it to **DNS only** (grey cloud, not proxied) — Cloudflare's proxy can interfere with Azure's domain validation and its free managed certificate issuance. Once Azure shows the custom domain validated and the certificate issued, add a **second** redirect URI on the Entra app registration for the custom domain (`https://cardo-intel.cardosystems.com/.auth/login/aad/callback`) alongside the original `azurestaticapps.net` one — sign-ins through the custom domain fail with `AADSTS50011` (redirect URI mismatch) until both are registered.
9. **Disable the old public path** — repo → Settings → Pages → set Source to "None," and delete the repo's `CNAME` file. **Done.** GitHub Pages is disabled and the `CNAME` file is gone, so the old `itcardo.github.io/cardo-intel` URL no longer serves anything and no longer redirects to `https://cardo-intel.cardosystems.com/` — anyone with an old bookmark needs the new URL. The Azure Static Web App is now the only place the dashboard is hosted.

---

## Step 3: Verify It Works

1. Go to `https://github.com/ITCardo/cardo-intel/actions` → "Weekly Competitive Research Refresh" → **Run workflow**.
2. Watch the jobs run: `determine-brands` → `research-agents` (one per brand, parallel) → `social-listeners` → `publish`. Each shows live status; click into any job for its log.
3. In `publish`, confirm "Deploy to Azure Static Web Apps" actually ran (not the "skipping" no-op step) — that only happens once `AZURE_STATIC_WEB_APPS_API_TOKEN` is set.
4. Open `https://cardo-intel.cardosystems.com/` in a private/incognito window: you should land on the Cardo-branded `login.html` first, then a Microsoft sign-in screen after clicking through, and only then the actual dashboard — confirm the "last updated" date matches today. A green run can still mean thin results if a step found nothing new, so check the actual content, not just the checkmark. **(Confirmed working.)**
5. Try signing in with a non-Cardo account — a completely unrecognized email is rejected outright by Entra ("We couldn't find an account with that username"); an email tied to some existing Microsoft account may be offered a one-time-passcode guest sign-in, which is exactly why step 2.5 (Enterprise Application assignment) matters — without it, that guest sign-in could actually succeed. **(Confirmed: unrecognized accounts rejected; assignment restriction in place.)**

---

## Customization

### Change the schedule

Edit `.github/workflows/daily-refresh.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * 1'   # Mondays 14:00 UTC — change day/time here
```

Push the change and it takes effect on the next scheduled run.

### Add a competitor

Add an entry to `research/brands.json` (slug, name, website, social handles, Facebook groups, Reddit search terms) and create an empty `research/<slug>.json`. Nothing else needs to change — `build.py`, all four scripts, and the workflow's brand matrix all read from that one file.

---

## Cost

- **Anthropic API**: the main cost driver — depends on which model the scripts use (`claude-opus-4-8` vs a cheaper Sonnet model) and how much web search runs each week. Realistically low single-digit dollars per week at this pipeline's volume (weekly cadence, capped output per call).
- **Keepa**: token-based subscription, only if enabled.
- **Apify**: usage-based, only if enabled.
- **GitHub Actions**: free (public repo).
- **Azure Static Web Apps**: Standard plan, ~$9/month flat — required specifically for tenant-restricted ("Custom authentication") login; the Free plan can only use the default multi-tenant sign-in, which would let any Microsoft account in.

---

## Troubleshooting

### Workflow doesn't show in the Actions tab
The workflow file is already on `main` — check you're looking at `ITCardo/cardo-intel`, not the original personal-account repo it was migrated from.

### "API key not found" / authentication error in logs
Add the missing secret (Step 1). Note `ANTHROPIC_API_KEY` is required for every job; `KEEPA_API_KEY` is genuinely optional; `APIFY_API_TOKEN` is *not* optional as the code stands today — `apify_social_listener.py` deliberately exits with an error if it's missing, which fails the `social-listeners` job and, because `publish` depends on it, blocks the whole site update that week even if research and Keepa worked fine.

### Workflow fails with a JSON parse error
Check the failing job's log — usually a Claude response got cut off or malformed. Re-run manually; these are rarely persistent.

### Dashboard not updating after a successful run
Hard-refresh your browser (Cmd+Shift+R) and wait 30–60 seconds for the Azure deploy to finish. Also confirm the `publish` job's "Deploy to Azure Static Web Apps" step actually ran (not the "skip" no-op, which happens if `AZURE_STATIC_WEB_APPS_API_TOKEN` is unset).

### `AADSTS50011: redirect URI ... does not match`
The redirect URI used at sign-in doesn't have a matching entry on the Entra app registration. Most often this means you're signing in through a hostname (e.g. a newly added custom domain) that hasn't had its own `.auth/login/aad/callback` redirect URI added yet — see Step 2.8. Add it under App registrations → your app → Authentication → Add URI, keeping the existing one(s) too.

### No automatic (scheduled) runs happening
GitHub disables scheduled workflows on repos with no commits in 60 days — as long as the repo stays active, this isn't a concern, but it's the first thing to check if the weekly run silently stops firing.

### Sign-in loops back to the login page, `/.auth/me` always shows `clientPrincipal: null`
See the "easy to miss" note in Step 2.3 above — almost always the app registration's "ID tokens (used for implicit and hybrid flows)" checkbox is unchecked. Confirm via the browser's Network tab on the `.auth/login/aad/callback` request; an `AADSTS700054` error confirms it.

---

## Documentation

- [docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md) — workflow reference
- [README.md](README.md) — system overview
- [docs/AGENTS.md](docs/AGENTS.md) — agent/script descriptions
- [.github/workflows/daily-refresh.yml](.github/workflows/daily-refresh.yml) — the workflow itself
