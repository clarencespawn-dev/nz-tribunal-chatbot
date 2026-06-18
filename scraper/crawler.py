"""
crawler.py
----------
Scrapy spider that crawls all pages under justice.govt.nz/tribunals/
and saves the URL, title, and text content of each page.

Usage:
    scrapy runspider scraper/crawler.py -o data/tribunal_data.json
"""

import scrapy


class TribunalSpider(scrapy.Spider):
    name = "tribunals"
    allowed_domains = ["www.justice.govt.nz"]
    start_urls = ["https://www.justice.govt.nz/tribunals/"]

    custom_settings = {
        # Be polite — don't hammer the server
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 4,
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
    }

    def parse(self, response):
        """Follow all internal links within the /tribunals/ section."""
        for link in response.css("a::attr(href)").getall():
            if link and "/tribunals/" in link:
                yield response.follow(link, callback=self.parse_page)

    def parse_page(self, response):
        """Extract title and text content from each tribunal page."""
        title = response.css("h1::text").get(default="").strip()
        paragraphs = response.css("p::text, li::text, h2::text, h3::text").getall()
        content = " ".join(p.strip() for p in paragraphs if p.strip())

        if content:
            yield {
                "url": response.url,
                "title": title,
                "content": content,
            }

        # Also follow links found on this page
        for link in response.css("a::attr(href)").getall():
            if link and "/tribunals/" in link:
                yield response.follow(link, callback=self.parse_page)
