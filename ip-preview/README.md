# IP crawler preview

Standalone preview of the IP watch. It is **not** connected to the main dashboard: it does not change
`build.py`, `dashboard_template.html`, `research/` or `daily-refresh.yml`, does not deploy to Azure and
does not commit results to `main`.

## Run it

1. Add two repository secrets (Settings > Secrets and variables > Actions): `EPO_OPS_KEY`, `EPO_OPS_SECRET`
   (the consumer key and secret from the EPO developer portal).
2. Paste the known Sena records into `ip-preview/known/sena.csv` (template inside).
3. Actions > **IP Crawler Preview** > Run workflow. Choose `demo` first to see the layout with invented records.
4. Open the finished run, download the artifact **ip-preview**, open `ip_preview.html`.

Local run: `python ip-preview/ip_crawler.py --demo` (no network) or set the two variables and run it without `--demo`.
Tests: `python -m pytest ip-preview/tests -q`.

## What it does

- **Pass 1** searches the EPO (OPS) by applicant name for every name in `config.json`, then compares each applicant
  string with the brand's names (ignores case, commas, full stops, spacing, Inc/Ltd/Limited; "Technology" = "Tech").
- **Pass 2** looks up every number on the known list directly.
- **Pass 3** adds the other members of each legal family, then reads legal events (lapse, withdrawal, refusal).
- Close names that need a person go to the **review list**. They are never counted as the brand's filings.
- NEW = number not on the known list (or not in the previous run). CHANGED = status moved forward (Pending > Granted > Expired).
- A brand with no known list and no previous run is stored quietly as the baseline: nothing is flagged NEW.
- Type (patent, design, utility model) comes from the kind code. Expired = a lapse/withdrawal/refusal event, or the
  term has passed (20 years patents, 10 years utility models, from the filing date). Term-based expiry is marked "est.".
- Every row links to Google Patents and Espacenet for manual cross-checking. Google Patents is not scraped
  (its search endpoint is closed to automated access).

## Names

Edit `config.json`. `names` are approved and are searched and matched. `suggested_variants` are searched but only ever
appear in the review list. `exclude` removes other companies with a similar name. The Chinese-character names of the
Shenzhen and Hong Kong companies are not in the file yet: add them to `names` once a colleague who reads Chinese confirms them.

## Limits and known gaps

- Written from the OPS 3.2 documentation and tested offline with a fake server. The first real run is the real test.
  The legal-events parser and the family lookup are the parts most likely to need a small fix.
- EPO fair use: free registered use is up to 4 GB a week, and automatic tools are asked to run 19:00-07:00 GMT or at weekends.
  The page shows a note when a run starts in the busy hours.
- OPS has the national offices only partly (legal status especially). Status marked "est." must be checked in the national register.
- Pinyin and translated Chinese names are the expected weak spot. Check the "Dropped" list in the diagnostics.
