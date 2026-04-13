import unicodedata
import io
import os
from datetime import datetime
import html

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak, HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

C = {
    "primary":  "#1A237E",
    "accent":   "#42A5F5",
    "success":  "#2E7D32",
    "warning":  "#F57F17",
    "danger":   "#C62828",
    "bg":       "#F5F7FA",
    "muted":    "#757575",
    "text":     "#212121",
    "grid":     "#E0E0E0",
}

STATUS_COLORS = {"high": C["success"], "medium": C["warning"], "low": C["danger"]}


def normalize(text):
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def build_styles():
    base = getSampleStyleSheet()
    rl_primary = colors.HexColor(C["primary"])
    rl_muted   = colors.HexColor(C["muted"])
    extra = {
        "ReportTitle": ParagraphStyle("ReportTitle", parent=base["Title"],
            fontSize=22, textColor=rl_primary, spaceAfter=2, leading=26),
        "SubTitle": ParagraphStyle("SubTitle", parent=base["Normal"],
            fontSize=10, textColor=rl_muted, spaceAfter=2),
        "SectionHeader": ParagraphStyle("SectionHeader", parent=base["Heading1"],
            fontSize=13, textColor=rl_primary, spaceBefore=12, spaceAfter=5),
        "KPILabel": ParagraphStyle("KPILabel", parent=base["Normal"],
            fontSize=7, textColor=rl_muted, alignment=TA_CENTER),
        "KPIValue": ParagraphStyle("KPIValue", parent=base["Normal"],
            fontSize=20, textColor=rl_primary, alignment=TA_CENTER, leading=24),
        "Insight": ParagraphStyle("Insight", parent=base["Normal"],
            fontSize=9, textColor=colors.HexColor(C["text"]),
            leftIndent=8, spaceBefore=3),
    }
    return {**{k: base[k] for k in base.byName}, **extra}


def fig_to_image(fig, width=6 * inch):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    img = Image(buf)
    aspect = img.imageHeight / img.imageWidth
    img.drawWidth  = width
    img.drawHeight = width * aspect
    plt.close(fig)
    return img


