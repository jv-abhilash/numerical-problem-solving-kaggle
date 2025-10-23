# src/p2_routing/classification/classifier.py
"""
Classifier functions for routing questions to topics.
Provides classify_topic, assess_difficulty, and infer_tools functions.
"""
from __future__ import annotations
from typing import Tuple, Optional, List
import re

from src.storage.interfaces import Topic
from .rules import rule_route, normalize_topic


def classify_topic(stem: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    Classify the topic of a question stem.

    Args:
        stem: The question text

    Returns:
        Tuple of (topic, subtopic, confidence)
        - topic: One of "algebra", "calculus", "discrete", "geometry" or None
        - subtopic: More specific topic classification (e.g., "integration", "matrices")
        - confidence: Confidence score between 0 and 1
    """
    # Use rule-based routing
    topic = rule_route(stem)

    # Infer subtopic based on keywords
    stem_lower = stem.lower()
    subtopic = None
    confidence = 0.8  # Base confidence for rule-based classification

    # Calculus subtopics
    if topic == "calculus":
        if any(kw in stem_lower for kw in ["∫", "integral", "integrate", "area under"]):
            subtopic = "integration"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["derivative", "differentiat", "dy/dx", "tangent", "normal"]):
            subtopic = "differentiation"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["limit", "lim", "→", "approaches"]):
            subtopic = "limits"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["sin", "cos", "tan", "trig"]):
            subtopic = "trigonometry"
            confidence = 0.85
        else:
            subtopic = "calculus"
            confidence = 0.7

    # Discrete subtopics
    elif topic == "discrete":
        if any(kw in stem_lower for kw in ["probability", "prob", "die", "dice", "coin", "cards"]):
            subtopic = "probability"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["permutation", "arrangement", "order"]):
            subtopic = "permutations"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["combination", "selection", "choose", "committee"]):
            subtopic = "combinations"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["mean", "median", "variance", "std", "statistics"]):
            subtopic = "statistics"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["set", "∪", "∩", "domain", "range"]):
            subtopic = "sets"
            confidence = 0.85
        elif any(kw in stem_lower for kw in ["lpp", "linear programming", "maximize", "minimize"]):
            subtopic = "linear programming"
            confidence = 0.95
        else:
            subtopic = "discrete"
            confidence = 0.7

    # Geometry subtopics
    elif topic == "geometry":
        if any(kw in stem_lower for kw in ["circle", "radius", "diameter", "chord"]):
            subtopic = "circles"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["triangle", "angle", "side"]):
            subtopic = "triangles"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["parabola", "ellipse", "hyperbola", "conic"]):
            subtopic = "conic sections"
            confidence = 0.95
        elif any(kw in stem_lower for kw in ["line", "slope", "distance", "midpoint", "coordinate"]):
            subtopic = "coordinate geometry"
            confidence = 0.85
        else:
            subtopic = "geometry"
            confidence = 0.7

    # Algebra subtopics
    else:  # topic == "algebra"
        if any(kw in stem_lower for kw in ["matrix", "matrices", "determinant", "inverse"]):
            subtopic = "matrices"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["vector", "direction ratio", "direction cosine"]):
            subtopic = "vectors"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["complex", "imaginary", "i²", "modulus", "argument"]):
            subtopic = "complex numbers"
            confidence = 0.95
        elif any(kw in stem_lower for kw in ["inequality", "inequalities"]):
            subtopic = "inequalities"
            confidence = 0.9
        elif any(kw in stem_lower for kw in ["polynomial", "roots", "quadratic", "cubic"]):
            subtopic = "polynomials"
            confidence = 0.85
        elif any(kw in stem_lower for kw in ["sequence", "series", "ap", "gp", "progression"]):
            subtopic = "sequences and series"
            confidence = 0.9
        else:
            subtopic = "algebra"
            confidence = 0.7

    return topic, subtopic, confidence


def assess_difficulty(stem: str, opts: List[str]) -> str:
    """
    Assess the difficulty level of a question.

    Args:
        stem: The question text
        opts: List of answer options

    Returns:
        One of "E" (easy), "M" (medium), or "H" (hard)
    """
    stem_lower = stem.lower()

    # Hard indicators
    hard_indicators = [
        len(stem) > 300,  # Long questions tend to be harder
        "prove" in stem_lower,
        "derive" in stem_lower,
        "show that" in stem_lower,
        any(kw in stem_lower for kw in ["complex", "advanced", "difficult"]),
        stem_lower.count("∫") > 1,  # Multiple integrals
        stem_lower.count("limit") > 1,  # Multiple limits
        "system of equations" in stem_lower,
        len(opts) > 4,  # More options can indicate complexity
    ]

    # Easy indicators
    easy_indicators = [
        len(stem) < 100,  # Short questions tend to be easier
        "find" in stem_lower and "value" in stem_lower,
        "calculate" in stem_lower,
        "simple" in stem_lower,
        "basic" in stem_lower,
        stem_lower.count("=") == 1 and stem_lower.count("+") <= 2,  # Simple arithmetic
    ]

    hard_score = sum(hard_indicators)
    easy_score = sum(easy_indicators)

    if hard_score >= 3:
        return "H"
    elif easy_score >= 3:
        return "E"
    elif hard_score > easy_score:
        return "H"
    elif easy_score > hard_score:
        return "E"
    else:
        return "M"  # Default to medium


def infer_tools(stem: str) -> List[str]:
    """
    Infer what computational tools might be needed for a question.

    Args:
        stem: The question text

    Returns:
        List of tool names that might be needed (e.g., ["sympy", "numpy"])
    """
    stem_lower = stem.lower()
    tools = []

    # Check for symbolic computation needs
    if any(kw in stem_lower for kw in ["∫", "integral", "derivative", "limit", "solve", "equation"]):
        tools.append("sympy")

    # Check for numerical computation needs
    if any(kw in stem_lower for kw in ["matrix", "determinant", "eigenvalue", "vector"]):
        tools.append("numpy")

    # Check for plotting needs
    if any(kw in stem_lower for kw in ["plot", "graph", "sketch", "draw"]):
        tools.append("matplotlib")

    # Check for statistical computation
    if any(kw in stem_lower for kw in ["mean", "median", "variance", "standard deviation", "statistics"]):
        tools.append("statistics")

    return tools
