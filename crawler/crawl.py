import argparse
import json
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from openai import OpenAI

client = OpenAI()  # api key must be in env


# ------------------------------------------------------------
# tools
# ------------------------------------------------------------

def render_page(url):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        browser.close()
        return html

def extract_text(html):
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
    return list(links)

def llm(prompt):
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content


# ------------------------------------------------------------
# agentic crawl
# ------------------------------------------------------------

def agentic_crawl(start_url, goal, max_pages, pages_out, summary_out):
    visited = set()
    frontier = [start_url]
    results = []

    with open(pages_out, "w", encoding="utf-8") as f:
        while frontier and len(visited) < max_pages:
            url = frontier.pop(0)
            if url in visited:
                continue
            visited.add(url)

            print(f"\n[agent] visiting {url}")

            try:
                html = render_page(url)
            except Exception as e:
                print(f"[fetch fail] {e}")
                continue

            text = extract_text(html)
            links = extract_links(url, html)

            # -----------------------
            # STRUCTURED EXTRACTION
            # -----------------------

            extract_prompt = f"""
extract structured marketing info relevant to:

goal: {goal}

text:
{text[:8000]}

return ONLY valid json with this exact schema:

{{
  "url": "{url}",
  "claims": [ ... ],
  "pricing": [ ... ],
  "positioning": [ ... ],
  "ctas": [ ... ],
  "notes": "..."
}}
"""
            try:
                structured = llm(extract_prompt)
                data = json.loads(structured)
            except Exception:
                data = {
                    "url": url,
                    "claims": [],
                    "pricing": [],
                    "positioning": [],
                    "ctas": [],
                    "notes": "extraction failure"
                }

            results.append(data)
            f.write(json.dumps(data) + "\n")

            # -----------------------
            # LINK DECISION
            # -----------------------

            decide_prompt = f"""
goal: {goal}

current url: {url}

here are outgoing links:
{links[:40]}

based on the goal, select the FEWEST but MOST valuable next links.
return ONLY a python list, no explanation.
"""
            try:
                nxt = llm(decide_prompt)
                nxt = eval(nxt) if isinstance(nxt, str) else []
                if not isinstance(nxt, list):
                    nxt = []
            except:
                nxt = []

            for link in nxt:
                if link not in visited and link not in frontier:
                    frontier.append(link)

            time.sleep(1)

    # --------------------------------------------------------
    # squash + aggregate summary
    # --------------------------------------------------------

    combined_prompt = f"""
you are given structured page-level marketing analysis as json items:

{json.dumps(results)[:24000]}

goal: {goal}

produce a single FINAL structured summary with this schema:

{{
  "overall_positioning": "...",
  "pricing_strategy": [...],
  "key_claims": [...],
  "target_segments": [...],
  "ctas": [...],
  "competitive_edges": [...],
  "weak_spots": [...],
  "concise_summary": "..."
}}

return ONLY valid json.
"""
    try:
        summary_raw = llm(combined_prompt)
        summary = json.loads(summary_raw)
    except:
        summary = {"error": "summary failed"}

    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n[done] aggregated summary written.")


# ------------------------------------------------------------
# cli
# ------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--pages-out", default="agent_pages.jsonl")
    parser.add_argument("--summary-out", default="agent_summary.json")
    args = parser.parse_args()

    agentic_crawl(
        start_url=args.url,
        goal=args.goal,
        max_pages=args.max_pages,
        pages_out=args.pages_out,
        summary_out=args.summary_out
    )

