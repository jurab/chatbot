import json
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from openai import OpenAI

client = OpenAI()  # api key must be in env

visited = set()

def fetch_rendered(url):
    print(f"[fetch] {url}")
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[fetch] fail: {e}")
        return None

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)

def extract_links(base, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        if urlparse(href).netloc == urlparse(base).netloc:
            links.add(href.split("#")[0])
    return links

def analyze_text(text):
    snippet = text[:6000]
    prompt = f"extract key marketing signals from this:\n\n{snippet}"
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

def crawl(start_url, out_path="crawl_output.jsonl", max_pages=20):
    queue = [start_url]

    with open(out_path, "a", encoding="utf-8") as out:
        while queue and len(visited) < max_pages:
            url = queue.pop()
            if url in visited:
                continue
            visited.add(url)

            print(f"\n[crawl] visiting: {url}")

            html = fetch_rendered(url)
            if not html:
                print(f"[crawl] fetch failed")
                continue

            text = clean_html(html)

            try:
                analysis = analyze_text(text)
            except Exception as e:
                print(f"[gpt] fail: {e}")
                analysis = f"error during gpt call: {e}"

            out.write(json.dumps({
                "url": url,
                "analysis": analysis,
                "text_sample": text[:1000]
            }) + "\n")

            links = extract_links(url, html)
            for link in links:
                if link not in visited:
                    queue.append(link)

            time.sleep(1)

# usage:
# crawl("https://www.eon.cz")

