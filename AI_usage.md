# Lab 5 AI Usage
Model: Claude
AI was utilized for creating the Snakefile and make_report.py 

## Prompts  used
1. Creating the Snakefile
I gave Claude both the `clean_messy_data.R` script and the `build_feature_table.py` files
that were used in Labs 3 and 4 respectively and asked it to 
"Create a Snakefile that cleans `messy_samples.csv` and queries `cohort.db` and then produce a summary report using the files given"

Response: 
"rule all:
    input:
        "clean_samples.csv",
        "feature_table.tsv",
        "summary_report.md",
        "summary_figure.png",


rule clean_messy_data:
    input:
        samples="messy_samples.csv",
        sequences="messy_sequences.fasta",
        script="clean_messy_data.R",
    output:
        samples="clean_samples.csv",
        sequences="clean_sequences.csv",
        sfm="samples_features_metadata.csv",
        feature_meta="feature_metadata.csv",
    log:
        "clean_messy_data.log",
    shell:
        "Rscript {input.script} > {log} 2>&1"


rule build_feature_table:
    input:
        db="cohort.db",
        script="build_feature_table.py",
    output:
        "feature_table.tsv",
    log:
        "build_feature_table.log",
    shell:
        "python {input.script} > {log} 2>&1"


rule summary_report:
    input:
        samples="clean_samples.csv",
        features="feature_table.tsv",
        script="make_report.py",
    output:
        report="summary_report.md",
        figure="summary_figure.png",
    params:
        genes="TP53,KRAS,EGFR,STK11,KEAP1",
    log:
        "summary_report.log",
    shell:
        "python {input.script} --samples {input.samples} "
        "--features {input.features} --genes {params.genes} "
        "--report {output.report} --figure {output.figure} > {log} 2>&1"
"

It gave the loose structure of the snakefile that I ended up using. The issue with 
this one was that it did nto have the paths for ach input and output.
for example under rule all, "clean_samples.csv" should be "data/processed/clean_samples.csv"
since that is where I had the file in my repo. 

2. make a python program that creates the summary report
"Based on the snakefile that was made, can you create a python program that creates the summary script and call it make_report.py?"
Response
```python
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
```

After running the program, I the python script worked as I wanted it, I just added some comments to it. 




