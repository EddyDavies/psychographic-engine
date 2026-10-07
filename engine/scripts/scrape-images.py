#!/usr/bin/env python3
"""Scrape product/offer images from client product pages using Playwright.

Given an offer or product URL, downloads all product images from the page,
then follows links to component product pages and downloads their images too.

Usage:
    uv run --with playwright --with httpx python3 scripts/scrape-images.py <url> --client {client-name}

Examples:
    # Scrape an offer page + its linked products
    uv run --with playwright --with httpx python3 scripts/scrape-images.py https://example.com/products/starter-bundle

    # Scrape a single product page
    uv run --with playwright --with httpx python3 scripts/scrape-images.py https://example.com/products/single-product/
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Skip images matching these patterns (logos, icons, payment badges, etc.)
SKIP_PATTERNS = [
    r"logo",
    r"icon",
    r"favicon",
    r"badge",
    r"payment",
    r"clearpay",
    r"klarna",
    r"trustpilot",
    r"star",
    r"placeholder",
    r"spinner",
    r"loading",
    r"arrow",
    r"close",
    r"menu",
    r"cart",
    r"search",
    r"avatar",
    r"gravatar",
    r"emoji",
    r"smileys",
    r"wp-content/plugins",
    r"wp-includes",
]

MIN_IMAGE_WIDTH = 200  # Skip images smaller than this


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "image"


def extract_page_slug(url: str) -> str:
    """Extract a slug from the URL path for naming."""
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else "page"
    return slugify(slug)


def should_skip(src: str) -> bool:
    """Check if an image URL matches skip patterns."""
    src_lower = src.lower()
    return any(re.search(p, src_lower) for p in SKIP_PATTERNS)


def is_404_page(page) -> bool:
    """Check if the current page is a 404/not-found page."""
    title = page.title().lower()
    return "not found" in title or "404" in title


def scrape_images_from_page(page, url: str) -> list[dict]:
    """Navigate to a page and extract all product image URLs with metadata."""
    print(f"\nScraping: {url}", file=sys.stderr)
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    if is_404_page(page):
        print(f"  Skipping — page not found (404)", file=sys.stderr)
        return []

    # Scroll down to trigger lazy loading
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)

    # Extract images from the page
    images = page.evaluate("""() => {
        const imgs = document.querySelectorAll('img');
        const results = [];
        const seen = new Set();

        for (const img of imgs) {
            // Try srcset first for highest quality, then src
            let src = '';
            if (img.srcset) {
                // Parse srcset and pick the largest
                const entries = img.srcset.split(',').map(s => s.trim().split(/\\s+/));
                let best = null;
                let bestW = 0;
                for (const [url, descriptor] of entries) {
                    const w = parseInt(descriptor) || 0;
                    if (w > bestW || !best) {
                        best = url;
                        bestW = w;
                    }
                }
                if (best) src = best;
            }
            if (!src) src = img.src;
            if (!src || src.startsWith('data:')) continue;

            // Get natural dimensions
            const w = img.naturalWidth || img.width || 0;
            const h = img.naturalHeight || img.height || 0;

            // Get alt text
            const alt = img.alt || '';

            // Deduplicate by URL (ignoring query params for size variants)
            const baseUrl = src.split('?')[0];
            if (seen.has(baseUrl)) continue;
            seen.add(baseUrl);

            results.push({ src, alt, width: w, height: h });
        }

        // Also check for background images on product gallery elements
        const galleries = document.querySelectorAll(
            '.woocommerce-product-gallery__image a, ' +
            '.woocommerce-product-gallery__image, ' +
            '[data-thumb]'
        );
        for (const el of galleries) {
            const href = el.getAttribute('href');
            if (href && !href.startsWith('#') && !seen.has(href.split('?')[0])) {
                seen.add(href.split('?')[0]);
                results.push({ src: href, alt: el.getAttribute('title') || '', width: 0, height: 0 });
            }
            const thumb = el.getAttribute('data-thumb');
            if (thumb && !seen.has(thumb.split('?')[0])) {
                // Skip thumbs, we want full size from href
            }
        }

        // Check og:image meta tag
        const ogImage = document.querySelector('meta[property="og:image"]');
        if (ogImage) {
            const content = ogImage.getAttribute('content');
            if (content && !seen.has(content.split('?')[0])) {
                seen.add(content.split('?')[0]);
                results.push({ src: content, alt: 'og-image', width: 0, height: 0 });
            }
        }

        return results;
    }""")

    # Filter out small/irrelevant images
    filtered = []
    for img in images:
        src = img["src"]
        if should_skip(src):
            continue
        # Keep images that are large enough or where we can't determine size
        if img["width"] > 0 and img["width"] < MIN_IMAGE_WIDTH:
            continue
        filtered.append(img)

    print(f"  Found {len(images)} total images, {len(filtered)} after filtering", file=sys.stderr)
    return filtered


def find_product_links(page, base_url: str) -> list[str]:
    """Find links to individual product pages from an offer/bundle page."""
    base_clean = base_url.split("?")[0].split("#")[0].rstrip("/")

    links = page.evaluate("""(baseUrl) => {
        const anchors = document.querySelectorAll('a[href]');
        const productLinks = new Set();
        const domain = new URL(baseUrl).origin;
        const basePath = new URL(baseUrl).pathname.replace(/\\/$/, '');

        for (const a of anchors) {
            let href = a.href;
            if (!href.startsWith(domain)) continue;

            const url = new URL(href);
            const path = url.pathname.replace(/\\/$/, '');

            // Skip fragments, query-only variants, and the current page
            if (path === basePath) continue;
            if (path === '' || path === '/') continue;

            // Skip non-product pages
            if (path.includes('/cart') || path.includes('/checkout') ||
                path.includes('/my-account') || path.includes('/shop') ||
                path.includes('/product-category') || path.includes('/page/')) continue;

            // Match product URLs: typically /organic/product-name/ or /product/product-name/
            if (path.match(/^\\/(organic|product)\\/[a-z0-9-]+$/)) {
                productLinks.add(url.origin + path + '/');
            }
        }
        return Array.from(productLinks);
    }""", base_url)

    print(f"  Found {len(links)} product links", file=sys.stderr)
    return links


def download_image(url: str, dest: Path, client: httpx.Client) -> bool:
    """Download an image to the destination path."""
    try:
        resp = client.get(url, follow_redirects=True, timeout=30)
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code} for {url}", file=sys.stderr)
            return False

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            print(f"  Not an image ({content_type}): {url}", file=sys.stderr)
            return False

        dest.write_bytes(resp.content)
        size_kb = len(resp.content) // 1024
        print(f"  Saved: {dest.name} ({size_kb}KB)", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  Download error: {e}", file=sys.stderr)
        return False


def determine_extension(url: str) -> str:
    """Determine file extension from URL."""
    path = urlparse(url).path.lower()
    for ext in (".png", ".webp", ".gif"):
        if ext in path:
            return ext
    return ".jpg"


def scrape_and_save(page, url: str, output_dir: Path, prefix: str, http_client: httpx.Client) -> int:
    """Scrape images from a page and save them to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images = scrape_images_from_page(page, url)

    saved = 0
    for i, img in enumerate(images, 1):
        src = img["src"]
        # Make absolute URL
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(url, src)

        ext = determine_extension(src)
        alt_slug = slugify(img["alt"])[:40] if img["alt"] else ""
        if alt_slug and alt_slug != "image":
            filename = f"{prefix}-{alt_slug}-{i}{ext}"
        else:
            filename = f"{prefix}-{i}{ext}"

        dest = output_dir / filename
        if download_image(src, dest, http_client):
            saved += 1

    return saved


