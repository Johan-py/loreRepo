import sys
import pandas as pd
import tempfile
from PySide6.QtWidgets import QDateEdit, QCheckBox, QProgressBar
from PySide6.QtCore import QDate, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QGroupBox,
    QMessageBox,
    QComboBox
)
from PySide6.QtGui import QFont, QColor
from ui.profile_sumary import ProfileSummary
from core.analyzer import run_analysis
from core.generate_report import generate_pdf_from_csv  
from core.generate_report_devops import generate_devops_pdf as generate_devops_pdf_func


# ==============================
# THREAD PARA ANÁLISIS ASÍNCRONO
# ==============================
class AnalysisThread(QThread):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, repo_url, since, until, branches, include_all_history):
        super().__init__()
        self.repo_url = repo_url
        self.since = since
        self.until = until
        self.branches = branches
        self.include_all_history = include_all_history
    
    def run(self):
        try:
            self.progress.emit("🔄 Clonando repositorio...")
            df = run_analysis(
                self.repo_url,
                since=self.since,
                until=self.until,
                branches=self.branches,
                include_all_history=self.include_all_history
            )
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Git Repository Analyzer - Análisis Completo de Commits")
        self.resize(1000, 750)

        # Layout principal
        main_layout = QVBoxLayout()

        # ==============================
        # SECCIÓN: CONFIGURACIÓN DEL REPOSITORIO
        # ==============================
        repo_group = QGroupBox("📁 Configuración del Repositorio")
        repo_layout = QVBoxLayout()

        # URL del repositorio
        self.label_repo = QLabel("URL del Repositorio GitHub:")
        self.label_repo.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        repo_layout.addWidget(self.label_repo)

        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/usuario/repositorio.git")
        repo_layout.addWidget(self.repo_input)

        # Selección de ramas
        self.label_branches = QLabel("Ramas a analizar (opcional):")
        self.label_branches.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        repo_layout.addWidget(self.label_branches)

        self.branches_input = QLineEdit()
        self.branches_input.setPlaceholderText("main, develop, feature/* (dejar vacío para todas las ramas)")
        self.branches_input.setToolTip("Ingresa los nombres de las ramas separados por coma. Si está vacío y la opción 'TODOS los commits' está activada, se analizarán TODOS los commits históricos.")
        repo_layout.addWidget(self.branches_input)

        # Información de ayuda
        self.help_label = QLabel("💡 Tip: Si activas 'TODOS los commits', se analizará TODO el historial independientemente de las ramas especificadas")
        self.help_label.setStyleSheet("color: gray; font-size: 9px;")
        repo_layout.addWidget(self.help_label)

        repo_group.setLayout(repo_layout)
        main_layout.addWidget(repo_group)

        # ==============================
        # SECCIÓN: OPCIONES DE ANÁLISIS
        # ==============================
        options_group = QGroupBox("⚙️ Opciones de Análisis")
        options_layout = QVBoxLayout()
        
        # Checkbox para TODOS los commits (incluyendo ramas eliminadas)
        self.all_commits_checkbox = QCheckBox("🔍 Incluir TODOS los commits (ramas activas, eliminadas y commits huérfanos)")
        self.all_commits_checkbox.setChecked(True)
        self.all_commits_checkbox.setStyleSheet("""
            QCheckBox {
                color: #2196F3;
                font-weight: bold;
                padding: 5px;
            }
        """)
        self.all_commits_checkbox.toggled.connect(self.toggle_all_commits_mode)
        options_layout.addWidget(self.all_commits_checkbox)
        
        # Checkbox para análisis completo (sin filtro de fechas)
        self.full_history_checkbox = QCheckBox("📅 Analizar TODO el historial (sin límite de fechas)")
        self.full_history_checkbox.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.full_history_checkbox.toggled.connect(self.toggle_date_filters)
        options_layout.addWidget(self.full_history_checkbox)
        
        # Layout para fechas
        dates_layout = QHBoxLayout()
        
        # Desde
        since_layout = QVBoxLayout()
        self.since_label = QLabel("Desde:")
        self.since_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        since_layout.addWidget(self.since_label)

        self.since_input = QDateEdit()
        self.since_input.setCalendarPopup(True)
        self.since_input.setDate(QDate.currentDate().addDays(-30))
        self.since_input.setDisplayFormat("yyyy-MM-dd")
        since_layout.addWidget(self.since_input)
        dates_layout.addLayout(since_layout)

        # Hasta
        until_layout = QVBoxLayout()
        self.until_label = QLabel("Hasta:")
        self.until_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        until_layout.addWidget(self.until_label)

        self.until_input = QDateEdit()
        self.until_input.setCalendarPopup(True)
        self.until_input.setDate(QDate.currentDate())
        self.until_input.setDisplayFormat("yyyy-MM-dd")
        until_layout.addWidget(self.until_input)
        dates_layout.addLayout(until_layout)
        
        options_layout.addLayout(dates_layout)
        
        # Selector de modo de merge
        merge_layout = QHBoxLayout()
        self.merge_label = QLabel("Estrategia de merge:")
        self.merge_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        merge_layout.addWidget(self.merge_label)
        
        self.merge_mode = QComboBox()
        self.merge_mode.addItems([
            "Preservar todos los commits (merge commit)",
            "Combinar commits (squash) - Útil para ver autores originales",
            "Rebase (historia lineal)"
        ])
        self.merge_mode.setToolTip("Define cómo se interpretan los merges en el análisis")
        merge_layout.addWidget(self.merge_mode)
        options_layout.addLayout(merge_layout)
        
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # ==============================
        # SECCIÓN: ACCIONES PRINCIPALES
        # ==============================
        actions_group = QGroupBox("🚀 Acciones")
        actions_layout = QHBoxLayout()

        # Botón analizar
        self.analyze_button = QPushButton("🔍 Analizar Repositorio")
        self.analyze_button.setMinimumHeight(45)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.analyze_button.clicked.connect(self.analyze_repo)
        actions_layout.addWidget(self.analyze_button)

        # Botón generar PDF general
        self.pdf_button = QPushButton("📄 Generar PDF General")
        self.pdf_button.setMinimumHeight(40)
        self.pdf_button.setEnabled(False)
        self.pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.pdf_button.clicked.connect(self.generate_pdf)
        actions_layout.addWidget(self.pdf_button)

        # Botón generar PDF DevOps
        self.devops_pdf_button = QPushButton("🚀 Generar PDF DevOps")
        self.devops_pdf_button.setMinimumHeight(40)
        self.devops_pdf_button.setEnabled(False)
        self.devops_pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #fb8c00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.devops_pdf_button.clicked.connect(self.generate_devops_pdf)
        actions_layout.addWidget(self.devops_pdf_button)

        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)

        # ==============================
        # BARRA DE PROGRESO
        # ==============================
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # ==============================
        # SECCIÓN: FILTRO Y TABLA DE RESULTADOS
        # ==============================
        results_group = QGroupBox("📊 Resultados del Análisis")
        results_layout = QVBoxLayout()

        # Filtro por autor
        filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Filtrar por autor:")
        self.filter_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        filter_layout.addWidget(self.filter_label)

        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText("Escribe el nombre del autor para filtrar...")
        self.author_filter.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.author_filter)

        # Botón limpiar filtro
        self.clear_filter_button = QPushButton("Limpiar")
        self.clear_filter_button.clicked.connect(self.clear_filter)
        filter_layout.addWidget(self.clear_filter_button)
        
        # Estadísticas rápidas
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: gray; font-size: 10px;")
        filter_layout.addWidget(self.stats_label)

        results_layout.addLayout(filter_layout)

        # Tabla de resultados
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        results_layout.addWidget(self.table)

        # Etiqueta de estado
        self.status_label = QLabel("✅ Listo para analizar")
        self.status_label.setStyleSheet("color: blue; padding: 10px; font-weight: bold;")
        results_layout.addWidget(self.status_label)

        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        self.setLayout(main_layout)

        # DataFrame para almacenar datos
        self.df = None
        self.analysis_thread = None

    # ==============================
    # TOGGLE OPCIONES
    # ==============================
    def toggle_all_commits_mode(self, checked):
        """Cambia el modo de análisis para incluir TODOS los commits"""
        if checked:
            self.status_label.setText("🔍 Modo: Analizando TODOS los commits (incluyendo ramas eliminadas y commits huérfanos)")
            self.status_label.setStyleSheet("color: #2196F3; padding: 10px; font-weight: bold;")
            self.branches_input.setEnabled(False)
            self.branches_input.setPlaceholderText("(Ignorado - se analizarán TODOS los commits)")
            self.help_label.setText("💡 Modo TODOS los commits activado: Se analizará TODO el historial independientemente de las ramas")
        else:
            self.status_label.setText("📌 Modo: Solo ramas activas especificadas")
            self.status_label.setStyleSheet("color: orange; padding: 10px; font-weight: bold;")
            self.branches_input.setEnabled(True)
            self.branches_input.setPlaceholderText("main, develop, feature/* (dejar vacío para main y develop)")
            self.help_label.setText("💡 Tip: Si activas 'TODOS los commits', se analizará TODO el historial independientemente de las ramas especificadas")
    
    def toggle_date_filters(self, checked):
        """Habilita/deshabilita los filtros de fecha cuando se selecciona full history"""
        self.since_input.setEnabled(not checked)
        self.until_input.setEnabled(not checked)
        
        if checked:
            self.since_label.setStyleSheet("color: gray; font-size: 10px;")
            self.until_label.setStyleSheet("color: gray; font-size: 10px;")
            if not self.all_commits_checkbox.isChecked():
                self.status_label.setText("📊 Modo: Análisis de TODO el historial (desde el primer commit)")
        else:
            self.since_label.setStyleSheet("color: black; font-size: 10px; font-weight: bold;")
            self.until_label.setStyleSheet("color: black; font-size: 10px; font-weight: bold;")
            if not self.all_commits_checkbox.isChecked():
                self.status_label.setText("📅 Modo: Análisis con rango de fechas")

    # ==============================
    # ANALIZAR REPOSITORIO
    # ==============================
    def analyze_repo(self):
        repo_url = self.repo_input.text().strip()
        if not repo_url:
            QMessageBox.warning(self, "Advertencia", "⚠️ Por favor, ingresa una URL de repositorio válida")
            return

        # Verificar si es análisis con TODOS los commits
        include_all_history = self.all_commits_checkbox.isChecked()
        
        # Verificar si es análisis completo de fechas
        full_history = self.full_history_checkbox.isChecked()
        
        if full_history:
            since = None
            until = None
            date_msg = "TODO el historial"
        else:
            since = self.since_input.date().toString("yyyy-MM-dd")
            until = self.until_input.date().toString("yyyy-MM-dd")
            date_msg = f"{since} - {until}"
        
        # Procesar ramas (solo si NO está activado el modo TODOS los commits)
        if include_all_history:
            branches = None
            branches_msg = "TODOS los commits históricos (incluyendo ramas eliminadas)"
        else:
            branches_text = self.branches_input.text().strip()
            if branches_text:
                branches = [b.strip() for b in branches_text.split(",") if b.strip()]
                if branches:
                    branches_msg = f"ramas: {', '.join(branches)}"
                else:
                    branches = None
                    branches_msg = "ramas: main y develop (por defecto)"
            else:
                branches = None
                branches_msg = "ramas: main y develop (por defecto)"
        
        # Mostrar estado inicial
        status_msg = f"🔍 Iniciando análisis...\n"
        status_msg += f"📅 Rango: {date_msg}\n"
        status_msg += f"🌿 {branches_msg}\n"
        if include_all_history:
            status_msg += f"✨ Incluyendo: Commits de ramas activas, eliminadas y commits huérfanos\n"
        
        self.status_label.setText(status_msg)
        self.status_label.setStyleSheet("color: orange; padding: 10px; font-weight: bold;")
        
        # Deshabilitar botones durante el análisis
        self.analyze_button.setEnabled(False)
        self.pdf_button.setEnabled(False)
        self.devops_pdf_button.setEnabled(False)
        
        # Mostrar barra de progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        
        # Crear y ejecutar thread de análisis
        self.analysis_thread = AnalysisThread(repo_url, since, until, branches, include_all_history)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.start()

    def on_analysis_progress(self, message):
        """Actualizar progreso del análisis"""
        self.status_label.setText(message)
        QApplication.processEvents()
    
    def on_analysis_finished(self, df):
        """Análisis completado exitosamente"""

        # Validación básica
        if df is None or df.empty:
            self.df = df
            self.status_label.setText("⚠️ No se encontraron commits en el repositorio")
            self.status_label.setStyleSheet("color: red; padding: 10px; font-weight: bold;")
            self.pdf_button.setEnabled(False)
            self.devops_pdf_button.setEnabled(False)
            self.table.setRowCount(0)

        else:
            try:
                # ==============================
                # COPIA SEGURA DEL DATAFRAME
                # ==============================
                self.df = df.copy()

                # ==============================
                # VALIDACIÓN DE COLUMNAS
                # ==============================
                if "author" not in self.df.columns:
                    raise ValueError("El DataFrame no contiene la columna 'author'")

                # ==============================
                # MAPEO DE EQUIPOS
                # ==============================
                team_map = {
                    "Johan Marcelo Beltrán Montaño": "DevOps",
                    "Jose Jonatan Zambrana Escobar": "DevOps",
                    "Roberto Carlos Emilio Alejo": "DevOps",
                }

                # Crear columna team

                # ==============================
                # REORDENAR COLUMNAS
                # ==============================
                cols = list(self.df.columns)

                if "aliases" in cols and "team" in cols:
                    cols.remove("team")
                    aliases_index = cols.index("aliases")
                    cols.insert(aliases_index + 1, "team")

                self.df = self.df[cols]

                # ==============================
                # MOSTRAR TABLA
                # ==============================
                self.show_table(self.df)
                self.pdf_button.setEnabled(True)
                self.devops_pdf_button.setEnabled(True)

                # ==============================
                # ESTADÍSTICAS
                # ==============================
                total_authors = len(self.df)

                if 'total_commits' in self.df.columns:
                    total_commits = self.df['total_commits'].sum()
                else:
                    total_commits = len(self.df)

                avg_consistency = (
                    self.df['consistency_score'].mean()
                    if 'consistency_score' in self.df.columns else 0
                )

                high_performers = (
                    len(self.df[self.df['consistency_score'] >= 80])
                    if 'consistency_score' in self.df.columns else 0
                )

                # ==============================
                # MENSAJE FINAL
                # ==============================
                status_msg = f"✅ Análisis completado exitosamente!\n"
                status_msg += f"📊 {total_commits:,} commits analizados\n"
                status_msg += f"👥 {total_authors} autores encontrados\n"
                status_msg += f"⭐ Consistencia promedio: {avg_consistency:.1f}/100\n"
                status_msg += f"🏆 Autores destacados (≥80): {high_performers}\n"

                if self.all_commits_checkbox.isChecked():
                    status_msg += "✨ Incluye commits de ramas eliminadas y commits huérfanos"

                self.status_label.setText(status_msg)
                self.status_label.setStyleSheet("color: green; padding: 10px; font-weight: bold;")

            except Exception as e:
                self.status_label.setText(f"❌ Error procesando resultados: {str(e)}")
                self.status_label.setStyleSheet("color: red; padding: 10px; font-weight: bold;")
                QMessageBox.critical(self, "Error", str(e))

        # ==============================
        # FINALIZACIÓN UI
        # ==============================
        self.progress_bar.setVisible(False)
        self.analyze_button.setEnabled(True)
    
    def on_analysis_error(self, error_msg):
        """Error durante el análisis"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.status_label.setStyleSheet("color: red; padding: 10px; font-weight: bold;")
        QMessageBox.critical(self, "Error", f"Error durante el análisis:\n\n{error_msg}")
        
        # Ocultar barra de progreso
        self.progress_bar.setVisible(False)
        self.analyze_button.setEnabled(True)

    # ==============================
    # FILTRO POR AUTOR
    # ==============================
    def apply_filter(self):
        if self.df is None or self.df.empty:
            return
            
        text = self.author_filter.text().lower().strip()
        if text:
            # Buscar en la columna 'author' (nombre real)
            if 'author' in self.df.columns:
                filtered_df = self.df[self.df['author'].str.lower().str.contains(text, na=False)]
            else:
                filtered_df = self.df
                
            self.show_table(filtered_df)
            self.stats_label.setText(f"Mostrando {len(filtered_df)} de {len(self.df)} autores")
        else:
            self.show_table(self.df)
            total_authors = len(self.df)
            self.stats_label.setText(f"Total: {total_authors} autores")

    def clear_filter(self):
        """Limpia el filtro de autores"""
        self.author_filter.clear()
        if self.df is not None:
            self.show_table(self.df)
            total_authors = len(self.df)
            self.stats_label.setText(f"Total: {total_authors} autores")

    # ==============================
    # ABRIR PERFIL DEL AUTOR
    # ==============================
    def open_profile(self, author):
        try:
            self.profile_window = ProfileSummary(self.df, author)
            self.profile_window.show()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir el perfil: {str(e)}")

    # ==============================
    # MOSTRAR TABLA DE RESULTADOS
    # ==============================
    def show_table(self, df: pd.DataFrame):
        if df.empty:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
            
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        
        # Configurar el ancho de las columnas
        for col_idx, col_name in enumerate(df.columns):
            if col_name == 'author':
                self.table.setColumnWidth(col_idx, 220)
            elif col_name == 'aliases':
                self.table.setColumnWidth(col_idx, 220)
            elif col_name in ['total_commits', 'lines_added', 'lines_deleted', 'total_lines_changed']:
                self.table.setColumnWidth(col_idx, 130)
            elif col_name in ['message_score', 'size_score', 'frequency_score', 'granularity_score', 'consistency_score']:
                self.table.setColumnWidth(col_idx, 120)

        for row in range(len(df)):
            for col in range(len(df.columns)):
                column_name = df.columns[col]
                value = df.iloc[row, col]

                # Formatear valores numéricos
                if column_name in ['message_score', 'size_score', 'frequency_score', 
                                  'granularity_score', 'consistency_score']:
                    if pd.notna(value):
                        value = f"{value:.2f}"
                
                # Crear botón para la columna 'author'
                if column_name == "author":
                    button = QPushButton(str(value))
                    button.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding: 5px;
                            border: none;
                            background-color: #f0f0f0;
                            color: #000000;  /* 🔥 esto arregla tu problema */
                        }
                  <      QPushButton:hover {
                            background-color: #e0e0e0;
                            text-decoration: underline;
                            color: #000000;
                        }
                    """)
                    button.clicked.connect(lambda _, a=value: self.open_profile(a))
                    self.table.setCellWidget(row, col, button)
                else:
                    item = QTableWidgetItem(str(value))

                    if column_name == 'consistency_score' and pd.notna(value):
                        try:
                            score = float(value)

                            if score >= 80:
                                item.setBackground(QColor(144, 238, 144))  # Verde claro
                                item.setForeground(QColor(0, 0, 0))        # Negro

                            elif score >= 60:
                                item.setBackground(QColor(255, 255, 144))  # Amarillo claro
                                item.setForeground(QColor(0, 0, 0))

                            elif score >= 40:
                                item.setBackground(QColor(255, 200, 144))  # Naranja claro
                                item.setForeground(QColor(0, 0, 0))

                            else:
                                item.setBackground(QColor(255, 160, 160))  # Rojo claro
                                item.setForeground(QColor(0, 0, 0))

                        except:
                            pass

                    self.table.setItem(row, col, item)

        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)

    # ==============================
    # GENERAR PDF GENERAL
    # ==============================
    def generate_pdf(self):
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "Advertencia", "⚠️ No hay datos para generar el PDF")
            return

        try:
            # Obtener información del análisis
            full_history = self.full_history_checkbox.isChecked()
            include_all_history = self.all_commits_checkbox.isChecked()
            
            if full_history:
                since = None
                until = None
                date_range = "TODO el historial"
            else:
                since = self.since_input.date().toString("yyyy-MM-dd")
                until = self.until_input.date().toString("yyyy-MM-dd")
                date_range = f"{since} - {until}"
            
            # Obtener información de ramas
            if include_all_history:
                branches_str = "TODOS los commits históricos (incluyendo ramas eliminadas)"
            else:
                branches_text = self.branches_input.text().strip()
                if branches_text:
                    branches = [b.strip() for b in branches_text.split(",") if b.strip()]
                    branches_str = ", ".join(branches) if branches else "main, develop"
                else:
                    branches_str = "main, develop"

            # Guardar DataFrame actual en un CSV temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                self.df.to_csv(tmp.name, index=False, encoding="utf-8")
                output_pdf = "data/author_report.pdf"

                # Generar PDF
                generate_pdf_from_csv(
                    csv_path=tmp.name,
                    output_path=output_pdf,
                    since=since,
                    until=until,
                    branches=branches_str
                )

                # Mensaje de éxito
                success_msg = f"✅ PDF General generado exitosamente!\n\n"
                success_msg += f"📄 Archivo: {output_pdf}\n"
                success_msg += f"📅 Rango: {date_range}\n"
                success_msg += f"🌿 {branches_str}\n"
                if include_all_history:
                    success_msg += f"✨ Incluye commits de ramas eliminadas"
                
                self.status_label.setText(f"✅ PDF General generado en: {output_pdf}")
                QMessageBox.information(self, "Éxito", success_msg)
                
        except Exception as e:
            error_msg = f"❌ Error al generar el PDF: {str(e)}"
            self.status_label.setText(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    # ==============================
    # GENERAR PDF DEVOPS
    # ==============================
    def generate_devops_pdf(self):
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "Advertencia", "⚠️ No hay datos para generar el PDF DevOps")
            return

        try:
            full_history = self.full_history_checkbox.isChecked()
            include_all_history = self.all_commits_checkbox.isChecked()
            
            if full_history:
                since = None
                until = None
                date_range = "TODO el historial"
            else:
                since = self.since_input.date().toString("yyyy-MM-dd")
                until = self.until_input.date().toString("yyyy-MM-dd")
                date_range = f"{since} - {until}"
            
            # Obtener información de ramas
            if include_all_history:
                branches_str = "TODOS los commits históricos (incluyendo ramas eliminadas)"
            else:
                branches_text = self.branches_input.text().strip()
                if branches_text:
                    branches = [b.strip() for b in branches_text.split(",") if b.strip()]
                    branches_str = ", ".join(branches) if branches else "main, develop"
                else:
                    branches_str = "main, develop"

            # Lista de autores DevOps
            devops_authors = [
                "Johan Marcelo Beltrán Montaño",
                "Jose Jonatan Zambrana Escobar",
                "Roberto Carlos Emilio Alejo"
            ]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                self.df.to_csv(tmp.name, index=False, encoding="utf-8")
                output_pdf = "data/devops_report.pdf"

                generate_devops_pdf_func(
                    csv_path=tmp.name,
                    output_path=output_pdf,
                    since=since,
                    until=until,
                    branches=branches_str,
                    devops_authors=devops_authors
                )

                success_msg = f"✅ PDF DevOps generado exitosamente!\n\n"
                success_msg += f"📄 Archivo: {output_pdf}\n"
                success_msg += f"📅 Rango: {date_range}\n"
                success_msg += f"🌿 {branches_str}\n"
                success_msg += f"👥 Autores DevOps: {len(devops_authors)}\n"
                if include_all_history:
                    success_msg += f"✨ Incluye commits de ramas eliminadas"
                
                self.status_label.setText(f"✅ PDF DevOps generado en: {output_pdf}")
                QMessageBox.information(self, "Éxito", success_msg)
                
        except Exception as e:
            error_msg = f"❌ Error al generar el PDF DevOps: {str(e)}"
            self.status_label.setText(error_msg)
            QMessageBox.critical(self, "Error", error_msg)


def main():
    app = QApplication(sys.argv)
    
    # Establecer estilo moderno
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()