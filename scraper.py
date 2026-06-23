import urllib.request
import urllib.error
from html.parser import HTMLParser
import json
import time

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.links.append(value)

BASE = "https://lgu.edu.pk"
visited = set()
all_urls = []

def scrape(url, depth=0):
    if depth > 1 or url in visited:
        return
    if not url.startswith(BASE):
        return
    
    visited.add(url)
    print(f"[{depth}] Scraping: {url}")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5)
        html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [SKIP] {e}")
        return
    
    parser = LinkExtractor()
    parser.feed(html)
    
    for href in parser.links:
        if href.startswith('/'):
            full = BASE + href
        elif href.startswith('http'):
            full = href
        else:
            full = BASE + '/' + href
        
        # Clean up URL
        if '?' in full:
            full = full.split('?')[0]
        if full.endswith('/'):
            full = full[:-1]
        
        if full not in visited and full.startswith(BASE):
            all_urls.append(full)
            scrape(full, depth + 1)
        
        time.sleep(0.1)

print("Starting scrape...\n")
scrape(BASE)

# Save results
with open("lgu_urls.txt", "w") as f:
    for url in sorted(set(all_urls)):
        f.write(url + "\n")

print(f"\nDone! Found {len(set(all_urls))} URLs")
print("Saved to: lgu_urls.txt")