def base_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(C["bg"])
    ax.set_title(title, fontsize=10, fontweight="bold", color=C["primary"], pad=7)
    ax.set_xlabel(xlabel, fontsize=8, color=C["muted"])
    ax.set_ylabel(ylabel, fontsize=8, color=C["muted"])
    ax.tick_params(labelsize=7, colors=C["muted"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(C["grid"])
    ax.grid(color=C["grid"], zorder=0)


# ── GRÁFICA 1: Score por equipo ──────────────
def chart_team_scores(team_df):
    df = team_df.sort_values("team_score")
    fig, ax = plt.subplots(figsize=(7, max(3, len(df) * 0.6)))
    fig.patch.set_facecolor("white")
    bar_colors = [STATUS_COLORS[s] for s in df["status_label"]]
    bars = ax.barh(df["team"], df["team_score"],
                   color=bar_colors, height=0.55, zorder=2)
    ax.axvline(70, color=C["success"], ls="--", lw=1, alpha=0.6, label="Alto (≥70)")
    ax.axvline(55, color=C["warning"], ls="--", lw=1, alpha=0.6, label="Aceptable (≥55)")
    ax.set_xlim(0, 108)
    for bar, val in zip(bars, df["team_score"]):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", fontsize=8, color=C["text"])
    ax.legend(fontsize=7)
    base_ax(ax, "Score de Desempeño por Equipo", "", "Score (0-100)")
    fig.tight_layout()
    return fig_to_image(fig, 5.8 * inch)


# ── GRÁFICA 2: Pipeline success rate ─────────
def chart_pipeline(team_df):
    df = team_df.sort_values("pipeline_success_rate")
    pcts = df["pipeline_success_rate"] * 100
    fig, ax = plt.subplots(figsize=(7, max(3, len(df) * 0.6)))
    fig.patch.set_facecolor("white")
    bar_colors = [C["success"] if p >= 70 else C["warning"] if p >= 55 else C["danger"] for p in pcts]
    bars = ax.barh(df["team"], pcts, color=bar_colors, height=0.55, zorder=2)
    ax.axvline(70, color=C["success"], ls="--", lw=1, alpha=0.6, label="Meta (70%)")
    ax.set_xlim(0, 115)
    for bar, val in zip(bars, pcts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8, color=C["text"])
    ax.legend(fontsize=7)
    base_ax(ax, "Tasa de Exito en Pipelines por Equipo", "", "%")
    fig.tight_layout()
    return fig_to_image(fig, 5.8 * inch)


# ── GRÁFICA 3: Pie de estado ─────────────────
def chart_status_pie(team_df):
    label_map = {"high": "Alto rendimiento", "medium": "Aceptable", "low": "Riesgo"}
    keys   = ["high", "medium", "low"]
    counts = team_df["status_label"].value_counts()
    vals  = [counts.get(k, 0) for k in keys]
    clrs  = [STATUS_COLORS[k] for k in keys]
    lbls  = [label_map[k] for k in keys]
    fig, ax = plt.subplots(figsize=(4, 3.6))
    fig.patch.set_facecolor("white")
    wedges, _, autotexts = ax.pie(
        vals, colors=clrs, autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
        startangle=140, pctdistance=0.72,
        wedgeprops=dict(width=0.52, edgecolor="white", linewidth=2),
    )
    for at in autotexts:
        at.set_fontsize(9); at.set_color("white"); at.set_fontweight("bold")
    ax.legend(wedges, lbls, fontsize=7, loc="lower center",
              bbox_to_anchor=(0.5, -0.06), ncol=3)
    ax.set_title("Distribucion de Estado", fontsize=10, fontweight="bold", color=C["primary"])
    fig.tight_layout()
    return fig_to_image(fig, 3.2 * inch)


# ── GRÁFICA 4: Radar ─────────────────────────
def chart_radar(team_df):
    metrics = ["consistency_score", "frequency_score", "size_score", "pipeline_pct"]
    labels  = ["Consistencia", "Frecuencia", "Tamano\nCommit", "Pipeline\n%"]
    df = team_df.copy()
    df["pipeline_pct"] = df["pipeline_success_rate"] * 100
    df = df.sort_values("team_score", ascending=False).head(6)
    N = len(metrics)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]
    fig, ax = plt.subplots(figsize=(4.5, 4.5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(C["bg"])
    cmap = plt.colormaps.get_cmap("tab10")
    for idx, (_, row) in enumerate(df.iterrows()):
        vals = [row[m] for m in metrics] + [row[metrics[0]]]
        ax.plot(angles, vals, "o-", lw=1.5, color=cmap(idx), label=str(row["team"]))
        ax.fill(angles, vals, alpha=0.08, color=cmap(idx))
    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=6, color=C["muted"])
    ax.grid(color=C["grid"])
    ax.spines["polar"].set_color(C["grid"])
    ax.set_title("Radar de Metricas por Equipo", fontsize=10, fontweight="bold",
                 color=C["primary"], pad=14)
    ax.legend(loc="upper right", bbox_to_anchor=(1.4, 1.1), fontsize=7)
    fig.tight_layout()
    return fig_to_image(fig, 3.8 * inch)


# ── GRÁFICA 5: Burbujas ──────────────────────
def chart_bubble(team_df):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.patch.set_facecolor("white")
    for _, row in team_df.iterrows():
        color = STATUS_COLORS[row["status_label"]]
        size  = max(180, row["team_size"] * 150)
        ax.scatter(row["total_commits"], row["team_score"],
                   s=size, color=color, alpha=0.75,
                   edgecolors="white", lw=1.5, zorder=3)
        ax.annotate(str(row["team"]), (row["total_commits"], row["team_score"]),
                    fontsize=7, ha="center", va="bottom",
                    xytext=(0, 6), textcoords="offset points")
    ax.axhline(70, color=C["success"], ls="--", lw=1, alpha=0.5)
    ax.axhline(55, color=C["warning"], ls="--", lw=1, alpha=0.5)
    legend_els = [
        mpatches.Patch(color=C["success"], label="Alto rendimiento"),
        mpatches.Patch(color=C["warning"], label="Aceptable"),
        mpatches.Patch(color=C["danger"],  label="Riesgo"),
    ]
    ax.legend(handles=legend_els, fontsize=7)
    base_ax(ax, "Actividad vs Desempeno  (tamano = n miembros)",
            "Total Commits", "Score del Equipo")
    fig.tight_layout()
    return fig_to_image(fig, 5.8 * inch)


# ── GRÁFICA 6: Heatmap ───────────────────────
def chart_heatmap(team_df):
    metrics = {
        "Consistencia":  "consistency_score",
        "Frecuencia":    "frequency_score",
        "Tamano Commit": "size_score",
        "Pipeline %":   "pipeline_pct",
        "Score Final":   "team_score",
    }
    df = team_df.copy()
    df["pipeline_pct"] = df["pipeline_success_rate"] * 100
    df = df.sort_values("team_score", ascending=False)
    matrix = df[list(metrics.values())].values
    fig, ax = plt.subplots(figsize=(7, max(3, len(df) * 0.7)))
    fig.patch.set_facecolor("white")
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(list(metrics.keys()), fontsize=8, color=C["text"])
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["team"].tolist(), fontsize=8, color=C["text"])
    for i in range(len(df)):
        for j, col in enumerate(metrics.values()):
            val = matrix[i, j]
            text_color = "white" if val < 40 or val > 80 else C["text"]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=8, color=text_color, fontweight="bold")
    plt.colorbar(im, ax=ax, fraction=0.025, pad=0.04, label="Score (0-100)")
    ax.set_title("Heatmap de Metricas por Equipo", fontsize=10,
                 fontweight="bold", color=C["primary"], pad=8)
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    return fig_to_image(fig, 6.5 * inch)


