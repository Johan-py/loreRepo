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

        self.setWindowTitle(f"Perfil de {author}")
        self.resize(900, 700)

        layout = QVBoxLayout()

        title = QLabel(f"Perfil de contribución: {author}")
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

        df_author = self.df[self.df["author"] == self.author]

        commits = df_author["total_commits"].values[0]
        lines = df_author["total_lines_changed"].values[0]
        consistency = df_author["consistency_score"].values[0]

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

        ax1.set_title("Total Commits")

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

        ax2.set_title("Total Lines Changed")

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

        ax3.set_xlim(0, 1)
        ax3.set_title("Consistency Score")

        self.figure.tight_layout()

        self.canvas.draw()