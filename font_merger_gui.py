#!/usr/bin/env python3
import os
import subprocess
import sys

from fontTools.ttLib import TTFont
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QScrollArea,
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


class FontListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            paths = []
            for url in md.urls():
                if not url.isLocalFile():
                    continue
                path = os.path.abspath(url.toLocalFile())
                if os.path.isfile(path) and path.lower().endswith((".ttf", ".otf", ".ttc", ".otc")):
                    paths.append(path)
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


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
        self.manual_scale_values = {}
        self.manual_scale_widgets = []

        font_box = QGroupBox("Fonts (priority: top > bottom)")
        font_layout = QHBoxLayout(font_box)
        self.font_list = FontListWidget()
        self.font_list.setToolTip(
            "Drag and drop font files here.\n"
            "You can also drag items inside the list to reorder priority."
        )
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

        self.auto_scale = QCheckBox("Auto scale non-first fonts (recommended)")
        self.auto_scale.setChecked(True)
        options_form.addRow("", self.auto_scale)

        self.scale_help = QLabel(
            "Scaling means matching visual glyph size between fonts.\n"
            "Auto scale uses font #1 as baseline.\n"
            "Manual per-font scale overrides auto scale for that font."
        )
        self.scale_help.setWordWrap(True)
        options_form.addRow("Scale help", self.scale_help)
        layout.addWidget(options_box)

        manual_box = QGroupBox("Manual Scale (per font)")
        manual_outer = QVBoxLayout(manual_box)
        manual_intro = QLabel("Set as: '<N>번 폰트는 1번 폰트의 [ ]% 크기'")
        manual_intro.setWordWrap(True)
        manual_outer.addWidget(manual_intro)

        self.manual_scroll = QScrollArea()
        self.manual_scroll.setWidgetResizable(True)
        self.manual_scroll_content = QWidget()
        self.manual_scroll_layout = QVBoxLayout(self.manual_scroll_content)
        self.manual_scroll.setWidget(self.manual_scroll_content)
        manual_outer.addWidget(self.manual_scroll)
        layout.addWidget(manual_box)

        self.auto_manual_hint = QLabel(
            "Rule: Auto scale applies to all non-first fonts. "
            "If manual scale is set for a font, manual scale wins for that font."
        )
        self.auto_manual_hint.setWordWrap(True)
        layout.addWidget(self.auto_manual_hint)

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
        self.font_list.files_dropped.connect(self.add_fonts_from_paths)
        self.font_list.model().rowsInserted.connect(self.update_variable_ui)
        self.font_list.model().rowsRemoved.connect(self.update_variable_ui)
        self.font_list.model().rowsMoved.connect(self.update_variable_ui)
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
        self.add_fonts_from_paths(paths)

    def add_fonts_from_paths(self, paths):
        existing = set(self.font_paths())
        for p in paths:
            if not p:
                continue
            abs_path = os.path.abspath(p)
            if abs_path in existing:
                continue
            self.font_list.addItem(abs_path)
            existing.add(abs_path)
        self.update_variable_ui()

    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.font_list.selectedIndexes()}, reverse=True)
        for row in rows:
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
        self.rebuild_manual_scale_inputs()

    def rebuild_manual_scale_inputs(self):
        # Keep existing manual values by font path.
        for font_index, path, spin in self.manual_scale_widgets:
            self.manual_scale_values[path] = spin.value()

        while self.manual_scroll_layout.count():
            item = self.manual_scroll_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.manual_scale_widgets = []
        fonts = self.font_paths()
        if len(fonts) <= 1:
            label = QLabel("Add at least two fonts to set per-font manual scale.")
            self.manual_scroll_layout.addWidget(label)
            self.manual_scroll_layout.addStretch(1)
            return

        for i in range(1, len(fonts)):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            label_left = QLabel(f"{i+1}번 폰트는 1번 폰트의")
            spin = QDoubleSpinBox()
            spin.setRange(10, 300)
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setSuffix("%")
            spin.setValue(self.manual_scale_values.get(fonts[i], 100.0))
            label_right = QLabel("크기")

            row_layout.addWidget(label_left)
            row_layout.addWidget(spin)
            row_layout.addWidget(label_right)
            row_layout.addStretch(1)
            self.manual_scroll_layout.addWidget(row)
            self.manual_scale_widgets.append((i + 1, fonts[i], spin))

        self.manual_scroll_layout.addStretch(1)

    def manual_scale_args(self):
        args = []
        for font_index, path, spin in self.manual_scale_widgets:
            value = spin.value()
            self.manual_scale_values[path] = value
            if abs(value - 100.0) < 1e-6:
                continue
            ratio = value / 100.0
            args.append(f"--scale-font{font_index}={ratio}")
        return args

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

        args += self.manual_scale_args()
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