# ── GRÁFICA 7: Top devs commits + pipeline ───
def chart_dev_commits(author_df, merged_df):
    pipe_stats = merged_df.groupby("author").agg(
        success_runs=("is_success", "sum"),
        total_runs=("is_success", "count"),
    ).reset_index()
    pipe_stats["fail_runs"] = pipe_stats["total_runs"] - pipe_stats["success_runs"]
    dev_df = author_df.merge(pipe_stats, on="author", how="left").fillna(0)
    dev_df = dev_df.nlargest(12, "total_commits")
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("white")
    x = np.arange(len(dev_df))
    ax.bar(x, dev_df["total_commits"], color=C["accent"], label="Commits totales", zorder=2)
    ax2 = ax.twinx()
    ax2.plot(x, dev_df["success_runs"], "o-", color=C["success"], lw=1.5, ms=5, label="Pipeline OK")
    ax2.plot(x, dev_df["fail_runs"], "s--", color=C["danger"],  lw=1.5, ms=5, label="Pipeline Fail")
    ax2.set_ylabel("Pipeline runs", fontsize=8, color=C["muted"])
    ax2.tick_params(labelsize=7)
    ax2.spines[["top", "right"]].set_color(C["grid"])
    ax.set_xticks(x)
    ax.set_xticklabels(dev_df["author"].str.replace("_", " "),
                       rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Commits", fontsize=8, color=C["muted"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(C["grid"])
    ax.tick_params(labelsize=7)
    ax.set_facecolor(C["bg"])
    ax.grid(axis="y", color=C["grid"], zorder=0)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles1 + handles2, labels1 + labels2, fontsize=7, loc="upper right")
    ax.set_title("Top Devs: Commits + Pipeline (exito vs fallo)",
                 fontsize=10, fontweight="bold", color=C["primary"], pad=8)
    fig.tight_layout()
    return fig_to_image(fig, 6.5 * inch)


