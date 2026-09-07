# Startup India Scraper for Zyte Scrapy Cloud

A Scrapy project designed to collect publicly accessible startup-directory information from the official Startup India portal.

## What it extracts

When the portal exposes the data publicly, the spider attempts to collect:

- Startup name
- Startup/profile URL
- Description
- Website
- Email and phone, when publicly displayed
- City and state
- Industry, sector and stage
- DPIIT recognition information
- Recognition number
- Incorporation date
- Founders/promoters
- Social links
- Crawl status and timestamp

## Important current-site limitation

The Startup India directory currently shows a **login/register wall** before startup records on its search page. The spider does not bypass login, CAPTCHA, authentication, or other access controls.

If the portal provides records publicly to your account/session in the future, the spider is ready to parse them. For JS-heavy/public pages, you can also run with Zyte API browser rendering.

## Deploy directly from GitHub

1. Create a new GitHub repository.
2. Upload the **contents of this ZIP** to the repository root.
3. Make sure `scrapy.cfg` is directly in the repository root.
4. In Zyte Scrapy Cloud, open **Code & Deploys → GitHub → Connect to GitHub**.
5. Select this repository and deploy the branch.

Zyte's GitHub deployment requires the Scrapy project, including `scrapy.cfg`, to be at the repository root.

## Run the spider

Spider name:

    startup_india

Default run:

    scrapy crawl startup_india

Useful examples:

    scrapy crawl startup_india -a max_pages=20

    scrapy crawl startup_india -a state=Karnataka -a city=Bengaluru

    scrapy crawl startup_india -a industry=AI -a max_pages=50

    scrapy crawl startup_india -a use_zyte=true -a max_pages=20

The last command requests Zyte API browser-rendered HTML. It requires a valid Zyte API key/subscription. In Scrapy Cloud, Zyte API availability depends on your account/subscription.

## Output

The project configures Scrapy Cloud/local Scrapy to write:

- `/scrapy/startups.jsonl`
- `/scrapy/startups.csv`

You can also use Scrapy Cloud's **Items → Export** functionality.

## Scheduling

After deployment, use the Scrapy Cloud dashboard's scheduling/periodic jobs feature to run the spider automatically (for example, daily).

The code itself does not create an external schedule or send data anywhere.

## Filters

The spider accepts:

- `max_pages` — maximum number of directory pages
- `page` — starting page number
- `industry`
- `sector`
- `state`
- `city`
- `stage`
- `use_zyte=true|false`

## Compliance

Use the scraper only for information that is publicly accessible and permitted by the target site's terms, robots directives, and applicable law. Do not use it to bypass authentication, CAPTCHA, rate limits, or other access controls.
