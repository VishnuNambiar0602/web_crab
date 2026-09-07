import os

BOT_NAME = "startup_india_scraper"

SPIDER_MODULES = ["startup_india_scraper.spiders"]
NEWSPIDER_MODULE = "startup_india_scraper.spiders"

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]

DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FEEDS = {
    "/scrapy/startups.jsonl": {
        "format": "jsonlines",
        "encoding": "utf8",
        "overwrite": True,
    },
    "/scrapy/startups.csv": {
        "format": "csv",
        "encoding": "utf8",
        "overwrite": True,
    },
}

FEED_EXPORT_ENCODING = "utf-8"

# Optional Zyte API integration:
# Run with: scrapy crawl startup_india -a use_zyte=true
# In Scrapy Cloud, the Zyte API key is supplied automatically when available.
ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")
if ZYTE_API_KEY:
    REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
    DOWNLOADER_MIDDLEWARES = {
        "scrapy_zyte_api.ScrapyZyteAPIDownloaderMiddleware": 1000,
    }
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
