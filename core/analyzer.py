import subprocess
import pandas as pd
import re
import os
import shutil
import unicodedata

REPO_DIR = "repo_temp"


# ===============================
# 🔧 UTILIDADES
# ===============================
def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, value))


def normalize_text(text):
    text = str(text).lower().strip()

    # quitar tildes
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))

    # normalizar espacios
    text = re.sub(r"\s+", " ", text)

    return text


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
# 📊 PARSEAR COMMITS
# ===============================
def parse_commits_from_output(output):
    """Parsea la salida de git log a lista de diccionarios"""
    lines = output.split("\n")
    
    commits = []
    current = None
    
    for line in lines:
        if "|" in line and len(line.split("|")) >= 5:
            if current:
                commits.append(current)
            
            try:
                h, author, email, date, msg = line.split("|", 4)
                current = {
                    "hash": h,
                    "author": author.strip(),
                    "email": email.strip(),
                    "date": date,
                    "message": msg.strip(),
                    "added": 0,
                    "deleted": 0
                }
            except:
                continue
        
        elif line.strip() and current:
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    added = parts[0] if parts[0] != '-' else '0'
                    deleted = parts[1] if parts[1] != '-' else '0'
                    current["added"] += int(added)
                    current["deleted"] += int(deleted)
                except:
                    pass
    
    if current:
        commits.append(current)
    
    return commits


# ===============================
# 📊 EXTRAER COMMITS
# ===============================
def extract_commits(since=None, until=None, branches=None, include_all_history=True):
    """
    Extrae commits incluyendo TODOS los commits históricos
    
    Args:
        since: fecha inicial (opcional)
        until: fecha final (opcional)
        branches: lista de ramas específicas (si es None, usa --all)
        include_all_history: si es True, incluye commits de ramas eliminadas y reflog
    """
    
    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "log",
    ]
    
    # 🔥 Estrategia para obtener TODOS los commits
    if branches:
        # Ramas específicas
        cmd.extend(branches)
    elif include_all_history:
        # 🔥 OBTENER TODOS LOS COMMITS EXISTENTES
        cmd.append("--all")           # Todas las referencias (ramas, tags, remotas)
        cmd.append("--reflog")        # Commits en reflog (recuperables)
    else:
        # Solo ramas principales activas
        cmd.extend(["main", "develop"])
    
    cmd.extend([
        "--pretty=format:%H|%an|%ae|%ad|%s",
        "--date=iso",
        "--numstat",
    ])

    if since:
        cmd.insert(3, f"--since={since}")
    if until:
        cmd.insert(3, f"--until={until}")

    print(f"[DEBUG] Comando ejecutado: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="ignore"
    )
    
    # Si el comando falla o no hay resultados, intentar sin --reflog
    if not result.stdout.strip() and include_all_history:
        print("[WARN] No se encontraron commits con --reflog, intentando sin él...")
        cmd = [
            "git",
            f"--git-dir={REPO_DIR}",
            "log",
            "--all",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso",
            "--numstat",
        ]
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
    
    # Parsear commits
    commits = parse_commits_from_output(result.stdout)
    
    df = pd.DataFrame(commits)
    
    if df.empty:
        print("[WARN] No se encontraron commits")
        return df
    
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df["changes"] = df["added"] + df["deleted"]
    
    print(f"[INFO] Se extrajeron {len(df)} commits")
    if not df.empty:
        print(f"[INFO] Rango de fechas: {df['date'].min()} a {df['date'].max()}")
    
    return df


def extract_commits_batch(branches=None, skip=0, max_count=1000):
    """
    Extrae commits en batches para manejar repositorios grandes
    
    Args:
        branches: lista de ramas
        skip: número de commits a saltar
        max_count: máximo número de commits a extraer
    """
    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "log",
    ]
    
    if branches:
        cmd.extend(branches)
    else:
        cmd.append("--all")
    
    # Agregar límite y offset
    cmd.extend([
        f"--skip={skip}",
        f"--max-count={max_count}",
        "--pretty=format:%H|%an|%ae|%ad|%s",
        "--date=iso",
        "--numstat",
    ])
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="ignore"
    )
    
    commits = parse_commits_from_output(result.stdout)
    df = pd.DataFrame(commits)
    
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        df = df.dropna(subset=["date"])
        df["changes"] = df["added"] + df["deleted"]
    
    return df