# ── GRÁFICA 8: Boxplot consistencia ─────────
def chart_boxplot(author_df):
    teams = author_df["team"].unique()
    data  = [author_df[author_df["team"] == t]["consistency_score"].values for t in teams]
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("white")
    bp = ax.boxplot(data, labels=teams, patch_artist=True,
                    medianprops=dict(color=C["primary"], lw=2),
                    whiskerprops=dict(color=C["muted"]),
                    capprops=dict(color=C["muted"]),
                    flierprops=dict(marker="o", color=C["danger"], markersize=4, alpha=0.6))
    cmap = plt.colormaps.get_cmap("tab10")
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(cmap(i)); patch.set_alpha(0.6)
    ax.axhline(55, color=C["warning"], ls="--", lw=1, alpha=0.7, label="Umbral minimo (55)")
    ax.legend(fontsize=7)
    base_ax(ax, "Dispersion de Consistencia por Equipo", "", "Consistency Score")
    fig.tight_layout()
    return fig_to_image(fig, 6.0 * inch)


# ─────────────────────────────────────────────
# HEADER / FOOTER
# ─────────────────────────────────────────────
def make_header_footer(generated_at):
    def draw(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize
        canvas.setFillColor(colors.HexColor(C["primary"]))
        canvas.rect(0, h - 34, w, 34, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(14, h - 22, "Reporte de Desempeno por Equipos")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 14, h - 22, f"Generado: {generated_at}")
        canvas.setStrokeColor(colors.HexColor(C["grid"]))
        canvas.line(30, 24, w - 30, 24)
        canvas.setFillColor(colors.HexColor(C["muted"]))
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(w / 2, 14,
            f"Pagina {doc.page}  |  Confidencial - Uso interno PO")
        canvas.restoreState()
    return draw


# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
def kpi_table(styles, team_df):
    high   = (team_df["status_label"] == "high").sum()
    low    = (team_df["status_label"] == "low").sum()
    kpis = [
        ("Equipos",         str(len(team_df)),                          C["primary"]),
        ("Score Promedio",  f"{team_df['team_score'].mean():.1f}",      C["accent"]),
        ("Alto Rendimiento",str(high),                                   C["success"]),
        ("En Riesgo",       str(low),                                    C["danger"]),
        ("Pipeline Exito",  f"{team_df['pipeline_success_rate'].mean()*100:.1f}%", C["warning"]),
        ("Total Commits",   f"{int(team_df['total_commits'].sum()):,}",  C["primary"]),
    ]
    h_row = [Paragraph(k[0], styles["KPILabel"]) for k in kpis]
    v_row = [Paragraph(k[1], styles["KPIValue"]) for k in kpis]
    tbl = Table([h_row, v_row], colWidths=[1.1*inch]*len(kpis), rowHeights=[26, 38])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor(C["bg"])),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW",     (0,0), (-1,0),  0.5, colors.HexColor(C["grid"])),
    ] + [("TEXTCOLOR", (i,1),(i,1), colors.HexColor(kpis[i][2])) for i in range(len(kpis))]))
    return tbl


# ─────────────────────────────────────────────
# TABLA DETALLE
# ─────────────────────────────────────────────
def detail_table(styles, team_df):
    cols = [
        ("Equipo",       "team",                  115, None),
        ("Miembros",     "team_size",               58, lambda v: str(int(v))),
        ("Commits",      "total_commits",            60, lambda v: f"{int(v):,}"),
        ("Consistencia", "consistency_score",        72, lambda v: f"{v:.1f}"),
        ("Frecuencia",   "frequency_score",          68, lambda v: f"{v:.1f}"),
        ("Tamano",       "size_score",               55, lambda v: f"{v:.1f}"),
        ("Pipeline",     "pipeline_success_rate",    62, lambda v: f"{v*100:.1f}%"),
        ("Runs",         "pipeline_runs",             45, lambda v: str(int(v))),
        ("Score",        "team_score",               48, lambda v: f"{v:.1f}"),
        ("Estado",       "status",                  100, None),
    ]
    headers = [Paragraph(f"<b>{c[0]}</b>", styles["Normal"]) for c in cols]
    data    = [headers]
    sorted_df = team_df.sort_values("team_score", ascending=False)
    for _, row in sorted_df.iterrows():
        r = []
        for _, col, _, fmt in cols:
            val = row.get(col, "")
            r.append(Paragraph(html.escape(fmt(val) if fmt else str(val)), styles["Normal"]))
        data.append(r)
    tbl = Table(data, colWidths=[c[2] for c in cols], repeatRows=1)
    style = [
        ("BACKGROUND",     (0,0),(-1,0), colors.HexColor(C["primary"])),
        ("TEXTCOLOR",      (0,0),(-1,0), colors.white),
        ("FONTSIZE",       (0,0),(-1,-1), 8),
        ("GRID",           (0,0),(-1,-1), 0.3, colors.HexColor(C["grid"])),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor(C["bg"])]),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("LEFTPADDING",    (0,0),(-1,-1), 5),
    ]
    for i, (_, row) in enumerate(sorted_df.iterrows(), start=1):
        bg = {"high": "#E8F5E9", "medium": "#FFFDE7", "low": "#FFEBEE"}[row["status_label"]]
        style.append(("BACKGROUND", (0,i),(-1,i), colors.HexColor(bg)))
    tbl.setStyle(TableStyle(style))
    return tbl


