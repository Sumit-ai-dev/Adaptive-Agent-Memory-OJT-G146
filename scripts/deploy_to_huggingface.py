"""
Automated Deployment Script for Hugging Face Assets.
Author: Sumit Das (arXiv Pre-print 2026)
Uploads the Agent Memory Resilience Benchmark Dataset and Interactive Gradio Space
to Hugging Face Hub using the official huggingface_hub Python SDK.
Zero emojis, strict type safety, idempotent repository synchronization.
"""

import argparse
import os
from pathlib import Path
import sys
from typing import Optional

from dotenv import load_dotenv
from huggingface_hub import HfApi, login


def get_token(cli_token: Optional[str] = None) -> str:
    # 1. CLI explicit token
    if cli_token and cli_token.strip():
        return cli_token.strip()

    # 2. Local .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    env_token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    # 3. Cached token
    token_cache = Path.home() / ".cache" / "huggingface" / "token"
    if token_cache.exists():
        cached = token_cache.read_text().strip()
        if cached:
            return cached

    raise ValueError(
        "No Hugging Face token found. Please provide --token or set HUGGINGFACE_TOKEN in .env."
    )


def deploy_assets(token: str, deploy_dataset: bool = True, deploy_space: bool = True) -> None:
    api = HfApi(token=token)
    user_info = api.whoami()
    username = user_info.get("name")
    print(f"Authenticated as Hugging Face user: {username} ({user_info.get('email', 'No email')})")

    root_dir = Path(__file__).resolve().parent.parent

    # 1. Deploy Benchmark Dataset
    if deploy_dataset:
        dataset_repo_id = f"{username}/agent-memory-resilience-benchmark"
        dataset_folder = root_dir / "hf_dataset"

        if not dataset_folder.exists():
            raise FileNotFoundError(f"Dataset folder not found at: {dataset_folder}")

        print(f"\n[1/2] Creating/Synchronizing Dataset Repository: {dataset_repo_id}...")
        api.create_repo(
            repo_id=dataset_repo_id,
            repo_type="dataset",
            private=False,
            exist_ok=True,
        )

        print(f"Uploading files from {dataset_folder} to {dataset_repo_id}...")
        api.upload_folder(
            folder_path=str(dataset_folder),
            repo_id=dataset_repo_id,
            repo_type="dataset",
            commit_message="Deploy Agent Memory Resilience & Poisoning Benchmark",
        )
        dataset_url = f"https://huggingface.co/datasets/{dataset_repo_id}"
        print(f"Dataset successfully deployed: {dataset_url}")

    # 2. Deploy Interactive Space
    if deploy_space:
        space_repo_id = f"{username}/adaptive-agent-memory-playground"
        space_folder = root_dir / "hf_space"

        if not space_folder.exists():
            raise FileNotFoundError(f"Space folder not found at: {space_folder}")

        print(f"\n[2/2] Creating/Synchronizing Space Repository: {space_repo_id}...")
        api.create_repo(
            repo_id=space_repo_id,
            repo_type="space",
            space_sdk="static",
            private=False,
            exist_ok=True,
        )

        print(f"Uploading files from {space_folder} to {space_repo_id}...")
        api.upload_folder(
            folder_path=str(space_folder),
            repo_id=space_repo_id,
            repo_type="space",
            commit_message="Deploy Adaptive Agent Memory Resilience Research Playground",
        )
        space_url = f"https://huggingface.co/spaces/{space_repo_id}"
        print(f"Space successfully deployed: {space_url}")

    print("\nAll Hugging Face assets synchronized successfully.")
    print(f"Profile URL: https://huggingface.co/{username}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Agent Memory benchmark and demo to Hugging Face Hub.")
    parser.add_argument("--token", type=str, default=None, help="Hugging Face User Access Token (Write scope).")
    parser.add_argument("--skip-dataset", action="store_true", help="Skip dataset deployment.")
    parser.add_argument("--skip-space", action="store_true", help="Skip space deployment.")

    args = parser.parse_args()

    try:
        token = get_token(args.token)
        deploy_assets(
            token=token,
            deploy_dataset=not args.skip_dataset,
            deploy_space=not args.skip_space,
        )
    except Exception as e:
        print(f"Deployment failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
