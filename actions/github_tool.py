import logging
import requests
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
API_KEYS_PATH = CONFIG_DIR / "api_keys.json"

def get_github_token() -> str:
    if API_KEYS_PATH.exists():
        try:
            data = json.loads(API_KEYS_PATH.read_text(encoding="utf-8"))
            return data.get("github_token", "").strip()
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return ""

def github_tool(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list_prs").lower().strip()
    repo = parameters.get("repo", "").strip()
    title = parameters.get("title", "").strip()
    body = parameters.get("body", "").strip()
    
    if not repo:
        repo = "thoratpratik2323-hue/sat"
        
    token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Saturday-AI"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        
    if action == "list_prs":
        url = f"https://api.github.com/repos/{repo}/pulls"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                prs = res.json()
                if not prs:
                    return f"No open pull requests found for {repo}, sir."
                output = [f"### [GITHUB] Open Pull Requests in {repo}:\n"]
                for i, pr in enumerate(prs[:5], 1):
                    output.append(f"{i}. #{pr['number']} **{pr['title']}** by @{pr['user']['login']}\n   *URL*: {pr['html_url']}")
                return "\n".join(output)
            else:
                return f"Failed to fetch PRs: Status {res.status_code} ({res.text[:60]}), sir."
        except Exception as e:
            return f"Error connecting to GitHub: {e}, sir."
            
    elif action == "create_issue":
        if not token:
            return "Sir, I need a 'github_token' set up in config/api_keys.json to create repository issues."
        if not title:
            return "Please provide an issue title, sir."
            
        url = f"https://api.github.com/repos/{repo}/issues"
        payload = {"title": title, "body": body}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 201:
                issue = res.json()
                return f"Successfully created issue #{issue['number']} on {repo}: '{title}'\nLink: {issue['html_url']}, sir!"
            else:
                return f"Failed to create issue: Status {res.status_code} ({res.text[:60]}), sir."
        except Exception as e:
            return f"Error creating GitHub issue: {e}, sir."
            
    elif action in ("summarize_commits", "list_commits"):
        url = f"https://api.github.com/repos/{repo}/commits"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                commits = res.json()
                if not commits:
                    return f"No commits found for {repo}, sir."
                output = [f"### [GITHUB] Recent Commits in {repo}:\n"]
                for i, c in enumerate(commits[:10], 1):
                    msg = c['commit']['message'].split('\n')[0]
                    author = c['commit']['author']['name']
                    date_str = c['commit']['author']['date'][:10]
                    output.append(f"{i}. **{msg}** by {author} ({date_str})")
                return "\n".join(output)
            else:
                return f"Failed to fetch commits: Status {res.status_code} ({res.text[:60]}), sir."
        except Exception as e:
            return f"Error fetching commits: {e}, sir."
            
    else:
        return "Unknown GitHub tool action, sir."
