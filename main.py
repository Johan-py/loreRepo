import subprocess
import pandas as pd
import re

REPO_DIR = "repo_temp.git"


def extract_commits():

    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "log",
        "--pretty=format:%H|%an|%ad|%s",
        "--date=iso",
        "--numstat"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
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
                "author": author,
                "date": date,
                "message": msg,
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

    df["date"] = pd.to_datetime(df["date"])
    df["changes"] = df["added"] + df["deleted"]

    return df


def compute_consistency(df):

    # detectar conventional commits
    pattern = r"^(feat|fix|docs|refactor|test|chore)"

    df["conventional"] = df["message"].apply(
        lambda x: bool(re.match(pattern, x))
    )

    report = []

    for author, data in df.groupby("author"):

        total_commits = len(data)

        conventional_ratio = data["conventional"].mean()

        avg_size = data["changes"].mean()

        size_std = data["changes"].std()

        consistency_score = (
            (conventional_ratio * 0.5) +
            (1 / (1 + size_std)) * 0.5
        )

        report.append({
            "author": author,
            "total_commits": total_commits,
            "conventional_ratio": round(conventional_ratio, 2),
            "avg_lines_changed": round(avg_size, 2),
            "size_variation": round(size_std, 2),
            "consistency_score": round(consistency_score, 2)
        })

    return pd.DataFrame(report)


df = extract_commits()

report = compute_consistency(df)
print(report)

report.to_csv("data/author_consistency_report.csv", index=False)