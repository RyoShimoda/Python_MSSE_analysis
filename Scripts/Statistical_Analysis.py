# 完全版

from pathlib import Path

import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats


# =========================================================================
# anovakun 完全互換 統計解析＆txtレポート生成関数
# =========================================================================
def generate_anovakun_report(data, title="Contextual Fear Extinction", filename="Anovakun_Like_Analysis.txt"):
    """
    Rの anovakun (AsBデザイン) と同一の統計計算(プールされた誤差分散 df=21, Shaffer法)を行い、
    結果を画面に出力すると同時に Results/ フォルダに .txt レポートとして保存する関数。
    """
    # --- [前処理] データのクリーニングと型の保証 ---
    df = data.copy() # 元データを変更しないようにコピーを作成
    df['Freezing'] = pd.to_numeric(df['Freezing'], errors='coerce').astype(float) # Freezing列を確実にfloat型に変換
    df = df.dropna(subset=['Freezing']) # Freezing列に欠損値（NaN）があれば除外
    
    # 時間(Time: 3, 6, 9, 12, 15)と群(Group: SED, LIE, MOE)の並び順を固定
    times = sorted(df['Time'].unique(), key=lambda x: int(x) if str(x).isdigit() else str(x))
    # --
    # df['Time'].unique() -> 「Time」列から重複を除いた値の配列を返す。
    # sorted(..., key=...) -> データを並び替える関数、keyの引数に「並び替えのルール」を指定
    # lambda x: ... -> その場限りの簡単な関数（匿名関数）を作成。リストの要素xを一ずつチェックする
    # int(x) if str(x).isdigit() else str(x) -> もしデータが数字（'10' など）なら整数型（10）に変換し、文字（'A' など）なら文字列のまま扱う
    # --
    groups = ['SED', 'LIE', 'MOE'] if {'SED', 'LIE', 'MOE'}.issubset(set(df['Group'].unique())) else sorted(df['Group'].unique())
    # --
    # set(df['Group'].unique()) -> 「Group」列の重複のない値を、集合（set）という重複を許さない形式に変換
    # .issubset(...) -> ある集合が、別の集合に「すっぽり含まれているか（部分集合か）」を判定する関数
    # Group列に['SED', 'LIE', 'MOE']がすべてそろっている場合は指定した順番で、一つでも足りない場合はアルファベット順に
    # --
    k = len(groups) # 群の数 (3)
    
    # レポート用文字列を格納するリスト（最後に連結してtxt保存・画面表示する）
    lines = []
    def p(text=""):
        lines.append(text)
        
    p("=" * 85)
    p(f"=== {title}: anovakun 完全互換 統合統計解析レポート ===")
    p("=" * 85)
    
    # ---------------------------------------------------------
    # 1. 記述統計量 (各条件のデータ数、平均値、標準偏差)
    # ---------------------------------------------------------
    p("\n<< 記述統計量 (Descriptive Statistics) >>")
    # 各群・各時間ごとに n(匹数), Mean(平均値), SD(標準偏差) を集計
    desc = df.groupby(['Group', 'Time'])['Freezing'].agg(n='count', Mean='mean', SD='std').reset_index()
    # 表示順を SED, LIE, MOE の順序に整列
    desc['Group'] = pd.Categorical(desc['Group'], categories=groups, ordered=True)
    desc['Time'] = pd.to_numeric(desc['Time'], errors='coerce')
    desc = desc.sort_values(by=['Group', 'Time']).drop(columns=['Time'])
    p(desc.to_string(index=False))
    
    # ---------------------------------------------------------
    # 2. 混合二元配置分散分析 (Mixed 2-way ANOVA: Group × Time)
    # ---------------------------------------------------------
    p("\n<< 1. 混合二元配置分散分析 (Mixed 2-way ANOVA: Group x Time) >>")
    # Pingouinを用いて群間要因(Group)と時間内要因(Time)の二元配置分散分析を実行
    aov = pg.mixed_anova(data=df, dv='Freezing', between='Group', within='Time', subject='No')
    p(aov.to_string(index=False))
    
    # ---------------------------------------------------------
    # 3. 群全体の主効果に対する多重比較 (Shaffer法: df=21)
    # ---------------------------------------------------------
    p("\n<< 2. 群全体の主効果に対する多重比較 (Shaffer method: df=21) >>")
    # 個体ごとの15分平均値を算出 (1匹あたり1つの値)
    sum_df = df.groupby(['No', 'Group'], as_index=False)['Freezing'].mean()
    group_means = {g: sum_df[sum_df['Group'] == g]['Freezing'].values for g in groups}
    
    # anovakunと同様に、1要因ANOVAの残差分散(MS_error)と残差自由度(df=21)を取得して検定に用いる
    aov_1w = pg.anova(data=sum_df, dv='Freezing', between='Group', detailed=True)
    ms_err_grp = aov_1w.loc[aov_1w['Source'] == 'Within', 'MS'].values[0] # 残差平均平方
    df_err_grp = int(aov_1w.loc[aov_1w['Source'] == 'Within', 'DF'].values[0]) # 自由度 (24-3=21)
    
    # 3群間のペアワイズ対比較 (SED vs LIE, SED vs MOE, LIE vs MOE)
    pairs = [('SED', 'LIE'), ('SED', 'MOE'), ('LIE', 'MOE')]
    grp_res = []
    p_raw = []
    for g1, g2 in pairs:
        m1, m2 = np.mean(group_means[g1]), np.mean(group_means[g2])
        diff = m1 - m2 # 平均値の差
        se = np.sqrt(ms_err_grp * (1/len(group_means[g1]) + 1/len(group_means[g2]))) # プールされた誤差分散による標準誤差
        t = diff / se # t値の計算
        pval = 2 * stats.t.sf(np.abs(t), df=df_err_grp) # t分布から両側p値を算出
        p_raw.append(pval)
        grp_res.append({'Pair': f"{g1} - {g2}", 'Diff': diff, 't-value': t, 'df': df_err_grp, 'p': pval})
        
    # --- Shafferの修正Bonferroni補正 (3ペアの場合、乗数は [3, 1, 1]) ---
    p_raw = np.array(p_raw)
    order = np.argsort(p_raw) # p値の昇順インデックス
    divs = [3, 1, 1] # Shafferの補正係数
    adj_p = np.empty(3)
    for i in range(3):
        adj_p[i] = min(1.0, p_raw[order][i] * divs[i])
        if i > 0:
            adj_p[i] = max(adj_p[i], adj_p[i-1]) # p値の逆転を防ぐ（単調性の確保）
    res_adj = np.empty(3)
    res_adj[order] = adj_p
    for idx, r in enumerate(grp_res):
        r['adj.p'] = res_adj[idx]
        r['sig'] = '***' if r['adj.p'] < 0.001 else '**' if r['adj.p'] < 0.01 else '*' if r['adj.p'] < 0.05 else 'ns'
    p(pd.DataFrame(grp_res).to_string(index=False))
    
    # ---------------------------------------------------------
    # 4. 各測定時間における単純主効果 ＆ Shaffer多重比較 (プール誤差 df=21)
    # ---------------------------------------------------------
    p("\n<< 3. 各Timeにおける単純主効果 & Shaffer多重比較 (プール誤差 df=21) >>")
    # 各時間ビン (3, 6, 9, 12, 15分) ごとにループ
    for t in times:
        sub = df[df['Time'] == t] # その時間のデータのみを抽出
        g_data = [sub[sub['Group'] == g]['Freezing'].values for g in groups]
        
        # 1. 各時間での群の1要因分散分析 (F検定)
        f_val, p_val = stats.f_oneway(*g_data)
        df_error = len(sub) - k # 24 - 3 = 21 (プールされた残差自由度)
        ss_error = sum(np.sum((g - np.mean(g))**2) for g in g_data) # 群内平方和
        ms_error = ss_error / df_error # プールされた誤差平均平方
        sig_f = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
        p(f"\n--- Time {t} : F(2, {df_error}) = {f_val:.4f}, p = {p_val:.4f} {sig_f} ---")
        
        # 2. プールされた誤差分散(df=21)を用いた3群間のt検定
        t_res, t_p_raw = [], []
        for g1, g2 in pairs:
            d1 = sub[sub['Group'] == g1]['Freezing'].values
            d2 = sub[sub['Group'] == g2]['Freezing'].values
            diff = np.mean(d1) - np.mean(d2)
            se = np.sqrt(ms_error * (1/len(d1) + 1/len(d2))) # プール分散によるSE
            t_val = diff / se
            pval = 2 * stats.t.sf(np.abs(t_val), df=df_error)
            t_p_raw.append(pval)
            t_res.append({'Pair': f"{g1} - {g2}", 'Diff': diff, 't-value': t_val, 'df': df_error, 'p': pval})
            
        # 3. Shaffer法によるp値の多重補正
        t_p_raw = np.array(t_p_raw)
        order = np.argsort(t_p_raw)
        adj_p = np.empty(3)
        for i in range(3):
            adj_p[i] = min(1.0, t_p_raw[order][i] * divs[i])
            if i > 0:
                adj_p[i] = max(adj_p[i], adj_p[i-1])
        t_res_adj = np.empty(3)
        t_res_adj[order] = adj_p
        for idx, r in enumerate(t_res):
            r['adj.p'] = t_res_adj[idx]
            r['sig'] = '***' if r['adj.p'] < 0.001 else '**' if r['adj.p'] < 0.01 else '*' if r['adj.p'] < 0.05 else 'ns'
        p(pd.DataFrame(t_res).to_string(index=False))
        
    # ---------------------------------------------------------
    # 5. 棒グラフ、箱ひげ図用 (15分間平均値の一元配置分散分析 & 前提条件検定)
    # ---------------------------------------------------------
    p("\n<< 4. 箱ひげ図用: 15分間平均値の一元配置分散分析 & 前提条件 >>")
    # ① 正規性の検定 (Shapiro-Wilk)
    p("--- 正規性の検定 (Shapiro-Wilk) ---")
    p(pg.normality(data=sum_df, dv='Freezing', group='Group').to_string())
    # ② 等分散性の検定 (Levene)
    p("\n--- 等分散性の検定 (Levene) ---")
    p(pg.homoscedasticity(data=sum_df, dv='Freezing', group='Group').to_string())
    # ③ 一元配置分散分析 (One-way ANOVA)
    p("\n--- 一元配置分散分析 (One-way ANOVA) ---")
    p(aov_1w.to_string(index=False))
    if aov_1w.loc[aov_1w['Source'] == 'Group', 'p_unc'].values[0] < 0.05:
        p("\n 群間の有意差が認められたため、群間の多重比較を実施。")
        # ④ 群間の多重比較 (Tukey法)
        p("\n--- 群間の多重比較 (Tukey法) ---")
        p(pg.pairwise_tukey(data=sum_df, dv='Freezing', between='Group').to_string())

    # ---------------------------------------------------------
    # 6. レポートの画面表示 ＆ txtファイルへの保存
    # ---------------------------------------------------------
    report_text = "\n".join(lines) # リスト内のすべての文字列を改行で連結
    print(report_text) # コンソール/ノートブック上に出力
    
    # Resultsフォルダを作成してUTF-8形式でテキストファイルに書き込み
    save_dir = Path("Results")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    print(f"\n[保存完了] {save_path.resolve()}\n")
    return report_text
