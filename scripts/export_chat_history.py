#!/usr/bin/env python3
"""
Chat Transcript Exporter
Converts the internal Antigravity IDE JSONL conversation log into a clean,
readable Markdown document.

Usage:
  python3 scripts/export_chat_history.py --output chat_transcript.md
"""

import argparse
import json
import re
from pathlib import Path

TRANSCRIPT_PATH = Path("/Users/sumitdas/.gemini/antigravity-ide/brain/910066c4-de66-46bd-97c5-bf14b9972be9/.system_generated/logs/transcript.jsonl")


def clean_user_content(raw: str) -> str:
    """Extract clean user request text from raw metadata tags."""
    match = re.search(r'<USER_REQUEST>(.*?)</USER_REQUEST>', raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Check if system message
    if "<SYSTEM_MESSAGE>" in raw:
        return ""
    return raw.strip()


def export_transcript(source_file: Path, output_file: Path, include_tools: bool = False):
    if not source_file.exists():
        print(f"Error: Transcript file not found at {source_file}")
        return

    exported_turns = 0
    with open(source_file, "r", encoding="utf-8") as f_in, open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write("# Antigravity IDE Conversation Export\n")
        f_out.write(f"**Conversation ID**: `910066c4-de66-46bd-97c5-bf14b9972be9`  \n")
        f_out.write(f"**Export Source**: `{source_file.name}`  \n\n---\n\n")

        current_speaker = None
        turn_index = 1

        for line in f_in:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            content = entry.get("content", "")

            if entry_type == "USER_INPUT":
                user_text = clean_user_content(content)
                if user_text:
                    f_out.write(f"\n### Turn {turn_index} - User\n\n{user_text}\n\n")
                    current_speaker = "USER"
                    turn_index += 1

            elif entry_type == "PLANNER_RESPONSE":
                # Text reply from model
                if content and content.strip():
                    f_out.write(f"### Assistant\n\n{content.strip()}\n\n---\n\n")
                    exported_turns += 1

                # Optional tool calls inspection
                if include_tools:
                    tool_calls = entry.get("tool_calls", [])
                    if tool_calls:
                        f_out.write("<details><summary>Tool Executions</summary>\n\n")
                        for tc in tool_calls:
                            fn_name = tc.get("function", {}).get("name", "tool")
                            f_out.write(f"- `{fn_name}`\n")
                        f_out.write("\n</details>\n\n")

    print(f"Successfully exported conversation to: {output_file}")
    print(f"Total turns exported: {exported_turns}")


def main():
    parser = argparse.ArgumentParser(description="Export chat history to clean Markdown.")
    parser.add_argument(
        "--source",
        type=Path,
        default=TRANSCRIPT_PATH,
        help="Path to transcript.jsonl log file"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("chat_transcript.md"),
        help="Output Markdown file path (default: chat_transcript.md)"
    )
    parser.add_argument(
        "--include-tools",
        action="store_true",
        help="Include details of tool invocations in output"
    )

    args = parser.parse_args()
    export_transcript(args.source, args.output, args.include_tools)


if __name__ == "__main__":
    main()
