# -*- coding: utf-8 -*-
"""生成英文成果概述用的两张图表（遵循 dataviz 参考调色板，light mode）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---- 参考调色板（light）----
SURFACE   = "#fcfcfb"
INK       = "#0b0b0b"
INK2      = "#52514e"
MUTED     = "#898781"
GRID      = "#e1e0d9"
BASELINE  = "#c3c2b7"
S1        = "#2a78d6"   # blue  slot 1
S2        = "#eb6834"   # orange slot 2
RED       = "#e34948"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 9,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

def style_ax(ax, ymax, ylabel):
    ax.set_ylim(0, ymax)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    for lbl in ax.get_xticklabels():
        lbl.set_color(INK2)

# ============ 图 1：基线对比（DeepSeek vs 论文 opus-4-6）============
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5))

panels = [
    ("Pointwise — macro-F1", [("Human-Only", 0.715, 0.806), ("Human+Generated", 0.791, 0.889)]),
    ("Pairwise — strict accuracy", [("Human-Only", 0.799, 0.825), ("Human+Generated", 0.597, 0.864)]),
]

for ax, (title, groups) in zip(axes, panels):
    labels = [g[0] for g in groups]
    ds  = [g[1] for g in groups]
    pap = [g[2] for g in groups]
    x = np.arange(len(labels))
    w = 0.34          # 细一点的条
    gap = 0.02        # 相邻条之间的表面留白

    b1 = ax.bar(x - w/2 - gap/2, ds,  w, label="DeepSeek (ours)", color=S1, zorder=3)
    b2 = ax.bar(x + w/2 + gap/2, pap, w, label="claude-opus-4-6 (paper)", color=S2, zorder=3)

    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width()/2, r.get_height() + 0.015,
                    f"{r.get_height():.3f}", ha="center", va="bottom",
                    fontsize=8, color=INK)

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_title(title, fontsize=10, color=INK, pad=8)
    style_ax(ax, 1.05, "")
    if ax is axes[0]:
        ax.set_ylabel("score", color=INK2, fontsize=9)

axes[0].legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK2)
fig.suptitle("Baseline: DeepSeek vs. the paper's strongest judge",
             fontsize=11.5, color=INK, y=1.0)
fig.tight_layout()
fig.savefig("figures_en/chart_baseline.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ============ 图 2：P3 / P4 消融（核心发现）============
fig, ax = plt.subplots(figsize=(6.6, 3.6))

prompts = ["Reference", "P3\n“which was judged novel?”",
           "P4\n“which is novel?”\n(below chance)"]
ds  = [0.597, 0.610, 0.409]
g54 = [0.779, 0.935, 0.409]

x = np.arange(len(prompts))
w = 0.34
gap = 0.02

b1 = ax.bar(x - w/2 - gap/2, ds,  w, label="DeepSeek (ours)",   color=S1, zorder=3)
b2 = ax.bar(x + w/2 + gap/2, g54, w, label="gpt-5.4 (paper)",   color=S2, zorder=3)

for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width()/2, r.get_height() + 0.02,
                f"{r.get_height():.3f}", ha="center", va="bottom",
                fontsize=8.5, color=INK)

# 随机基线
ax.axhline(0.5, color=RED, linewidth=1.6, linestyle=(0, (5, 3)), zorder=4)
ax.text(len(prompts) - 0.45, 0.508, "chance level (0.50)",
        color=RED, fontsize=8.5, ha="right", va="bottom")

# 标注 P4 跌破随机：直接把该组刻度标签标红，避免任何遮挡
ax.annotate("", xy=(1.80, 0.385), xytext=(1.55, 0.30),
            arrowprops=dict(arrowstyle="->", color=RED, linewidth=1.2,
                            connectionstyle="arc3,rad=-0.2"))

ax.set_xticks(x); ax.set_xticklabels(prompts, fontsize=9)
ax.get_xticklabels()[2].set_color(RED)   # P4 组标红：跌破随机线
style_ax(ax, 1.08, "Pairwise strict accuracy")
ax.set_title("Prompt rewording collapses the judge\n(Human+Generated, 154 pairs)",
             fontsize=10.5, color=INK, pad=10)
ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK2)
fig.tight_layout()
fig.savefig("figures_en/chart_p3p4.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("两张图已生成：figures_en/chart_baseline.png, figures_en/chart_p3p4.png")
