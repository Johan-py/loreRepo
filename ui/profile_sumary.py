import pandas as pd
import seaborn as sns

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class ProfileSummary(QWidget):

    def __init__(self, df: pd.DataFrame, author: str):
        super().__init__()

        self.df = df
        self.author = author
        row = df[df["author"] == author]

        if row.empty:
            raise ValueError(f"Autor no encontrado: {author}")

        self.row = row.iloc[0]  # 🔥 guardar fila completa
        self.display_name = self.row["author"]
        self.setWindowTitle(f"Perfil de {author}")
        self.resize(900, 700)

        layout = QVBoxLayout()

        title = QLabel(f"Perfil de contribución: {self.display_name}")
        layout.addWidget(title)

        # botón volver
        back_button = QPushButton("⬅ Volver")
        back_button.clicked.connect(self.close)
        layout.addWidget(back_button)

        self.figure = Figure(figsize=(10, 7))
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(self.canvas)

        self.setLayout(layout)

        self.plot_data()

    def plot_data(self):

        sns.set_theme(style="darkgrid")

        df_author = self.df[self.df["author"] == self.display_name]

        commits = self.row["total_commits"]
        lines = self.row["total_lines_changed"]
        consistency = self.row["consistency_score"]

        self.figure.clear()

        ax1 = self.figure.add_subplot(311)
        ax2 = self.figure.add_subplot(312)
        ax3 = self.figure.add_subplot(313)

        # ---------- COMMITS ----------
        bars1 = ax1.barh(["Commits"], [commits])

        for bar in bars1:
            width = bar.get_width()
            ax1.text(
                width,
                bar.get_y() + bar.get_height()/2,
                f'{int(width)}',
                va='center',
                ha='left',
                fontsize=11,
                fontweight='bold'
            )


        # ---------- LINES CHANGED ----------
        bars2 = ax2.barh(["Lines Changed"], [lines])

        for bar in bars2:
            width = bar.get_width()
            ax2.text(
                width,
                bar.get_y() + bar.get_height()/2,
                f'{int(width)}',
                va='center',
                ha='left',
                fontsize=11,
                fontweight='bold'
            )


        # ---------- CONSISTENCY ----------
        bars3 = ax3.barh(["Consistency Score"], [consistency])

        for bar in bars3:
            width = bar.get_width()
            ax3.text(
                width,
                bar.get_y() + bar.get_height()/2,
                f'{width:.2f}',
                va='center',
                ha='left',
                fontsize=11,
                fontweight='bold'
            )

        ax3.set_xlim(0, 100)

        self.figure.tight_layout()

        self.canvas.draw()