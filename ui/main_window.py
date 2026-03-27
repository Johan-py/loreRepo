import sys
import pandas as pd
import tempfile
from PySide6.QtWidgets import QDateEdit
from PySide6.QtCore import QDate
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
from core.generate_report import generate_pdf_from_csv  
from core.generate_report_devops import generate_devops_pdf as generate_devops_pdf_func
class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Git Repository Analyzer")
        self.resize(800, 600)

        layout = QVBoxLayout()

        # --- Repositorio ---
        self.label = QLabel("Repositorio GitHub")
        layout.addWidget(self.label)

        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/user/repo.git")
        layout.addWidget(self.repo_input)

        # --- Filtros de fecha ---
        self.since_label = QLabel("Desde")
        layout.addWidget(self.since_label)

        self.since_input = QDateEdit()
        self.since_input.setCalendarPopup(True)
        self.since_input.setDate(QDate.currentDate().addDays(-7))
        layout.addWidget(self.since_input)

        self.until_label = QLabel("Hasta")
        layout.addWidget(self.until_label)

        self.until_input = QDateEdit()
        self.until_input.setCalendarPopup(True)
        self.until_input.setDate(QDate.currentDate())
        layout.addWidget(self.until_input)

        # --- Botones de acción ---
        self.analyze_button = QPushButton("Analizar repositorio")
        self.analyze_button.clicked.connect(self.analyze_repo)
        layout.addWidget(self.analyze_button)

        self.pdf_button = QPushButton("📄 Generar PDF")
        self.pdf_button.setEnabled(False)
        self.pdf_button.clicked.connect(self.generate_pdf)
        layout.addWidget(self.pdf_button)

        # --- Filtro por autor ---
        self.filter_label = QLabel("Filtrar por autor")
        layout.addWidget(self.filter_label)

        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText("Nombre del autor...")
        self.author_filter.textChanged.connect(self.apply_filter)
        layout.addWidget(self.author_filter)

        # --- Tabla ---
        self.table = QTableWidget()
        layout.addWidget(self.table)
        # boton devops
        self.devops_pdf_button = QPushButton("📄 Generar PDF DevOps")
        self.devops_pdf_button.setEnabled(False)
        self.devops_pdf_button.clicked.connect(self.generate_devops_pdf)
        layout.addWidget(self.devops_pdf_button)
        self.setLayout(layout)

        # dataframe original
        self.df = None

    # ==============================
    # Analizar repositorio
    # ==============================
    def analyze_repo(self):
        repo_url = self.repo_input.text()
        if not repo_url:
            self.label.setText("⚠️ Ingresa un repositorio válido")
            return

        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        self.df = run_analysis(repo_url, since=since, until=until)

        self.show_table(self.df)
        self.pdf_button.setEnabled(True)  # habilitar PDF
        
        self.devops_pdf_button.setEnabled(True)  # habilita PDF DevOps

    # ==============================
    # Filtro por autor
    # ==============================
    def apply_filter(self):
        if self.df is None:
            return
        text = self.author_filter.text().lower()
        filtered_df = self.df[self.df["author"].str.lower().str.contains(text)]
        self.show_table(filtered_df)

    # ==============================
    # Abrir perfil
    # ==============================
    def open_profile(self, author):
        self.profile_window = ProfileSummary(self.df, author)
        self.profile_window.show()

    # ==============================
    # Mostrar tabla
    # ==============================
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
                    button.clicked.connect(lambda _, a=value: self.open_profile(a))
                    self.table.setCellWidget(row, col, button)
                else:
                    self.table.setItem(row, col, QTableWidgetItem(str(value)))

        self.table.resizeColumnsToContents()

    # ==============================
    # Generar PDF desde DataFrame
    # ==============================
    def generate_pdf(self):
        if self.df is None or self.df.empty:
            self.label.setText("⚠️ No hay datos para generar PDF")
            return

        # Obtener rango de fechas actual
        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        # Guardar DataFrame actual en un CSV temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            self.df.to_csv(tmp.name, index=False, encoding="utf-8")
            output_pdf = "data/author_report.pdf"

            # 🔹 Pasar rango de fechas al PDF
            generate_pdf_from_csv(csv_path=tmp.name,
                                output_path=output_pdf,
                                since=since,
                                until=until)

            self.label.setText(f"✅ PDF generado en: {output_pdf}")
    # ==============================
    # Generar PDF DevOps
    # ==============================
    def generate_devops_pdf(self):
        if self.df is None or self.df.empty:
            self.label.setText("⚠️ No hay datos para generar PDF DevOps")
            return

        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        devops_authors = [
            "Johan Marcelo Beltrán Montaño",
            "Jose Jonatan Zambrana Escobar",
            "Roberto Carlos Emilio Alejo"
        ]

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            self.df.to_csv(tmp.name, index=False, encoding="utf-8")
            output_pdf = "data/devops_report.pdf"

            generate_devops_pdf_func(
                csv_path=tmp.name,
                output_path=output_pdf,
                since=since,
                until=until,
                devops_authors=devops_authors
            )

            self.label.setText(f"✅ PDF DevOps generado en: {output_pdf}")
