#!/usr/bin/env python3
import os
import re
import subprocess
import sys

from fontTools.ttLib import TTFont
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


def has_wght_axis(font_path):
    try:
        font = TTFont(font_path)
        try:
            if "fvar" not in font:
                return False
            for axis in font["fvar"].axes:
                if axis.axisTag == "wght":
                    return True
            return False
        finally:
            font.close()
    except Exception:
        return False


def parse_manual_scale_text(text, font_count):
    """
    Parse: '2=0.93, 3=1.05'
    Returns ['--scale-font2=0.93', '--scale-font3=1.05']
    """
    if not text.strip():
        return []

    args = []
    pairs = [p.strip() for p in text.split(",") if p.strip()]
    for pair in pairs:
        m = re.match(r"^(\d+)\s*=\s*([0-9]*\.?[0-9]+)$", pair)
        if not m:
            raise ValueError("Manual scale format must be like '2=0.93,3=1.05'")
        idx = int(m.group(1))
        scale = float(m.group(2))
        if idx < 2 or idx > font_count:
            raise ValueError(f"manual scale index must be between 2 and {font_count}")
        if scale <= 0:
            raise ValueError("manual scale value must be > 0")
        args.append(f"--scale-font{idx}={scale}")
    return args


class MergeWorker(QThread):
    log = Signal(str)
    done = Signal()
    failed = Signal(str)

    def __init__(self, commands):
        super().__init__()
        self.commands = commands

    def run(self):
        try:
            for cmd in self.commands:
                self.log.emit("$ " + " ".join(cmd))
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in proc.stdout:
                    self.log.emit(line.rstrip())
                rc = proc.wait()
                if rc != 0:
                    raise RuntimeError(f"command failed with exit code {rc}")
            self.done.emit()
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Merger GUI")
        self.resize(980, 700)
        self.worker = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        font_box = QGroupBox("Fonts (priority: top > bottom)")
        font_layout = QHBoxLayout(font_box)
        self.font_list = QListWidget()
        font_layout.addWidget(self.font_list, 1)

        side_btns = QVBoxLayout()
        self.btn_add = QPushButton("Add Fonts")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_up = QPushButton("Move Up")
        self.btn_down = QPushButton("Move Down")
        side_btns.addWidget(self.btn_add)
        side_btns.addWidget(self.btn_remove)
        side_btns.addWidget(self.btn_up)
        side_btns.addWidget(self.btn_down)
        side_btns.addStretch(1)
        font_layout.addLayout(side_btns)
        layout.addWidget(font_box)

        options_box = QGroupBox("Options")
        options_form = QFormLayout(options_box)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Optional base name")
        options_form.addRow("Name", self.name_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(1, 2000)
        self.weight_input.setValue(400)
        self.weight_input.setDecimals(1)
        options_form.addRow("Weight (variable fonts)", self.weight_input)

        self.auto_scale = QCheckBox("Auto scale non-first fonts")
        options_form.addRow("", self.auto_scale)

        self.manual_scale_input = QLineEdit()
        self.manual_scale_input.setPlaceholderText("2=0.93,3=1.05")
        options_form.addRow("Manual scale", self.manual_scale_input)
        layout.addWidget(options_box)

        action_row = QHBoxLayout()
        self.variable_badge = QLabel("Variable font detected: no")
        self.batch_button = QPushButton("Generate 100~900")
        self.batch_button.setVisible(False)
        self.merge_button = QPushButton("Merge Once")
        action_row.addWidget(self.variable_badge)
        action_row.addStretch(1)
        action_row.addWidget(self.batch_button)
        action_row.addWidget(self.merge_button)
        layout.addLayout(action_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.btn_add.clicked.connect(self.add_fonts)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        self.merge_button.clicked.connect(self.run_single)
        self.batch_button.clicked.connect(self.run_batch)
        self.font_list.model().rowsInserted.connect(self.update_variable_ui)
        self.font_list.model().rowsRemoved.connect(self.update_variable_ui)
        self.update_variable_ui()

    def log(self, message):
        self.log_view.appendPlainText(message)

    def add_fonts(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Font Files",
            "",
            "Font Files (*.ttf *.otf *.ttc *.otc);;All Files (*)",
        )
        for p in paths:
            if p:
                self.font_list.addItem(os.path.abspath(p))
        self.update_variable_ui()

    def remove_selected(self):
        row = self.font_list.currentRow()
        if row >= 0:
            self.font_list.takeItem(row)
        self.update_variable_ui()

    def move_up(self):
        row = self.font_list.currentRow()
        if row > 0:
            item = self.font_list.takeItem(row)
            self.font_list.insertItem(row - 1, item)
            self.font_list.setCurrentRow(row - 1)

    def move_down(self):
        row = self.font_list.currentRow()
        if 0 <= row < self.font_list.count() - 1:
            item = self.font_list.takeItem(row)
            self.font_list.insertItem(row + 1, item)
            self.font_list.setCurrentRow(row + 1)

    def font_paths(self):
        return [self.font_list.item(i).text() for i in range(self.font_list.count())]

    def has_variable_fonts(self):
        return any(has_wght_axis(p) for p in self.font_paths())

    def update_variable_ui(self):
        variable = self.has_variable_fonts()
        self.variable_badge.setText(f"Variable font detected: {'yes' if variable else 'no'}")
        self.weight_input.setVisible(variable)
        self.batch_button.setVisible(variable)

    def build_base_args(self):
        fonts = self.font_paths()
        if not fonts:
            raise ValueError("Add at least one font.")

        variable = self.has_variable_fonts()
        args = [sys.executable, os.path.join(os.path.dirname(__file__), "_font_merger.py")]

        name = self.name_input.text().strip()
        if name:
            args += ["--name", name]

        if variable:
            args += ["--weight", str(self.weight_input.value())]

        if self.auto_scale.isChecked():
            args.append("--auto-scale")

        args += parse_manual_scale_text(self.manual_scale_input.text(), len(fonts))
        args += fonts
        return args, variable

    def run_commands(self, commands):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Running", "A merge task is already running.")
            return
        self.worker = MergeWorker(commands)
        self.worker.log.connect(self.log)
        self.worker.done.connect(lambda: QMessageBox.information(self, "Done", "Completed successfully."))
        self.worker.failed.connect(lambda e: QMessageBox.critical(self, "Failed", e))
        self.worker.start()

    def run_single(self):
        try:
            args, _ = self.build_base_args()
            self.run_commands([args])
        except Exception as e:
            QMessageBox.critical(self, "Invalid input", str(e))

    def run_batch(self):
        try:
            base_args, variable = self.build_base_args()
            if not variable:
                QMessageBox.warning(self, "Not available", "Batch generation is available only for variable fonts.")
                return

            commands = []
            for w in range(100, 1000, 100):
                cmd = []
                i = 0
                while i < len(base_args):
                    token = base_args[i]
                    if token == "--weight":
                        cmd.extend(["--weight", str(w)])
                        i += 2
                    else:
                        cmd.append(token)
                        i += 1
                commands.append(cmd)

            self.run_commands(commands)
        except Exception as e:
            QMessageBox.critical(self, "Invalid input", str(e))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
