from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from matplotlib.lines import Line2D


# -------------------------------------------------------------
# 1.軸のスタイルを適用する補助関数
# -------------------------------------------------------------
def _apply_axis_style(
    ax,
    *,
    title,
    xlabel,
    ylabel,
    ylim,
    xticks,
    tick_size=12,
):
    FONT_PROP = font_manager.FontProperties(family="Times New Roman") # Times New Roman を明示的に指定するための FontProperties を作る
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 1, 20))
    ax.set_xticks(xticks)

    ax.set_title(title, fontsize=14, fontfamily="Times New Roman", pad=10)
    ax.set_xlabel(xlabel, fontsize=12, fontfamily="Times New Roman")
    ax.set_ylabel(ylabel, fontsize=12, fontfamily="Times New Roman")

    ax.tick_params(axis="both", labelsize=tick_size)
    for label in ax.get_xticklabels() + ax.get_yticklabels():  # x軸とy軸の目盛りラベルをすべて取得
        label.set_fontproperties(FONT_PROP)                    # 目盛りラベルにも Times New Roman を適用する

    return ax

# -------------------------------------------------------------
# 2.凡例に使うマーカーをまとめて作る補助関数
# -------------------------------------------------------------
def _make_legend_handles(palette, group_order):
    return [
        Line2D(
            [0], [0],
            linestyle="",
            marker="o",
            markersize=8,
            markerfacecolor=palette[group],
            markeredgecolor="black",
            markeredgewidth=0.5,
            color=palette[group],
            label=group,
        )
        for group in group_order
    ]

# -------------------------------------------------------------
# 3.折れ線グラフを描画して保存する関数
# -------------------------------------------------------------
def plot_save(
    df,
    *,
    title="Extinction",
    group_col="Group",
    time_col="Time",
    value_col="Freezing",
    group_order=("SED", "LIE", "MOE"),
    palette=None,
    xlabel="Time (min)",
    ylabel="Freezing Time (%)",
    ylim=(0, 100),
    xticks=(3, 6, 9, 12, 15),
    figsize=(3, 3),
    save_path=None,
    show_legend=True,
    legend_loc="upper left",
    legend_title=None,
    legend_frameon=False,
    method="seaborn",
):
    FONT_PROP = font_manager.FontProperties(family="Times New Roman")
    if palette is None:
        palette = {
            "SED": "gray",
            "LIE": "skyblue",
            "MOE": "lightgreen",
        }

    df = df.copy() # 元のデータを壊さないようにコピーする
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")  # Time 列を数値に変換し、変換できないものは NaN にする
    df = df.dropna(subset=[time_col, value_col, group_col])  # 時間、値、群のどれかが欠測の行を削除する

    fig, ax = plt.subplots(figsize=figsize) # グラフの図と軸を作成する
    
    # seaborn か matplotlib かで描画方法を分ける
    # seabornで描画
    if method == "seaborn":
        sns.set_theme(style="ticks")
        sns.lineplot(
            data=df,
            x=time_col,
            y=value_col,
            hue=group_col,
            hue_order=list(group_order),
            palette=palette,
            estimator="mean",
            errorbar="se",
            marker="o",
            markersize=8,
            linewidth=1.5,
            err_style="bars",
            err_kws={
                "ecolor": "black",
                "elinewidth": 0.5,
                "capsize": 3,
                "capthick": 0.5,
                "zorder": 1,
            },
            markeredgecolor="black",
            markeredgewidth=0.5,
            ax=ax,
        )
        sns.despine(ax=ax)

    # matplotlibで描画
    elif method == "matplotlib":
        # 各群ごとに時間別に平均、標準偏差、サンプル数を計算する
        summary = (
            df.groupby([group_col, time_col], as_index=False)[value_col]
            .agg(mean="mean", std="std", n="count")
        )
         # 標準誤差を計算する
        summary["se"] = summary["std"] / np.sqrt(summary["n"])

        for group in group_order:
            tmp = summary[summary[group_col] == group].sort_values(time_col) # その群だけを抽出し、時間順に並べる
            ax.errorbar(
                tmp[time_col],
                tmp["mean"],
                yerr=tmp["se"],
                fmt="o-",
                color=palette.get(group, "black"),
                ecolor="black",
                elinewidth=0.5,
                capsize=3,
                markersize=8,
                linewidth=1.5,
                label=group,
                markeredgecolor="black",
                markeredgewidth=0.5,
            )

        ax.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("black")
        ax.spines["bottom"].set_color("black")
        ax.spines["left"].set_linewidth(1.5)
        ax.spines["bottom"].set_linewidth(1.5)

    else:
        raise ValueError("method must be 'seaborn' or 'matplotlib'")

    _apply_axis_style(
        ax,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        ylim=ylim,
        xticks=xticks,
    )

    if show_legend:
        handles = _make_legend_handles(palette, group_order)
        legend = ax.legend(
            handles=handles,
            loc=legend_loc,
            frameon=legend_frameon,
            title=legend_title,
            borderaxespad=0,
            handletextpad=0.2,
        )
        for text in legend.get_texts():
            text.set_fontproperties(FONT_PROP)
    else:
        legend = ax.get_legend()
        if legend is not None:
            legend.set_visible(False)

    plt.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax

