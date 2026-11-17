# Lab 5 workflow: chains my Lab 3 cleaning script and my Lab 4 feature-table
# script into one DAG that ends in a summary report. Written for Snakemake 9.24
#
#   snakemake -n                         dry run: list jobs + reasons
#   snakemake --cores 1                  run everything
#   snakemake --delete-all-output        remove every file the workflow made
#   snakemake --rulegraph | dot -Tpng > evidence/rulegraph.png
#
# The Lab 3 and Lab 4 scripts have their file paths written inside them, so
# the input/output paths below match those exactly. Every file a script reads
# (including the script itself) is declared as an input.


rule all:
    input:
        "data/processed/clean_samples.csv",
        "output/feature_table.tsv",
        "output/report/summary_report.md",
        "output/report/summary_figure.png",


# Stage 1 (Lab 3): regex cleaning of messy_samples.csv.
# The script also cleans the FASTA and builds the samples x features table,
# so the FASTA is a real input and all four files are real outputs.
rule clean_messy_data:
    input:
        samples="data/raw/messy_samples.csv",
        sequences="data/raw/messy_sequences.fasta",
        script="scripts/clean_messy_data.R",
    output:
        samples="data/processed/clean_samples.csv",
        sequences="data/processed/clean_sequences.csv",
        sfm="data/processed/samples_features_metadata.csv",
        feature_meta="data/processed/feature_metadata.csv",
    log:
        "logs/clean_messy_data.log",
    shell:
        "Rscript {input.script} > {log} 2>&1"


# Stage 2 (Lab 4): query cohort.db -> patient x gene feature table.
# The SQL lives inside build_feature_table.py, so the script is the input.
rule build_feature_table:
    input:
        db="data/cohort.db",
        script="scripts/build_feature_table.py",
    output:
        "output/feature_table.tsv",
    log:
        "logs/build_feature_table.log",
    shell:
        "python {input.script} > {log} 2>&1"


# Stage 3: summary report (text + figure) from both tables.
rule summary_report:
    input:
        samples="data/processed/clean_samples.csv",
        features="output/feature_table.tsv",
        script="scripts/make_report.py",
    output:
        report="output/report/summary_report.md",
        figure="output/report/summary_figure.png",
    params:
        genes="TP53,KRAS,EGFR,STK11,KEAP1",
    log:
        "logs/summary_report.log",
    shell:
        "python {input.script} --samples {input.samples} "
        "--features {input.features} --genes {params.genes} "
        "--report {output.report} --figure {output.figure} > {log} 2>&1"