# ─────────────────────────────────────────────
# INSIGHTS
# ─────────────────────────────────────────────
def insights(team_df):
    msgs = []
    best  = team_df.loc[team_df["team_score"].idxmax()]
    worst = team_df.loc[team_df["team_score"].idxmin()]
    msgs.append(f"<b>Mejor equipo:</b> {best['team']} - score {best['team_score']:.1f}")
    msgs.append(f"<b>Mayor riesgo:</b> {worst['team']} - score {worst['team_score']:.1f}")
    low_pipe = team_df[team_df["pipeline_success_rate"] < 0.50]
    if not low_pipe.empty:
        msgs.append(f"<b>Pipeline inestable (&lt;50%):</b> {', '.join(low_pipe['team'])}")
    late = team_df[team_df["frequency_score"] < 40]
    if not late.empty:
        msgs.append(f"<b>Integracion tardia:</b> {', '.join(late['team'])} - riesgo de merge conflicts")
    high_count = (team_df["status_label"] == "high").sum()
    msgs.append(f"<b>Salud general:</b> {high_count}/{len(team_df)} equipos en alto rendimiento")
    avg_pipe = team_df["pipeline_success_rate"].mean()
    if avg_pipe < 0.60:
        msgs.append(f"<b>Alerta CI/CD:</b> Pipeline promedio {avg_pipe*100:.1f}% - revisar estrategia del sprint")
    return msgs


