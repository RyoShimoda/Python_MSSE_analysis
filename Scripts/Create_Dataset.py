# For Fear Extinction 

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
        # 旧 .xls では pandas で警告が出ることがあるので抑制
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*OLE2 inconsistency.*")
        df = pd.read_excel(file)
        
        col4 = pd.to_numeric(df.iloc[:, 3], errors="coerce")  # 4列目（D列）
        col5 = pd.to_numeric(df.iloc[:, 4], errors="coerce")  # 5列目（E列）
        bins_Ex = [ # 3分毎のbinの範囲とラベル
            (3, 8, "3"),
            (9, 14, "6"),
            (15, 20, "9"),
            (21, 26, "12"),
            (27, 32, "15"),
        ]
        if type == "FC":
            FC_data =(
            col4.iloc[2:8]
            .assign(
            No = lambda df: Path(file).stem, # No列にpathからファイル名を抽出して追加
            Group = lambda df: infer_group(Path(file).stem), # グループを推測して追加
            Time  = lambda df: list(range(1, len(df) + 1)), # Time列に1から行数までの連番を追加
            )
            .assign(Freezing = lambda df: df['Interval.3'] / 60 * 100 ) # Freezing Time (%) を計算し列に追加
            .iloc[:, 1:5] 
            )
            
            rows.append(FC_data) # データフレームをリストに追加

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

