import os
import sys
import subprocess
from pathlib import Path

# Database of the 20 premium Claude & MCP coding repositories from the Instagram guide
AWESOME_REPOS = [
    {
        "id": 1,
        "name": "Claude Code",
        "author": "anthropics",
        "url": "https://github.com/anthropics/claude-code",
        "description": "Anthropic's official agentic developer CLI. It allows Claude to interact directly with your local terminal, edit files, run git commands, run tests, and search your codebase autonomously.",
        "features": [
            "Agentic terminal control",
            "Local file modification and creation",
            "Git commits and diff tracking",
            "Fast, multi-file code editing"
        ]
    },
    {
        "id": 2,
        "name": "Claude Cookbooks",
        "author": "anthropics",
        "url": "https://github.com/anthropics/claude-cookbooks",
        "description": "Anthropic's official collection of code recipes, Jupyter notebooks, and integration guides showing advanced patterns using the Claude API.",
        "features": [
            "Prompt engineering guides",
            "Tool use (Function calling) recipes",
            "Retrieval-Augmented Generation (RAG) samples",
            "System prompt optimization models"
        ]
    },
    {
        "id": 3,
        "name": "Claude Quickstarts",
        "author": "anthropics",
        "url": "https://github.com/anthropics/claude-quickstarts",
        "description": "Official templates and boilerplate applications to get up and running with the Claude API using Python, Node.js, and browser frontends in minutes.",
        "features": [
            "Boilerplate code for Express/Flask",
            "Client-side API call examples",
            "Pre-configured Docker environments",
            "Standard API authentication setups"
        ]
    },
    {
        "id": 4,
        "name": "Claude Desktop Extensions",
        "author": "anthropics",
        "url": "https://github.com/anthropics/claude-desktop-extensions",
        "description": "A repository housing standard, official Model Context Protocol (MCP) server plugins designed for the Claude Desktop application to let it browse, search, and edit files.",
        "features": [
            "Browser tools integration",
            "Local filesystem search tools",
            "Developer environments setup",
            "Official MCP compliance testbeds"
        ]
    },
    {
        "id": 5,
        "name": "Awesome Claude Code",
        "author": "hesreallyhim",
        "url": "https://github.com/hesreallyhim/awesome-claude-code",
        "description": "A community-curated list of scripts, custom prompt configurations, extensions, and shell utilities designed to augment Anthropic's Claude Code CLI tool.",
        "features": [
            "Custom command aliases",
            "Developer utility bindings",
            "Community tips and performance guides",
            "Integration scripts for IDEs"
        ]
    },
    {
        "id": 6,
        "name": "Awesome MCP Servers",
        "author": "punkpeye",
        "url": "https://github.com/punkpeye/awesome-mcp-servers",
        "description": "A massive, community-maintained catalog of Model Context Protocol (MCP) servers, categorized by utility (Database, Search, APIs, DevTools) to expand any LLM client's abilities.",
        "features": [
            "Database connectors (PostgreSQL, SQLite, Redis)",
            "Web search and data scrapers",
            "External SaaS integrations (Github, Slack, Spotify)",
            "Step-by-step setup guides"
        ]
    },
    {
        "id": 7,
        "name": "SuperClaude Framework",
        "author": "SuperClaude-Org",
        "url": "https://github.com/SuperClaude-Org/SuperClaude_Framework",
        "description": "An open-source software framework engineered specifically to construct and orchestrate highly responsive, reliable multi-agent workflows powered by Claude models.",
        "features": [
            "Declarative agent definitions",
            "State machine-based task execution",
            "High token efficiency and caching rules",
            "Built-in conversation memory management"
        ]
    },
    {
        "id": 8,
        "name": "Claude Code Router",
        "author": "musistudio",
        "url": "https://github.com/musistudio/claude-code-router",
        "description": "An intelligent routing gateway designed to split developer commands between smaller fast models and premium reasoning models to minimize cost while retaining accuracy.",
        "features": [
            "Intent-based command routing",
            "Dynamic latency monitoring",
            "Gemini Flash/Haiku to Sonnet/Pro offloading",
            "Comprehensive token consumption statistics"
        ]
    },
    {
        "id": 9,
        "name": "Claude Task Master",
        "author": "eyaltoledano",
        "url": "https://github.com/eyaltoledano/claude-task-master",
        "description": "An autonomous agent executor that takes a high-level goal and uses Claude to plan, create tasks, edit files, and self-correct until the goal is fully accomplished.",
        "features": [
            "Hierarchical task decomposition",
            "Closed-loop error self-correction",
            "Full terminal execution environment",
            "Interactive progress reports"
        ]
    },
    {
        "id": 10,
        "name": "Claude Engineer",
        "author": "Doriandarko",
        "url": "https://github.com/Doriandarko/claude-engineer",
        "description": "A popular command-line coding assistant that turns Claude into an interactive software engineer, capable of working on directories, refactoring files, and tracking errors.",
        "features": [
            "Web search and file editing tools",
            "Automated package installation",
            "Terminal execution output analysis",
            "High developer user rating"
        ]
    },
    {
        "id": 11,
        "name": "Claude Swarm",
        "author": "parallaxsys",
        "url": "https://github.com/parallaxsys/claude-swarm",
        "description": "An agentic swarm framework modeled after biological networks, allowing hundreds of specialized Claude agents to communicate, coordinate, and execute massive software tasks.",
        "features": [
            "Asynchronous communication channels",
            "Consensus-based decision loops",
            "Conflict resolution mechanisms",
            "Horizontal scaling properties"
        ]
    },
    {
        "id": 12,
        "name": "Claude Dev Tools",
        "author": "zebbern",
        "url": "https://github.com/zebbern/claude-dev-tools",
        "description": "A repository filled with browser extensions and local script configurations that bridge Claude's web UI directly to local IDE filesystems and developer consoles.",
        "features": [
            "One-click browser-to-IDE code copying",
            "Web console log scrapers",
            "Automated system state reporting",
            "Fast chrome extensions"
        ]
    },
    {
        "id": 13,
        "name": "MCP Compass",
        "author": "liuyoshio",
        "url": "https://github.com/liuyoshio/mcp-compass",
        "description": "A highly useful registry indexer and discovery system designed to locate, verify, and document active Model Context Protocol servers across GitHub.",
        "features": [
            "Automatic github repository crawling",
            "MCP version compliance validation",
            "Standardized schema visualization",
            "Command-line setup automation"
        ]
    },
    {
        "id": 14,
        "name": "MCP Installer",
        "author": "anaisbetts",
        "url": "https://github.com/anaisbetts/mcp-installer",
        "description": "An intuitive, automated desktop tool designed to install, manage, and configure new Model Context Protocol servers inside your Claude Desktop configuration in one click.",
        "features": [
            "GUI/CLI server installer",
            "Auto-updates `claude_desktop_config.json`",
            "Environment variable validator",
            "Connection diagnostic tool"
        ]
    },
    {
        "id": 15,
        "name": "MCPHub",
        "author": "idosal",
        "url": "https://github.com/idosal/mcphub",
        "description": "An open-source centralized hub and package marketplace designed to register, rank, and download MCP plugins and servers easily.",
        "features": [
            "Central marketplace architecture",
            "User reviews and rating charts",
            "Easy package configuration templates",
            "Docker-based server launching support"
        ]
    },
    {
        "id": 16,
        "name": "Continue",
        "author": "continuedev",
        "url": "https://github.com/continuedev/continue",
        "description": "The absolute leading open-source IDE extension for VS Code and JetBrains. Connects your codebase locally to any LLM API (Gemini, Claude, Ollama) for code completions and chat.",
        "features": [
            "Tab autocomplete based on local context",
            "Code explanation and refactoring side panel",
            "Custom command extensions via `.continuerc`",
            "Fully open-source and customizable"
        ]
    },
    {
        "id": 17,
        "name": "Cline",
        "author": "cline",
        "url": "https://github.com/cline/cline",
        "description": "An autonomous coding assistant that runs inside VS Code, using command execution, file modification, web search, and MCP tools directly to edit and test software.",
        "features": [
            "Direct terminal read/write execution",
            "Web search and browser inspection",
            "Clean diff-based file writing",
            "Full developer approval gate"
        ]
    },
    {
        "id": 18,
        "name": "Open Interpreter",
        "author": "OpenInterpreter",
        "url": "https://github.com/OpenInterpreter/open-interpreter",
        "description": "A highly capable open-source tool that executes natural language instructions by generating and running Python, JS, and Shell scripts locally in your terminal.",
        "features": [
            "Interactive system command runner",
            "Handles file sorting, media conversion, and automation",
            "Sandboxed Docker mode support",
            "Voice control module bindings"
        ]
    },
    {
        "id": 19,
        "name": "Aider AI",
        "author": "Aider-AI",
        "url": "https://github.com/Aider-AI/aider",
        "description": "The gold-standard git-based CLI assistant. Perfect for editing multiple files simultaneously, tracking edits with automated git commits, and using advanced reasoning models.",
        "features": [
            "Git commit-on-success architecture",
            "Multi-file repository map builder",
            "Interactive and batch modes",
            "Native Gemini, Anthropic, OpenAI API support"
        ]
    },
    {
        "id": 20,
        "name": "OpenDevin",
        "author": "OpenDevin",
        "url": "https://github.com/OpenDevin/OpenDevin",
        "description": "An open-source agent platform striving to build an autonomous software engineer that collaborates with users to build complete features and compile software projects.",
        "features": [
            "Web-based dashboard interface",
            "Docker-isolated terminal execution environment",
            "Hierarchical agent models",
            "Multi-language software engineering"
        ]
    }
]