def get_available_branches():
    """Obtiene la lista de ramas disponibles en el repositorio"""
    result = subprocess.run(
        ["git", f"--git-dir={REPO_DIR}", "branch", "--list"],
        capture_output=True,
        text=True,
        errors="ignore"
    )
    
    branches = []
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line and not line.startswith("*"):
            branches.append(line)
        elif line and line.startswith("*"):
            branches.append(line[2:])
    
    return branches


def get_total_commit_count(branches=None):
    """Obtiene el número total de commits a analizar"""
    cmd = [
        "git",
        f"--git-dir={REPO_DIR}",
        "rev-list",
        "--count"
    ]
    
    if branches:
        cmd.extend(branches)
    else:
        cmd.append("--all")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="ignore"
    )
    
    try:
        return int(result.stdout.strip())
    except:
        return 0


# ===============================
# 👥 CARGAR USUARIOS
# ===============================
def load_user_mapping(path="data/users.csv"):
    df_users = pd.read_csv(path)

    df_users = df_users.dropna(subset=["nombre_completo", "github_username"])
    df_users["nombre_norm"] = df_users["nombre_completo"].apply(normalize_text)
    df_users["user_norm"] = df_users["github_username"].apply(normalize_text)

    return df_users


# ===============================
# 🔄 NORMALIZAR AUTORES
# ===============================
def normalize_authors(df, df_users):
    df["author_raw"] = df["author"]
    df["author_norm"] = df["author"].apply(normalize_text)

    mapping_user = dict(zip(df_users["user_norm"], df_users["nombre_completo"]))
    mapping_name = dict(zip(df_users["nombre_norm"], df_users["nombre_completo"]))

    ALIASES = {
        "parche": "Adrian Perez Tapia",
        "alex": "Alex Choque Ajata",
        "jose": "Jose Adrian Villazon Rojas",
        "Tu Nombre": "Shawn Brandon Bellido Zeballos"
    }

    def resolve_display(author, email):
        a = normalize_text(author)
        e = normalize_text(email)

        e = re.sub(r".*\+", "", e)

        if a in ALIASES:
            return ALIASES[a]

        if a in mapping_user:
            return mapping_user[a]

        for user in mapping_user:
            if re.search(rf"\b{re.escape(user)}\b", e):
                return mapping_user[user]

        if a in mapping_name:
            return mapping_name[a]

        for user in mapping_user:
            if user in a:
                return mapping_user[user]

        for name in mapping_name:
            if name in a:
                return mapping_name[name]

        print(f"[WARN] Autor no mapeado: {author} | {email}")
        return author

    df["display_name"] = df.apply(
        lambda row: resolve_display(row["author"], row["email"]),
        axis=1
    )

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

    for author, data in df.groupby("display_name"):
        data = data[~data["message"].fillna("").str.startswith("Merge")].copy()
        if len(data) == 0:
            continue

        def clean_msg(x):
            return re.sub(r"\s+", " ", str(x)).strip()

        data["conventional"] = data["message"].apply(
            lambda x: bool(re.match(pattern, clean_msg(x), re.IGNORECASE))
        )

        total_commits = len(data)
        total_added = data["added"].sum()
        total_deleted = data["deleted"].sum()
        total_lines = total_added + total_deleted

        message_score = clamp(data["conventional"].mean() * 100)

        size_std = data["changes"].std()
        size_score = clamp(
            100 if pd.isna(size_std)
            else 100 * (1 - (size_std / MAX_STD))
        )

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

        big_commits = (data["changes"] > BIG_COMMIT_THRESHOLD).sum()
        granularity_score = clamp(
            (1 - (big_commits / total_commits)) * 100
        )

        consistency_score = clamp(
            0.35 * message_score +
            0.25 * size_score +
            0.20 * frequency_score +
            0.20 * granularity_score
        )

        if total_lines < MIN_LINES_THRESHOLD:
            consistency_score = 0

        report.append({
            "author": author,
            "aliases": ", ".join(data["author_raw"].unique()),
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


# ===============================
# 🚀 ENTRYPOINT PRINCIPAL (UNIFICADO)
# ===============================
def run_analysis(repo_url, since=None, until=None, branches=None, include_all_history=True):
    """
    Ejecuta el análisis completo
    
    Args:
        repo_url: URL del repositorio
        since: fecha inicial (opcional)
        until: fecha final (opcional)
        branches: lista de ramas a analizar (None = usa estrategia según include_all_history)
        include_all_history: si es True, analiza TODOS los commits (incluyendo ramas eliminadas)
    """
    
    update_repo(repo_url)

    # Determinar qué ramas analizar
    if branches is not None:
        # Si se especificaron ramas, usarlas directamente
        branches_to_analyze = branches
    elif include_all_history:
        # Si se quiere TODO el historial, usar None para que extract_commits use --all
        branches_to_analyze = None
    else:
        # Solo ramas principales
        available_branches = get_available_branches()
        branches_to_analyze = [b for b in ["main", "develop"] if b in available_branches]
        
        if not branches_to_analyze:
            print(f"[WARN] No se encontraron ramas main/develop. Usando todas las ramas.")
            branches_to_analyze = None
    
    # Extraer commits
    df = extract_commits(
        since=since, 
        until=until, 
        branches=branches_to_analyze,
        include_all_history=include_all_history
    )
    
    if df.empty:
        print("[ERROR] No se encontraron commits para analizar")
        return pd.DataFrame()

    # Cargar y normalizar autores
    df_users = load_user_mapping()
    df = normalize_authors(df, df_users)

    print("\n--- AUTORES NORMALIZADOS ---")
    print(df[["author", "display_name"]].drop_duplicates().head(20))

    # Calcular consistencia
    report = compute_consistency(df)

    # Guardar resultados
    os.makedirs("data", exist_ok=True)
    report.to_csv("data/author_consistency_report.csv", index=False)
    
    # Guardar metadata
    metadata = {
        "repo_url": repo_url,
        "branches_analyzed": branches_to_analyze if branches_to_analyze else "all (incluye ramas eliminadas)" if include_all_history else "main/develop",
        "since": since if since else "inicio",
        "until": until if until else "actual",
        "include_all_history": include_all_history,
        "total_commits": len(df),
        "total_authors": len(report),
        "analysis_date": pd.Timestamp.now().isoformat()
    }
    
    pd.DataFrame([metadata]).to_csv("data/analysis_metadata.csv", index=False)

    return report


# ===============================
# FUNCIÓN PARA ANÁLISIS COMPLETO POR BATCHES
# ===============================
def run_full_history_analysis(repo_url, branches=None, batch_size=1000):
    """
    Analiza TODO el historial del repositorio en batches para manejar repos grandes
    
    Args:
        repo_url: URL del repositorio
        branches: lista de ramas a analizar
        batch_size: número de commits por batch
    """
    update_repo(repo_url)
    
    if branches is None:
        branches = ["main", "develop"]
    
    available_branches = get_available_branches()
    branches_to_analyze = [b for b in branches if b in available_branches]
    
    if not branches_to_analyze:
        print(f"[WARN] Ninguna de las ramas {branches} existe. Usando todas las ramas.")
        branches_to_analyze = None
    
    all_commits = []
    total_commits = get_total_commit_count(branches_to_analyze)
    print(f"[INFO] Total de commits a analizar: {total_commits}")
    
    offset = 0
    while True:
        print(f"[INFO] Procesando batch {offset//batch_size + 1}...")
        batch_df = extract_commits_batch(
            branches=branches_to_analyze, 
            skip=offset, 
            max_count=batch_size
        )
        
        if batch_df.empty:
            break
            
        all_commits.append(batch_df)
        offset += batch_size
        
        if len(batch_df) < batch_size:
            break
    
    if not all_commits:
        print("[ERROR] No se encontraron commits")
        return pd.DataFrame()
    
    df = pd.concat(all_commits, ignore_index=True)
    print(f"[INFO] Total de commits extraídos: {len(df)}")
    
    df_users = load_user_mapping()
    df = normalize_authors(df, df_users)
    
    print("\n--- AUTORES NORMALIZADOS ---")
    print(df[["author", "display_name"]].drop_duplicates().head(20))
    
    report = compute_consistency(df)
    
    os.makedirs("data", exist_ok=True)
    report.to_csv("data/author_consistency_report_full_history.csv", index=False)
    
    metadata = {
        "repo_url": repo_url,
        "branches_analyzed": branches_to_analyze or "all",
        "since": "inicio del repositorio",
        "until": "actual",
        "total_commits": len(df),
        "total_authors": len(report),
        "analysis_date": pd.Timestamp.now().isoformat(),
        "analysis_type": "full_history"
    }
    
    pd.DataFrame([metadata]).to_csv("data/analysis_metadata_full_history.csv", index=False)
    
    return report