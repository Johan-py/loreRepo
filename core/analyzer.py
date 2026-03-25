import subprocess
import pandas as pd
import re
import os
import shutil

REPO_DIR = "repo_temp"
def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, value))

# ===============================
# 🚀 ENTRYPOINT
# ===============================
def run_analysis(repo_url, since=None, until=None):

    update_repo(repo_url)

    df = extract_commits(since=since, until=until)

    report = compute_consistency(df)

    # guardar reporte
    os.makedirs("data", exist_ok=True)
    report.to_csv("data/author_consistency_report.csv", index=False)

    return report


# ===============================
# 📦 CLONAR REPO
# ===============================
def update_repo(repo_url):

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


# ===============================
# 📊 EXTRAER COMMITS
# ===============================
def extract_commits(since=None, until=None):

    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "log",
        "--pretty=format:%H|%an|%ad|%s",
        "--date=iso",
        "--numstat"
    ]

    # 📅 filtros de fecha
    if since:
        cmd.insert(3, f"--since={since}")
    if until:
        cmd.insert(3, f"--until={until}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="ignore"
    )

    lines = result.stdout.split("\n")

    commits = []
    current = None

    for line in lines:

        # 🧠 nuevo commit
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

        # 📈 stats de líneas
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

    # 🧹 limpieza
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"])

    df["changes"] = df["added"] + df["deleted"]

    return df


# ===============================
# 🧠 CALCULAR CONSISTENCIA
# ===============================
def compute_consistency(df):

    pattern = r"^(feat|fix|docs|refactor|test|chore|add)(\(.+\))?:\s*.+"

    MAX_STD = 180
    BIG_COMMIT_THRESHOLD = 251
    MIN_LINES_THRESHOLD = 5
    MAX_COMMITS_PER_DAY = 5

    report = []

    for author, data in df.groupby("author"):

        # 🚫 eliminar merges
        data = data[~data["message"].str.startswith("Merge")].copy()

        if len(data) == 0:
            continue

        # limpiar mensajes
        def clean_msg(x):
            return re.sub(r"\s+", " ", str(x)).strip()

        data["conventional"] = data["message"].apply(
            lambda x: bool(re.match(pattern, clean_msg(x), re.IGNORECASE))
        )

        total_commits = len(data)
        total_added = data["added"].sum()
        total_deleted = data["deleted"].sum()
        total_lines = total_added + total_deleted

        # ===============================
        # 1️⃣ MENSAJES
        # ===============================
        message_score = clamp(data["conventional"].mean() * 100)

        # ===============================
        # 2️⃣ TAMAÑO
        # ===============================
        size_std = data["changes"].std()

        size_score = (
            100 if pd.isna(size_std)
            else 100 * (1 - (size_std / MAX_STD))
        )
        size_score = size_score

        # ===============================
        # 3️⃣ FRECUENCIA
        # ===============================
        days_active = data["date"].dt.floor("D").nunique()
        date_range = (data["date"].max() - data["date"].min()).days + 1

        if date_range <= 0:
            frequency_score = 100
        else:
            activity_ratio = days_active / date_range
            commits_per_day = total_commits / date_range
            intensity_score = min(1, commits_per_day / MAX_COMMITS_PER_DAY)

            frequency_score = (
                (0.7 * activity_ratio) +
                (0.3 * intensity_score)
            ) * 100

        frequency_score = clamp(frequency_score)

        # ===============================
        # 4️⃣ GRANULARIDAD
        # ===============================
        big_commits = (data["changes"] > BIG_COMMIT_THRESHOLD).sum()

        granularity_score = (
            1 - (big_commits / total_commits)
        ) * 100

        granularity_score = clamp(granularity_score)

        # ===============================
        # 🧮 SCORE FINAL
        # ===============================
        consistency_score = (
            0.35 * message_score +
            0.25 * size_score +
            0.20 * frequency_score +
            0.20 * granularity_score
        )

        consistency_score = clamp(consistency_score)

        # filtro mínimo
        if total_lines < MIN_LINES_THRESHOLD:
            consistency_score = 0

        report.append({
            "author": author,
            "total_commits": int(total_commits),
            "lines_added": int(total_added),
            "lines_deleted": int(total_deleted),
            "total_lines_changed": int(total_lines),

            "message_score": round(message_score, 2),
            "size_score": round(size_score, 2),
            "frequency_score": round(frequency_score, 2),
            "granularity_score": round(granularity_score, 2),

            "consistency_score": round(consistency_score, 2)
        })

    report_df = pd.DataFrame(report)

    return report_df.sort_values(
        by="consistency_score",
        ascending=False
    ).reset_index(drop=True)