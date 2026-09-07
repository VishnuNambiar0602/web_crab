import os

BOT_NAME = "startup_india_scraper"
SPIDER_MODULES = ["startup_india_scraper.spiders"]
NEWSPIDER_MODULE = "startup_india_scraper.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.25
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 8.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
RETRY_TIMES = 3
COOKIES_ENABLED = False

ITEM_PIPELINES = {}

FEEDS = {
    "startups.csv": {
        "format": "csv",
        "overwrite": True,
        "encoding": "utf8",
        "fields": [
            "startup_name", "company_slug", "profile_url", "source",
            "source_snapshot", "district", "state", "primary_industry",
            "sectors", "description", "website", "dpiit_recognised",
            "cin", "funding_signal", "founders", "public_emails",
            "public_phones", "linkedin", "instagram", "facebook",
            "twitter", "source_page", "crawl_status",
        ],
    },
    "startups.jsonl": {"format": "jsonlines", "overwrite": True},
}

# Zyte API transparent/browser rendering. A Zyte API key should be configured
# in Scrapy Cloud project settings or the environment, never committed here.
ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")
if ZYTE_API_KEY:
    ZYTE_API_TRANSPARENT_MODE = True
    DOWNLOADER_MIDDLEWARES = {
        "scrapy_zyte_api.ScrapyZyteAPIDownloaderMiddleware": 1000,
    }
    REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