def get_awesome_repo_info(query: str = None) -> str:
    """Retrieves beautifully formatted information or a listing of the 20 Claude/MCP repositories."""
    if not query or query.strip().lower() in ("list", "all", "show", "help"):
        res = [
            "## 🌟 20 Claude & MCP GitHub Repos That Can Completely Change Your Life\n",
            "Here is the premium catalog of essential agentic and developer tools from your Instagram guide:\n"
        ]
        for r in AWESOME_REPOS:
            res.append(f"**{r['id']}. {r['name']}** by *{r['author']}*")
            res.append(f"- 🔗 GitHub: {r['url']}")
            res.append(f"- 💡 {r['description']}")
            res.append("")
        return "\n".join(res)

    q = query.strip().lower()
    
    # Try finding an exact match by index or ID
    matching = None
    if q.isdigit():
        idx = int(q)
        for r in AWESOME_REPOS:
            if r["id"] == idx:
                matching = r
                break
    
    # Soft text search
    if not matching:
        for r in AWESOME_REPOS:
            if q in r["name"].lower() or q in r["description"].lower() or q in r["author"].lower():
                matching = r
                break

    if not matching:
        return f"I couldn't find a repository in the list of 20 matching '{query}'. Try asking for a specific name like 'Aider AI', 'Cline', or 'Open Interpreter'."

    res = [
        f"### 📦 Repository Info: **{matching['name']}**",
        f"- **GitHub Link**: {matching['url']}",
        f"- **Author**: {matching['author']}",
        f"- **Index No.**: {matching['id']}/20",
        "",
        f"**Description**:\n{matching['description']}",
        "",
        "**Key Features**:"
    ]
    for feat in matching["features"]:
        res.append(f"- {feat}")
        
    res.append("\n*To clone this repository to your active workspace, say: 'clone repo " + matching['name'] + "'*")
    return "\n".join(res)

