import os
import urllib.parse
import xml.etree.ElementTree as ET

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    import wikipedia
    _WIKI_OK = True
except ImportError:
    _WIKI_OK = False

def fetch_realtime_knowledge(query):
    """
    Fetch recent real-time news/information using Tavily API (if TAVILY_API_KEY configured)
    or fallback to Google News RSS + Wikipedia lookup.
    """
    print(f"[REAL-TIME SEARCH] Querying: '{query}'")
    
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if tavily_api_key and _REQUESTS_OK:
        print("[REAL-TIME SEARCH] Tavily API key detected. Running Tavily query...")
        try:
            search_depth = "advanced" if any(w in query.lower() for w in ["deep", "advanced", "details", "explain", "in-depth", "depth"]) else "basic"
            headers = {"Content-Type": "application/json"}
            payload = {
                "api_key": tavily_api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": True,
                "max_results": 5
            }
            r = requests.post("https://api.tavily.com/search", json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                answer = data.get("answer")
                
                parsed_results = []
                if answer:
                    parsed_results.append(f"**Direct Answer:** {answer}\n")
                
                for res in results[:4]:
                    title = res.get("title", "News")
                    url = res.get("url", "")
                    content = res.get("content", "")
                    parsed_results.append(f"- **{title}** ({url}): {content}")
                
                print(f"[REAL-TIME SEARCH] Tavily search success ({search_depth} depth).")
                return "\n".join(parsed_results)
        except Exception as e:
            print(f"[REAL-TIME SEARCH ERR] Tavily query failed: {e}. Falling back to standard engines...")

    # Clean the query for Hinglish and common words
    cleaned_query = query.lower()
    for word in ["prime", "jarvis", "assistant", "please", "batao", "bata", "tell me", "show me", "search for", "find out", "do you know", "who is", "what is", "tell me about", "kya hai", "kaisa tha", "kab tha", "kese tha", "tha", "hai", "ka", "ke", "ki", "ko", "se", "ne"]:
        cleaned_query = cleaned_query.replace(word, " ")
    
    words = [w.strip() for w in cleaned_query.split() if w.strip()]
    search_term = " ".join(words)
    if not search_term:
        search_term = query
        
    print(f"[REAL-TIME SEARCH] Refined search query: '{search_term}'")
    
    # Try fetching Google News RSS
    if _REQUESTS_OK:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_term)}&hl=en-IN&gl=IN&ceid=IN:en"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=5, verify=False)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                items = root.findall('.//item')
                if items:
                    parsed_results = []
                    for item in items[:4]:
                        title = item.find('title').text if item.find('title') is not None else ""
                        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                        parsed_results.append(f"- **{title}** (Published: {pub_date})")
                    print(f"[REAL-TIME SEARCH] Successfully fetched {len(parsed_results)} results.")
                    return "\n".join(parsed_results)
        except Exception as e:
            print(f"[REAL-TIME SEARCH ERR] Google News fetch failed: {e}")
        
    # Wikipedia Fallback
    if _WIKI_OK:
        print(f"[REAL-TIME SEARCH] Falling back to Wikipedia...")
        try:
            wiki_res = wikipedia.summary(search_term, sentences=2)
            print(f"[REAL-TIME SEARCH] Wikipedia fallback success.")
            return f"- Wikipedia summary for '{search_term}': {wiki_res}"
        except Exception as wiki_err:
            print(f"[REAL-TIME SEARCH ERR] Wikipedia fallback also failed: {wiki_err}")
        
    return f"I couldn't fetch real-time information for '{query}' at the moment, Sir."
