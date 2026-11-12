"""
Example: Wrapping any OpenAI-compatible chat loop (OpenAI, Groq, Ollama, Gemini)
with AEMA reliability-aware memory.
"""

import os
from aema import AdaptiveMemory


def run_turn(user_query: str, user_id: str = "default_user") -> None:
    mem = AdaptiveMemory(user_id=user_id)
    hits = mem.recall(user_query, domain="coding", top_k=3)

    context_block = mem.format_for_prompt(user_query, domain="coding", top_k=3)
    print(f"Retrieved {len(hits)} verified memories.")
    if context_block:
        print(context_block)

    # If openai is configured, inject `context_block` into system message:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": context_block or "You are a helpful coding assistant."},
                {"role": "user", "content": user_query},
            ],
        )
        print("\nModel Response:\n", resp.choices[0].message.content)


if __name__ == "__main__":
    mem = AdaptiveMemory(user_id="dev_1")
    mem.remember(
        task="Async SQLite database locked error",
        strategy="Enable WAL mode (`PRAGMA journal_mode=WAL`) and set `busy_timeout=30000`.",
        pitfall="Do not share one unpooled write transaction across concurrent async workers.",
        domain="coding",
    )
    run_turn("How do I fix SQLite locked error in Python async workers?", user_id="dev_1")

