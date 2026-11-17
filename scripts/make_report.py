# Lab 5 report step
# Reads the cleaned samples table (Lab 3) and the feature table (Lab 4),
# then writes a short markdown report and one figure.
#
# Snakemake runs this, but you can also run it by hand:
# python scripts/make_report.py --samples data/processed/clean_samples.csv \
#     --features output/feature_table.tsv --genes TP53,KRAS,EGFR,STK11,KEAP1 \
#     --report output/report/summary_report.md --figure output/report/summary_figure.png

import argparse
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # save figures to file, no pop-up window
import matplotlib.pyplot as plt
import pandas as pd


# turn a dataframe into a markdown table
def md_table(df):
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


# round decimals so the table is readable
def fmt(v):
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)


# summary section for one table: size, missing values, numeric stats
def describe_table(name, df):
    out = [f"## {name}", "", f"- Rows: **{len(df)}**", f"- Columns: **{df.shape[1]}**", ""]

    miss = df.isna().mean().mul(100).round(1).rename("pct_missing").reset_index()
    miss = miss.rename(columns={"index": "column"})
    miss.insert(1, "dtype", [str(df[c].dtype) for c in miss["column"]])
    out += ["### Columns and missingness", "", md_table(miss), ""]

    num = df.select_dtypes("number")
    if not num.empty:
        desc = num.describe().T[["count", "mean", "std", "min", "max"]].reset_index()
        desc = desc.rename(columns={"index": "column"})
        out += ["### Numeric columns", "", md_table(desc), ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", required=True)
    p.add_argument("--features", required=True)
    p.add_argument("--genes", default="")
    p.add_argument("--report", required=True)
    p.add_argument("--figure", required=True)
    a = p.parse_args()

    samples = pd.read_csv(a.samples)
    features = pd.read_csv(a.features, sep="\t")
    genes = [g for g in a.genes.split(",") if g]

    # figure with two panels side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # left: % missing in each column of the cleaned samples table
    miss = samples.isna().mean().mul(100).sort_values()
    ax1.barh(miss.index.astype(str), miss.values, color="#4C72B0")
    ax1.set_xlabel("% missing")
    ax1.set_title(f"Cleaned samples table (n={len(samples)})")

    # right: % of patients with at least one mutation in each gene
    # long format = one row per patient + gene (like Query A)
    if {"gene_symbol", "mutation_count"} <= set(features.columns):
        hit = features["mutation_count"].fillna(0) > 0
        freq = hit.groupby(features["gene_symbol"]).mean().mul(100).sort_values()
        gene_cols = list(freq.index)
    # wide format = one row per patient, one column per gene
    else:
        gene_cols = [c for c in features.columns
                     if any(g.lower() in str(c).lower() for g in genes)]
        freq = None
        if gene_cols:
            counts = features[gene_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
            freq = (counts > 0).mean().mul(100).sort_values()

    if gene_cols:
        ax2.barh(freq.index, freq.values, color="#DD8452")
        ax2.set_xlabel("% of patients with >=1 mutation")
        right_title = "Gene features"
    else:
        # no gene columns found, so just show missingness instead
        fmiss = features.isna().mean().mul(100).sort_values()
        ax2.barh(fmiss.index.astype(str), fmiss.values, color="#DD8452")
        ax2.set_xlabel("% missing")
        right_title = "Feature table"
    ax2.set_title(f"{right_title} (n={len(features)})")

    fig.tight_layout()
    Path(a.figure).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.figure, dpi=150)

    # write the markdown report
    parts = [
        "# Lab 5 summary report",
        "",
        f"_Made by the Snakemake workflow on {datetime.now():%Y-%m-%d %H:%M}._",
        "",
        "Inputs: `data/processed/clean_samples.csv` (Lab 3) and "
        "`output/feature_table.tsv` (Lab 4).",
        "",
        f"![summary figure]({Path(a.figure).name})",
        "",
        describe_table("Cleaned samples table (from messy_samples.csv)", samples),
        describe_table("Patient feature table (from cohort.db)", features),
    ]
    Path(a.report).write_text("\n".join(parts))
    print(f"wrote {a.report} and {a.figure}")


if __name__ == "__main__":
    main()
