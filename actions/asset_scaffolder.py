"""
asset_scaffolder.py — Visual Asset Scaffolder for extracting styling parameters and generating layouts.
"""

from actions.prime_utils import UnifiedModelClient

def asset_scaffolder(parameters: dict, player=None) -> str:
    """
    Generates CSS layout templates or extracts styling parameters from input designs.
    """
    action = parameters.get("action", "generate_layout")
    target = parameters.get("target", "")
    
    if not target:
        return "Please provide 'target' prompt/content parameter, sir."

    def log(msg: str):
        print(f"[Asset Scaffolder] {msg}")
        if player:
            player.write_log(f"[Asset Scaffolder] {msg}")

    client = UnifiedModelClient()

    log(f"Running asset scaffolder action '{action}' on: \"{target[:60]}...\"")
    
    try:
        if action == "generate_layout":
            prompt = (
                f"Create a beautiful HTML/CSS layout design based on the target specification.\n"
                f"Specification: {target}\n\n"
                f"Return only the complete single-file HTML code with embedded CSS style definitions."
            )
        elif action == "extract_styling":
            prompt = (
                f"Analyze the following HTML/CSS code and extract design tokens (colors, font parameters, margin styles, layouts).\n"
                f"Code:\n{target}\n\n"
                f"Return a structured markdown list of all extracted visual styles."
            )
        else:
            return f"Invalid action: '{action}'"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
        
    except Exception as e:
        return f"Asset scaffolding failed: {e}"
