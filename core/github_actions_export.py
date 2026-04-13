import requests
import csv
import os
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OWNER = "Johan-py"
REPO = "PropBol"

TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

OUTPUT_DIR = "/home/dantalion/Documents/devOpsCore/loreRepo/data"

DELAY = 0.2
TIMEOUT = 10
MAX_RETRIES = 3


# ─────────────────────────────────────────────
# PAGINACIÓN
# ─────────────────────────────────────────────
def get_paginated(url):
    results = []
    page = 1

    while True:
        print(f"📄 Página {page}...")
        resp = requests.get(
            url,
            headers=HEADERS,
            params={"per_page": 100, "page": page},
            timeout=TIMEOUT
        )

        if not resp.ok:
            print(f"❌ Error {resp.status_code}: {resp.text[:100]}")
            break

        data = resp.json()
        items = data.get("workflow_runs", [])

        if not items:
            break

        results.extend(items)
        page += 1

    return results


# ─────────────────────────────────────────────
# AUTOR DEL COMMIT (ROBUSTO)
# ─────────────────────────────────────────────
def get_commit_author(sha):
    url = f"{BASE_URL}/commits/{sha}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(DELAY)

            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if resp.status_code == 404:
                print(f"⚠️ SHA no encontrado: {sha}")
                return "unknown", "unknown"

            if resp.status_code == 403:
                print("⛔ Rate limit alcanzado. Esperando 10s...")
                time.sleep(10)
                continue

            if not resp.ok:
                print(f"⚠️ Error {resp.status_code} en SHA {sha}")
                continue

            data = resp.json()

            name = data.get("commit", {}).get("author", {}).get("name", "unknown")
            email = data.get("commit", {}).get("author", {}).get("email", "unknown")

            return name, email

        except requests.exceptions.Timeout:
            print(f"⏳ Timeout en SHA {sha} (intento {attempt})")

        except Exception as e:
            print(f"❌ Error inesperado en SHA {sha}: {e}")

    return "unknown", "unknown"


# ─────────────────────────────────────────────
# FILTRO FECHA
# ─────────────────────────────────────────────
def filter_runs_by_date(runs, since=None, until=None):
    if not since and not until:
        return runs

    since_dt = datetime.fromisoformat(since) if since else None
    until_dt = datetime.fromisoformat(until) if until else None

    filtered = []

    for r in runs:
        created = datetime.fromisoformat(r["created_at"].replace("Z", ""))

        if since_dt and created < since_dt:
            continue
        if until_dt and created > until_dt:
            continue

        filtered.append(r)

    return filtered


# ─────────────────────────────────────────────
# EXPORT CSV CON PROGRESO
# ─────────────────────────────────────────────
def export_runs_csv(runs, filename):
    campos = [
        "id",
        "name",
        "status",
        "conclusion",
        "head_branch",
        "head_sha",
        "created_at",
        "event",
        "commit_author_name",
        "commit_author_email",
    ]

    total = len(runs)
    errors = 0

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()

        for i, r in enumerate(runs, 1):
            sha = r.get("head_sha")

            print(f"🔍 [{i}/{total}] Procesando SHA: {sha}")

            name, email = get_commit_author(sha)

            if name == "unknown":
                errors += 1

            writer.writerow({
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "head_branch": r.get("head_branch"),
                "head_sha": sha,
                "created_at": r.get("created_at"),
                "event": r.get("event"),
                "commit_author_name": name,
                "commit_author_email": email,
            })

    print(f"\n✅ CSV generado: {filename}")
    print(f"⚠️ SHAs sin resolver: {errors}/{total}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main(since=None, until=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_file = os.path.join(OUTPUT_DIR, "pipeline_runs.csv")

    print("📦 Obteniendo runs...")
    runs = get_paginated(f"{BASE_URL}/actions/runs")

    print(f"📊 Total runs: {len(runs)}")

    runs = filter_runs_by_date(runs, since, until)

    print(f"📅 Runs filtrados: {len(runs)}")

    export_runs_csv(runs, output_file)


# ─────────────────────────────────────────────
# EJECUCIÓN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main(
        since="2026-03-23",
        until="2026-04-11"
    )