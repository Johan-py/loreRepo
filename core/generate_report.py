from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, LongTable
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
import html
import pandas as pd
import os

def generate_pdf_from_csv(csv_path="data/author_consistency_report.csv",
                          output_path="data/author_report.pdf",
                          since=None,
                          until=None,
                          exclude_authors=None):
    """
    Genera un PDF a partir del CSV de author consistency.
    since, until: cadenas 'YYYY-MM-DD' para mostrar rango de fechas en el PDF
    exclude_authors: lista de autores a excluir del reporte
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
    # if excluded_count > 0:
    #     print(f"📊 Se excluyeron {excluded_count} autores del reporte")
    
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
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # -------------------------------
    # Título
    # -------------------------------
    title = Paragraph("<para align='center'><b>Reporte de Consistencia de Contribuciones</b></para>", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Rango de fechas
    # -------------------------------
    if since and until:
        date_range_text = f"<para align='center'>Rango de fechas: {since} → {until}</para>"
        elements.append(Paragraph(date_range_text, styles["Normal"]))
        elements.append(Spacer(1, 10))
    
    # Mostrar información de exclusión
    if excluded_count > 0:
        exclude_text = f"<para align='center'><font color='red'>⚠️ Se excluyeron {excluded_count} autores del reporte</font></para>"
        elements.append(Paragraph(exclude_text, styles["Normal"]))
        elements.append(Spacer(1, 10))

    # -------------------------------
    # Top 3 autores (después de exclusión)
    # -------------------------------
    top3 = df.head(3)
    elements.append(Paragraph("🏆 Top 3 Contributors", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    for i, (_, row) in enumerate(top3.iterrows(), start=1):
        score = row['consistency_score']
        if score >= 80:
            color = "green"
        elif score >= 50:
            color = "orange"
        else:
            color = "red"
        text = f"<b>{i}. {html.escape(row['author'])}</b> — <font color='{color}'><b>{score:.2f}</b></font>"
        elements.append(Paragraph(text, styles["Normal"]))

    elements.append(Spacer(1, 15))

    # -------------------------------
    # Tabla completa
    # -------------------------------
    columns = ["Autor", "Commits", "Líneas", "Mensajes", "Tama", "Frequen", "Granula", "Puntuacion"]
    data = [columns]

    for _, row in df.iterrows():
        data.append([
            Paragraph(html.escape(str(row["author"])), styles["Normal"]),
            int(row["total_commits"]),
            int(row["total_lines_changed"]),
            f'{row["message_score"]:.1f}',
            f'{row["size_score"]:.1f}',
            f'{row["frequency_score"]:.1f}',
            f'{row["granularity_score"]:.1f}',
            f'{row["consistency_score"]:.1f}',
        ])

    col_widths = [160, 60, 70, 50, 50, 50, 50, 60]
    table = LongTable(data, repeatRows=1, colWidths=col_widths)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    # Colorear columna de Score dinámicamente
    for i, row in enumerate(data[1:], start=1):
        score = float(row[-1])
        if score >= 80:
            bg = colors.lightgreen
        elif score >= 50:
            bg = colors.khaki
        else:
            bg = colors.salmon
        table.setStyle([("BACKGROUND", (-1, i), (-1, i), bg)])

    elements.append(table)

    # -------------------------------
    # Generar PDF
    # -------------------------------
    doc.build(elements)
    print(f"✅ PDF generado en: {output_path}")


# -------------------------------
# Ejecución directa
# -------------------------------
if __name__ == "__main__":
    # ejemplo de fechas
    generate_pdf_from_csv(since="2026-03-20", until="2026-03-27")