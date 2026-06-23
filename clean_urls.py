"""
Cleans lgu_urls.txt:
- removes anchor-only fragments (#...)
- removes cdn-cgi junk (email protection, etc.)
- removes duplicate/near-duplicate trailing slashes
- removes non-page file types (images etc.) -> saved separately
- separates PDFs into their own file for later processing
- removes exact duplicates
- sorts final list
"""

INPUT_FILE = "lgu_urls.txt"
CLEAN_FILE = "lgu_urls_clean.txt"
PDF_FILE = "lgu_urls_pdfs.txt"
REMOVED_FILE = "lgu_urls_removed.txt"

NON_PAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
    ".css", ".js", ".ico", ".woff", ".woff2", ".ttf",
    ".zip", ".mp4", ".mp3"
)

def normalize(url):
    # Strip trailing slash (but keep it if URL is just the domain root)
    if url.endswith("/") and url.count("/") > 2:
        url = url[:-1]
    return url

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

clean = set()
pdfs = set()
removed = []

for url in urls:
    lower = url.lower()

    # Anchor-only fragments like .../#something
    if "/#" in url or url.endswith("#"):
        removed.append(url)
        continue

    # Cloudflare email protection / cdn-cgi junk
    if "cdn-cgi" in lower:
        removed.append(url)
        continue

    # PDFs -> separate file
    if lower.endswith(".pdf"):
        pdfs.add(normalize(url))
        continue

    # Non-page files (images, scripts, fonts, etc.)
    if lower.endswith(NON_PAGE_EXTENSIONS):
        removed.append(url)
        continue

    # Author/login/profile junk (often not useful for chatbot)
    if "/author/" in lower or "/wp-admin" in lower or "/wp-login" in lower:
        removed.append(url)
        continue

    clean.add(normalize(url))

# Save results
with open(CLEAN_FILE, "w", encoding="utf-8") as f:
    for url in sorted(clean):
        f.write(url + "\n")

with open(PDF_FILE, "w", encoding="utf-8") as f:
    for url in sorted(pdfs):
        f.write(url + "\n")

with open(REMOVED_FILE, "w", encoding="utf-8") as f:
    for url in sorted(set(removed)):
        f.write(url + "\n")

print(f"Original URLs: {len(urls)}")
print(f"Clean page URLs: {len(clean)} -> {CLEAN_FILE}")
print(f"PDF URLs: {len(pdfs)} -> {PDF_FILE}")
print(f"Removed junk URLs: {len(set(removed))} -> {REMOVED_FILE}")