# -------------------------------------------------------------
# 4. 有意差ブラケット（コの字線とアスタリスク）を描画する補助関数
# -------------------------------------------------------------
def add_sig_bracket(ax, x1, x2, y, h=4, text="*", text_offset=-4.0, fontsize=16):
    """
    ax: 描画対象のAxes
    x1, x2: 比較する2群のx座標
    y: ブラケットの基準高さ (%)
    h: ブラケットの縦線の長さ
    text: 有意記号 ("*", "**", "***" など)
    """
    # コの字型の線を描画: (x1, y) -> (x1, y+h) -> (x2, y+h) -> (x2, y)
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], color="black", linewidth=1.0, zorder=6)
    # 中央にアスタリスク等のテキストを配置
    ax.text(
        (x1 + x2) / 2,
        y + h + text_offset,
        text,
        ha="center",
        va="bottom",
        color="black",
        fontsize=fontsize,
        fontfamily="Times New Roman",
        zorder=6,
    )


# -------------------------------------------------------------
# 5. 有意記号付き 棒グラフ（平均 + SE + Jitter）描画関数
# -------------------------------------------------------------
def plot_group_bar_jitter_sig(
    df,
    *,
    title="Extinction",
    group_col="Group",
    value_col="Freezing",
    group_order=("SED", "LIE", "MOE"),
    palette=None,
    ylabel="Freezing Time (%)",
    ylim=(0, 130), # 有意記号を入れるため上限を130%に拡張
    figsize=(3, 3),
    save_path=None,
    sig_brackets=None, # [(x1, x2, y, h, text), ...]
):
    FONT_PROP = font_manager.FontProperties(family="Times New Roman")
    if palette is None:
        palette = {"SED": "gray", "LIE": "skyblue", "MOE": "lightgreen"}

    df = df.copy().dropna(subset=[group_col, value_col])
    groups = [g for g in group_order if g in df[group_col].unique()]

    # 平均とSEを計算
    summary = (
        df.groupby(group_col, as_index=False)[value_col]
        .agg(mean="mean", std="std", n="count")
    )
    summary["se"] = summary["std"] / np.sqrt(summary["n"])
    summary[group_col] = pd.Categorical(summary[group_col], categories=groups, ordered=True)
    summary = summary.sort_values(group_col)

    fig, ax = plt.subplots(figsize=figsize)
    x_pos = np.arange(len(groups)) # 0: SED, 1: LIE, 2: MOE

    # 棒グラフの描画
    ax.bar(
        x_pos,
        summary["mean"].to_numpy(),
        width=0.7,
        color=[palette[g] for g in groups],
        edgecolor="black",
        linewidth=1.0,
        alpha=0.9,
        yerr=summary["se"].to_numpy(),
        capsize=3,
        error_kw={"ecolor": "black", "elinewidth": 1.0, "capthick": 1.0},
        zorder=2,
    )

    # 個体ごとの Jitter 散布図
    rng = np.random.default_rng(42)
    for i, group in enumerate(groups):
        vals = df.loc[df[group_col] == group, value_col].to_numpy()
        jitter_x = rng.normal(loc=i, scale=0.06, size=len(vals))
        ax.scatter(jitter_x, vals, s=18, color="black", alpha=0.5, edgecolors="none", zorder=3)

    # 有意記号ブラケットの描画
    if sig_brackets:
        for x1, x2, y, h, txt in sig_brackets:
            add_sig_bracket(ax, x1, x2, y, h, txt)

    # 軸・ラベル設定
    ax.set_xticks(x_pos)
    ax.set_xticklabels(groups, fontfamily="Times New Roman")
    ax.set_ylabel(ylabel, fontsize=12, fontfamily="Times New Roman")
    ax.set_title(title, fontsize=14, fontfamily="Times New Roman", pad=10)
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(0, 101, 20)) # 目盛りは 0~100 まで表示

    ax.tick_params(axis="both", labelsize=11)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT_PROP)
    
    # 軸線の制御: ★ 左軸(y軸)の線を 0~100 でピタッと止める ★
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_bounds(0, 100) # 100より上には線を伸ばさない
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    plt.tight_layout()

    # 保存処理（高解像度 PNG / PDF / TIFF）
    if save_path:
        base_path = Path(save_path)
        base_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(base_path.with_suffix(".png"), dpi=300, bbox_inches="tight")
        # plt.savefig(base_path.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
        # plt.savefig(base_path.with_suffix(".tiff"), dpi=300, bbox_inches="tight")
        print(f"[保存完了] {base_path.with_suffix('.png').resolve()}")

    return fig, ax


