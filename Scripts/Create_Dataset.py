# For Fear Extinction 

import contextlib
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# -------------------------------------------------------------
# 1.ファイル名からグループを推測する関数
# -------------------------------------------------------------

def infer_group(name: str) -> str:
    if "SED" in name:
        return "SED"
    elif "LIE" in name:
        return "LIE"
    elif "MOE" in name:
        return "MOE"
    return "Other"

# -------------------------------------------------------------
# 2.指定したファイルからFreezingのデータを読み込む関数
# -------------------------------------------------------------

def read_freezing_data(files, type = "FC"):
    rows = [] # 空のリストを作成して、各ファイルのデータを格納

    for file in files:
        # 旧 .xls では pandas/xlrd が stderr に直接 WARNING を出すことがあるため抑制
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*OLE2 inconsistency.*")
            with open(os.devnull, "w") as devnull:  # noqa: SIM117
                with contextlib.redirect_stderr(devnull):
                    df = pd.read_excel(file)
        
        col5 = pd.to_numeric(df.iloc[:, 4], errors="coerce")  # 5列目（E列）
        bins_Ex = [ # 3分毎のbinの範囲とラベル
            (3, 8, "3"),
            (9, 14, "6"),
            (15, 20, "9"),
            (21, 26, "12"),
            (27, 32, "15"),
        ]
        if type == "FC":
            for time_label in range(1, 7):
                freezing = (
                    col5.iloc[2 + (time_label - 1)  : 2 + time_label]
                    .astype(float) # 数値に変換
                    .mul(100 / 60) # 60秒ごとのデータをパーセントに変換
                    .iloc[0] # 1つの値を取得
                )
                rows.append({
                    "No": Path(file).stem, # ファイル名を追加
                    "Group": infer_group(Path(file).stem), # グループを推測して追加
                    "Time": time_label, # ラベルを追加
                    "Freezing": freezing
                })

        elif type == "per3":
            for start, end, time_label in bins_Ex: # 3分毎のbinごとにデータを処理
                freezing = (
                   col5.iloc[start - 1:end] # 3:8 (3-1:8 -> 2から7行目をスライス), 9:14, ...
                    .astype(float)           # 数値に変換
                    .mul(100 / 30)           # 30秒ごとのデータを3分ごとの平均に変換
                    .mean()                  # 平均値を計算  
                )
                rows.append({
                    "No": Path(file).stem,   # ファイル名を追加
                    "Group": infer_group(Path(file).stem),  
                    "Time": time_label,      # ラベルを追加
                    "Freezing": freezing,    # 平均値を追加
                })
        else :
            values = []
            for start, end, _ in bins_Ex:
                freezing = (
                    col5.iloc[start - 1:end]
                    .astype(float)
                    .mul(100 / 30)
                    .mean()
                )
                values.append(freezing)

            overall_freezing = np.mean(values) if values else np.nan

            rows.append({
                "No": Path(file).stem,
                 "Group": infer_group(Path(file).stem),
                 "Freezing": overall_freezing,
            })

    return pd.DataFrame(rows)

