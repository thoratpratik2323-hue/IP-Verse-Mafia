try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 3) -> str:
    """
    Performs a DuckDuckGo web search and returns formatted snippets.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # text query
            for r in ddgs.text(query, max_results=max_results):
                title = r.get('title', 'No Title')
                body = r.get('body', r.get('snippet', ''))
                results.append(f"- {title}: {body}")
    except Exception as e:
        print(f"[Web Search] Error querying DuckDuckGo: {e}")
        return f"Error performing web search: {e}"
    
    if not results:
        return "Koi result nahi mila."
    
    return "\n".join(results)