def main():
    parser = argparse.ArgumentParser(description="Scrape product/offer images from a webpage")
    parser.add_argument("url", help="URL of the offer or product page to scrape")
    parser.add_argument("--client", required=True, help="Client name")
    parser.add_argument("--no-follow", action="store_true", help="Don't follow links to product pages")
    args = parser.parse_args()

    client_dir = PROJECT_ROOT / "clients" / args.client
    products_images_dir = client_dir / "products" / "images"
    offers_images_dir = client_dir / "offers" / "images"

    url = args.url.rstrip("/") + "/"
    page_slug = extract_page_slug(url)

    # Determine if this looks like an offer/bundle page vs a single product
    # Heuristic: offer pages tend to have words like "pack", "bundle", "set", "box" in the slug
    offer_keywords = ["pack", "bundle", "set", "box", "gift", "combo", "kit", "collection"]
    is_offer = any(kw in page_slug for kw in offer_keywords)

    print(f"Page type: {'offer' if is_offer else 'product'}", file=sys.stderr)
    print(f"Client: {args.client}", file=sys.stderr)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        http_client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )

        total_saved = 0

        # Scrape the main page
        if is_offer:
            output_dir = offers_images_dir
        else:
            output_dir = products_images_dir

        total_saved += scrape_and_save(page, url, output_dir, page_slug, http_client)

        # If it's an offer page and we should follow links, scrape product pages too
        if is_offer and not args.no_follow:
            product_links = find_product_links(page, url)

            for product_url in product_links:
                product_slug = extract_page_slug(product_url)
                total_saved += scrape_and_save(
                    page, product_url, products_images_dir, product_slug, http_client
                )

        http_client.close()
        browser.close()

    print(f"\nDone: {total_saved} images saved", file=sys.stderr)
    if is_offer:
        print(f"  Offer images: {offers_images_dir}", file=sys.stderr)
    if not args.no_follow or not is_offer:
        print(f"  Product images: {products_images_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
