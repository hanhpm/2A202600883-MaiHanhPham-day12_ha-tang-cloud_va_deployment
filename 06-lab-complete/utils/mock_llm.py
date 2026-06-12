"""Mock LLM used so the deployment lab runs without paid API keys."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI response. In production this would come from a real LLM provider.",
        "The agent is running correctly and received your question.",
        "Cloud deployment packages the agent so other users can call it reliably.",
    ],
    "docker": [
        "Docker packages the app and its dependencies into a repeatable container image."
    ],
    "deploy": [
        "Deployment moves the app from a local machine to a managed server or cloud platform."
    ],
    "health": [
        "The health endpoint confirms the process is alive and ready for platform checks."
    ],
}


def ask(question: str, delay: float = 0.05) -> str:
    time.sleep(delay + random.uniform(0, 0.02))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])
