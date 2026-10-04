#!/usr/bin/env python3
"""
Telemetry Data Plotter and LaTeX Table Generator for IEEE/Scopus Research Paper.
Ingests JSONL telemetry from benchmarks/results/telemetry_latest.jsonl.
Generates:
  1. Pass@k Progression Curves across k in [1, 2, 3]
  2. Ablation Comparison Bar Chart (ERR, Token Economy, Quarantine Precision)
  3. Formatted IEEE LaTeX Table II snippet
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np

from benchmarks.metrics import compute_all_metrics, load_telemetry

# Set publication typography
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'Times'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9.5,
    'figure.titlesize': 13,
    'lines.linewidth': 2.0,
    'lines.markersize': 6,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
})


def plot_pass_progression(summary: Dict, output_path: str):
    """Plot Pass@k progression curves across k in {1, 2, 3} for each condition."""
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=300)
    
    conditions = ["vanilla", "naive_rag", "symmetric", "adaptive"]
    colors = {
        "vanilla": "#94A3B8",
        "naive_rag": "#EF4444",
        "symmetric": "#F59E0B",
        "adaptive": "#10B981",
    }
    labels = {
        "vanilla": "Vanilla ReAct (No Memory)",
        "naive_rag": "Naive Vector RAG",
        "symmetric": "Symmetric Reflexion",
        "adaptive": "Adaptive Memory (Ours)",
    }
    markers = {
        "vanilla": "o",
        "naive_rag": "s",
        "symmetric": "^",
        "adaptive": "D",
    }

    k_values = [1, 2, 3]

    for cond in conditions:
        if cond not in summary:
            continue
        pk_dict = summary[cond].get("pass_at_k", {})
        y_vals = [pk_dict.get(k, pk_dict.get(str(k), 0.0)) for k in k_values]
        
        ax.plot(
            k_values,
            y_vals,
            marker=markers[cond],
            color=colors[cond],
            label=labels[cond],
            linewidth=2.2,
            markersize=7,
        )

    ax.set_title("Pass@k Task Success Progression Across Repeated Trials", fontsize=11, fontweight="bold")
    ax.set_xlabel("Trial Budget (k)", fontsize=10)
    ax.set_ylabel("Pass@k Success Rate", fontsize=10)
    ax.set_xticks(k_values)
    ax.set_ylim(0.0, 1.05)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Saved Pass@k plot to: {output_path}")


def plot_ablation_metrics(summary: Dict, output_path: str):
    """Plot Error Recurrence Rate (ERR) and Token Economy (E_token) bar chart."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3.5), dpi=300)

    conditions = ["vanilla", "naive_rag", "symmetric", "adaptive"]
    cond_labels = ["Vanilla", "Naive RAG", "Symmetric", "Adaptive\n(Ours)"]
    palette = ["#94A3B8", "#EF4444", "#F59E0B", "#10B981"]

    err_vals = [summary.get(c, {}).get("error_recurrence", 0.0) for c in conditions]
    token_vals = [summary.get(c, {}).get("token_economy", 1.0) for c in conditions]

    # Subplot 1: Error Recurrence Rate (lower is better)
    bars1 = ax1.bar(cond_labels, err_vals, color=palette, width=0.55, edgecolor="#1E293B", linewidth=0.8)
    ax1.set_title("Error Recurrence Rate (ERR) ↓", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Recurrence Probability", fontsize=9)
    ax1.set_ylim(0.0, 1.0)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, yval + 0.02, f"{yval:.2f}", ha="center", va="bottom", fontsize=8)

    # Subplot 2: Token Economy Ratio (higher is better)
    bars2 = ax2.bar(cond_labels, token_vals, color=palette, width=0.55, edgecolor="#1E293B", linewidth=0.8)
    ax2.axhline(1.0, color="#64748B", linestyle=":", label="Baseline (Vanilla)")
    ax2.set_title("Token Economy Ratio (E_token) ↑", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Efficiency vs Baseline", fontsize=9)
    ax2.set_ylim(0.0, max(token_vals + [1.5]) * 1.25)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, yval + 0.04, f"{yval:.2f}x", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Saved Ablation plot to: {output_path}")


def generate_latex_table(summary: Dict, output_path: str):
    """Generate LaTeX snippet for Table II in the paper."""
    lines = [
        r"% Auto-generated Table II from empirical benchmark telemetry",
        r"\begin{table}[t]",
        r"\caption{Ablation Study Across Evaluation Benchmarks}",
        r"\label{tab:ablation_results}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"\textbf{Condition} & \textbf{Pass@1} & \textbf{Pass@3} & \textbf{ERR} $\downarrow$ & \textbf{$E_{\text{token}}$} $\uparrow$ & \textbf{$Q_{\text{prec}}$} $\uparrow$ \\",
        r"\midrule",
    ]

    labels = {
        "vanilla": "Vanilla ReAct (No Memory)",
        "naive_rag": "Naive Vector RAG",
        "symmetric": "Symmetric Reflexion",
        "adaptive": r"\textbf{Adaptive Memory (Ours)}",
    }

    for cond in ["vanilla", "naive_rag", "symmetric", "adaptive"]:
        if cond not in summary:
            continue
        m = summary[cond]
        pk = m.get("pass_at_k", {})
        p1 = pk.get(1, pk.get("1", 0.0))
        p3 = pk.get(3, pk.get("3", 0.0))
        err = m.get("error_recurrence", 0.0)
        tok = m.get("token_economy", 1.0)
        qprec = m.get("quarantine_prec", 0.0)

        row = (
            f"{labels[cond]} & "
            f"{p1:.3f} & "
            f"{p3:.3f} & "
            f"{err:.3f} & "
            f"{tok:.2f}$\\times$ & "
            f"{qprec:.3f} \\\\"
        )
        lines.append(row)

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    content = "\n".join(lines) + "\n"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved LaTeX Table snippet to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot telemetry metrics and generate LaTeX table")
    parser.add_argument(
        "--telemetry",
        default="benchmarks/results/telemetry_latest.jsonl",
        help="Path to telemetry JSONL",
    )
    args = parser.parse_args()

    if not os.path.exists(args.telemetry):
        print(f"Telemetry file not found at {args.telemetry}. Run benchmarks/run_all.py first.")
        return

    records = load_telemetry(args.telemetry)
    summary = compute_all_metrics(records, benchmark=None)

    plot_pass_progression(summary, "benchmarks/plots/fig4_pass_progression.png")
    plot_ablation_metrics(summary, "benchmarks/plots/fig3_ablation_results.png")
    generate_latex_table(summary, "paper/table2_generated.tex")


if __name__ == "__main__":
    main()
