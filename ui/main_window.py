import sys
import pandas as pd

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel
)
from ui.profile_sumary import ProfileSummary
from core.analyzer import run_analysis


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Git Repository Analyzer")
        self.resize(800, 500)

        layout = QVBoxLayout()

        self.label = QLabel("Repositorio GitHub")
        layout.addWidget(self.label)

        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText(
            "https://github.com/user/repo.git"
        )
        layout.addWidget(self.repo_input)

        self.analyze_button = QPushButton("Analizar repositorio")
        self.analyze_button.clicked.connect(self.analyze_repo)
        layout.addWidget(self.analyze_button)

        # 🔎 filtro por autor
        self.filter_label = QLabel("Filtrar por autor")
        layout.addWidget(self.filter_label)

        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText("Nombre del autor...")
        self.author_filter.textChanged.connect(self.apply_filter)
        layout.addWidget(self.author_filter)

        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.setLayout(layout)

        # dataframe original
        self.df = None

    def analyze_repo(self):

        repo_url = self.repo_input.text()

        self.df = run_analysis(repo_url)

        self.show_table(self.df)

    def apply_filter(self):

        if self.df is None:
            return

        text = self.author_filter.text().lower()

        filtered_df = self.df[
            self.df["author"].str.lower().str.contains(text)
        ]

        self.show_table(filtered_df)
    def open_profile(self, author):

        self.profile_window = ProfileSummary(self.df, author)
        self.profile_window.show()
    def show_table(self, df: pd.DataFrame):

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)

        for row in range(len(df)):
            for col in range(len(df.columns)):

                column_name = df.columns[col]
                value = df.iloc[row, col]

                if column_name == "author":

                    button = QPushButton(str(value))
                    button.clicked.connect(
                        lambda _, a=value: self.open_profile(a)
                    )

                    self.table.setCellWidget(row, col, button)

                else:

                    self.table.setItem(
                        row,
                        col,
                        QTableWidgetItem(str(value))
                    )

        self.table.resizeColumnsToContents()


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())