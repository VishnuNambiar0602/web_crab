import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

import scrapy

from startup_india_scraper.items import StartupItem


class StartupIndiaSpider(scrapy.Spider):
    """
    Scrapes publicly accessible Startup India startup-directory pages.

    Important:
    - Startup India's current directory may require login/registration before
      showing startup records. This spider does NOT bypass authentication,
      CAPTCHA, or access controls.
    - If the public directory is rendered dynamically or blocks plain HTTP,
      run with use_zyte=true and a valid Zyte API subscription/key.
    """

    name = "startup_india"
    allowed_domains = ["startupindia.gov.in"]

    search_url = (
        "https://www.startupindia.gov.in/content/sih/en/search.html"
    )

    custom_settings = {
        "CLOSESPIDER_TIMEOUT": 3500,
    }

    def __init__(
        self,
        max_pages=10,
        page=0,
        industry="",
        sector="",
        state="",
        city="",
        stage="",
        use_zyte="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.max_pages = max(1, min(int(max_pages), 500))
        self.start_page = max(0, int(page))
        self.industry = industry.strip()
        self.sector = sector.strip()
        self.state = state.strip()
        self.city = city.strip()
        self.stage = stage.strip()
        self.use_zyte = str(use_zyte).lower() in {"1", "true", "yes", "y"}

    def start_requests(self):
        yield self._search_request(self.start_page)

    def _search_request(self, page_number):
        params = {
            "roles": "Startup",
            "page": page_number,
        }
        # These parameter names mirror the directory's visible filters.
        optional = {
            "industry": self.industry,
            "sector": self.sector,
            "state": self.state,
            "city": self.city,
            "stage": self.stage,
        }
        params.update({k: v for k, v in optional.items() if v})

        url = f"{self.search_url}?{urlencode(params)}"
        meta = {"page_number": page_number}

        if self.use_zyte:
            meta["zyte_api"] = {
                "browserHtml": True,
                "geolocation": "IN",
            }

        return scrapy.Request(
            url,
            callback=self.parse_search,
            errback=self.handle_error,
            meta=meta,
            dont_filter=True,
        )

    def parse_search(self, response):
        page_number = response.meta["page_number"]
        body_text = self._clean_text(" ".join(response.css("body ::text").getall()))

        if self._looks_like_login_wall(body_text):
            yield {
                "source": "startupindia.gov.in",
                "source_url": response.url,
                "crawl_status": "login_required_or_access_restricted",
                "message": (
                    "Startup India returned a login/registration wall before "
                    "startup records became available. No authentication was bypassed."
                ),
                "scraped_at": self._now(),
            }
            return

        detail_urls = self._extract_detail_urls(response)

        # Some versions of the site render data as links only after JS.
        # If no profile links were exposed, try parsing cards directly.
        yielded_card = False
        for card in self._candidate_cards(response):
            item = self._item_from_card(card, response.url)
            if item and item.get("startup_name"):
                yielded_card = True
                yield item

        seen = set()
        for url in detail_urls:
            if url in seen:
                continue
            seen.add(url)
            meta = {}
            if self.use_zyte:
                meta["zyte_api"] = {
                    "browserHtml": True,
                    "geolocation": "IN",
                }
            yield scrapy.Request(
                url,
                callback=self.parse_detail,
                errback=self.handle_error,
                meta=meta,
            )

        if page_number + 1 < self.start_page + self.max_pages:
            # Avoid endlessly paging if the site gives us neither records nor links.
            if detail_urls or yielded_card:
                yield self._search_request(page_number + 1)

    def parse_detail(self, response):
        item = self._extract_detail_item(response)
        if item.get("startup_name"):
            yield item

    def _extract_detail_urls(self, response):
        urls = []
        for a in response.css("a[href]"):
            href = a.attrib.get("href", "").strip()
            text = self._clean_text(" ".join(a.css("::text").getall()))
            absolute = urljoin(response.url, href)
            parsed = urlparse(absolute)

            if parsed.netloc.lower() != "www.startupindia.gov.in":
                continue

            path = parsed.path.lower()
            # Keep likely startup profile routes while excluding site navigation.
            if (
                "/startup" in path
                or "/startups/" in path
                or "/startup/" in path
            ):
                if absolute not in urls and text:
                    urls.append(absolute)

        return urls

    def _candidate_cards(self, response):
        selectors = [
            "article",
            "li[class*='card']",
            "div[class*='startup-card']",
            "div[class*='startup_card']",
            "div[class*='result-card']",
            "div[class*='result_card']",
            "div[class*='search-result']",
            "div[class*='search_result']",
        ]
        seen = set()
        for selector in selectors:
            for node in response.css(selector):
                key = "".join(node.css("::text").getall())[:500]
                if key not in seen:
                    seen.add(key)
                    yield node

    def _item_from_card(self, card, source_url):
        text = self._clean_text(" ".join(card.css("::text").getall()))
        if len(text) < 15:
            return None

        links = []
        for a in card.css("a[href]"):
            href = a.attrib.get("href", "").strip()
            if href:
                links.append(urljoin(source_url, href))

        profile_url = next(
            (
                u for u in links
                if urlparse(u).netloc.lower() == "www.startupindia.gov.in"
                and "/startup" in urlparse(u).path.lower()
            ),
            "",
        )

        name = ""
        headings = card.css("h1::text, h2::text, h3::text, h4::text, strong::text")
        if headings:
            name = self._clean_text(" ".join(headings.getall()))
        if not name:
            name = text.split(" | ")[0].strip()[:250]

        item = StartupItem(
            source="startupindia.gov.in",
            source_url=source_url,
            profile_url=profile_url,
            startup_name=name,
            description=text[:2000],
            scraped_at=self._now(),
            crawl_status="public_record",
        )
        self._fill_common_links(item, card, source_url)
        return item

    def _extract_detail_item(self, response):
        item = StartupItem(
            source="startupindia.gov.in",
            source_url=response.url,
            profile_url=response.url,
            scraped_at=self._now(),
            crawl_status="public_record",
        )

        # JSON-LD is usually more stable than CSS class names.
        jsonld = self._jsonld_objects(response)
        for obj in jsonld:
            if not item.get("startup_name"):
                item["startup_name"] = self._first_value(
                    obj, ["name", "legalName", "alternateName"]
                )
            if not item.get("description"):
                item["description"] = self._first_value(obj, ["description"])
            if not item.get("website"):
                item["website"] = self._first_value(obj, ["url"])

        labels = {
            "industry": ["industry", "industries"],
            "sector": ["sector", "sectors"],
            "stage": ["stage", "startup stage", "business stage"],
            "city": ["city"],
            "state": ["state"],
            "country": ["country"],
            "email": ["email", "e-mail"],
            "phone": ["phone", "mobile", "contact number"],
            "recognition_number": [
                "dpiit recognition number",
                "recognition number",
                "certificate number",
            ],
            "incorporation_date": [
                "date of incorporation",
                "incorporation date",
            ],
        }

        for field, variants in labels.items():
            value = self._label_value(response, variants)
            if value and not item.get(field):
                item[field] = value

        if not item.get("startup_name"):
            title = self._clean_text(response.css("title::text").get(""))
            item["startup_name"] = re.sub(
                r"\s*[-|]\s*Startup India.*$", "", title, flags=re.I
            ).strip()

        if not item.get("description"):
            item["description"] = self._meta_description(response)

        item["dpiit_recognised"] = self._extract_bool(
            item.get("dpiit_recognised")
            or self._label_value(
                response,
                ["dpiit recognised", "dpiit recognized", "recognised startup"],
            )
        )

        websites = self._extract_links(response, [
            "http", "www.", "linkedin.com", "facebook.com",
            "instagram.com", "twitter.com", "x.com"
        ])
        if not item.get("website"):
            item["website"] = self._best_external_website(websites)

        item["social_links"] = [
            u for u in websites
            if any(
                domain in urlparse(u).netloc.lower()
                for domain in (
                    "linkedin.com", "facebook.com", "instagram.com",
                    "twitter.com", "x.com"
                )
            )
        ]

        founders = self._label_value(
            response, ["founder", "founders", "promoter", "promoters"]
        )
        if founders:
            item["founders"] = founders

        return item

    def _label_value(self, response, labels):
        # Try definition lists, table rows, and text blocks.
        for label in labels:
            pattern = re.compile(rf"^{re.escape(label)}\s*[:\-]?\s*$", re.I)

            for dt in response.css("dt"):
                txt = self._clean_text(" ".join(dt.css("::text").getall()))
                if pattern.match(txt):
                    dd = dt.xpath("following-sibling::dd[1]")
                    value = self._clean_text(" ".join(dd.css("::text").getall()))
                    if value:
                        return value

            for tr in response.css("tr"):
                cells = [
                    self._clean_text(" ".join(c.css("::text").getall()))
                    for c in tr.css("th, td")
                ]
                if len(cells) >= 2 and re.match(
                    rf"^{re.escape(label)}$", cells[0], re.I
                ):
                    return cells[1]

        # Fallback: inspect visible text lines.
        lines = [
            self._clean_text(x)
            for x in response.css("body ::text").getall()
            if self._clean_text(x)
        ]
        for i, line in enumerate(lines):
            for label in labels:
                m = re.match(
                    rf"^{re.escape(label)}\s*[:\-]\s*(.+)$", line, re.I
                )
                if m:
                    return m.group(1).strip()[:1000]
                if line.lower() == label.lower() and i + 1 < len(lines):
                    return lines[i + 1][:1000]
        return ""

    def _jsonld_objects(self, response):
        objects = []
        for raw in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if isinstance(data, list):
                objects.extend(x for x in data if isinstance(x, dict))
            elif isinstance(data, dict):
                objects.append(data)
        return objects

    def _extract_links(self, response, prefixes):
        result = []
        for href in response.css("a::attr(href)").getall():
            href = href.strip()
            absolute = urljoin(response.url, href)
            if not absolute.startswith(("http://", "https://")):
                continue
            if absolute not in result:
                result.append(absolute)
        return result

    def _best_external_website(self, urls):
        excluded = {
            "startupindia.gov.in",
            "www.startupindia.gov.in",
            "facebook.com",
            "www.facebook.com",
            "linkedin.com",
            "www.linkedin.com",
            "instagram.com",
            "www.instagram.com",
            "twitter.com",
            "www.twitter.com",
            "x.com",
            "www.x.com",
        }
        for url in urls:
            host = urlparse(url).netloc.lower().split(":")[0]
            if host and host not in excluded and not host.endswith(".startupindia.gov.in"):
                return url
        return ""

    def _meta_description(self, response):
        return self._clean_text(
            response.css("meta[name='description']::attr(content)").get("")
        )

    def _first_value(self, obj, keys):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return self._clean_text(value)
        return ""

    def _extract_bool(self, value):
        if not value:
            return None
        text = str(value).lower()
        if any(x in text for x in ["yes", "true", "recognised", "recognized"]):
            return True
        if any(x in text for x in ["no", "false", "not recognised", "not recognized"]):
            return False
        return None

    def _fill_common_links(self, item, node, source_url):
        links = [
            urljoin(source_url, h.strip())
            for h in node.css("a::attr(href)").getall()
            if h.strip()
        ]
        external = self._best_external_website(links)
        if external:
            item["website"] = external
        item["social_links"] = [
            u for u in links
            if any(
                d in urlparse(u).netloc.lower()
                for d in ("linkedin.com", "facebook.com", "instagram.com",
                          "twitter.com", "x.com")
            )
        ]

    def _looks_like_login_wall(self, text):
        low = text.lower()
        indicators = [
            "please login/register to proceed further",
            "please login to proceed",
            "login/register to proceed",
            "don't have an account? register now",
        ]
        return any(x in low for x in indicators)

    def _clean_text(self, value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def handle_error(self, failure):
        request = failure.request
        yield {
            "source": "startupindia.gov.in",
            "source_url": request.url,
            "crawl_status": "request_error",
            "error": repr(failure.value),
            "scraped_at": self._now(),
        }
