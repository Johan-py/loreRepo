from core.analyzer import run_analysis, generate_team_report
from core.github_actions_export import main as github_main
import os

def run_full_pipeline(repo_url, since=None, until=None):
    print("🚀 Iniciando pipeline completo")

    # 1. ANALISIS GIT
    print("📦 Ejecutando análisis de commits...")
    run_analysis(
        repo_url=repo_url,
        since=since,
        until=until,
        include_all_history=True
    )

    # 2. GITHUB ACTIONS
    print("📦 Extrayendo runs de GitHub Actions...")
    github_main(
        since=since,
        until=until
    )

    # 3. PDF FINAL
    print("📊 Generando PDF...")

    generate_team_report(
        author_csv="data/author_consistency_report.csv",
        pipeline_csv="data/pipeline_runs.csv",
        output="data/team_report.pdf"
    )

    print("✅ Pipeline completado")