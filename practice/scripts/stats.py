"""
stats.py
========
Python replacement for the statistical part of Analyzing_for_MSSE.R,
i.e. the `anovakun()` calls (design "AsB" and "As"), `shapiro.test()`
and `leveneTest()`.

`anovakun` (Iseki, freeware R package widely used in Japanese
psychology/behavioural-science labs) is not available in Python, so
the ANOVA source tables, Huynh-Feldt / Greenhouse-Geisser corrections,
partial eta squared and Tukey HSD post-hoc are re-implemented here
directly with numpy/scipy (no internet-only dependency such as
pingouin/statsmodels required).

Two designs are covered, matching the calls in the R script:

    design="AsB"  -> mixed_anova_AsB()   (between: Group, within: Time)
    design="As"   -> anova_As()          (one-way between-subjects ANOVA)

plus:
    shapiro_wilk(), levene_test(), tukey_hsd(), cohens_d()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------- helpers --
def _epsilon_gg_hf(residuals: np.ndarray, n_groups: int):
    """Greenhouse-Geisser / Huynh-Feldt epsilon for a within-subject factor
    in a (possibly mixed) design.

    `residuals` : (N_subjects, b) matrix of Y_ijk - cellmean_ik  (i.e. each
                  subject's time-profile after removing that subject's own
                  group-by-time cell mean -- this isolates the S x B
                  interaction, which is the correct term sphericity is
                  evaluated on).
    `n_groups`  : number of between-subject levels (a). Use 1 for a purely
                  within-subject design.
    """
    n_subj, b = residuals.shape
    # pooled covariance matrix of the b repeated measurements
    S = np.cov(residuals, rowvar=False, ddof=1)
    if b < 2:
        return 1.0, 1.0
    trace = np.trace(S)
    eps_gg = trace**2 / ((b - 1) * np.sum(S**2))
    eps_gg = min(max(eps_gg, 1.0 / (b - 1)), 1.0)

    N = n_subj
    num = N * (b - 1) * eps_gg - 2
    den = (b - 1) * (N - n_groups - (b - 1) * eps_gg)
    eps_hf = num / den if den != 0 else 1.0
    eps_hf = min(max(eps_hf, eps_gg), 1.0)
    return eps_gg, eps_hf


@dataclass
class AnovaRow:
    source: str
    ss: float
    df: float
    ms: float
    F: float | None
    p: float | None
    peta2: float | None = None
    eps_gg: float | None = None
    eps_hf: float | None = None
    p_gg: float | None = None
    p_hf: float | None = None


@dataclass
class AnovaTable:
    rows: List[AnovaRow] = field(default_factory=list)

    def __str__(self):
        lines = [
            f"{'Source':<14}{'SS':>12}{'df':>8}{'MS':>12}{'F':>10}{'p':>10}"
            f"{'p.eta2':>9}{'GGeps':>8}{'p(GG)':>10}{'HFeps':>8}{'p(HF)':>10}"
        ]
        for r in self.rows:
            def fmt(x, nd=4):
                return "" if x is None else f"{x:.{nd}f}"
            lines.append(
                f"{r.source:<14}{r.ss:>12.3f}{r.df:>8.2f}{r.ms:>12.3f}"
                f"{fmt(r.F,3):>10}{fmt(r.p):>10}{fmt(r.peta2):>9}"
                f"{fmt(r.eps_gg,3):>8}{fmt(r.p_gg):>10}"
                f"{fmt(r.eps_hf,3):>8}{fmt(r.p_hf):>10}"
            )
        return "\n".join(lines)


def anovakun(dataset: pd.DataFrame, design: str, *args, long: bool = False,
             type2: bool = False, nopost: bool = False, tech: bool = False,
             data_frame: bool = False, copy: bool = False, dv: str | None = None,
             group_col: str | None = None, time_cols: List[str] | None = None,
             hf: bool = True, peta: bool = True, **kwargs) -> AnovaTable:
    """Python-compatible entry point matching the common R `anovakun()` API.

    Supported in this project:
      - design="AsB"  -> mixed_anova_AsB(...)
      - design="As"   -> anova_As(...)

    This keeps the call pattern close to the original R workflow while still
    using pandas/scipy under the hood.
    """
    del args, type2, nopost, tech, data_frame, copy

    if design == "AsB":
        if dv is None:
            dv = kwargs.pop("dv", None) or "Freezing"
        if group_col is None:
            group_col = kwargs.pop("group", None) or kwargs.pop("group_col", None) or "Group"

        if long:
            if "Time" not in dataset.columns:
                raise ValueError("long=True requires a 'Time' column in the dataset.")
            if dv not in dataset.columns:
                raise ValueError(f"dv='{dv}' not found in the long-format dataset.")
            if group_col not in dataset.columns:
                if "Group" in dataset.columns:
                    group_col = "Group"
                else:
                    raise ValueError("A group column is required for the AsB design.")
            time_values = sorted(dataset["Time"].dropna().unique())
            wide = dataset.pivot_table(index=[col for col in dataset.columns if col not in {"Time", dv}],
                                       columns="Time", values=dv, aggfunc="mean").reset_index()
            if group_col not in wide.columns:
                wide[group_col] = dataset[[group_col]].drop_duplicates().iloc[:, 0].values
            if time_cols is None:
                time_cols = [str(t) for t in time_values]
            dataset = wide

        if time_cols is None:
            time_cols = [c for c in dataset.columns if c not in {group_col, "No", dv}]
        return mixed_anova_AsB(dataset, group_col=group_col, time_cols=time_cols, hf=hf, peta=peta)

    if design == "As":
        if dv is None:
            dv = kwargs.pop("dv", None) or "Freezing"
        if group_col is None:
            group_col = kwargs.pop("group", None) or kwargs.pop("group_col", None) or "Group"
        return anova_As(dataset, dv=dv, group_col=group_col, peta=peta)

    raise ValueError(f"Unsupported design '{design}'. Supported designs are 'As' and 'AsB'.")


# ------------------------------------------------------------ AsB design --
def mixed_anova_AsB(wide: pd.DataFrame, group_col: str = "Group",
                     time_cols: List[str] | None = None,
                     hf: bool = True, peta: bool = True) -> AnovaTable:
    """Two-way mixed ANOVA: between-subject factor A = Group, within-subject
    factor B = Time (repeated on the same animals). Equivalent to
    `anovakun(dataset, "AsB", Group=..., Time=..., hf=T, peta=T)`.

    `wide` must have one row per animal: group_col + one column per time
    point (use data.to_wide()).
    """
    if time_cols is None:
        time_cols = [c for c in wide.columns if c not in (group_col, "No")]

    groups = wide[group_col].to_numpy()
    Y = wide[time_cols].to_numpy(dtype=float)  # (N, b)
    N, b = Y.shape
    levels = pd.unique(groups)
    a = len(levels)

    grand_mean = Y.mean()
    subj_mean = Y.mean(axis=1)  # per-subject mean over time

    # group-level stats
    group_means_over_all = {}
    group_time_means = {}
    n_per_group = {}
    for g in levels:
        Yg = Y[groups == g]
        n_per_group[g] = Yg.shape[0]
        group_means_over_all[g] = Yg.mean()
        group_time_means[g] = Yg.mean(axis=0)  # (b,)

    time_means = Y.mean(axis=0)  # (b,)

    # ---- Sums of squares --------------------------------------------------
    SS_total = np.sum((Y - grand_mean) ** 2)

    SS_A = sum(n_per_group[g] * b * (group_means_over_all[g] - grand_mean) ** 2 for g in levels)

    SS_SA = 0.0
    for g in levels:
        Yg = Y[groups == g]
        subj_means_g = Yg.mean(axis=1)
        SS_SA += b * np.sum((subj_means_g - group_means_over_all[g]) ** 2)

    SS_B = N * np.sum((time_means - grand_mean) ** 2)

    SS_AB = 0.0
    for g in levels:
        SS_AB += n_per_group[g] * np.sum(
            (group_time_means[g] - group_means_over_all[g] - time_means + grand_mean) ** 2
        )

    SS_BSA = SS_total - SS_A - SS_SA - SS_B - SS_AB

    df_A, df_SA = a - 1, N - a
    df_B, df_AB, df_BSA = b - 1, (a - 1) * (b - 1), (N - a) * (b - 1)

    MS_A, MS_SA = SS_A / df_A, SS_SA / df_SA
    MS_B, MS_AB, MS_BSA = SS_B / df_B, SS_AB / df_AB, SS_BSA / df_BSA

    F_A = MS_A / MS_SA
    p_A = stats.f.sf(F_A, df_A, df_SA)
    F_B = MS_B / MS_BSA
    p_B = stats.f.sf(F_B, df_B, df_BSA)
    F_AB = MS_AB / MS_BSA
    p_AB = stats.f.sf(F_AB, df_AB, df_BSA)

    peta_A = SS_A / (SS_A + SS_SA) if peta else None
    peta_B = SS_B / (SS_B + SS_BSA) if peta else None
    peta_AB = SS_AB / (SS_AB + SS_BSA) if peta else None

    table = AnovaTable()
    table.rows.append(AnovaRow("Group(A)", SS_A, df_A, MS_A, F_A, p_A, peta_A))
    table.rows.append(AnovaRow("S/A(error)", SS_SA, df_SA, MS_SA, None, None))
    row_B = AnovaRow("Time(B)", SS_B, df_B, MS_B, F_B, p_B, peta_B)
    row_AB = AnovaRow("A x B", SS_AB, df_AB, MS_AB, F_AB, p_AB, peta_AB)

    if hf:
        # residuals with subject's own group*time cell mean removed
        resid = np.empty_like(Y)
        for g in levels:
            mask = groups == g
            resid[mask] = Y[mask] - group_time_means[g][None, :]
        eps_gg, eps_hf = _epsilon_gg_hf(resid, n_groups=a)

        row_B.eps_gg, row_B.eps_hf = eps_gg, eps_hf
        row_B.p_gg = stats.f.sf(F_B, df_B * eps_gg, df_BSA * eps_gg)
        row_B.p_hf = stats.f.sf(F_B, df_B * eps_hf, df_BSA * eps_hf)

        row_AB.eps_gg, row_AB.eps_hf = eps_gg, eps_hf
        row_AB.p_gg = stats.f.sf(F_AB, df_AB * eps_gg, df_BSA * eps_gg)
        row_AB.p_hf = stats.f.sf(F_AB, df_AB * eps_hf, df_BSA * eps_hf)

    table.rows.append(row_B)
    table.rows.append(row_AB)
    table.rows.append(AnovaRow("BxS/A(error)", SS_BSA, df_BSA, MS_BSA, None, None))
    return table


# -------------------------------------------------------------- As design --
def anova_As(df: pd.DataFrame, dv: str = "Freezing", group_col: str = "Group",
             peta: bool = True) -> AnovaTable:
    """One-way between-subjects ANOVA. Equivalent to
    `anovakun(dataset, "As", Group=..., peta=T)`."""
    groups = df[group_col].unique()
    samples = [df.loc[df[group_col] == g, dv].to_numpy(dtype=float) for g in groups]
    grand_mean = df[dv].mean()
    N = len(df)
    a = len(groups)

    SS_A = sum(len(s) * (s.mean() - grand_mean) ** 2 for s in samples)
    SS_total = np.sum((df[dv].to_numpy(dtype=float) - grand_mean) ** 2)
    SS_err = SS_total - SS_A

    df_A, df_err = a - 1, N - a
    MS_A, MS_err = SS_A / df_A, SS_err / df_err
    F = MS_A / MS_err
    p = stats.f.sf(F, df_A, df_err)
    peta2 = SS_A / (SS_A + SS_err) if peta else None

    table = AnovaTable()
    table.rows.append(AnovaRow("Group(A)", SS_A, df_A, MS_A, F, p, peta2))
    table.rows.append(AnovaRow("error", SS_err, df_err, MS_err, None, None))
    return table


# ---------------------------------------------------------- normal./var. --
def shapiro_wilk(x: pd.Series | np.ndarray):
    """Equivalent of `shapiro.test()`."""
    stat, p = stats.shapiro(np.asarray(x, dtype=float))
    return {"W": stat, "p": p}


def levene_test(df: pd.DataFrame, dv: str = "Freezing", group_col: str = "Group"):
    """Equivalent of `car::leveneTest(dv ~ group, data)` (uses the median-
    centred, i.e. Brown-Forsythe, version -- same default as leveneTest())."""
    groups = df[group_col].unique()
    samples = [df.loc[df[group_col] == g, dv].to_numpy(dtype=float) for g in groups]
    stat, p = stats.levene(*samples, center="median")
    return {"F": stat, "p": p}


# --------------------------------------------------------------- post-hoc --
def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    pooled_sd = np.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    return (x.mean() - y.mean()) / pooled_sd


def tukey_hsd(df: pd.DataFrame, dv: str = "Freezing", group_col: str = "Group") -> pd.DataFrame:
    """Tukey HSD all-pairs post-hoc for a one-way between-subjects design,
    equivalent to what anovakun reports as the multiple-comparison table
    after design="As"."""
    groups = sorted(df[group_col].unique())
    samples = {g: df.loc[df[group_col] == g, dv].to_numpy(dtype=float) for g in groups}
    N = len(df)
    a = len(groups)
    grand_mean = df[dv].mean()
    SS_err = sum(np.sum((s - s.mean()) ** 2) for s in samples.values())
    df_err = N - a
    MS_err = SS_err / df_err

    rows = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            g1, g2 = groups[i], groups[j]
            x, y = samples[g1], samples[g2]
            n1, n2 = len(x), len(y)
            mean_diff = x.mean() - y.mean()
            se = np.sqrt(MS_err / 2 * (1 / n1 + 1 / n2))
            q = abs(mean_diff) / se
            p = stats.studentized_range.sf(q, a, df_err)
            d = cohens_d(x, y)
            rows.append({
                "Comparison": f"{g1} vs {g2}",
                "Mean diff": mean_diff,
                "q": q,
                "p (Tukey)": p,
                "Cohen's d": d,
            })
    return pd.DataFrame(rows)
