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
    """
    Genera un PDF únicamente con los autores DevOps excluidos del ranking principal.
    - Incluye autores aunque no tengan commits.
    - Tareas se asignan individualmente y Puntuacion depende del número de tareas completadas.
    
    Args:
        csv_path: Ruta al archivo CSV con los datos
        output_path: Ruta donde guardar el PDF
        since: Fecha inicial (YYYY-MM-DD)
        until: Fecha final (YYYY-MM-DD)
        branches: Ramas analizadas (string o lista)
        devops_authors: Lista de autores DevOps
        tasks_config: Configuración de tareas por autor
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
        df = pd.DataFrame(columns=["author","total_commits","total_lines_changed","message_score","size_score","frequency_score","granularity_score"])
    else:
        df = pd.read_csv(csv_path, encoding="utf-8")

    # Preparar PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=30, leftMargin=30,
                           topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Crear estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#FF9800')
    )
    
    elements = []

    # ===============================
    # TÍTULO E INFORMACIÓN
    # ===============================
    try:
        title = Paragraph("Reporte Equipo DevOps", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
    except:
        elements.append(Paragraph("Reporte Equipo DevOps", styles["Title"]))
        elements.append(Spacer(1, 12))
    
    # Información del análisis
    try:
        info_lines = []
        
        # Fechas
        if since and until:
            info_lines.append(f"Rango de fechas: {since} → {until}")
        elif since:
            info_lines.append(f"Desde: {since} → Actual")
        elif until:
            info_lines.append(f"Hasta: {until}")
        else:
            info_lines.append("Rango: TODO el historial")
        
        # Ramas analizadas
        if branches:
            if isinstance(branches, list):
                branches_str = ", ".join(branches)
            else:
                branches_str = branches
            info_lines.append(f"Ramas analizadas: {branches_str}")
        
        # Fecha de generación
        info_lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for line in info_lines:
            elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 4))
        
        elements.append(Spacer(1, 6))
    except Exception as e:
        print(f"⚠️ Error en información: {e}")

    # ===============================
    # ESTADÍSTICAS DEL EQUIPO
    # ===============================
    try:
        elements.append(Paragraph("Estadísticas del Equipo", styles["Heading3"]))
        elements.append(Spacer(1, 8))
        
        # Calcular estadísticas solo para autores DevOps que están en el CSV
        devops_data = []
        total_devops_commits = 0
        total_devops_lines = 0
        
        for author in devops_authors:
            if "author" in df.columns:
                author_match = df[df['author'].str.strip().str.lower() == author.lower()]
                if not author_match.empty:
                    row = author_match.iloc[0]
                    commits = int(row.get('total_commits', 0))
                    lines = int(row.get('total_lines_changed', 0))
                    total_devops_commits += commits
                    total_devops_lines += lines
                    devops_data.append({
                        'author': author,
                        'commits': commits,
                        'lines': lines,
                    })
        
        if devops_data:
            
            stats_data = []
            stats_data.append(["Métrica", "Valor"])
            stats_data.append(["Miembros del equipo", f"{len(devops_authors)}"])
            stats_data.append(["Total de commits", f"{total_devops_commits:,}"])
            stats_data.append(["Total de líneas cambiadas", f"{total_devops_lines:,}"])
            
            stats_table = Table(stats_data, colWidths=[150, 150])
            stats_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor('#FF9800')),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            
            elements.append(stats_table)
            elements.append(Spacer(1, 15))
    except Exception as e:
        print(f"⚠️ Error en estadísticas: {e}")

    # ===============================
    # TABLA DE EVALUACIÓN
    # ===============================
    try:
        elements.append(Paragraph("Evaluación de Tareas por Autor", styles["Heading3"]))
        elements.append(Spacer(1, 8))

        # Definir columnas (SIN columna de consistencia)
        columns = ["Autor", "Commits", "Líneas", "Tareas", "Puntuación"]
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
                    task_score = int((done / total) * 100)
                else:
                    task_score = 0
            except:
                task_score = 0
                tareas = "0/0"

            data.append([
                html.escape(author),
                f"{commits:,}",
                f"{lines:,}",
                tareas,
                f"{task_score}"
            ])

        # Crear tabla
        col_widths = [180, 60, 70, 60, 70]
        table = LongTable(data, repeatRows=1, colWidths=col_widths)
        
        table_style = [
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor('#FF9800')),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("ALIGN", (0,0), (-1,0), "CENTER"),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("ALIGN", (0,1), (0,-1), "LEFT"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("FONTSIZE", (0,1), (-1,-1), 9),
        ]
        
        # Colorear filas según puntuación de tareas
        for i, row in enumerate(data[1:], start=1):
            try:
                score = float(row[4])
                if score >= 80:
                    bg = colors.lightgreen
                elif score >= 60:
                    bg = colors.khaki
                elif score >= 40:
                    bg = colors.orange
                else:
                    bg = colors.salmon
                table_style.append(("BACKGROUND", (4, i), (4, i), bg))
            except:
                pass
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
    except Exception as e:
        print(f"⚠️ Error en tabla: {e}")

    # ===============================
    # DETALLE DE TAREAS
    # ===============================
    try:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Detalle de Tareas por Autor", styles["Heading4"]))
        elements.append(Spacer(1, 8))
        
        for author in devops_authors:
            tareas = tasks_config.get(author, "0/0")
            try:
                done, total = map(int, tareas.split("/"))
                if total > 0:
                    percentage = int((done / total) * 100)
                    if done == total:
                        status = "Completado"
                    else:
                        status = f"{done}/{total} completadas"
                    task_detail = f"• {author}: {tareas} tareas ({percentage}%) - {status}"
                else:
                    task_detail = f"• {author}: Sin tareas asignadas"
            except:
                task_detail = f"• {author}: Configuración de tareas inválida"
            
            elements.append(Paragraph(task_detail, styles["Normal"]))
            elements.append(Spacer(1, 3))
    except Exception as e:
        print(f"⚠️ Error en detalle de tareas: {e}")

    # ===============================
    # MÉTRICAS DE CONSISTENCIA
    # ===============================
    # if devops_data:
    #     try:
    #         elements.append(Spacer(1, 15))
    #         elements.append(Paragraph("Métricas de Consistencia del Equipo", styles["Heading4"]))
    #         elements.append(Spacer(1, 5))
            
    #         for data in sorted(devops_data, key=lambda x: x['consistency'], reverse=True):
    #             author_name = data['author']
    #             consistency = data['consistency']
    #             consistency_text = f"• {author_name}: {consistency:.1f}/100"
    #             elements.append(Paragraph(consistency_text, styles["Normal"]))
    #             elements.append(Spacer(1, 2))
    #     except Exception as e:
    #         print(f"⚠️ Error en métricas: {e}")

    # ===============================
    # NOTAS Y CONCLUSIONES
    # ===============================
    try:
        elements.append(Spacer(1, 20))
        footer_text = """
        Notas:
        • Puntuación de tareas: basada en el porcentaje de tareas completadas
        • Los autores DevOps son evaluados tanto por su contribución en código como por la finalización de tareas
        • Este reporte complementa el ranking general de consistencia
        """
        elements.append(Paragraph(footer_text, styles["Normal"]))
    except Exception as e:
        print(f"⚠️ Error en notas: {e}")

    # ===============================
    # GENERAR PDF
    # ===============================
    try:
        doc.build(elements)
        print(f"✅ PDF DevOps generado en: {output_path}")
        print("\n📊 Resumen del Equipo DevOps:")
        for author in devops_authors:
            tareas = tasks_config.get(author, "0/0")
            try:
                done, total = map(int, tareas.split("/"))
                if total > 0:
                    percentage = int((done / total) * 100)
                    print(f"  • {author}: {done}/{total} tareas completadas ({percentage}%)")
                else:
                    print(f"  • {author}: Sin tareas asignadas")
            except:
                print(f"  • {author}: Error en configuración de tareas")
        
        # Mostrar estadísticas de commits
        if devops_data:
            print(f"\n📈 Estadísticas de código:")
            print(f"  • Total commits: {total_devops_commits:,}")
            print(f"  • Total líneas: {total_devops_lines:,}")
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")


if __name__ == "__main__":
    generate_devops_pdf(
        csv_path="data/author_consistency_report.csv",
        output_path="data/devops_report.pdf",
        since="2026-03-20",
        until="2026-03-27",
        branches=["main", "develop"]
    )