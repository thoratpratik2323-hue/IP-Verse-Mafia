"""
actions/riven_agent.py -- Riven Movie Recommendation Engine using NLP & Cosine Similarity.
"""
import math
import re
import os
import json
from pathlib import Path

MOVIES_DB = Path(__file__).resolve().parent.parent / "config" / "riven_movies.json"

DEFAULT_MOVIES = [
    {
        "title": "The Dark Knight",
        "genres": "Action, Crime, Drama",
        "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice."
    },
    {
        "title": "Inception",
        "genres": "Action, Sci-Fi, Adventure",
        "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O."
    },
    {
        "title": "Interstellar",
        "genres": "Sci-Fi, Drama, Adventure",
        "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival on a dying Earth."
    },
    {
        "title": "The Matrix",
        "genres": "Action, Sci-Fi",
        "description": "When a beautiful stranger leads computer hacker Neo to a forbidding underworld, he discovers the shocking truth--the life he knows is the elaborate deception of an evil cyber-intelligence."
    },
    {
        "title": "Se7en",
        "genres": "Crime, Drama, Mystery",
        "description": "Two detectives, a rookie and a veteran, hunt a serial killer who uses the seven deadly sins as his motives."
    },
    {
        "title": "The Dark Knight Rises",
        "genres": "Action, Crime, Thriller",
        "description": "Eight years after the Joker's reign of anarchy, Batman, with the help of the mysterious Catwoman, is forced from his exile to save Gotham City from the brutal guerrilla terrorist Bane."
    },
    {
        "title": "Memento",
        "genres": "Mystery, Thriller",
        "description": "A man with short-term memory loss attempts to track down his wife's murderer."
    }
]

def load_movies() -> list:
    if not MOVIES_DB.exists():
        MOVIES_DB.parent.mkdir(parents=True, exist_ok=True)
        MOVIES_DB.write_text(json.dumps(DEFAULT_MOVIES, indent=4), encoding="utf-8")
        return DEFAULT_MOVIES
    try:
        return json.loads(MOVIES_DB.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_MOVIES

def save_movies(movies: list):
    try:
        MOVIES_DB.write_text(json.dumps(movies, indent=4), encoding="utf-8")
    except Exception:
        pass

def tokenize(text: str) -> list:
    return re.findall(r'[a-z0-9]+', text.lower())

def get_recommendations(target_title: str, movies: list, top_n: int = 3) -> list:
    target_lower = target_title.lower()
    target_movie = None
    for m in movies:
        if target_lower in m["title"].lower():
            target_movie = m
            break
            
    if not target_movie:
        return []
        
    docs = [tokenize(m["description"] + " " + m["genres"]) for m in movies]
    all_words = set(w for doc in docs for w in doc)
    
    idf = {}
    n_docs = len(movies)
    for word in all_words:
        n_containing = sum(1 for doc in docs if word in doc)
        idf[word] = math.log(n_docs / (1 + n_containing))
        
    vectors = []
    for doc in docs:
        tf = {}
        for word in doc:
            tf[word] = tf.get(word, 0) + 1
        vec = {}
        for word, count in tf.items():
            vec[word] = (count / len(doc)) * idf[word]
        vectors.append(vec)
        
    target_idx = movies.index(target_movie)
    target_vec = vectors[target_idx]
    
    def cosine_similarity(v1, v2):
        words = set(v1.keys()) & set(v2.keys())
        dot_product = sum(v1.get(w, 0) * v2.get(w, 0) for w in words)
        norm1 = math.sqrt(sum(val**2 for val in v1.values()))
        norm2 = math.sqrt(sum(val**2 for val in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)
        
    scores = []
    for i, m in enumerate(movies):
        if i == target_idx:
            continue
        sim = cosine_similarity(target_vec, vectors[i])
        scores.append((m, sim))
        
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]

def riven_recommend(
    action: str = "recommend",
    title: str | None = None,
    movie_details: dict | None = None,
    top_n: int = 3
) -> str:
    """Riven Movie Recommendation Action."""
    movies = load_movies()
    
    if action == "add" and movie_details:
        m_title = movie_details.get("title")
        m_genres = movie_details.get("genres", "Drama")
        m_desc = movie_details.get("description", "")
        
        if not m_title:
            return "Bhai, movie add karne ke liye 'title' parameters hona zaroori hai!"
            
        new_movie = {
            "title": m_title,
            "genres": m_genres,
            "description": m_desc
        }
        movies.append(new_movie)
        save_movies(movies)
        return f"✅ [Riven] Movie added successfully: '{m_title}' ({m_genres})!"
        
    if action == "recommend":
        if not title:
            return "Bhai, recommendation ke liye movie 'title' parameter hona zaroori hai!"
            
        recs = get_recommendations(title, movies, top_n)
        if not recs:
            # Try fuzzy matching using simple word overlap if exact match fails
            return f"Bhai, movie database me '{title}' nahi mili. Nayi movie add karne ko bolein!"
            
        formatted = []
        for rank, (m, score) in enumerate(recs, 1):
            formatted.append(
                f"{rank}. 🎬 **{m['title']}** (Similarity Score: {score:.2%})\n"
                f"   - **Genres:** {m['genres']}\n"
                f"   - *Overview:* {m['description']}"
            )
            
        return (
            f"🎬 **Riven Movie Recommendations for '{title}':**\n\n" +
            "\n\n".join(formatted)
        )
        
    return "Unknown action. Supported actions: 'recommend', 'add'."
