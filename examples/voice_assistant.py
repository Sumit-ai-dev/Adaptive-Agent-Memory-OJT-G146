"""
Example: Integrating AEMA AdaptiveMemory into a multi-user Voice AI Assistant.
Works on a local laptop with zero config (SQLite) and scales to Postgres pgvector.
"""

from aema import AdaptiveMemory


def respond_for_voice(user_id: str, user_transcript: str) -> str:
    mem = AdaptiveMemory(user_id=user_id)

    # 1. Recall user-isolated verified lessons before calling your LLM/TTS
    guidance = mem.format_for_prompt(user_transcript, top_k=3)
    system_prompt = (
        "You are a concise voice assistant. Answer clearly for speech synthesis.\n"
        + (f"\n{guidance}" if guidance else "")
    )
    return system_prompt


if __name__ == "__main__":
    # User A prefers brief spoken answers without markdown
    mem_a = AdaptiveMemory(user_id="speaker_abhay")
    lesson = mem_a.remember(
        task="Voice TTS reading markdown symbols aloud",
        strategy="Never output asterisks, backticks, or bullet points; use natural spoken sentences.",
        pitfall="Avoid URLs and code fences in voice responses.",
    )

    # User B has isolated memory — User A's preference does not leak to User B
    mem_b = AdaptiveMemory(user_id="speaker_sumit")
    assert mem_b.recall("Voice TTS markdown") == []

    print("Prompt injected for speaker_abhay:\n")
    print(respond_for_voice("speaker_abhay", "Explain how voice TTS should format responses"))

    # Simulate bad feedback -> auto-quarantined after 3 failures
    for _ in range(3):
        update = mem_a.feedback(lesson["id"], success=False)
    print("\nAfter 3 failures:", update)

