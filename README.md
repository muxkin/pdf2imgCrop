# pdf2imgCrop

一个用于裁剪 PDF 页面内容并输出为图片或 PDF 的 Python 工具。
> 如果想从pptx转换为高清图片，可以先试用Adobe Acrobat的ppt插件。注意需要在插件的**首选项->高级设置->图像**中将分辨率调高到300dpi以上。（我自己用的dpi是2400）

## 功能特点

- 将PDF文件输出为JPG、PNG、WebP、AVIF或TIF格式的图片
- 支持直接裁剪并输出PDF文件
- 自动裁剪图片周围的空白边距
- 支持自定义DPI设置
- 支持自动或手动控制 WebP 压缩方式
- 支持自定义 JPG 质量、WebP 有损质量和 TIFF 压缩方式
- 命令行界面，使用简单

## 安装

```bash
pip install pdf2imgCrop
```

## 使用方法

### 命令行使用

基本用法：
```bash
pdf2imgcrop your_file.pdf
```

指定DPI和输出格式：
```bash
pdf2imgcrop your_file.pdf -d 600 -f png

pdf2imgcrop your_file.pdf -d 600 -f pdf

pdf2imgcrop your_file.pdf -f tif --tif-compression lzw

pdf2imgcrop your_file.pdf -f jpg --jpg-quality 85

pdf2imgcrop your_file.pdf -f webp --webp-compression auto

pdf2imgcrop your_file.pdf -f webp --webp-compression lossy --webp-quality 75
```

查看帮助：
```bash
pdf2imgcrop --help
```

### 参数说明

- `file`: PDF文件路径（必需）
- `-d`, `--dpi`: 输出图片的DPI（默认：300）
- `-f`, `--format`: 输出格式，可选 `jpg`、`png`、`webp`、`avif`、`tif` 或 `pdf`（默认：`jpg`）
- `-v`, `--version`: 输出当前版本号并退出
- `--jpg-quality`: JPG 输出质量，范围 `0-100`（默认：`95`）
- `--webp-compression`: WebP 压缩方式，可选 `auto`、`lossy` 或 `lossless`（默认：`auto`）
- `--webp-quality`: WebP 有损压缩质量，范围 `0-100`（默认：`80`）
- `--tif-compression`: TIFF 压缩方式，可选 `none`、`lzw` 或 `jpeg`（默认：`lzw`）

## 代码示例

```python
from pdf2imgCrop.core import convert_pdf

# 基本用法
convert_pdf("your_file.pdf")

# 自定义DPI和格式
convert_pdf("your_file.pdf", dpi=600, file_format="png")

# 自定义 JPG 质量
convert_pdf("your_file.pdf", file_format="jpg", jpg_quality=85)

# WebP 自动选择有损或无损压缩
convert_pdf("your_file.pdf", file_format="webp", webp_compression="auto")

# 手动指定 WebP 有损压缩质量
convert_pdf("your_file.pdf", file_format="webp", webp_compression="lossy", webp_quality=75)

# 以 LZW 压缩输出 TIFF
convert_pdf("your_file.pdf", file_format="tif", tif_compression="lzw")

# 直接裁剪并输出 PDF
convert_pdf("your_file.pdf", dpi=600, file_format="pdf")
```

## 输出

输出文件将保存在与输入PDF文件同名的目录中，后缀为"output"。例如，如果输入文件是"document.pdf"，输出目录将是"documentoutput"。当输出格式为图片时，会按页生成图片文件；当输出格式为 `pdf` 时，会生成一个裁剪后的 PDF 文件。
