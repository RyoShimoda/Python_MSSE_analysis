# For Fear Extinction 

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# 旧形式 .xls の OLE2 警告を抑制
# warnings.filterwarnings("ignore", message=".*OLE2 inconsistency.*")

def infer_group(name: str) -> str: # ファイル名からグループを推測する関数
    if "SED" in name:
        return "SED"
    elif "LIE" in name:
        return "LIE"
    elif "MOE" in name:
        return "MOE"
    return "Other"

def read_extinction_per3(files):   # 3分ごとのデータを読み込む関数
    rows = [] # 空のリストを作成して、各ファイルのデータを格納

    for file in files:
        # 旧 .xls では pandas で警告が出ることがあるので抑制
        # with warnings.catch_warnings():
            # warnings.filterwarnings("ignore", message=".*OLE2 inconsistency.*")
        df = pd.read_excel(file)

        col5 = pd.to_numeric(df.iloc[:, 4], errors="coerce")  # 5列目（E列）
        bins = [ # 3分毎のbinの範囲とラベル
            (3, 8, "3"),
            (9, 14, "6"),
            (15, 20, "9"),
            (21, 26, "12"),
            (27, 32, "15"),
        ]

        for start, end, time_label in bins: # 3分毎のbinごとにデータを処理
            freezing = (
                col5.iloc[start - 1:end] # 3:8, 9:14, ...
                .astype(float)           # 数値に変換
                .mul(100 / 30)           # 30秒ごとのデータを3分ごとの平均に変換
                .mean()                  # 平均値を計算  
            )
            rows.append({
                "No": Path(file).stem,   # ファイル名を追加
                "Time": time_label,      # ラベルを追加
                "Freezing": freezing,    # 平均値を追加
                "Group": infer_group(Path(file).stem),  # グループを推測して追加
            })

    return pd.DataFrame(rows)