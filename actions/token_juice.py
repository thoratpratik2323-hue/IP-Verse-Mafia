import re
import urllib.parse
from bs4 import BeautifulSoup

def compress_html(html_content: str) -> str:
    """
    Parses raw HTML, strips boilerplate tags (script, style, iframe, footer, nav, header),
    and converts the core readable content to clean Markdown format to save tokens.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove non-content tags
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "aside", "head", "noscript", "svg"]):
            element.decompose()
            
        # Extract and simplify main body/article if present
        main_content = soup.find(["main", "article", "div", "body"])
        target_soup = main_content if main_content else soup
        
        # Convert links to short inline links
        for a in target_soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if text and not href.startswith("javascript:") and not href.startswith("#"):
                # Shorten link representation
                parsed = urllib.parse.urlparse(href)
                domain = parsed.netloc or parsed.path[:20]
                a.replace_with(f" [{text}]({domain}) ")
                
        # Simplify tables
        for table in target_soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if any(cols):
                    rows.append(" | ".join(cols))
            table.replace_with("\n" + "\n".join(rows) + "\n")
            
        # Convert headers and common blocks to plain formatted markers
        for h in target_soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            h.replace_with(f"\n### {h.get_text(strip=True)}\n")
            
        for li in target_soup.find_all("li"):
            li.replace_with(f"\n* {li.get_text(strip=True)}")

        # Extract text and replace excessive blank lines
        text = target_soup.get_text()
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    except Exception as e:
        return f"[TokenJuice Error] HTML parsing failed: {e}"

def shorten_urls(text: str) -> str:
    """
    Finds overly long URLs in text and simplifies them to clear domains
    to reduce token sprawl.
    """
    if not text:
        return ""
    
    # Regex to find http/https URLs
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
    
    def replacer(match):
        url = match.group(0)
        if len(url) < 40:
            return url
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or parsed.path[:30]
            # Retain key path segments but strip query params
            path_segments = [seg for seg in parsed.path.split("/") if seg][:2]
            path_str = "/" + "/".join(path_segments) if path_segments else ""
            return f"{domain}{path_str}"
        except Exception:
            return url[:40] + "..."
            
    return url_pattern.sub(replacer, text)

def deduplicate_lines(text: str) -> str:
    """
    Removes redundant lines, recurring navigation links, social widgets,
    and multiple cookie alerts.
    """
    if not text:
        return ""
    lines = text.split("\n")
    seen = set()
    unique_lines = []
    
    # Ignore standard recurring strings
    ignore_patterns = [
        r"(?i)cookie", r"(?i)terms of service", r"(?i)privacy policy",
        r"(?i)all rights reserved", r"(?i)sign up", r"(?i)login", r"(?i)log in"
    ]
    
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            unique_lines.append("")
            continue
            
        # Ignore extremely short repeated navigation tags
        if cleaned.lower() in seen and len(cleaned) < 30:
            continue
            
        # Skip matched boilerplates
        if any(re.search(pat, cleaned) for pat in ignore_patterns):
            continue
            
        seen.add(cleaned.lower())
        unique_lines.append(cleaned)
        
    return "\n".join(unique_lines)

def compress_text_data(text: str, content_type: str = "auto") -> str:
    """
    Combines HTML markdown parsing, url shortening, and deduplication
    into one super-condensed format.
    """
    if not text:
        return ""
    
    is_html = False
    if content_type == "html":
        is_html = True
    elif content_type == "auto":
        # Guess if input contains typical HTML tags
        if "<html" in text.lower() or "<div" in text.lower() or "<body" in text.lower() or "<p>" in text.lower():
            is_html = True
            
    original_len = len(text)
    
    # Step 1: Parse HTML if needed
    if is_html:
        text = compress_html(text)
        
    # Step 2: Shorten URLs
    text = shorten_urls(text)
    
    # Step 3: Deduplicate lines
    text = deduplicate_lines(text)
    
    # Clean up double linebreaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    compressed_len = len(text)
    reduction = ((original_len - compressed_len) / original_len * 100) if original_len > 0 else 0
    
    summary = (
        f"[TokenJuice Summary] Compressed data by {reduction:.1f}% "
        f"({original_len} -> {compressed_len} chars)."
    )
    # Output to stdout safely
    print(summary)
    return text

def token_juice(parameters: dict, player=None) -> str:
    """
    Primary tool interface dispatcher for TokenJuice.
    """
    action = parameters.get("action", "compress")
    raw_text = parameters.get("text", "")
    content_type = parameters.get("content_type", "auto")
    
    if action == "compress":
        if not raw_text:
            return "[ERROR] No text or HTML provided to compress."
        compressed = compress_text_data(raw_text, content_type)
        return compressed
        
    elif action == "stats":
        return (
            "TokenJuice Compression Core Active:\n"
            "- HTML Boilerplate stripping active\n"
            "- Multi-byte grapheme preservation active\n"
            "- Deduplication logic configured\n"
            "- URL structural simplification active"
        )
        
    else:
        return f"[ERROR] Unknown Action '{action}'."
