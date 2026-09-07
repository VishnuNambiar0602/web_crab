import os
import re
from urllib.parse import urljoin

import scrapy
from scrapy.exceptions import CloseSpider

from startup_india_scraper.items import StartupItem


BASE = "https://indianstartupmap.com"
LETTERS = ["0-9"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def clean(value):
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value


class IndiaStartupsSpider(scrapy.Spider):
    name = "india_startups"
    allowed_domains = ["indianstartupmap.com"]

    # Public source: Indian Startup Map, an independent site that states its
    # startup register is reproduced from Startup India/state portals.
    source_name = "Indian Startup Map"
    source_snapshot = "2026-08"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.letter = os.getenv("START_LETTER", "A").upper()
        self.start_page = int(os.getenv("START_PAGE", "1"))
        self.max_index_pages = int(os.getenv("MAX_INDEX_PAGES", "1"))
        self.enrich = env_bool("ENRICH_COMPANY_PAGES", False)
        self.max_items = int(os.getenv("MAX_ITEMS", "100"))
        self.items_seen = 0

        if self.letter not in LETTERS:
            raise ValueError(f"START_LETTER must be one of {LETTERS}")

    async def start(self):
        end_page = self.start_page + self.max_index_pages - 1
        for page in range(self.start_page, end_page + 1):
            yield scrapy.Request(
                f"{BASE}/companies/{self.letter.lower()}/{page}",
                callback=self.parse_index,
            )

    def parse_index(self, response):
        cards = response.css('main a[href*="/company/"]')
        if not cards:
            # Fallback for layout changes: any company profile link on page.
            cards = response.css('a[href^="/company/"]')

        emitted = 0
        seen_urls = set()
        for card in cards:
            href = card.attrib.get("href", "")
            profile_url = urljoin(response.url, href)
            if profile_url in seen_urls:
                continue
            seen_urls.add(profile_url)

            name = clean(" ".join(card.css("::text").getall()))
            # Usually the city/industry are sibling text in the card.
            context = clean(" ".join(card.xpath(".//..//text()").getall()))
            district = ""
            industry = ""
            if " · " in context:
                bits = [clean(x) for x in context.split(" · ") if clean(x)]
                if len(bits) >= 2:
                    district, industry = bits[-2], bits[-1]

            if self.enrich:
                yield scrapy.Request(
                    profile_url,
                    callback=self.parse_company,
                    cb_kwargs={
                        "fallback_name": name,
                        "fallback_district": district,
                        "fallback_industry": industry,
                        "source_page": response.url,
                    },
                )
            else:
                self.items_seen += 1
                emitted += 1
                yield StartupItem(
                    startup_name=name,
                    company_slug=profile_url.rstrip("/").split("/")[-1],
                    profile_url=profile_url,
                    source=self.source_name,
                    source_snapshot=self.source_snapshot,
                    district=district,
                    state="",
                    primary_industry=industry,
                    sectors="",
                    description="",
                    website="",
                    dpiit_recognised="",
                    cin="",
                    funding_signal="",
                    founders="",
                    public_emails="",
                    public_phones="",
                    linkedin="",
                    instagram="",
                    facebook="",
                    twitter="",
                    source_page=response.url,
                    crawl_status="directory_record",
                )

            if self.items_seen >= self.max_items:
                raise CloseSpider("MAX_ITEMS reached")

        self.logger.info("Parsed %s startup profile links from %s", emitted, response.url)

    def parse_company(
        self,
        response,
        fallback_name="",
        fallback_district="",
        fallback_industry="",
        source_page="",
    ):
        text = clean(" ".join(response.css("body ::text").getall()))

        def after(label):
            match = re.search(re.escape(label) + r"\s*([^|]+?)(?=\s{2,}|$)", text, re.I)
            return clean(match.group(1)) if match else ""

        website = ""
        for href in response.css('a[href^="http"]::attr(href)').getall():
            if "indianstartupmap.com" not in href:
                website = href
                break

        links = response.css('a[href^="http"]::attr(href)').getall()
        linkedin = next((u for u in links if "linkedin.com" in u.lower()), "")
        instagram = next((u for u in links if "instagram.com" in u.lower()), "")
        facebook = next((u for u in links if "facebook.com" in u.lower()), "")
        twitter = next((u for u in links if "twitter.com" in u.lower() or "x.com" in u.lower()), "")

        description = ""
        # Prefer meta description, then common profile description blocks.
        description = clean(response.css('meta[name="description"]::attr(content)').get())
        if not description:
            description = clean(" ".join(response.css("main p::text").getall()[:4]))

        state = ""
        m = re.search(r"\bDistrict\s+([^,]+),\s+([A-Za-z &]+)\b", text, re.I)
        if m:
            state = clean(m.group(2))

        emails = sorted(set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)))
        phones = sorted(set(re.findall(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)))

        yield StartupItem(
            startup_name=fallback_name or clean(response.css("h1::text").get()),
            company_slug=response.url.rstrip("/").split("/")[-1],
            profile_url=response.url,
            source=self.source_name,
            source_snapshot=self.source_snapshot,
            district=fallback_district,
            state=state,
            primary_industry=fallback_industry,
            sectors=after("Sectors as filed:") or after("Sectors:"),
            description=description,
            website=website,
            dpiit_recognised="DPIIT recognised" in text or "DPIIT recognition" in text,
            cin=after("CIN"),
            funding_signal="Funding signal" if "Funding signal" in text else "",
            founders="",
            public_emails="; ".join(emails),
            public_phones="; ".join(phones),
            linkedin=linkedin,
            instagram=instagram,
            facebook=facebook,
            twitter=twitter,
            source_page=source_page,
            crawl_status="company_profile",
        )
