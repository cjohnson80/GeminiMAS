import urllib.request
import urllib.parse
import sys
import re
import concurrent.futures
import functools

# Optimized Scraper with Multi-threading and simple caching simulation
CACHE = {}

def fetch_url_content(url):
    if url in CACHE:
        return CACHE[url]
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            CACHE[url] = content
            return content
    except Exception as e:
        return f"Error fetching {url}: {e}"

def search(query):
    search_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    html = fetch_url_content(search_url)
    
    if "Error" in html:
        print(html)
        return

    # Extracting result links to demonstrate multi-threading
    links = re.findall(r'href="(https?://.*?)"', html)
    # Filter out DDG internal links
    external_links = [l for l in links if "duckduckgo.com" not in l][:5]

    print(f"Searching for: {query}\n")
    
    # Multi-threaded fetching of search result snippets/titles
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_url_content, url): url for url in external_links}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                data = future.result()
                title_match = re.search(r'<title>(.*?)</title>', data, re.IGNORECASE)
                title = title_match.group(1) if title_match else "No Title Found"
                print(f"Result {i+1} [{url}]:\n{title}\n")
            except Exception as exc:
                print(f'{url} generated an exception: {exc}')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        search(sys.argv[1])
    else:
        print("Usage: python3 web_scraper.py 'query'")