# -------------------------------------------------------------
# 6. 有意記号付き 箱ひげ図（平均値 + 中央値 + Jitter）描画関数
# -------------------------------------------------------------
def plot_group_boxplot_sig(
    df,
    *,
    title="Extinction",
    group_col="Group",
    value_col="Freezing",
    group_order=("SED", "LIE", "MOE"),
    palette=None,
    ylabel="Freezing Time (%)",
    ylim=(0, 130), # 有意記号を入れるため上限を130%に拡張
    figsize=(3, 3),
    save_path=None,
    sig_brackets=None, # [(x1, x2, y, h, text), ...]
):
    FONT_PROP = font_manager.FontProperties(family="Times New Roman")
    if palette is None:
        palette = {"SED": "gray", "LIE": "skyblue", "MOE": "lightgreen"}

    df = df.copy().dropna(subset=[group_col, value_col])
    groups = [g for g in group_order if g in df[group_col].unique()]
    data = [df.loc[df[group_col] == g, value_col].to_numpy() for g in groups]

    fig, ax = plt.subplots(figsize=figsize)

    # 箱ひげ図
    bp = ax.boxplot(
        data,
        patch_artist=True,
        widths=0.5,
        showfliers=False,
        showmeans=True,
        meanline=True,
        meanprops={"color": "black", "linewidth": 1},
        medianprops={"color": "none", "linewidth": 0},
        boxprops={"edgecolor": "black", "linewidth": 1.2},
        whiskerprops={"color": "black", "linewidth": 1.2},
        capprops={"color": "black", "linewidth": 1.2},
    )

    # 箱の色塗り
    for patch, group in zip(bp["boxes"], groups):
        patch.set_facecolor(palette[group])
        patch.set_alpha(0.8)
        patch.set_edgecolor("black")

    # 中央値: ひし形（白抜き）
    for i, group in enumerate(groups, start=1):
        median_val = np.median(df.loc[df[group_col] == group, value_col].to_numpy())
        ax.scatter(i, median_val, marker="D", s=55, facecolor="white", edgecolor="black", linewidth=0.5, zorder=5)

    # 個体ごとの Jitter
    rng = np.random.default_rng(123)
    for i, group in enumerate(groups, start=1):
        vals = df.loc[df[group_col] == group, value_col].to_numpy()
        jitter_x = rng.normal(loc=i, scale=0.06, size=len(vals))
        ax.scatter(jitter_x, vals, s=18, color="black", alpha=0.5, edgecolors="none", zorder=3)

    # 有意記号ブラケットの描画（boxplotは 1-indexed: 1=SED, 2=LIE, 3=MOE）
    if sig_brackets:
        for x1, x2, y, h, txt in sig_brackets:
            add_sig_bracket(ax, x1, x2, y, h, txt)

    # 軸・ラベル設定
    ax.set_xticks(range(1, len(groups) + 1))
    ax.set_xticklabels(groups, fontfamily="Times New Roman")
    ax.set_ylabel(ylabel, fontsize=12, fontfamily="Times New Roman")
    ax.set_title(title, fontsize=14, fontfamily="Times New Roman", pad=10)
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(0, 101, 20)) # 目盛りは 0~100 まで表示

    ax.tick_params(axis="both", labelsize=11)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT_PROP)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_bounds(0, 100) # 100より上には線を伸ばさない
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    plt.tight_layout()

    # 保存処理（高解像度 PNG / PDF / TIFF）
    if save_path:
        base_path = Path(save_path)
        base_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(base_path.with_suffix(".png"), dpi=300, bbox_inches="tight")
        # plt.savefig(base_path.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
        # plt.savefig(base_path.with_suffix(".tiff"), dpi=300, bbox_inches="tight")
        print(f"[保存完了] {base_path.with_suffix('.png').resolve()}")

    return fig, ax