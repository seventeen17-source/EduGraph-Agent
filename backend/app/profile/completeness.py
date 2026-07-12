from app.profile.schemas import StudentProfile


def compute_completeness(profile: StudentProfile) -> float:
    weights = {
        "background": 0.20,
        "learning_goal": 0.20,
        "knowledge_base": 0.20,
        "cognitive_style": 0.10,
        "preferences": 0.10,
        "weak_points": 0.08,
        "ability_state": 0.07,
        "progress": 0.05,
    }
    scores = {
        "background": 1.0 if profile.background.major and profile.background.grade else 0.0,
        "learning_goal": 1.0 if profile.learning_goal.goal_type or profile.learning_goal.description else 0.0,
        "knowledge_base": 1.0
        if profile.node_mastery
        else 0.5
        if profile.knowledge_base.known_topics
        else 0.3
        if profile.knowledge_base.unknown_topics
        else 0.0,
        "cognitive_style": 1.0 if profile.cognitive_style.primary else 0.0,
        "preferences": 1.0 if profile.preferences.resource_ranking else 0.0,
        "weak_points": 1.0
        if profile.weak_points.self_reported or profile.weak_points.diagnosed
        else 0.0,
        "ability_state": 0.5,
        "progress": profile.progress.completion_rate,
    }
    return round(sum(weights[key] * scores[key] for key in weights), 4)


def missing_dimensions(profile: StudentProfile) -> list[str]:
    missing: list[str] = []
    if not profile.background.major or not profile.background.grade:
        missing.append("background")
    if not profile.learning_goal.goal_type and not profile.learning_goal.description:
        missing.append("learning_goal")
    if not profile.knowledge_base.known_topics and not profile.knowledge_base.unknown_topics and not profile.node_mastery:
        missing.append("knowledge_base")
    if not profile.cognitive_style.primary:
        missing.append("cognitive_style")
    if not profile.preferences.resource_ranking:
        missing.append("preferences")
    return missing