# ══════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════
def generate_pdf(team_df, author_df, merged_df, output="team_report.pdf"):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    styles = build_styles()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter),
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.65*inch, bottomMargin=0.45*inch)
    on_page = make_header_footer(generated_at)
    el = []

    # PAG 1: Resumen ejecutivo
    el.append(Spacer(1, 0.15*inch))
    el.append(Paragraph("Reporte de Desempeno por Equipos", styles["ReportTitle"]))
    el.append(Paragraph(f"Sprint actual  |  {generated_at}  |  Confidencial", styles["SubTitle"]))
    el.append(HRFlowable(width="100%", thickness=2,
                         color=colors.HexColor(C["accent"]), spaceAfter=10))
    el.append(kpi_table(styles, team_df))
    el.append(Spacer(1, 12))
    el.append(Paragraph("Insights para el PO", styles["SectionHeader"]))
    for msg in insights(team_df):
        el.append(Paragraph(f"* {msg}", styles["Insight"]))
    el.append(Spacer(1, 10))
    el.append(Paragraph("Tabla Resumen", styles["SectionHeader"]))
    el.append(detail_table(styles, team_df))

    # PAG 2: Score + Pie + Pipeline + Radar
    el.append(PageBreak())
    el.append(Paragraph("Score y Distribucion de Estado", styles["SectionHeader"]))
    el.append(Spacer(1, 6))
    row1 = Table([[chart_team_scores(team_df), chart_status_pie(team_df)]],
                 colWidths=[6.1*inch, 3.5*inch])
    row1.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                               ("LEFTPADDING",(0,0),(-1,-1),4),
                               ("RIGHTPADDING",(0,0),(-1,-1),4)]))
    el.append(row1)
    el.append(Spacer(1, 10))
    row2 = Table([[chart_pipeline(team_df), chart_radar(team_df)]],
                 colWidths=[6.1*inch, 3.5*inch])
    row2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4)]))
    el.append(row2)

    # PAG 3: Heatmap + Bubble
    el.append(PageBreak())
    el.append(Paragraph("Heatmap de Metricas + Actividad vs Desempeno", styles["SectionHeader"]))
    el.append(Spacer(1, 6))
    el.append(chart_heatmap(team_df))
    el.append(Spacer(1, 10))
    el.append(chart_bubble(team_df))

    # PAG 4: Devs + Boxplot
    el.append(PageBreak())
    el.append(Paragraph("Vista por Desarrollador", styles["SectionHeader"]))
    el.append(Spacer(1, 6))
    el.append(chart_dev_commits(author_df, merged_df))
    el.append(Spacer(1, 10))
    el.append(Paragraph("Dispersion de Consistencia por Equipo", styles["SectionHeader"]))
    el.append(Spacer(1, 6))
    el.append(chart_boxplot(author_df))

    doc.build(el, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generado: {output}")


# ══════════════════════════════════════════════
# CORE
# ══════════════════════════════════════════════
def generate_team_report(
    author_csv="data/author_consistency_report.csv",
    pipeline_csv="data/pipeline_runs.csv",
    output="data/team_report.pdf",
):
    author_df   = pd.read_csv(author_csv)
    pipeline_df = pd.read_csv(pipeline_csv)

    pipeline_df = pipeline_df[pipeline_df["status"] == "completed"].copy()
    pipeline_df["is_success"] = pipeline_df["conclusion"] == "success"

    author_df["author_clean"]   = author_df["author"].apply(normalize)
    pipeline_df["author_clean"] = pipeline_df["commit_author_name"].apply(normalize)

    author_df["aliases"] = author_df["aliases"].fillna(author_df["author"])
    EXCLUDE_TEAMS = {"DevOpsCore"}
    author_df = author_df[~author_df["team"].isin(EXCLUDE_TEAMS)].copy()
    expanded = []
    for _, row in author_df.iterrows():
        for alias in str(row["aliases"]).split(","):
            nr = row.copy(); nr["alias_clean"] = normalize(alias)
            expanded.append(nr)
    author_expanded = pd.DataFrame(expanded)

    merged = pipeline_df.merge(author_expanded,
                               left_on="author_clean", right_on="alias_clean",
                               how="left")
    print(f"Sin match en pipeline: {merged['team'].isna().sum()}")

    team_pipeline = merged.groupby("team").agg(
        pipeline_success_rate=("is_success", "mean"),
        pipeline_runs=("id", "count"),
    ).reset_index()

    team_dev = author_df.groupby("team").agg(
        team_size=("author", "count"),
        total_commits=("total_commits", "sum"),
        consistency_score=("consistency_score", "mean"),
        frequency_score=("frequency_score", "mean"),
        size_score=("size_score", "mean"),
    ).reset_index()

    team_df = team_dev.merge(team_pipeline, on="team", how="left").fillna(0)

    team_df["team_score"] = (
        team_df["consistency_score"]      * 0.30 +
        team_df["frequency_score"]        * 0.20 +
        team_df["size_score"]             * 0.10 +
        team_df["pipeline_success_rate"] * 100 * 0.40
    )

    def classify(s):
        return "high" if s >= 70 else "medium" if s >= 55 else "low"

    status_labels = {"high": "Alto", "medium": "Aceptable", "low": "Riesgo"}
    team_df["status_label"] = team_df["team_score"].apply(classify)
    team_df["status"]       = team_df["status_label"].map(status_labels)
    team_df = team_df.sort_values("team_score", ascending=False).head(7).copy()
    print(team_df[["team", "team_score", "status_label"]].to_string(index=False))

    generate_pdf(team_df, author_df, merged, output)


if __name__ == "__main__":
    generate_team_report()