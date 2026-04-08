from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, LongTable
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import html
import pandas as pd
import os
from datetime import datetime

def generate_pdf_from_csv(csv_path="data/author_consistency_report.csv",
                          output_path="data/author_report.pdf",
                          since=None,
                          until=None,
                          branches=None,
                          exclude_authors=None):
    """
    Genera un PDF a partir del CSV de author consistency.
    
    Args:
        csv_path: Ruta al archivo CSV con los datos
        output_path: Ruta donde guardar el PDF
        since: Fecha inicial (YYYY-MM-DD)
        until: Fecha final (YYYY-MM-DD)
        branches: Ramas analizadas (string o lista)
        exclude_authors: Lista de autores a excluir del reporte
    """
    
    # Lista de autores a excluir por defecto
    if exclude_authors is None:
        exclude_authors = [
            "Johan Marcelo Beltrán Montaño",
            "Johan-py",
            "Jose Jonatan Zambrana Escobar",
            "JonatanZambrana",
            "Roberto Carlos Emilio Alejo",
            "Emilio Alejo Roberto Carlos"
        ]

    # -------------------------------
    # Validar existencia del CSV
    # -------------------------------
    if not os.path.exists(csv_path):
        print(f"❌ No existe el archivo: {csv_path}")
        return

    df = pd.read_csv(csv_path, encoding="utf-8")
    if df.empty:
        print("❌ El CSV está vacío")
        return

    # -------------------------------
    # Validar columnas necesarias
    # -------------------------------
    required_columns = [
        "author", "total_commits", "total_lines_changed",
        "commit_score",  # 🆕
        "message_score", "size_score", "frequency_score",
        "granularity_score", "consistency_score"
    ]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Falta la columna en CSV: {col}")

    # -------------------------------
    # EXCLUIR AUTORES
    # -------------------------------
    original_count = len(df)
    
    # Filtrar autores excluidos (case-insensitive)
    df = df[~df['author'].str.strip().str.lower().isin([author.lower() for author in exclude_authors])]
    
    excluded_count = original_count - len(df)
    
    # Verificar si después de excluir aún hay datos
    if df.empty:
        print("❌ No hay autores para mostrar después de excluir los especificados")
        return

    # -------------------------------
    # Ordenar por consistency_score
    # -------------------------------
    df = df.sort_values(by="consistency_score", ascending=False)

    # -------------------------------
    # Preparar documento PDF
    # -------------------------------
    doc = SimpleDocTemplate(output_path, pagesize=letter, 
                           rightMargin=30, leftMargin=30,
                           topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Crear estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    elements = []

    # ===============================
    # TÍTULO
    # ===============================
    try:
        title = Paragraph("<para align='center'><b>Reporte de Consistencia de Contribuciones</b></para>", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
    except Exception as e:
        print(f"⚠️ Error en título: {e}")
        elements.append(Paragraph("Reporte de Consistencia de Contribuciones", styles["Title"]))
        elements.append(Spacer(1, 12))

    # ===============================
    # INFORMACIÓN DEL ANÁLISIS
    # ===============================
    try:
        info_lines = []
        
        # Fechas
        if since and until:
            info_lines.append(f"📅 Rango de fechas: {since} → {until}")
        elif since:
            info_lines.append(f"📅 Desde: {since} → Actual")
        elif until:
            info_lines.append(f"📅 Hasta: {until}")
        else:
            info_lines.append("📅 Rango: TODO el historial")
        
        # Ramas analizadas
        if branches:
            if isinstance(branches, list):
                branches_str = ", ".join(branches)
            else:
                branches_str = branches
            info_lines.append(f"🌿 Ramas analizadas: {branches_str}")
        
        # Fecha de generación
        info_lines.append(f"📅 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for line in info_lines:
            elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 4))
        
        elements.append(Spacer(1, 6))
    except Exception as e:
        print(f"⚠️ Error en información: {e}")
    
    # Mostrar información de exclusión
    if excluded_count > 0:
        try:
            exclude_text = f"⚠️ Se excluyeron {excluded_count} autores del reporte"
            elements.append(Paragraph(exclude_text, styles["Normal"]))
            elements.append(Spacer(1, 10))
        except:
            pass

    # ===============================
    # ESTADÍSTICAS GENERALES
    # ===============================
    try:
        elements.append(Paragraph("Estadísticas Generales", styles["Heading3"]))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Modelo de Evaluación", styles["Heading3"]))
        elements.append(Spacer(1, 6))

        formula_text = """
        Score = 20% Commits + 20% Mensajes + 20% Tamaño + 20% Frecuencia + 20% Granularidad
        """

        elements.append(Paragraph(formula_text, styles["Normal"]))
        elements.append(Spacer(1, 10))
        total_authors = len(df)
        total_commits = df['total_commits'].sum()
        total_lines = df['total_lines_changed'].sum()
        avg_consistency = df['consistency_score'].mean()
        high_performers = len(df[df['consistency_score'] >= 80])
        medium_performers = len(df[(df['consistency_score'] >= 60) & (df['consistency_score'] < 80)])
        low_performers = len(df[df['consistency_score'] < 60])
        
        stats_data = []
        stats_data.append(["Métrica", "Valor"])
        stats_data.append(["Total de autores", f"{total_authors}"])
        stats_data.append(["Total de commits", f"{total_commits:,}"])
        stats_data.append(["Total de líneas cambiadas", f"{total_lines:,}"])
        stats_data.append(["Consistencia promedio", f"{avg_consistency:.1f}/100"])
        stats_data.append(["Autores destacados (≥80)", f"{high_performers} ({high_performers/total_authors*100:.1f}%)" if total_authors > 0 else "0"])
        stats_data.append(["Autores intermedios (60-79)", f"{medium_performers} ({medium_performers/total_authors*100:.1f}%)" if total_authors > 0 else "0"])
        stats_data.append(["Autores por mejorar (<60)", f"{low_performers} ({low_performers/total_authors*100:.1f}%)" if total_authors > 0 else "0"])
        
        stats_table = Table(stats_data, colWidths=[150, 150])
        stats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
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
    # TOP 3 AUTORES
    # ===============================
    try:
        top3 = df.head(3)
        elements.append(Paragraph("Top 3 Contributors", styles["Heading3"]))
        elements.append(Spacer(1, 8))

        for i, (_, row) in enumerate(top3.iterrows(), start=1):
            score = row['consistency_score']
            author_name = html.escape(str(row['author']))
            commits = int(row['total_commits'])
            lines = int(row['total_lines_changed'])
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            text = (
                f"{medal} {i}. {author_name} — Score: {score:.2f} | "
                f"C:{row['commit_score']:.0f} M:{row['message_score']:.0f} "
                f"S:{row['size_score']:.0f} F:{row['frequency_score']:.0f} "
                f"G:{row['granularity_score']:.0f}"
            )
            elements.append(Paragraph(text, styles["Normal"]))
            elements.append(Spacer(1, 4))

        elements.append(Spacer(1, 15))
    except Exception as e:
        print(f"⚠️ Error en top 3: {e}")

    # ===============================
    # TABLA COMPLETA
    # ===============================
    try:
        elements.append(Paragraph("Reporte Detallado por Autor", styles["Heading3"]))
        elements.append(Spacer(1, 8))
        
        columns = [
            "Autor", "Commits", "Líneas",
            "Commits#",   # 🆕
            "Mensajes",
            "Tamaño",
            "Frecuencia",
            "Granularidad",
            "Score"
        ]
        data = [columns]

        for _, row in df.iterrows():
            # Función para formatear puntuaciones
            def format_score(score):
                if pd.isna(score):
                    return "0.0"
                if score >= 80:
                    return f"{score:.1f}"
                elif score >= 60:
                    return f"{score:.1f}"
                elif score >= 40:
                    return f"{score:.1f}"
                else:
                    return f"{score:.1f}"
            
            data.append([
                html.escape(str(row["author"])),
                f"{int(row['total_commits']):,}",
                f"{int(row['total_lines_changed']):,}",
                format_score(row["commit_score"]),
                format_score(row["message_score"]),
                format_score(row["size_score"]),
                format_score(row["frequency_score"]),
                format_score(row["granularity_score"]),
                format_score(row["consistency_score"]),
            ])

        # Calcular anchos de columna
        col_widths = [130, 50, 60, 50, 50, 50, 50, 55, 60]
        table = LongTable(data, repeatRows=1, colWidths=col_widths)

        # Estilo base de la tabla
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
        ]
        
        # Colorear filas según puntuación general
        for i, row in enumerate(data[1:], start=1):
            try:
                score = float(row[-1])
                if score >= 80:
                    bg = colors.lightgreen
                elif score >= 60:
                    bg = colors.khaki
                elif score >= 40:
                    bg = colors.orange
                else:
                    bg = colors.salmon
                table_style.append(("BACKGROUND", (0, i), (-1, i), bg))
            except:
                pass
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)

    except Exception as e:
        print(f"⚠️ Error en tabla: {e}")
        # Tabla simple sin formato complejo como fallback
        try:
            elements.append(Paragraph("Reporte Detallado por Autor", styles["Heading3"]))
            elements.append(Spacer(1, 8))
            
            simple_data = [["Autor", "Commits", "Líneas", "Puntuación"]]
            for _, row in df.head(20).iterrows():
                simple_data.append([
                    html.escape(str(row["author"])),
                    str(int(row['total_commits'])),
                    str(int(row['total_lines_changed'])),
                    f"{row['consistency_score']:.1f}"
                ])
            
            simple_table = Table(simple_data)
            simple_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            elements.append(simple_table)
        except:
            pass

    # ===============================
    # NOTAS AL PIE
    # ===============================
    try:
        elements.append(Spacer(1, 20))
        footer_text = """
        Notas:
        • Puntuación de Consistencia: promedio ponderado de 5 métricas (20% cada una)
        • Commits: evalúa si el número de commits está dentro del rango ideal del sprint
        • Mensajes: porcentaje de commits con formato Conventional Commit
        • Tamaño: consistencia en el tamaño de los commits (desviación estándar)
        • Frecuencia: regularidad de actividad durante el sprint
        • Granularidad: penaliza commits excesivamente grandes
        """
        elements.append(Paragraph(footer_text, styles["Normal"]))
    except Exception as e:
        print(f"⚠️ Error en notas: {e}")

    # ===============================
    # GENERAR PDF
    # ===============================
    try:
        doc.build(elements)
        print(f"✅ PDF generado en: {output_path}")
        print(f"   📊 {len(df)} autores analizados")
        print(f"   📈 Consistencia promedio: {avg_consistency:.1f}/100")
        print(f"   🏆 Top contributor: {df.iloc[0]['author']} ({df.iloc[0]['consistency_score']:.1f})")
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")
        
        # Intentar con una versión más simple
        print("🔄 Intentando generar PDF con formato simplificado...")
        doc2 = SimpleDocTemplate(output_path.replace('.pdf', '_simple.pdf'), pagesize=letter)
        simple_elements = []
        simple_elements.append(Paragraph("Reporte de Consistencia de Contribuciones", styles["Title"]))
        simple_elements.append(Spacer(1, 12))
        
        # Tabla simple
        simple_data = [["Autor", "Commits", "Líneas", "Puntuación"]]
        for _, row in df.head(20).iterrows():
            simple_data.append([
                str(row["author"]),
                str(int(row['total_commits'])),
                str(int(row['total_lines_changed'])),
                f"{row['consistency_score']:.1f}"
            ])
        
        simple_table = Table(simple_data)
        simple_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        simple_elements.append(simple_table)
        
        doc2.build(simple_elements)
        print(f"✅ PDF simplificado generado en: {output_path.replace('.pdf', '_simple.pdf')}")


# -------------------------------
# Ejecución directa
# -------------------------------
if __name__ == "__main__":
    generate_pdf_from_csv(
        since="2026-03-20", 
        until="2026-03-27",
        branches=["main", "develop"]
    )