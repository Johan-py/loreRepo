import subprocess
import pandas as pd
import re
import os
import shutil

REPO_DIR = "repo_temp"


def run_analysis(repo_url):

    update_repo(repo_url)

    df = extract_commits()

    report = compute_consistency(df)

    # guardar reporte
    os.makedirs("data", exist_ok=True)
    report.to_csv("data/author_consistency_report.csv", index=False)

    return report


def update_repo(repo_url):

    # eliminar repo anterior
    if os.path.exists(REPO_DIR):
        shutil.rmtree(REPO_DIR)

    print("Clonando repositorio...")

    subprocess.run([
        "git",
        "clone",
        "--bare",
        repo_url,
        REPO_DIR
    ], check=True)


def extract_commits():

    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "log",
        "--pretty=format:%H|%an|%ad|%s",
        "--date=iso",
        "--numstat"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    lines = result.stdout.split("\n")

    commits = []
    current = None

    for line in lines:

        if "|" in line and len(line.split("|")) >= 4:

            if current:
                commits.append(current)

            h, author, date, msg = line.split("|", 3)

            current = {
                "hash": h,
                "author": author.strip(),
                "date": date,
                "message": msg.strip(),
                "added": 0,
                "deleted": 0
            }

        elif line.strip() and current:

            parts = line.split("\t")

            if len(parts) >= 3:

                try:
                    current["added"] += int(parts[0])
                    current["deleted"] += int(parts[1])
                except:
                    pass

    if current:
        commits.append(current)

    df = pd.DataFrame(commits)

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"])

    df["changes"] = df["added"] + df["deleted"]

    return df


def compute_consistency(df):

    pattern = r"^(feat|fix|docs|refactor|test|chore)"

    df["conventional"] = df["message"].apply(
        lambda x: bool(re.match(pattern, x))
    )

    report = []

    for author, data in df.groupby("author"): 

        total_commits = len(data)

        total_added = data["added"].sum()
        total_deleted = data["deleted"].sum()

        total_lines = total_added + total_deleted

        # 1️⃣ consistencia mensajes
        message_consistency = data["conventional"].mean()

        # 2️⃣ consistencia tamaño commit
        size_std = data["changes"].std()
        size_consistency = 1 / (1 + size_std) if not pd.isna(size_std) else 1

        # 3️⃣ consistencia temporal
        commits_by_day = data.groupby(data["date"].dt.floor("D")).size()        
        freq_std = commits_by_day.std()

        frequency_consistency = (
            1 / (1 + freq_std) if not pd.isna(freq_std) else 1
        )

        # 4️⃣ granularidad
        big_commits = (data["changes"] > 500).sum()
        granularity_consistency = 1 - (big_commits / total_commits)

        consistency_score = (
            0.35 * message_consistency +
            0.25 * size_consistency +
            0.20 * frequency_consistency +
            0.20 * granularity_consistency
        )

        if total_lines < 100:
            consistency_score = 0

        report.append({
            "author": author,
            "total_commits": int(total_commits),
            "lines_added": int(total_added),
            "lines_deleted": int(total_deleted),
            "total_lines_changed": int(total_lines),
            "frequency_consistency": round(frequency_consistency, 2),
            "consistency_score": round(consistency_score, 2)
        })

    report_df = pd.DataFrame(report)

    # ordenar ranking
    report_df = report_df.sort_values(
        by="consistency_score",
        ascending=False
    ).reset_index(drop=True)

    return report_df