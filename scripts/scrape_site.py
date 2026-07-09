import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re
import shutil
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.kdipower.co.in/"
DOMAIN = "www.kdipower.co.in"

# Directories
DIRS = {
    "website": "data/website",
    "products": "data/products",
    "images": "data/images"
}

# Clean old data to avoid stale files
for d in ["data/website", "data/products"]:
    if os.path.exists(d):
        shutil.rmtree(d)
        
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

visited_urls = set()
visited_images = set()

def clean_filename(name):
    return re.sub(r'[^\w\-_\.]', '_', name)

def get_text_from_html(soup):
    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    
    # Also attempt to remove common sidebar/navigation classes if present
    for tag in soup.find_all(class_=re.compile("menu|nav|footer|sidebar|header", re.I)):
        tag.decompose()
        
    text = soup.get_text(separator='\n')
    # clean up empty lines
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def crawl(url):
    if url in visited_urls:
        return
    
    print(f"Crawling: {url}")
    visited_urls.add(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, timeout=10, verify=False, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return

    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Determine save path based on url
    parsed_url = urlparse(url)
    path = parsed_url.path
    if path == "/" or path == "":
        name = "home"
        folder = DIRS["website"]
    else:
        name = path.strip("/").replace(".html", "")
        if not name:
            name = "index"
        if "cable" in name.lower() or "wire" in name.lower() or "conductor" in name.lower():
            folder = DIRS["products"]
        else:
            folder = DIRS["website"]
            
    name = clean_filename(name)
        
    # Extract images
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            src = img.get('data-src') or img.get('data-img')
        if src:
            img_url = urljoin(url, src)
            if img_url.startswith("data:image"):
                continue
            if img_url not in visited_images:
                visited_images.add(img_url)
                try:
                    img_resp = requests.get(img_url, timeout=10, verify=False, headers=headers)
                    if img_resp.status_code == 200:
                        img_name = clean_filename(os.path.basename(urlparse(img_url).path))
                        if not img_name:
                            img_name = f"image_{len(visited_images)}.jpg"
                        with open(os.path.join(DIRS["images"], img_name), "wb") as f:
                            f.write(img_resp.content)
                except Exception as e:
                    print(f"Failed to download image {img_url}: {e}")
                    
    # Find links BEFORE decomposing the soup
    links_to_visit = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if href:
            full_url = urljoin(url, href)
            full_url = full_url.split('#')[0]
            parsed_full = urlparse(full_url)
            if parsed_full.netloc == DOMAIN and full_url not in visited_urls:
                if not parsed_full.path.endswith(('.pdf', '.jpg', '.png', '.zip', '.jpeg', '.gif')):
                    links_to_visit.append(full_url)

    # Extract text (this modifies the soup by decomposing elements)
    text = get_text_from_html(soup)
    if text:
        with open(os.path.join(folder, f"{name}.txt"), "w", encoding="utf-8") as f:
            f.write(f"Source URL: {url}\n\n{text}")
            
    # Now visit the collected links
    for link in set(links_to_visit):
        crawl(link)
        time.sleep(0.5)

if __name__ == "__main__":
    print("Starting scrape...")
    crawl(BASE_URL)
    print("Scrape complete!")
