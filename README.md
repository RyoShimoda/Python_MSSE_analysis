# Python_MSSE_analysis
## はじめに

このリポジトリには、MSSE（Medicine & Science in Sports & Exercise) に掲載された以下の論文の実験１の内容を、Pythonを用いて解析したコードや出力したグラフ、統計解析結果のテキストファイルが保存されています。もともとのRでの解析はAnalyse_MSSEというリポジトリに格納しています。なお、実験のRawデータに関しては公開していません。
Accelerated Fear Extinction by Regular Light-Intensity Exercise: A Possible Role of Hippocampal BDNF-TrkB Signaling. 2024-02 | Journal article. DOI: 10.1249/mss.0000000000003312

## リポジトリの構成

```
├── Results/        # 解析結果が格納されているフォルダ
│   ├── Plots/      # 描画されたグラフが格納されているフォルダ
│   │   ├── ○○.png
│   │   └── ⋮
│   ├── Anovakun_Like_Analysis_Ex1.txt # Rのanovakun関数 (井関ら) に類似した出力結果が出力されているファイル (消去学習一日目)
│   ├── Anovakun_Like_Analysis_Ex2.txt # 消去学習二日目の統計解析結果ファイル
│   └── Anovakun_Like_Analysis_FC.txt  # 恐怖条件付けの統計解析結果ファイル
├── Scripts/        # 実行用のJupyterファイルと関数用のpyファイルが格納されているフォルダ
│   ├── Create_Dataset.py                 # データ読み込みと整形を行う関数が格納されたファイル
│   ├── Create_Plots.py                   # グラフの描画関数が格納されたファイル
│   ├── Fear_Conditioning_Analysis.ipynb  # 恐怖条件付けのデータ読み込み、グラフの整形、統計解析を行うファイル
│   ├── Fear_Extinction_Day_1.ipynb       # 消去学習一日目の``
│   ├── Fear_Extinction_Day_2.ipynb       # 消去学習二日目の``
│   └── Statistical_Analysis.py           # Rのanovakunに類似した出力を出す関数が格納されたファイル
└── practice/       # 練習で用いたJupyterファイルやグラフが格納されているフォルダ
    ├── Results/    # 練習で出力したグラフや統計解析結果が格納されているフォルダ
    └── scripts/    # 練習で使用したJupyterファイルが格納されていうるフォルダ 
```

## 実行環境

- **OS: Windows 11
- **Python version: 3.14.7

## 
