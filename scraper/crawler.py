"""
crawler.py
----------
Scrapy spider that crawls all pages under
justice.govt.nz/tribunals/tenancy/ (the Tenancy Tribunal section only —
about, process, fees, decisions, adjudicators, etc.) and saves the URL,
title, and text content of each page.

Scoped to a single tribunal for now so the crawl logic can be validated
on a smaller section before being widened back out to all tribunals.

Usage:
    scrapy runspider scraper/crawler.py -o data/tribunal_data.json

Tip: add -L INFO or -L DEBUG to see stats on how many pages were
discovered vs scraped, e.g.:
    scrapy runspider scraper/crawler.py -o data/tribunal_data.json -L INFO
"""

import scrapy
from urllib.parse import urlparse


# Only crawl URLs whose path starts with /tribunals/tenancy/ — keeps us
# strictly within the Tenancy Tribunal section. To widen the crawl back
# out to every tribunal, change this to "/tribunals/".
TRIBUNALS_PATH_PREFIX = "/tribunals/tenancy/"

# Skip non-content files and obvious dead ends
SKIP_EXTENSIONS = (
    ".pdf", ".docx", ".doc", ".xlsx", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".mp3", ".mp4",
)


def is_in_scope(url: str) -> bool:
    """Return True if the URL is a justice.govt.nz Tenancy Tribunal page we want to crawl."""
    parsed = urlparse(url)
    if parsed.netloc not in ("www.justice.govt.nz", "justice.govt.nz"):
        return False
    if not parsed.path.startswith(TRIBUNALS_PATH_PREFIX):
        return False
    if parsed.path.lower().endswith(SKIP_EXTENSIONS):
        return False
    return True


class TribunalSpider(scrapy.Spider):
    name = "tribunals"
    allowed_domains = ["www.justice.govt.nz", "justice.govt.nz"]
    start_urls = ["https://www.justice.govt.nz/tribunals/tenancy/"]

    custom_settings = {
        # Be polite — don't hammer the server
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 4,
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
        # Follow redirects, retry on failure
        "RETRY_TIMES": 2,
        # No artificial depth limit — let it crawl the full section.
        # (Set DEPTH_LIMIT to e.g. 5 here if you want to cap it.)
        "DEPTH_LIMIT": 0,
    }

    def parse(self, response):
        """Entry point — extract content AND follow links, for every page."""
        yield from self._extract_and_follow(response)

    def _extract_and_follow(self, response):
        # Only process actual HTML pages
        content_type = response.headers.get("Content-Type", b"").decode(errors="ignore")
        if "text/html" not in content_type:
            return

        title = response.css("h1::text").get(default="").strip()
        # Grab text from common content elements, including divs with text
        # directly (some govt CMS pages wrap copy in <div> rather than <p>)
        paragraphs = response.css(
            "main p::text, main li::text, main h2::text, main h3::text, "
            "main h4::text, main td::text, main th::text, "
            "p::text, li::text, h2::text, h3::text"
        ).getall()
        content = " ".join(p.strip() for p in paragraphs if p.strip())

        if content:
            yield {
                "url": response.url,
                "title": title,
                "content": content,
            }
        else:
            self.logger.debug(f"No content extracted from {response.url}")

        # Discover every link on the page (nav menus, in-page links,
        # "related pages" widgets, breadcrumbs, etc.) and follow any that
        # are in-scope Tenancy Tribunal pages we haven't visited yet.
        all_links = response.css("a::attr(href)").getall()
        self.logger.info(f"{response.url} -> found {len(all_links)} links")

        for link in all_links:
            if not link:
                continue
            absolute_url = response.urljoin(link)
            # Strip URL fragments (#section) to avoid re-crawling the same page
            absolute_url = absolute_url.split("#")[0]
            if is_in_scope(absolute_url):
                yield response.follow(absolute_url, callback=self.parse)

    custom_settings = {
        # Be polite — don't hammer the server
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 4,
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
        # Follow redirects, retry on failure
        "RETRY_TIMES": 2,
        # No artificial depth limit — let it crawl the full section.
        # (Set DEPTH_LIMIT to e.g. 5 here if you want to cap it.)
        "DEPTH_LIMIT": 0,
    }

    def parse(self, response):
        """Entry point — extract content AND follow links, for every page."""
        yield from self._extract_and_follow(response)

    def _extract_and_follow(self, response):
        # Only process actual HTML pages
        content_type = response.headers.get("Content-Type", b"").decode(errors="ignore")
        if "text/html" not in content_type:
            return

        title = response.css("h1::text").get(default="").strip()
        # Grab text from common content elements, including divs with text
        # directly (some govt CMS pages wrap copy in <div> rather than <p>)
        paragraphs = response.css(
            "main p::text, main li::text, main h2::text, main h3::text, "
            "main h4::text, main td::text, main th::text, "
            "p::text, li::text, h2::text, h3::text"
        ).getall()
        content = " ".join(p.strip() for p in paragraphs if p.strip())

        if content:
            yield {
                "url": response.url,
                "title": title,
                "content": content,
            }
        else:
            self.logger.debug(f"No content extracted from {response.url}")

        # Discover every link on the page (nav menus, in-page links,
        # "related pages" widgets, breadcrumbs, etc.) and follow any that
        # are in-scope tribunal pages we haven't visited yet.
        all_links = response.css("a::attr(href)").getall()
        self.logger.info(f"{response.url} -> found {len(all_links)} links")

        for link in all_links:
            if not link:
                continue
            absolute_url = response.urljoin(link)
            # Strip URL fragments (#section) to avoid re-crawling the same page
            absolute_url = absolute_url.split("#")[0]
            if is_in_scope(absolute_url):
                yield response.follow(absolute_url, callback=self.parse)
