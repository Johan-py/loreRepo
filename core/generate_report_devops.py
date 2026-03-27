from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, LongTable
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
import html
import pandas as pd
import os

def generate_devops_pdf(csv_path="data/author_consistency_report.csv",
                        output_path="data/devops_report.pdf",
                        since=None,
                        until=None,
                        devops_authors=None,
                        tasks_config=None):
    """
    Genera un PDF únicamente con los autores DevOps excluidos del ranking principal.
    - Incluye autores aunque no tengan commits.
    - Tareas se asignan individualmente y Puntuacion depende del número de tareas completadas.
    """
    
    # Configuración de autores por defecto
    if devops_authors is None:
        devops_authors = [
            "Johan Marcelo Beltrán Montaño",
            "Jose Jonatan Zambrana Escobar",
            "Roberto Carlos Emilio Alejo"
        ]
    
    # Configuración de tareas por autor (dict con formato "completadas/total")
    if tasks_config is None:
        tasks_config = {
            "Johan Marcelo Beltrán Montaño": "4/4",
            "Jose Jonatan Zambrana Escobar": "3/3",
            "Roberto Carlos Emilio Alejo": "1/1"
        }

    # Crear DataFrame vacío si CSV no existe o está vacío
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        df = pd.DataFrame(columns=["author","total_commits","total_lines_changed"])
    else:
        df = pd.read_csv(csv_path, encoding="utf-8")

    # Preparar PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Título y rango de fechas
    elements.append(Paragraph("<para align='center'><b>Reporte Equipo DevOps</b></para>", styles["Title"]))
    elements.append(Spacer(1, 12))
    if since and until:
        elements.append(Paragraph(f"<para align='center'>Rango de fechas: {since} → {until}</para>", styles["Normal"]))
        elements.append(Spacer(1, 10))
    
    # Mostrar leyenda de tareas
    elements.append(Paragraph("<para align='center'><b>Evaluación de Tareas por Autor</b></para>", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    columns = ["Autor", "Commits", "Líneas", "Tareas", "Puntuacion"]
    data = [columns]

    for author in devops_authors:
        # Datos por defecto
        commits = 0
        lines = 0

        # Buscar datos en CSV (si existe)
        if "author" in df.columns:
            # Buscar coincidencia exacta o parcial
            author_match = df[df['author'].str.strip().str.lower() == author.lower()]
            if not author_match.empty:
                row = author_match.iloc[0]
                commits = int(row.get('total_commits', 0))
                lines = int(row.get('total_lines_changed', 0))

        # Obtener tareas para este autor
        tareas = tasks_config.get(author, "0/0")
        
        # Calcular puntuación basada en tareas completadas
        try:
            done, total = map(int, tareas.split("/"))
            if total > 0:
                puntuacion = int((done / total) * 100)
            else:
                puntuacion = 0
        except:
            puntuacion = 0
            tareas = "0/0"

        data.append([
            Paragraph(html.escape(author), styles["Normal"]),
            commits,
            lines,
            tareas,
            puntuacion
        ])

    # Crear tabla
    col_widths = [200, 60, 60, 60, 70]
    table = LongTable(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("ALIGN", (0,1), (0,-1), "LEFT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
    ]))

    # Colorear puntuación
    for i, row in enumerate(data[1:], start=1):
        try:
            score = float(row[-1])
            if score >= 80:
                bg = colors.lightgreen
            elif score >= 50:
                bg = colors.khaki
            else:
                bg = colors.salmon
            table.setStyle([("BACKGROUND", (-1,i), (-1,i), bg)])
        except:
            pass

    elements.append(table)
    
    # Agregar detalle de tareas al final
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<para><b>Detalle de Tareas:</b></para>", styles["Heading4"]))
    elements.append(Spacer(1, 5))
    
    for author in devops_authors:
        tareas = tasks_config.get(author, "0/0")
        done, total = map(int, tareas.split("/"))
        if total > 0:
            percentage = int((done / total) * 100)
            status = "✅ Completado" if done == total else f"⏳ {done}/{total} completadas"
            task_detail = f"• <b>{author}</b>: {tareas} tareas ({percentage}%) - {status}"
        else:
            task_detail = f"• <b>{author}</b>: Sin tareas asignadas"
        elements.append(Paragraph(task_detail, styles["Normal"]))
        elements.append(Spacer(1, 3))

    # Generar PDF
    doc.build(elements)
    print(f"✅ PDF DevOps generado en: {output_path}")
    print("\n📊 Resumen de tareas:")
    for author in devops_authors:
        tareas = tasks_config.get(author, "0/0")
        done, total = map(int, tareas.split("/"))
        print(f"  • {author}: {done}/{total} tareas completadas ({int((done/total)*100) if total > 0 else 0}%)")
    
if __name__ == "__main__":
    generate_devops_pdf(
        csv_path="data/author_consistency_report.csv",
        output_path="data/devops_report.pdf",
        since="2026-03-20",
        until="2026-03-27"
    )