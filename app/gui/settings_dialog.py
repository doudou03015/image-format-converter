"""Application settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.models.settings import AppSettings


class SettingsDialog(QDialog):
    """Dialog for persistent application defaults."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("浅色", "light")
        self.theme_combo.addItem("深色", "dark")

        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItem("默认输出到原目录", "source")
        self.output_mode_combo.addItem("默认输出到指定目录", "custom")

        self.output_dir_edit = QLineEdit()
        self.output_dir_button = QPushButton("浏览...")
        self.output_dir_button.clicked.connect(self._choose_output_dir)

        self.format_combo = QComboBox()
        self.format_combo.addItem("JPG / JPEG", "jpg")
        self.format_combo.addItem("PNG", "png")
        self.format_combo.addItem("WebP", "webp")
        self.format_combo.addItem("BMP", "bmp")
        self.format_combo.addItem("TIFF", "tiff")
        self.format_combo.addItem("ICO", "ico")

        self.jpg_quality_spin = QSpinBox()
        self.jpg_quality_spin.setRange(1, 100)

        self.auto_open_output_checkbox = QCheckBox("转换完成后自动打开输出目录")

        form = QFormLayout()
        form.addRow("界面主题", self.theme_combo)
        form.addRow("默认输出方式", self.output_mode_combo)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_dir_edit)
        output_row.addWidget(self.output_dir_button)
        form.addRow("默认输出目录", output_row)
        form.addRow("默认目标格式", self.format_combo)
        form.addRow("默认 JPG 质量", self.jpg_quality_spin)
        form.addRow("", self.auto_open_output_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._apply_settings(settings)
        self.output_mode_combo.currentIndexChanged.connect(self._toggle_output_dir_enabled)
        self._toggle_output_dir_enabled()

    def get_settings(self) -> AppSettings:
        """Return settings collected from the dialog fields."""

        return AppSettings(
            theme=self.theme_combo.currentData(),
            default_output_mode=self.output_mode_combo.currentData(),
            default_output_dir=self.output_dir_edit.text().strip(),
            default_format=self.format_combo.currentData(),
            jpg_quality=self.jpg_quality_spin.value(),
            auto_open_output_dir=self.auto_open_output_checkbox.isChecked(),
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        self._set_combo_data(self.theme_combo, settings.theme)
        self._set_combo_data(self.output_mode_combo, settings.default_output_mode)
        self._set_combo_data(self.format_combo, settings.default_format)
        self.output_dir_edit.setText(settings.default_output_dir)
        self.jpg_quality_spin.setValue(settings.jpg_quality)
        self.auto_open_output_checkbox.setChecked(settings.auto_open_output_dir)

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择默认输出目录",
            self.output_dir_edit.text() or str(Path.home()),
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def _toggle_output_dir_enabled(self) -> None:
        enabled = self.output_mode_combo.currentData() == "custom"
        self.output_dir_edit.setEnabled(enabled)
        self.output_dir_button.setEnabled(enabled)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
