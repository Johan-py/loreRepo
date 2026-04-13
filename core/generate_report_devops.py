from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, LongTable
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import html
import pandas as pd
import os
from datetime import datetime


def generate_devops_pdf(csv_path="data/author_consistency_report.csv",
                        output_path="data/devops_report.pdf",
                        since=None,
                        until=None,
                        branches=None,
                        devops_authors=None,
                        tasks_config=None):

    # ===============================
    # AUTORES
    # ===============================
    if devops_authors is None:
        devops_authors = [
            "Johan Marcelo Beltrán Montaño",
            "Jose Jonatan Zambrana Escobar",
            "Roberto Carlos Emilio Alejo"
        ]

    # ===============================
    # TAREAS CON % Y SCORE
    # ===============================
    if tasks_config is None:
        tasks_config = {
            "Johan Marcelo Beltrán Montaño": [
                {"title": "CI/CD", "desc": "Pipeline GitHub Actions", "progress": 100, "score": 20},
                {"title": "Deploy", "desc": "Vercel + Render", "progress": 60, "score": 20},
                {"title": "Soporte", "desc": "107/115 incidentes (~93%)", "progress": 93, "score": 30},
                {"title": "Asistencia", "desc": "Cobertura 74%", "progress": 74, "score": 10},
                {"title": "Automatización", "desc": "Scripts DevOps", "progress": 100, "score": 20},
                {"title": "Review", "desc": "Presentacion review", "progress": 95, "score": 30},

            ],
            "Jose Jonatan Zambrana Escobar": [
                {"title": "DB", "desc": "Diseño y setup", "progress": 100, "score": 30},
                {"title": "Soporte DB", "desc": "Asistencia equipos", "progress": 50.9, "score": 20},
                {"title": "Testing", "desc": "Tests backend", "progress": 20, "score": 25},
                {"title": "Monitoring", "desc": "Monitoreo backend", "progress": 20, "score": 25},
                {"title": "Review", "desc": "Presentacion review", "progress": 95, "score": 30},

            ],
            "Roberto Carlos Emilio Alejo": [
                {"title": "Monitoreo repo", "desc": "Supervisión continua", "progress": 20, "score": 30},
                {"title": "Incidentes críticos", "desc": "Soporte conflictos", "progress": 70, "score": 40},
                {"title": "Control PRs", "desc": "Validación estándares", "progress": 15, "score": 30},
                {"title": "Review", "desc": "Presentacion review", "progress": 95, "score": 30},

            ]
        }

    # ===============================
    # DATA
    # ===============================
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        df = pd.DataFrame(columns=["author", "total_commits", "total_lines_changed"])
    else:
        df = pd.read_csv(csv_path, encoding="utf-8")

    # ===============================
    # PDF SETUP
    # ===============================
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        alignment=TA_CENTER,
        textColor=colors.orange
    )

    elements = []

    # ===============================
    # HEADER
    # ===============================
    elements.append(Paragraph("Reporte DevOps", title_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Generado: {datetime.now()}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    # ===============================
    # TABLA PRINCIPAL
    # ===============================
    data = [["Autor", "Commits", "Líneas", "Score"]]

    for author in devops_authors:
        commits = 0
        lines = 0

        if "author" in df.columns:
            match = df[df['author'].str.lower().str.strip() == author.lower()]
            if not match.empty:
                row = match.iloc[0]
                commits = int(row.get("total_commits", 0))
                lines = int(row.get("total_lines_changed", 0))

        tasks = tasks_config.get(author, [])

        total_weight = sum(t.get("score", 0) for t in tasks)
        weighted_score = sum((t.get("progress", 0) * t.get("score", 0)) for t in tasks)

        final_score = int(weighted_score / total_weight) if total_weight > 0 else 0

        data.append([
            html.escape(author),
            f"{commits:,}",
            f"{lines:,}",
            f"{final_score}"
        ])

    table = LongTable(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)

    # ===============================
    # DETALLE DE TAREAS
    # ===============================
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Detalle de Tareas", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    for author in devops_authors:
        elements.append(Paragraph(f"<b>{html.escape(author)}</b>", styles["Normal"]))
        elements.append(Spacer(1, 4))

        tasks = tasks_config.get(author, [])

        total_weight = sum(t.get("score", 0) for t in tasks)
        weighted_score = sum((t.get("progress", 0) * t.get("score", 0)) for t in tasks)
        final_score = int(weighted_score / total_weight) if total_weight > 0 else 0

        for t in tasks:
            progress = t.get("progress", 0)
            score = t.get("score", 0)

            text = f"{progress}% | ({score} pts) <b>{html.escape(t['title'])}</b>: {html.escape(t['desc'])}"
            elements.append(Paragraph(text, styles["Normal"]))
            elements.append(Spacer(1, 3))

        elements.append(Paragraph(f"<i>Score final: {final_score}</i>", styles["Normal"]))
        elements.append(Spacer(1, 10))

    # ===============================
    # BUILD
    # ===============================
    doc.build(elements)

    print(f"✅ PDF generado en: {output_path}")

    # ===============================
    # RESUMEN CONSOLA
    # ===============================
    print("\nResumen:")
    for author in devops_authors:
        tasks = tasks_config.get(author, [])

        total_weight = sum(t.get("score", 0) for t in tasks)
        weighted_score = sum((t.get("progress", 0) * t.get("score", 0)) for t in tasks)

        final_score = int(weighted_score / total_weight) if total_weight > 0 else 0

        print(f"• {author}: {final_score}%")


if __name__ == "__main__":
    generate_devops_pdf(
        since="2026-03-20",
        until="2026-03-27",
        branches=["main", "develop"]
    )