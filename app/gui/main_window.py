"""Main application window."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import APP_NAME, __version__
from app.gui.settings_dialog import SettingsDialog
from app.gui.theme import get_stylesheet
from app.gui.widgets.file_list_widget import FileListWidget
from app.models.settings import ConversionOptions
from app.models.task import BatchProgress, ConversionResult, ConversionTask, ImageInfoSummary, SessionSummary
from app.services.conversion_worker import BatchConversionWorker
from app.services.converter import ConverterService
from app.services.file_scanner import FileScanner
from app.services.preview_service import PreviewService
from app.services.settings_service import SettingsService
from app.utils.exceptions import ImageReadError
from app.utils.image_info import collect_image_info, human_readable_size


class MainWindow(QMainWindow):
    """Main GUI for browsing, previewing, and converting images."""

    def __init__(self, settings_service: SettingsService, logger: logging.Logger) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.logger = logger
        self.settings = self.settings_service.load()
        self.file_scanner = FileScanner()
        self.preview_service = PreviewService()
        self.converter = ConverterService(self.logger)

        self.file_paths: list[Path] = []
        self.file_info_cache: dict[Path, ImageInfoSummary] = {}
        self.session_results: list[ConversionResult] = []
        self.latest_output_dir: Path | None = None
        self.worker_thread: QThread | None = None
        self.worker: BatchConversionWorker | None = None
        self._close_after_worker = False

        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.setMinimumSize(1380, 860)
        self.setAcceptDrops(True)

        self._build_actions()
        self._build_ui()
        self._apply_settings_to_ui()
        self._apply_theme()
        self._connect_signals()
        self._update_format_hint()
        self._update_file_count()

    def _build_actions(self) -> None:
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._open_settings_dialog)

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)

        menu = self.menuBar()
        tools_menu = menu.addMenu("工具")
        tools_menu.addAction(settings_action)

        help_menu = menu.addMenu("帮助")
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        layout = QVBoxLayout(central)
        layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        button_row = QHBoxLayout()
        self.add_files_button = self._secondary_button("添加文件")
        self.add_folder_button = self._secondary_button("添加文件夹")
        self.remove_selected_button = self._secondary_button("删除选中")
        self.clear_list_button = self._secondary_button("清空列表")
        button_row.addWidget(self.add_files_button)
        button_row.addWidget(self.add_folder_button)
        button_row.addWidget(self.remove_selected_button)
        button_row.addWidget(self.clear_list_button)

        self.recursive_checkbox = QCheckBox("递归扫描子文件夹")
        self.file_count_label = QLabel("待处理文件：0")
        self.file_list = FileListWidget()
        tip_label = QLabel("支持拖拽图片文件或文件夹到左侧列表，自动过滤非图片。")
        tip_label.setWordWrap(True)

        layout.addLayout(button_row)
        layout.addWidget(self.recursive_checkbox)
        layout.addWidget(self.file_count_label)
        layout.addWidget(self.file_list, stretch=1)
        layout.addWidget(tip_label)
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_preview_group())
        layout.addWidget(self._build_tabs(), stretch=1)
        layout.addWidget(self._build_progress_group())
        return widget

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox("图片预览")
        layout = QHBoxLayout(group)

        self.preview_label = QLabel("请先添加图片并选中一个文件")
        self.preview_label.setObjectName("PreviewFrame")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(380, 280)

        info_layout = QFormLayout()
        self.info_name = QLabel("-")
        self.info_size = QLabel("-")
        self.info_format = QLabel("-")
        self.info_filesize = QLabel("-")
        self.info_mode = QLabel("-")
        self.info_alpha = QLabel("-")
        self.format_hint_label = QLabel()
        self.format_hint_label.setWordWrap(True)
        self.alpha_hint_label = QLabel()
        self.alpha_hint_label.setWordWrap(True)

        info_layout.addRow("文件名", self.info_name)
        info_layout.addRow("尺寸", self.info_size)
        info_layout.addRow("原格式", self.info_format)
        info_layout.addRow("文件大小", self.info_filesize)
        info_layout.addRow("色彩模式", self.info_mode)
        info_layout.addRow("透明通道", self.info_alpha)
        info_layout.addRow("格式说明", self.format_hint_label)
        info_layout.addRow("透明提示", self.alpha_hint_label)

        layout.addWidget(self.preview_label, stretch=5)
        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        layout.addWidget(info_widget, stretch=4)
        return group

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_options_tab(), "转换设置")
        tabs.addTab(self._build_log_tab(), "运行日志")
        return tabs

    def _build_options_tab(self) -> QWidget:
        container = QWidget()
        root = QVBoxLayout(container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.addWidget(self._build_output_group())
        content_layout.addWidget(self._build_format_group())
        content_layout.addWidget(self._build_resize_group())
        content_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        root.addWidget(scroll)
        return container

    def _build_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.export_log_button = self._secondary_button("导出本次转换日志")
        layout.addWidget(self.log_output, stretch=1)
        layout.addWidget(self.export_log_button, alignment=Qt.AlignRight)
        return widget

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("输出与命名")
        layout = QGridLayout(group)

        self.output_format_combo = QComboBox()
        for label, data in [
            ("JPG / JPEG", "jpg"),
            ("PNG", "png"),
            ("WebP", "webp"),
            ("BMP", "bmp"),
            ("TIFF", "tiff"),
            ("ICO", "ico"),
        ]:
            self.output_format_combo.addItem(label, data)

        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItem("输出到原目录", "source")
        self.output_mode_combo.addItem("输出到指定目录", "custom")

        self.output_dir_edit = QLineEdit()
        self.output_dir_button = self._secondary_button("浏览...")

        self.naming_mode_combo = QComboBox()
        self.naming_mode_combo.addItem("原文件名 + 新后缀", "source_ext")
        self.naming_mode_combo.addItem("原文件名 + 标识后缀", "suffix_marker")

        self.naming_marker_edit = QLineEdit("_converted")
        self.rename_prefix_edit = QLineEdit()
        self.rename_suffix_edit = QLineEdit()

        self.duplicate_strategy_combo = QComboBox()
        self.duplicate_strategy_combo.addItem("自动重命名", "rename")
        self.duplicate_strategy_combo.addItem("跳过已存在文件", "skip")
        self.duplicate_strategy_combo.addItem("覆盖已存在文件", "overwrite")

        layout.addWidget(QLabel("目标格式"), 0, 0)
        layout.addWidget(self.output_format_combo, 0, 1)
        layout.addWidget(QLabel("输出位置"), 0, 2)
        layout.addWidget(self.output_mode_combo, 0, 3)
        layout.addWidget(QLabel("输出目录"), 1, 0)
        layout.addWidget(self.output_dir_edit, 1, 1, 1, 2)
        layout.addWidget(self.output_dir_button, 1, 3)
        layout.addWidget(QLabel("命名规则"), 2, 0)
        layout.addWidget(self.naming_mode_combo, 2, 1)
        layout.addWidget(QLabel("命名标识"), 2, 2)
        layout.addWidget(self.naming_marker_edit, 2, 3)
        layout.addWidget(QLabel("统一前缀"), 3, 0)
        layout.addWidget(self.rename_prefix_edit, 3, 1)
        layout.addWidget(QLabel("统一后缀"), 3, 2)
        layout.addWidget(self.rename_suffix_edit, 3, 3)
        layout.addWidget(QLabel("重名处理"), 4, 0)
        layout.addWidget(self.duplicate_strategy_combo, 4, 1)
        return group

    def _build_format_group(self) -> QGroupBox:
        group = QGroupBox("格式参数与兼容处理")
        layout = QGridLayout(group)

        self.jpg_quality_spin = QSpinBox()
        self.jpg_quality_spin.setRange(1, 100)
        self.preserve_exif_checkbox = QCheckBox("尽量保留 EXIF 元数据")
        self.preserve_icc_checkbox = QCheckBox("尽量保留 ICC Profile")
        self.auto_fix_orientation_checkbox = QCheckBox("自动应用 EXIF 方向纠正")
        self.png_optimize_checkbox = QCheckBox("PNG 优化压缩")
        self.webp_lossless_checkbox = QCheckBox("WebP 无损模式")
        self.webp_quality_spin = QSpinBox()
        self.webp_quality_spin.setRange(1, 100)
        self.tiff_compression_combo = QComboBox()
        self.tiff_compression_combo.addItem("无压缩", "raw")
        self.tiff_compression_combo.addItem("LZW", "tiff_lzw")
        self.tiff_compression_combo.addItem("Adobe Deflate", "tiff_adobe_deflate")

        self.jpg_background_button = self._secondary_button("选择背景色")
        self.jpg_background_hex = QLabel("#FFFFFF")
        self._set_background_preview("#FFFFFF")

        layout.addWidget(QLabel("JPG 质量"), 0, 0)
        layout.addWidget(self.jpg_quality_spin, 0, 1)
        layout.addWidget(self.preserve_exif_checkbox, 0, 2)
        layout.addWidget(self.preserve_icc_checkbox, 0, 3)
        layout.addWidget(self.auto_fix_orientation_checkbox, 1, 0, 1, 2)
        layout.addWidget(self.png_optimize_checkbox, 1, 2)
        layout.addWidget(QLabel("WebP 质量"), 2, 0)
        layout.addWidget(self.webp_quality_spin, 2, 1)
        layout.addWidget(self.webp_lossless_checkbox, 2, 2)
        layout.addWidget(QLabel("TIFF 压缩"), 2, 3)
        layout.addWidget(self.tiff_compression_combo, 2, 4)
        layout.addWidget(QLabel("JPG 透明背景"), 3, 0)
        layout.addWidget(self.jpg_background_button, 3, 1)
        layout.addWidget(self.jpg_background_hex, 3, 2)
        return group

    def _build_resize_group(self) -> QGroupBox:
        group = QGroupBox("尺寸与批处理")
        layout = QGridLayout(group)

        self.resize_enabled_checkbox = QCheckBox("限制最长边")
        self.max_long_edge_spin = QSpinBox()
        self.max_long_edge_spin.setRange(64, 20000)
        self.max_long_edge_spin.setSuffix(" px")
        self.auto_open_output_checkbox = QCheckBox("转换完成后自动打开输出目录")

        layout.addWidget(self.resize_enabled_checkbox, 0, 0)
        layout.addWidget(self.max_long_edge_spin, 0, 1)
        layout.addWidget(self.auto_open_output_checkbox, 0, 2)
        return group

    def _build_progress_group(self) -> QGroupBox:
        group = QGroupBox("批量处理状态")
        layout = QVBoxLayout(group)

        self.progress_status_label = QLabel("就绪")
        self.current_file_label = QLabel("当前文件：-")
        self.count_status_label = QLabel("成功 0 | 失败 0 | 跳过 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("开始转换")
        self.cancel_button = self._secondary_button("取消")
        self.cancel_button.setEnabled(False)
        self.open_output_button = self._secondary_button("打开输出目录")
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.open_output_button)
        button_row.addStretch(1)

        layout.addWidget(self.progress_status_label)
        layout.addWidget(self.current_file_label)
        layout.addWidget(self.count_status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(button_row)
        return group

    def _connect_signals(self) -> None:
        self.add_files_button.clicked.connect(self._add_files)
        self.add_folder_button.clicked.connect(self._add_folder)
        self.remove_selected_button.clicked.connect(self._remove_selected_files)
        self.clear_list_button.clicked.connect(self._clear_files)
        self.file_list.paths_dropped.connect(self._handle_dropped_paths)
        self.file_list.itemSelectionChanged.connect(self._update_preview)
        self.output_dir_button.clicked.connect(self._choose_output_dir)
        self.output_mode_combo.currentIndexChanged.connect(self._toggle_output_dir_state)
        self.output_format_combo.currentIndexChanged.connect(self._update_format_hint)
        self.output_format_combo.currentIndexChanged.connect(self._update_alpha_warning)
        self.jpg_background_button.clicked.connect(self._choose_background_color)
        self.export_log_button.clicked.connect(self._export_session_log)
        self.start_button.clicked.connect(self._start_conversion)
        self.cancel_button.clicked.connect(self._cancel_conversion)
        self.open_output_button.clicked.connect(self._open_output_dir)

    def _apply_settings_to_ui(self) -> None:
        self._set_combo_data(self.output_format_combo, self.settings.default_format)
        self._set_combo_data(self.output_mode_combo, self.settings.default_output_mode)
        self.output_dir_edit.setText(self.settings.default_output_dir)
        self.jpg_quality_spin.setValue(self.settings.jpg_quality)
        self.preserve_exif_checkbox.setChecked(self.settings.preserve_exif)
        self.preserve_icc_checkbox.setChecked(self.settings.preserve_icc_profile)
        self.recursive_checkbox.setChecked(self.settings.recursive_scan)
        self.auto_fix_orientation_checkbox.setChecked(self.settings.auto_fix_orientation)
        self.png_optimize_checkbox.setChecked(self.settings.png_optimize)
        self.webp_lossless_checkbox.setChecked(self.settings.webp_lossless)
        self.webp_quality_spin.setValue(self.settings.webp_quality)
        self._set_combo_data(self.tiff_compression_combo, self.settings.tiff_compression)
        self.resize_enabled_checkbox.setChecked(self.settings.resize_enabled)
        self.max_long_edge_spin.setValue(self.settings.max_long_edge)
        self._set_combo_data(self.duplicate_strategy_combo, self.settings.duplicate_strategy)
        self._set_combo_data(self.naming_mode_combo, self.settings.naming_mode)
        self.naming_marker_edit.setText(self.settings.naming_marker)
        self.rename_prefix_edit.setText(self.settings.rename_prefix)
        self.rename_suffix_edit.setText(self.settings.rename_suffix)
        self.auto_open_output_checkbox.setChecked(self.settings.auto_open_output_dir)
        self._set_background_preview(self.settings.jpg_background)
        self._toggle_output_dir_state()

    def _apply_theme(self) -> None:
        self.setStyleSheet(get_stylesheet(self.settings.theme))

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            updated = dialog.get_settings()
            self.settings.theme = updated.theme
            self.settings.default_output_mode = updated.default_output_mode
            self.settings.default_output_dir = updated.default_output_dir
            self.settings.default_format = updated.default_format
            self.settings.jpg_quality = updated.jpg_quality
            self.settings.auto_open_output_dir = updated.auto_open_output_dir
            self.settings_service.save(self.settings)
            self._apply_settings_to_ui()
            self._apply_theme()

    def _show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            "关于",
            (
                f"{APP_NAME} v{__version__}\n\n"
                "依赖：PySide6、Pillow、pytest、PyInstaller\n"
                "说明：JPG 是有损格式，PNG 转 JPG 并不是严格无损。\n"
                "如果源图包含透明通道，转 JPG 时透明区域会被背景色替代。"
            ),
        )

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        self._handle_dropped_paths([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._persist_settings()
        if self.worker_thread and self.worker_thread.isRunning():
            answer = QMessageBox.question(self, APP_NAME, "当前仍在转换中，是否请求取消并关闭程序？")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._close_after_worker = True
            self._cancel_conversion()
            self.progress_status_label.setText("正在取消并等待当前文件处理完成...")
            event.ignore()
            return
        event.accept()

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            str(Path.home()),
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif *.ico)",
        )
        if files:
            self._add_input_paths([Path(item) for item in files])

    def _add_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择图片文件夹", str(Path.home()))
        if directory:
            self._add_input_paths([Path(directory)])

    def _handle_dropped_paths(self, paths: list[str]) -> None:
        self._add_input_paths([Path(item) for item in paths if item])

    def _add_input_paths(self, paths: list[Path]) -> None:
        discovered = self.file_scanner.scan(paths, recursive=self.recursive_checkbox.isChecked())
        if not discovered:
            QMessageBox.information(self, APP_NAME, "没有发现可处理的图片文件。")
            return

        added_count = 0
        errors: list[str] = []
        for path in discovered:
            if path in self.file_paths:
                continue
            try:
                info = collect_image_info(path)
            except ImageReadError:
                errors.append(f"{path.name}：文件损坏或格式不可读")
                self.logger.warning("Unreadable image skipped: %s", path)
                continue

            self.file_paths.append(path)
            self.file_info_cache[path] = info
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, str(path))
            item.setToolTip(str(path))
            self.file_list.addItem(item)
            added_count += 1

        self._update_file_count()
        self._update_alpha_warning()
        if added_count and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

        if errors:
            QMessageBox.warning(self, APP_NAME, "以下文件未加入列表：\n" + "\n".join(errors[:10]))

    def _remove_selected_files(self) -> None:
        for item in self.file_list.selectedItems():
            path = Path(item.data(Qt.UserRole))
            self.file_info_cache.pop(path, None)
            if path in self.file_paths:
                self.file_paths.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self._update_file_count()
        self._update_alpha_warning()
        self._update_preview()

    def _clear_files(self) -> None:
        self.file_paths.clear()
        self.file_info_cache.clear()
        self.file_list.clear()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("请先添加图片并选中一个文件")
        for label in [self.info_name, self.info_size, self.info_format, self.info_filesize, self.info_mode, self.info_alpha]:
            label.setText("-")
        self._update_file_count()
        self._update_alpha_warning()

    def _update_file_count(self) -> None:
        self.file_count_label.setText(f"待处理文件：{len(self.file_paths)}")

    def _update_preview(self) -> None:
        current_item = self.file_list.currentItem()
        if not current_item:
            return

        path = Path(current_item.data(Qt.UserRole))
        info = self.file_info_cache.get(path)
        if not info:
            return

        try:
            pixmap = self.preview_service.build_preview(path, max_size=(540, 320))
        except ImageReadError as exc:
            self.preview_label.setText(str(exc))
            self.logger.warning("Preview failed for %s", path)
            return

        self.preview_label.setText("")
        self.preview_label.setPixmap(pixmap)
        self.info_name.setText(info.file_name)
        self.info_size.setText(f"{info.width} x {info.height}")
        self.info_format.setText(info.format_name)
        self.info_filesize.setText(human_readable_size(info.file_size))
        self.info_mode.setText(info.mode)
        self.info_alpha.setText("是" if info.has_alpha else "否")
        self._update_alpha_warning()

    def _update_format_hint(self) -> None:
        target = self.output_format_combo.currentData()
        hints = {
            "jpg": "JPG 为有损格式，适合照片类图片。若源图有透明区域，会使用背景色填充后再导出。",
            "png": "PNG 支持无损压缩和透明通道，适合截图、图标和需要保真输出的图片。",
            "webp": "WebP 同时支持有损和无损模式，适合在体积和质量之间平衡。",
            "bmp": "BMP 兼容性高，但体积通常较大。",
            "tiff": "TIFF 适合归档与印刷场景，可保留高质量数据与部分元信息。",
            "ico": "ICO 常用于应用图标，建议输入尽量接近正方形图片。",
        }
        self.format_hint_label.setText(hints.get(target, ""))
        self._update_alpha_warning()

    def _update_alpha_warning(self) -> None:
        target = self.output_format_combo.currentData()
        alpha_count = sum(1 for info in self.file_info_cache.values() if info.has_alpha)
        if target == "jpg" and alpha_count:
            self.alpha_hint_label.setText(
                f"当前列表中有 {alpha_count} 张图片带透明通道。转为 JPG 时透明区域将被背景色替代，且输出不是严格无损。"
            )
        elif target == "jpg":
            self.alpha_hint_label.setText("JPG 不支持透明通道，且属于有损格式。")
        else:
            self.alpha_hint_label.setText("当前目标格式可根据格式能力尽量保留透明信息。")

    def _toggle_output_dir_state(self) -> None:
        enabled = self.output_mode_combo.currentData() == "custom"
        self.output_dir_edit.setEnabled(enabled)
        self.output_dir_button.setEnabled(enabled)

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_dir_edit.text() or str(Path.home()),
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def _choose_background_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.jpg_background_hex.text()), self, "选择 JPG 背景色")
        if color.isValid():
            self._set_background_preview(color.name().upper())

    def _set_background_preview(self, color_hex: str) -> None:
        self.jpg_background_hex.setText(color_hex.upper())
        self.jpg_background_hex.setStyleSheet(
            f"background:{color_hex}; border:1px solid #cbd5e1; border-radius:6px; padding:6px; min-width:72px;"
        )

    def _collect_conversion_options(self) -> ConversionOptions | None:
        output_mode = self.output_mode_combo.currentData()
        output_dir = Path(self.output_dir_edit.text().strip()) if self.output_dir_edit.text().strip() else None
        if output_mode == "custom" and not output_dir:
            QMessageBox.warning(self, APP_NAME, "请选择输出目录。")
            return None

        return ConversionOptions(
            output_format=self.output_format_combo.currentData(),
            output_mode=output_mode,
            output_dir=output_dir,
            naming_mode=self.naming_mode_combo.currentData(),
            naming_marker=self.naming_marker_edit.text().strip() or "_converted",
            rename_prefix=self.rename_prefix_edit.text().strip(),
            rename_suffix=self.rename_suffix_edit.text().strip(),
            duplicate_strategy=self.duplicate_strategy_combo.currentData(),
            jpg_quality=self.jpg_quality_spin.value(),
            preserve_exif=self.preserve_exif_checkbox.isChecked(),
            preserve_icc_profile=self.preserve_icc_checkbox.isChecked(),
            jpg_background=self.jpg_background_hex.text(),
            png_optimize=self.png_optimize_checkbox.isChecked(),
            webp_lossless=self.webp_lossless_checkbox.isChecked(),
            webp_quality=self.webp_quality_spin.value(),
            tiff_compression=self.tiff_compression_combo.currentData(),
            auto_fix_orientation=self.auto_fix_orientation_checkbox.isChecked(),
            resize_enabled=self.resize_enabled_checkbox.isChecked(),
            max_long_edge=self.max_long_edge_spin.value(),
        )

    def _start_conversion(self) -> None:
        if not self.file_paths:
            QMessageBox.information(self, APP_NAME, "请先添加要转换的图片。")
            return

        options = self._collect_conversion_options()
        if not options:
            return

        tasks = [ConversionTask(source_path=path, options=options) for path in self.file_paths]
        self.session_results.clear()
        self.latest_output_dir = None
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.progress_status_label.setText(f"准备开始，共 {len(tasks)} 个文件")
        self.current_file_label.setText("当前文件：-")
        self.count_status_label.setText("成功 0 | 失败 0 | 跳过 0")

        self.worker_thread = QThread(self)
        self.worker = BatchConversionWorker(self.converter, tasks)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self._on_progress_changed)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.batch_finished.connect(self._on_batch_finished)
        self.worker.batch_finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.logger.info("Batch conversion started with %d tasks", len(tasks))
        self.worker_thread.start()

    def _cancel_conversion(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.progress_status_label.setText("已请求取消，正在等待当前文件完成...")
            self.logger.info("Cancellation requested")

    def _on_progress_changed(self, progress: BatchProgress) -> None:
        percent = int((progress.processed / max(progress.total, 1)) * 100)
        self.progress_bar.setValue(percent)
        self.progress_status_label.setText(f"已处理 {progress.processed} / {progress.total}")
        self.current_file_label.setText(f"当前文件：{progress.current_file}")
        self.count_status_label.setText(
            f"成功 {progress.success_count} | 失败 {progress.failure_count} | 跳过 {progress.skipped_count}"
        )

    def _on_file_finished(self, result: ConversionResult) -> None:
        self.session_results.append(result)
        timestamp = datetime.now().strftime("%H:%M:%S")
        if result.status == "success":
            self.latest_output_dir = result.output_path.parent if result.output_path else self.latest_output_dir
            message = f"[{timestamp}] 成功：{result.source_path.name} -> {result.output_path}"
        elif result.status == "skipped":
            message = f"[{timestamp}] 跳过：{result.source_path.name} -> 目标文件已存在"
        else:
            message = f"[{timestamp}] 失败：{result.source_path.name} -> {result.error_message}"
        self.log_output.appendPlainText(message)

    def _on_batch_finished(self, summary: SessionSummary) -> None:
        if summary.total and not summary.cancelled:
            self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_status_label.setText("已取消" if summary.cancelled else "转换完成")
        self.logger.info(
            "Batch finished: processed=%d success=%d failure=%d skipped=%d cancelled=%s",
            summary.processed,
            summary.success_count,
            summary.failure_count,
            summary.skipped_count,
            summary.cancelled,
        )

        message = (
            f"总数：{summary.total}\n"
            f"已处理：{summary.processed}\n"
            f"成功：{summary.success_count}\n"
            f"失败：{summary.failure_count}\n"
            f"跳过：{summary.skipped_count}"
        )
        if summary.cancelled:
            message += "\n\n任务已取消。"

        self._persist_settings()

        if not self._close_after_worker:
            QMessageBox.information(self, APP_NAME, message)

        if not self._close_after_worker and self.auto_open_output_checkbox.isChecked() and self.latest_output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.latest_output_dir)))

    def _cleanup_worker(self) -> None:
        should_close = self._close_after_worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
        if should_close:
            self._close_after_worker = False
            self.close()

    def _open_output_dir(self) -> None:
        if self.output_mode_combo.currentData() == "custom" and self.output_dir_edit.text().strip():
            target = Path(self.output_dir_edit.text().strip())
        elif self.latest_output_dir:
            target = self.latest_output_dir
        elif self.file_paths:
            target = self.file_paths[0].parent
        else:
            QMessageBox.information(self, APP_NAME, "当前没有可打开的输出目录。")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _export_session_log(self) -> None:
        if not self.session_results:
            QMessageBox.information(self, APP_NAME, "当前没有可导出的转换记录。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出转换日志",
            str(Path.home() / f"conversion_log_{datetime.now():%Y%m%d_%H%M%S}.csv"),
            "CSV 文件 (*.csv)",
        )
        if not file_path:
            return

        with Path(file_path).open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["源文件", "状态", "输出文件", "错误信息", "耗时(ms)"])
            for result in self.session_results:
                writer.writerow(
                    [
                        str(result.source_path),
                        result.status,
                        str(result.output_path) if result.output_path else "",
                        result.error_message or "",
                        result.elapsed_ms,
                    ]
                )

        QMessageBox.information(self, APP_NAME, "转换日志已导出。")

    def _persist_settings(self) -> None:
        self.settings.default_format = self.output_format_combo.currentData()
        self.settings.default_output_mode = self.output_mode_combo.currentData()
        self.settings.default_output_dir = self.output_dir_edit.text().strip()
        self.settings.jpg_quality = self.jpg_quality_spin.value()
        self.settings.preserve_exif = self.preserve_exif_checkbox.isChecked()
        self.settings.preserve_icc_profile = self.preserve_icc_checkbox.isChecked()
        self.settings.jpg_background = self.jpg_background_hex.text()
        self.settings.png_optimize = self.png_optimize_checkbox.isChecked()
        self.settings.webp_lossless = self.webp_lossless_checkbox.isChecked()
        self.settings.webp_quality = self.webp_quality_spin.value()
        self.settings.tiff_compression = self.tiff_compression_combo.currentData()
        self.settings.recursive_scan = self.recursive_checkbox.isChecked()
        self.settings.auto_fix_orientation = self.auto_fix_orientation_checkbox.isChecked()
        self.settings.resize_enabled = self.resize_enabled_checkbox.isChecked()
        self.settings.max_long_edge = self.max_long_edge_spin.value()
        self.settings.duplicate_strategy = self.duplicate_strategy_combo.currentData()
        self.settings.naming_mode = self.naming_mode_combo.currentData()
        self.settings.naming_marker = self.naming_marker_edit.text().strip() or "_converted"
        self.settings.rename_prefix = self.rename_prefix_edit.text().strip()
        self.settings.rename_suffix = self.rename_suffix_edit.text().strip()
        self.settings.auto_open_output_dir = self.auto_open_output_checkbox.isChecked()
        self.settings_service.save(self.settings)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _secondary_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("secondary", True)
        return button
