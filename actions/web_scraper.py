"""
web_scraper.py — Autonomous scraping agent utilizing BeautifulSoup and Gemini.
Extracts structured elements (tables, headers, text blocks) from any web page.
"""

import requests
from bs4 import BeautifulSoup
from actions.prime_utils import UnifiedModelClient

def web_scraper(parameters: dict, player=None) -> str:
    """
    Fetches a URL and uses Gemini to extract specific content based on instructions.
    """
    url = parameters.get("url", "")
    instruction = parameters.get("instruction", "Extract key information")
    
    if not url:
        return "Please provide 'url' parameter, sir."

    def log(msg: str):
        print(f"[Web Scraper] {msg}")
        if player:
            player.write_log(f"[Web Scraper] {msg}")

    log(f"Fetching URL: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return f"Failed to retrieve page, status code: {resp.status_code}"
            
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Strip script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines[:200]) # Cap text block to avoid token overflow
        
        client = UnifiedModelClient()
            
        log("Analyzing content with Gemini...")
        prompt = (
            f"You are an elite scraping agent. Below is raw text scraped from {url}.\n"
            f"Instruction: {instruction}\n\n"
            f"Raw text:\n{clean_text}\n\n"
            f"Response format: Return only the extracted structured markdown text matching the instruction."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
        
    except Exception as e:
        return f"Scraping failed with exception: {e}"
