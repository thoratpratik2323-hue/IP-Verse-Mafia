"""
core/intent_router.py — Smart AI Intent Router for IP Prime.

Analyzes user queries to classify if they are coding-related, using a lightweight
classifier to improve accuracy.
"""

from __future__ import annotations

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import numpy as np

# Initialize structured logger
from core.logging_config import setup_logging
logger = setup_logging("ip_prime.intent_router")

# Training data (minimal set, can be expanded)
TRAINING_DATA = [
    ("write a function", 1), ("code this", 1), ("debug this error", 1),
    ("how do i loop", 1), ("python script", 1), ("sql query", 1),
    ("hello", 0), ("how are you", 0), ("what is the weather", 0),
    ("set a reminder", 0), ("open whatsapp", 0), ("good morning", 0)
]

X_train = [text for text, label in TRAINING_DATA]
y_train = [label for text, label in TRAINING_DATA]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(X_train)
classifier = LogisticRegression()
classifier.fit(X, y_train)

def is_coding_task(user_message: str) -> bool:
    """
    Determines if a user query is coding-related using a trained classifier.
    """
    if not user_message:
        return False
        
    # Predict
    features = vectorizer.transform([user_message.lower()])
    prediction = classifier.predict(features)[0]
    
    if prediction == 1:
        logger.info("[Router] Coding task detected for: '%s'", user_message[:30])
        return True

    logger.debug("[Router] General task detected for: '%s'", user_message[:30])
    return False