def clone_awesome_repo(repo_name: str, dest_dir: str = None) -> str:
    """Clones one of the 20 premium repositories directly to the system workspace for exploration."""
    q = repo_name.strip().lower()
    
    matching = None
    if q.isdigit():
        idx = int(q)
        for r in AWESOME_REPOS:
            if r["id"] == idx:
                matching = r
                break
                
    if not matching:
        for r in AWESOME_REPOS:
            if q in r["name"].lower():
                matching = r
                break

    if not matching:
        return f"Error: Repository '{repo_name}' is not in the recognized list of 20 premium resources."

    # Prepare destination directory path
    base_dir = Path(__file__).resolve().parent.parent
    if not dest_dir:
        # Clone into a subfolder 'awesome_repos/<repo_name>' inside the active IP Prime workspace
        dest_path = base_dir / "awesome_repos" / matching["name"].lower().replace(" ", "_")
    else:
        dest_path = Path(dest_dir) / matching["name"].lower().replace(" ", "_")

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and any(dest_path.iterdir()):
        return f"### ⚠️ Directory Already Exists\nThe target folder is already populated:\n📂 `{dest_path.resolve()}`"

    print(f"[Repo Cloner] Cloning {matching['name']} from {matching['url']} to {dest_path}...")
    try:
        # Check if git is on system PATH
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except Exception:
        return "Error: Git is not installed or not available on the system PATH. Please install Git to clone repositories."

    try:
        cmd = ["git", "clone", matching["url"], str(dest_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return (
                f"### ✅ Repository Cloned Successfully!\n"
                f"- **Project**: `{matching['name']}`\n"
                f"- **GitHub URL**: {matching['url']}\n"
                f"- **Local Path**: `{dest_path.resolve()}`\n\n"
                f"You can now explore, read, or configure this tool inside your active workspace."
            )
        else:
            return f"Error cloning repository: {result.stderr or 'Unknown git failure.'}"
            
    except Exception as e:
        return f"Exception occurred while cloning repository: {e}"
