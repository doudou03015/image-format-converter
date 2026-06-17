# 图片格式转换工具

一个面向 Windows 用户、基于 `PySide6 + Pillow` 的桌面图片格式转换项目。它不是单文件脚本，而是按正式工程方式拆分了 GUI、服务层、配置、日志、测试和打包方案，方便后续继续扩展为更完整的桌面产品。

## 功能概览

- 支持单张、多张、整个文件夹的图片导入
- 支持拖拽图片文件和拖拽文件夹
- 支持批量转换与进度显示
- 支持预览与图片基础信息展示
- 支持输出到原目录或指定目录
- 支持 JPG / PNG / WebP / BMP / TIFF / ICO 输出
- 支持 JPG 质量、WebP 模式、PNG 优化、TIFF 压缩、最长边限制等参数
- 支持 JPG 透明背景填充策略
- 支持转换日志导出与本地日志文件记录
- 支持记住上次使用设置
- 支持浅色 / 深色主题

## 重要说明

- `JPG` 是有损格式，`PNG -> JPG` 不是严格无损转换。
- 如果源图包含透明通道，导出为 `JPG` 时透明区域会被背景色替代。
- 当前版本对动画 GIF / 多帧 ICO 的处理以静态首帧为主，适合作为通用格式转换工具的第一版。

## 项目结构

```text
project_root/
  app/
    main.py
    gui/
      main_window.py
      settings_dialog.py
      theme.py
      widgets/
        file_list_widget.py
    services/
      converter.py
      conversion_worker.py
      file_scanner.py
      preview_service.py
      settings_service.py
    models/
      settings.py
      task.py
    utils/
      exceptions.py
      image_info.py
      logger.py
      paths.py
  config/
    default_settings.json
  build/
    image_converter.spec
  tests/
    test_converter.py
    test_image_info.py
  README.md
  requirements.txt
  pyproject.toml
```

## 运行环境

- Python 3.11+
- Windows 10 / 11 优先
- 也尽量避免写死为只能在 Windows 使用

## 安装

### 1. 创建虚拟环境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

如果只是运行程序：

```powershell
pip install -r requirements.txt
```

如果还需要运行测试或打包 exe：

```powershell
pip install -e ".[dev]"
```

## 启动项目

```powershell
python -m app.main
```

## 运行测试

```powershell
python -m pytest -p no:cacheprovider
```

## 打包为 exe

### 方案一：直接使用命令

```powershell
pyinstaller --noconfirm --clean --windowed --name 图片格式转换工具 `
  --add-data "config\\default_settings.json;config" `
  app\\main.py
```

### 方案二：使用 spec 文件

```powershell
pyinstaller build\image_converter.spec
```

### 打包资源处理说明

- `config/default_settings.json` 必须通过 `--add-data` 或 spec 的 `datas` 打进包内
- 用户运行后的设置文件和日志文件不会写到程序目录，而是写入用户目录
- Windows 下通常位于：

```text
%APPDATA%\ImageFormatConverter\
```

包含：

- `settings.json`
- `logs\image_converter_YYYYMMDD.log`
- 如果当前环境无权写入用户目录，程序会自动回退到项目目录下的 `.runtime\ImageFormatConverter\`

### 常见打包问题

- 如果 PyInstaller 缺少 Pillow 编解码插件，优先升级 `Pillow` 与 `PyInstaller`
- 某些安全软件可能拦截首次生成的 exe，建议在企业内网分发前签名
- 如果启动后找不到默认配置，通常是 `--add-data` 没带上 `config/default_settings.json`
- 如果界面启动但图片预览为空，先检查系统是否完整安装了图形运行环境和对应图像插件

## 使用说明

1. 点击“添加文件”或“添加文件夹”，也可以直接拖拽到窗口。
2. 在“转换设置”里选择目标格式、输出目录和命名规则。
3. 根据目标格式调整参数，例如：
   - `JPG`：质量、EXIF、ICC、透明背景色
   - `PNG`：优化压缩
   - `WebP`：无损 / 有损和质量
   - `TIFF`：压缩方式
4. 点击“开始转换”。
5. 在右下角查看进度、成功 / 失败数量和当前处理文件。
6. 在“运行日志”页导出本次转换记录。

## 设计原则

- GUI 和业务逻辑分层
- 转换逻辑独立封装到 service
- 配置、日志、路径处理单独封装
- 核心模块包含类型注解和 docstring
- 批量转换使用 `QThread + Worker`，避免阻塞界面

## 后续可扩展方向

- 批量图片压缩与目标体积控制
- 批量裁剪、缩放、水印
- 动画 GIF / 多页 TIFF 的完整帧处理
- OCR 自动命名
- 资源管理器右键菜单集成
- 历史任务列表与预设模板

## 许可证

本项目使用 MIT License，详见 `LICENSE`。
