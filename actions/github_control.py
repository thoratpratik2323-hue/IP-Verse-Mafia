from github import Github
from actions.github_tool import get_github_token

def github_action(command: str, token: str = None, repo_name: str = "thoratpratik2323-hue/sat") -> str:
    """
    Executes GitHub actions (list issues, create issue, latest commit) using PyGithub.
    """
    if not token:
        token = get_github_token()
    if not token:
        return "Sir, please set up your 'github_token' in config/api_keys.json to run GitHub controls."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        command_clean = command.lower().strip()

        if "open issues" in command_clean or "list issues" in command_clean:
            issues = repo.get_issues(state="open")
            result = []
            # List top 5 open issues
            for i in list(issues)[:5]:
                result.append(f"#{i.number}: {i.title}")
            return "\n".join(result) if result else "Koi open issue nahi hai."

        elif "create issue" in command_clean:
            title = command_clean.split("create issue", 1)[-1].strip()
            if not title:
                return "Please specify the issue title, sir."
            issue = repo.create_issue(title=title)
            return f"Issue create ho gaya: #{issue.number} - {title}"

        elif "latest commit" in command_clean or "last commit" in command_clean:
            commits = repo.get_commits()
            if commits.totalCount > 0:
                commit = commits[0]
                msg = commit.commit.message.split('\n')[0]
                author = commit.commit.author.name
                return f"Last commit: '{msg}' by {author}."
            else:
                return "No commits found in this repository."

        return "GitHub command samajh nahi aaya."
    except Exception as e:
        print(f"[GitHub Control] Error: {e}")
        return f"Error executing GitHub command: {e}"
