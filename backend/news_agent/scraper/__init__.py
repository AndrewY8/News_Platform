from .beautiful_soup.beautiful_soup import BeautifulSoupScraper
from .web_base_loader.web_base_loader import WebBaseLoaderScraper
from .pymupdf.pymupdf import PyMuPDFScraper
from .browser.browser import BrowserScraper
from .browser.nodriver_scraper import NoDriverScraper
from .tavily_extract.tavily_extract import TavilyExtract
from .firecrawl.firecrawl import FireCrawl
from .scraper import Scraper

__all__ = [
    "BeautifulSoupScraper",
    "WebBaseLoaderScraper",
    "PyMuPDFScraper",
    "BrowserScraper",
    "NoDriverScraper",
    "TavilyExtract",
    "Scraper",
    "FireCrawl",
]
