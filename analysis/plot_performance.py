#!/usr/bin/env python3
"""
Performance Comparison Plot

Plots average time per hash across all attack configurations.

Usage:
    python analysis/plot_performance.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Data ──────────────────────────────────────────────────────────────────────
configs = [
    "DEGA\n8-qubit",
    "DEGA\n10-qubit",
    "Classical\n(Bloom)",
    "Classical\n(No Bloom)",
    "Grover\n8-qubit",
    "DEGA\n12-qubit",
    "DEGA\n14-qubit",
    "DEGA\n16-qubit",
    "Grover\n10-qubit",
]

avg_times = [
    0.449,   # DEGA 8q
    0.453,   # DEGA 10q
    0.495,   # Classical Bloom
    0.499,   # Classical No Bloom
    0.632,   # Grover 8q
    0.645,   # DEGA 12q
    0.797,   # DEGA 14q
    1.178,   # DEGA 16q
    1.669,   # Grover 10q
]

# Colour groups
colors = [
    "#2196F3",  # DEGA 8q
    "#42A5F5",  # DEGA 10q
    "#4CAF50",  # Classical Bloom
    "#A5D6A7",  # Classical No Bloom
    "#FF9800",  # Grover 8q
    "#90CAF9",  # DEGA 12q
    "#BBDEFB",  # DEGA 14q
    "#E3F2FD",  # DEGA 16q
    "#FFB74D",  # Grover 10q
]

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15, 7))

x = np.arange(len(configs))
bars = ax.bar(x, avg_times, color=colors, edgecolor="white", linewidth=0.8, width=0.6)

# Value labels on bars
for bar, val in zip(bars, avg_times):
    label = f"{val:.3f}s"
    y_pos = bar.get_height() + 0.02
    ax.text(bar.get_x() + bar.get_width() / 2, y_pos, label,
            ha="center", va="bottom", fontsize=12, fontweight="bold")

# Axes
ax.set_xticks(x)
ax.set_xticklabels(configs, fontsize=13)
ax.set_ylabel("Average Time per Hash (seconds)", fontsize=14)
ax.set_title("Attack Performance Comparison — Average Time per Hash\n(100 hashes: 60 covered + 40 uncovered)",
             fontsize=15, fontweight="bold", pad=16)
ax.set_ylim(0, max(avg_times) * 1.15)
ax.yaxis.grid(True, linestyle="--", alpha=0.5)
ax.tick_params(axis='y', labelsize=12)
ax.set_axisbelow(True)

# Legend
legend_handles = [
    mpatches.Patch(color="#2196F3", label="DEGA (Quantum)"),
    mpatches.Patch(color="#FF9800", label="Standard Grover (Quantum)"),
    mpatches.Patch(color="#4CAF50", label="Classical"),
]
ax.legend(handles=legend_handles, loc="upper left", fontsize=13)

plt.tight_layout()
plt.savefig("analysis/performance_comparison.svg", format="svg", bbox_inches="tight")
print("[+] Saved: analysis/performance_comparison.svg")
plt.show()
