# India Startup Lead Generator — Zyte / Scrapy

This is a Scrapy project designed for Zyte Scrapy Cloud. It does **not** attempt to bypass the Startup India login wall.

## Why this version is different

The current Startup India public search page displays a login/registration wall before startup records are available. Instead of trying to defeat that restriction, this project uses **Indian Startup Map** as a public discovery source. Indian Startup Map states that it reproduces Startup India/state-portal startup data and currently exposes a large public A-to-Z company index.

Important: Indian Startup Map is an independent publication, not the Government of India or Startup India. Treat its records as a third-party reproduction and verify important information independently.

## What it collects

### Fast directory mode (default)
- Startup/company name
- Public company profile URL
- District/city shown in the directory
- Primary industry
- Source page
- Source snapshot

### Enrichment mode
Set `ENRICH_COMPANY_PAGES=true` to visit each public company profile and attempt to collect:
- Description
- Website
- State
- Sectors as filed
- CIN, when displayed
- DPIIT recognition indicator, when displayed
- Public email addresses appearing on the page
- Public phone numbers appearing on the page
- Public social links appearing on the page

The enrichment mode does **not** log in, bypass CAPTCHAs, or access private data.

## Recommended first Zyte run

Use these environment/job settings:

```text
START_LETTER=A
START_PAGE=1
MAX_INDEX_PAGES=1
MAX_ITEMS=100
ENRICH_COMPANY_PAGES=false
```

This gives you a small test batch first.

## Then enrich a test batch

```text
START_LETTER=A
START_PAGE=1
MAX_INDEX_PAGES=1
MAX_ITEMS=25
ENRICH_COMPANY_PAGES=true
```

If the company profile pages are returning useful fields, increase `MAX_ITEMS` gradually.

## Crawling the whole public index

The source currently publishes 2,297 index pages covering 228,415 company records with a full page. A full crawl is therefore much larger than a normal test job. Do not start the complete crawl until you have validated a small batch and checked Zyte usage/costs.

You can split work by letter/page, for example:

```text
START_LETTER=A
START_PAGE=1
MAX_INDEX_PAGES=237
```

and then repeat for B, C, etc. The exact page counts can change as the source changes, so validate each batch.

## Local test

```bash
pip install -r requirements.txt
scrapy crawl india_startups -O startups.csv
```

For enrichment:

```bash
set ENRICH_COMPANY_PAGES=true
set MAX_ITEMS=25
scrapy crawl india_startups -O startups_enriched.csv
```

## Zyte deployment

The repository is structured with `scrapy.cfg` at the root and `scrapinghub.yml` for Scrapy Cloud. GitHub deployment is supported by Scrapy Cloud.

Do not commit Zyte API keys or Scrapy Cloud API keys. Configure credentials through Zyte/project settings.

## Output

The project writes:

- `startups.csv`
- `startups.jsonl`

## Data-quality notes

A startup registration is not proof that a company is currently operating. The source itself warns that some registered startups may be dormant. Use the records as leads/discovery data, and verify company status before outreach.
