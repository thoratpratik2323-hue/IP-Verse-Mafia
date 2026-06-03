from google import genai

def get_dsa_hints(problem_text: str, callback=None) -> str:
    """Queries Gemini to generate 3 progressive hints and complexity targets for a DSA problem."""
    if not problem_text or problem_text.isspace():
        return "Problem statement is empty, sir."
        
    try:
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
        
        prompt = (
            f"You are a friendly DSA mentor. Analyze this programming problem statement. "
            f"Generate: \n"
            f"1. Problem Classification/Tags (e.g. Graph, Dynamic Programming, Two Pointers)\n"
            f"2. Hint 1: Intuition & General Approach\n"
            f"3. Hint 2: Core Algorithm/Pseudocode pattern (NO direct code, only logical steps)\n"
            f"4. Hint 3: Edge cases, dry run explanation or complexity boundaries\n\n"
            f"CRITICAL: Do NOT give direct executable code solution (no C++, Python, Java code)! "
            f"Give the advice in a structured, friendly Hinglish buddy tone.\n\n"
            f"Problem statement:\n{problem_text}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        res_text = response.text.strip()
        if callback:
            callback(res_text)
        return res_text
    except Exception as e:
        err_msg = f"Failed to get DSA hints: {e}"
        if callback:
            callback(err_msg)
        return err_msg

def dsa_helper(parameters: dict, player=None) -> str:
    """Dispatcher for DSA Helper action."""
    problem = parameters.get("problem", "")
    return get_dsa_hints(problem)
