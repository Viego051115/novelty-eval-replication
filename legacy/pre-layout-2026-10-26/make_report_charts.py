# -*- coding: utf-8 -*-
"""生成复刻结果图表：图4a/4b 对比热力图 + 图13 生成器对比"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#898781"
GRID="#e1e0d9"; POS="#1baf7a"; NEG="#e34948"; NEUTRAL="#f0efec"

plt.rcParams.update({
    "font.family":"Microsoft YaHei", "font.sans-serif":["Microsoft YaHei","Segoe UI"], "axes.unicode_minus":False, "font.size":9,
    "figure.facecolor":SURFACE, "axes.facecolor":SURFACE, "savefig.facecolor":SURFACE,
})

# 红(负) - 中性 - 青(正) 的发散色图
CMAP = LinearSegmentedColormap.from_list("delta", [NEG, "#f5b5b4", NEUTRAL, "#8fd9bd", POS])

# ================= 数据 =================
# 我们的 DeepSeek 结果（相对参考的变化，百分点）
OURS_PW = {  # 图4b pairwise
 "Human-Only": {"P1":-2.6,"P2":-1.3,"P3":-3.2,"P4":-13.0,"P5":-7.8,"noagg":-5.9,"plan":-2.0},
 "Human+Generated": {"P1":-9.1,"P2":0.0,"P3":+0.6,"P4":-24.0,"P5":-16.2,"noagg":-3.9,"plan":-1.9},
}
PAPER_G54_PW = {
 "Human-Only": {"P1":-2.0,"P2":-0.7,"P3":+0.0,"P4":-7.2,"P5":-2.6,"noagg":-2.6,"plan":+0.0},
 "Human+Generated": {"P1":-9.7,"P2":+1.9,"P3":+15.6,"P4":-37.0,"P5":-18.2,"noagg":-3.9,"plan":+1.9},
}
PAPER_O46_PW = {
 "Human-Only": {"P1":-1.9,"P2":-1.3,"P3":-3.9,"P4":-24.7,"P5":-5.2,"noagg":-0.6,"plan":-1.9},
 "Human+Generated": {"P1":-5.8,"P2":-3.9,"P3":+13.6,"P4":-13.6,"P5":-7.8,"noagg":-2.6,"plan":-6.5},
}

OURS_PT = {  # 图4a pointwise
 "Human-Only": {"P1_pw":+5.3,"P2_pw":-0.1,"noagg":-2.4,"plan":-1.0},
 "Human+Generated": {"P1_pw":+4.9,"P2_pw":+2.0,"noagg":-4.2,"plan":-3.6},
}
PAPER_G54_PT = {
 "Human-Only": {"P1_pw":-6.0,"P2_pw":-1.2,"noagg":-3.0,"plan":+1.4},
 "Human+Generated": {"P1_pw":+6.9,"P2_pw":-5.9,"noagg":+1.3,"plan":-8.2},
}
PAPER_O46_PT = {
 "Human-Only": {"P1_pw":-6.7,"P2_pw":+0.7,"noagg":-2.3,"plan":-2.2},
 "Human+Generated": {"P1_pw":+0.4,"P2_pw":+3.6,"noagg":+1.3,"plan":+0.1},
}

LABEL_PW = {"P1":"P1 无护栏","P2":"P2 删判据","P3":"P3 被判新颖?","P4":"P4 哪个新颖?",
            "P5":"P5 更被判新颖?","noagg":"关闭聚合","plan":"计划格式"}
LABEL_PT = {"P1_pw":"P1 无护栏","P2_pw":"P2 删判据","noagg":"关闭聚合","plan":"计划格式"}

def draw_heatmap(ours, g54, o46, labels, title, outfile, vmax=40):
    rows = list(labels.keys())
    cols = ["DeepSeek\n(本次)", "gpt-5.4\n(论文)", "claude-opus-4-6\n(论文)"]
    settings = ["Human-Only", "Human+Generated"]

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 0.52*len(rows)+2.2), sharey=True)
    for ax, setting in zip(axes, settings):
        data = np.array([[ours[setting].get(r, np.nan) for r in rows],
                         [g54[setting].get(r, np.nan) for r in rows],
                         [o46[setting].get(r, np.nan) for r in rows]]).T
        ax.imshow(data, cmap=CMAP, vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(range(3)); ax.set_xticklabels(cols, fontsize=8.5, color=INK2)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([labels[r] for r in rows], fontsize=8.5, color=INK2)
        ax.set_title(setting, fontsize=10, color=INK, pad=8)
        ax.tick_params(length=0)
        for s in ax.spines.values(): s.set_visible(False)
        for i in range(len(rows)):
            for j in range(3):
                v = data[i, j]
                if np.isnan(v):
                    ax.text(j, i, "—", ha="center", va="center", fontsize=8.5, color=MUTED)
                else:
                    txt = f"{v:+.1f}"
                    strength = min(abs(v)/vmax, 1)
                    color = "white" if strength > 0.55 else INK
                    ax.text(j, i, txt, ha="center", va="center",
                            fontsize=8.5, color=color, fontweight="bold" if abs(v)>=20 else "normal")
        # 网格白线
        ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
        ax.grid(which="minor", color=SURFACE, linewidth=2)
    fig.suptitle(title, fontsize=12, color=INK, y=1.0)
    fig.text(0.01, -0.02, "数值 = 相对参考配置的变化（百分点）。红 = 性能下降，青 = 性能上升。",
             fontsize=8.2, color=MUTED)
    fig.tight_layout()
    fig.savefig(outfile, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", outfile)

draw_heatmap(OURS_PW, PAPER_G54_PW, PAPER_O46_PW, LABEL_PW,
             "图 4b 复刻：Pairwise 消融（DeepSeek vs 论文）",
             "figures_en/replica_fig4b.png", vmax=40)
draw_heatmap(OURS_PT, PAPER_G54_PT, PAPER_O46_PT, LABEL_PT,
             "图 4a 复刻：Pointwise 消融（DeepSeek vs 论文）",
             "figures_en/replica_fig4a.png", vmax=15)

# ================= 图 13 =================
gens = ["人类\n(Human-Only)", "gpt-5", "gpt-5.1", "gpt-5.4", "opus-4-5"]
vals = [81.2, 25.4, np.nan, np.nan, np.nan]
fig, ax = plt.subplots(figsize=(6.6, 3.4))
colors = [POS] + [NEG]*(len(gens)-1)
bars = ax.bar(range(len(gens)), [v if not np.isnan(v) else 0 for v in vals], 0.55,
              color=colors, zorder=3)
for i, v in enumerate(vals):
    if np.isnan(v):
        ax.text(i, 3, "待跑", ha="center", va="bottom", fontsize=8.5, color=MUTED)
    else:
        ax.text(i, v+1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=9, color=INK)
ax.axhline(50, color=NEG, linewidth=1.4, linestyle=(0,(5,3)), zorder=4)
ax.text(len(gens)-0.45, 51.5, "chance level (50%)", color=NEG, fontsize=8.5, ha="right")
ax.set_xticks(range(len(gens))); ax.set_xticklabels(gens, fontsize=8.5)
ax.set_ylim(0, 95); ax.set_ylabel("pairwise strict accuracy (%)", color=INK2, fontsize=9)
ax.set_title("图 13 复刻：换低新颖想法的生成器（DeepSeek 当评委）", fontsize=10.5, color=INK, pad=10)
ax.tick_params(colors=MUTED, length=0)
ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)
for s in ("top","right","left"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#c3c2b7")
fig.tight_layout()
fig.savefig("figures_en/replica_fig13.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("saved figures_en/replica_fig13.png")