import sys
import pandas as pd
import tempfile
from PySide6.QtWidgets import QDateEdit
from PySide6.QtCore import QDate
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
from core.generate_report import generate_pdf_from_csv  
from core.generate_report_devops import generate_devops_pdf as generate_devops_pdf_func
class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Git Repository Analyzer")
        self.resize(800, 600)

        layout = QVBoxLayout()

        # --- Repositorio ---
        self.label = QLabel("Repositorio GitHub")
        layout.addWidget(self.label)

        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/user/repo.git")
        layout.addWidget(self.repo_input)

        # --- Filtros de fecha ---
        self.since_label = QLabel("Desde")
        layout.addWidget(self.since_label)

        self.since_input = QDateEdit()
        self.since_input.setCalendarPopup(True)
        self.since_input.setDate(QDate.currentDate().addDays(-7))
        layout.addWidget(self.since_input)

        self.until_label = QLabel("Hasta")
        layout.addWidget(self.until_label)

        self.until_input = QDateEdit()
        self.until_input.setCalendarPopup(True)
        self.until_input.setDate(QDate.currentDate())
        layout.addWidget(self.until_input)

        # --- Botones de acción ---
        self.analyze_button = QPushButton("Analizar repositorio")
        self.analyze_button.clicked.connect(self.analyze_repo)
        layout.addWidget(self.analyze_button)

        self.pdf_button = QPushButton("📄 Generar PDF")
        self.pdf_button.setEnabled(False)
        self.pdf_button.clicked.connect(self.generate_pdf)
        layout.addWidget(self.pdf_button)

        # --- Filtro por autor ---
        self.filter_label = QLabel("Filtrar por autor")
        layout.addWidget(self.filter_label)

        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText("Nombre del autor...")
        self.author_filter.textChanged.connect(self.apply_filter)
        layout.addWidget(self.author_filter)

        # --- Tabla ---
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.setLayout(layout)
        # botos devops
        self.devops_pdf_button = QPushButton("📄 Generar PDF DevOps")
        self.devops_pdf_button.setEnabled(False)
        self.devops_pdf_button.clicked.connect(self.generate_devops_pdf)
        layout.addWidget(self.devops_pdf_button)
        # dataframe original
        self.df = None

    # ==============================
    # Analizar repositorio
    # ==============================
    def analyze_repo(self):
        repo_url = self.repo_input.text()
        if not repo_url:
            self.label.setText("⚠️ Ingresa un repositorio válido")
            return

        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        self.df = run_analysis(repo_url, since=since, until=until)

        self.show_table(self.df)
        self.pdf_button.setEnabled(True)  # habilitar PDF
        
        self.pdf_button.setEnabled(True)
        self.devops_pdf_button.setEnabled(True)  # habilita PDF DevOps

    # ==============================
    # Filtro por autor
    # ==============================
    def apply_filter(self):
        if self.df is None:
            return
        text = self.author_filter.text().lower()
        filtered_df = self.df[self.df["author"].str.lower().str.contains(text)]
        self.show_table(filtered_df)

    # ==============================
    # Abrir perfil
    # ==============================
    def open_profile(self, author):
        self.profile_window = ProfileSummary(self.df, author)
        self.profile_window.show()

    # ==============================
    # Mostrar tabla
    # ==============================
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
                    button.clicked.connect(lambda _, a=value: self.open_profile(a))
                    self.table.setCellWidget(row, col, button)
                else:
                    self.table.setItem(row, col, QTableWidgetItem(str(value)))

        self.table.resizeColumnsToContents()

    # ==============================
    # Generar PDF desde DataFrame
    # ==============================
    def generate_pdf(self):
        if self.df is None or self.df.empty:
            self.label.setText("⚠️ No hay datos para generar PDF")
            return

        # Obtener rango de fechas actual
        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        # Guardar DataFrame actual en un CSV temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            self.df.to_csv(tmp.name, index=False, encoding="utf-8")
            output_pdf = "data/author_report.pdf"

            # 🔹 Pasar rango de fechas al PDF
            generate_pdf_from_csv(csv_path=tmp.name,
                                output_path=output_pdf,
                                since=since,
                                until=until)

            self.label.setText(f"✅ PDF generado en: {output_pdf}")
    # ==============================
    # Generar PDF DevOps
    # ==============================
    def generate_devops_pdf(self):
        if self.df is None or self.df.empty:
            self.label.setText("⚠️ No hay datos para generar PDF DevOps")
            return

        since = self.since_input.date().toString("yyyy-MM-dd")
        until = self.until_input.date().toString("yyyy-MM-dd")

        devops_authors = [
            "Johan Marcelo Beltrán Montaño",
            "Jose Jonatan Zambrana Escobar",
            "Roberto Carlos Emilio Alejo"
        ]

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            self.df.to_csv(tmp.name, index=False, encoding="utf-8")
            output_pdf = "data/devops_report.pdf"

            generate_devops_pdf_func(
                csv_path=tmp.name,
                output_path=output_pdf,
                since=since,
                until=until,
                devops_authors=devops_authors
            )

            self.label.setText(f"✅ PDF DevOps generado en: {output_pdf}")
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()