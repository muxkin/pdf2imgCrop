import os
import sys

import fitz
from PIL import Image, ImageOps, features
from fitz import Page
from tqdm import tqdm

IMAGE_FORMATS = {"jpg", "png", "webp", "avif", "tif"}
WEBP_COMPRESSIONS = {"auto", "lossy", "lossless"}
TIFF_COMPRESSIONS = {
    "none": None,
    "lzw": "tiff_lzw",
    "jpeg": "jpeg",
}


def _binarize_pixel(pixel: int) -> int:
    if pixel > 250:
        return 255
    return 0


def _get_output_dir(file: str) -> str:
    filename, _ = os.path.splitext(file)
    output_dir = filename + "output"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _get_problematic_font_warnings(doc: fitz.Document) -> list[str]:
    warnings: list[str] = []
    seen: set[tuple[int, str, str]] = set()

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        for font in page.get_fonts():
            xref = int(font[0])
            font_name = str(font[3])
            encoding = str(font[5])
            key = (page_index, font_name, encoding)
            if key in seen:
                continue
            seen.add(key)

            if xref <= 0:
                warnings.append(
                    f"页码={page_index + 1}; 字体={font_name}; 编码={encoding}; 状态=无法提取字体对象; 风险=渲染时可能发生字体替代"
                )
                continue

            extracted = doc.extract_font(xref)
            font_buffer = b""
            if len(extracted) == 4:
                _, _, _, font_buffer = extracted
            if not font_buffer:
                warnings.append(
                    f"页码={page_index + 1}; 字体={font_name}; 编码={encoding}; 状态=字体未嵌入PDF; 风险=渲染时可能发生字体替代"
                )

    return warnings


def _print_font_warnings(doc: fitz.Document) -> None:
    warnings = _get_problematic_font_warnings(doc)
    if not warnings:
        return

    print("警告: 检测到源PDF包含可能导致字体替代的字体问题。", file=sys.stderr)
    print(f"问题字体记录数: {len(warnings)}", file=sys.stderr)
    print("详细记录:", file=sys.stderr)
    for index, warning in enumerate(warnings, start=1):
        print(f"  [{index}] {warning}", file=sys.stderr)
    print(
        "当前渲染流程无法强制将PDF默认字体替换为 Times New Roman；如需准确字形，请重新导出并嵌入字体。",
        file=sys.stderr,
    )


def _render_page_image(pg: Page, dpi: int) -> Image.Image:
    scale = dpi / 72
    mat = fitz.Matrix(scale, scale).prerotate(0)
    pix = pg.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _get_content_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    grayscale = img.convert("L")
    thresholded = grayscale.point(_binarize_pixel)
    return ImageOps.invert(thresholded).getbbox()


def _should_use_lossless_webp(img: Image.Image) -> bool:
    if img.mode in {"RGBA", "LA"} or img.info.get("transparency") is not None:
        return True

    sample = img.convert("RGB")
    sample.thumbnail((128, 128), Image.Resampling.LANCZOS)
    colors = sample.getcolors(maxcolors=256)
    return colors is not None


def _save_webp_image(
    img: Image.Image,
    output_path: str,
    webp_compression: str,
    webp_quality: int,
) -> None:
    if webp_compression == "auto":
        lossless = _should_use_lossless_webp(img)
    else:
        lossless = webp_compression == "lossless"

    if lossless:
        img.save(output_path, lossless=True, quality=100, method=6)
    else:
        img.save(output_path, lossless=False, quality=webp_quality, method=6)


def _save_cropped_image(
    pg: Page,
    page_number: int,
    output_dir: str,
    dpi: int,
    file_format: str,
    jpg_quality: int,
    webp_compression: str,
    webp_quality: int,
    tif_compression: str,
) -> None:
    img = _render_page_image(pg, dpi)
    bbox = _get_content_bbox(img)
    if bbox is None:
        cropped_img = img
    else:
        cropped_img = img.crop(bbox)
    output_path = os.path.join(output_dir, f"{page_number + 1}.{file_format}")

    if file_format == "jpg":
        cropped_img.save(output_path, quality=jpg_quality, dpi=(dpi, dpi))
    elif file_format == "png":
        cropped_img.save(output_path, dpi=(dpi, dpi))
    elif file_format == "webp":
        _save_webp_image(cropped_img, output_path, webp_compression, webp_quality)
    elif file_format == "tif":
        compression = TIFF_COMPRESSIONS[tif_compression]
        if compression is None:
            cropped_img.save(output_path, dpi=(dpi, dpi))
        elif compression == "jpeg":
            cropped_img.save(
                output_path,
                dpi=(dpi, dpi),
                compression=compression,
                quality=jpg_quality,
            )
        else:
            cropped_img.save(output_path, dpi=(dpi, dpi), compression=compression)
    else:
        cropped_img.save(output_path, quality=95)


def _save_cropped_pdf(doc: fitz.Document, output_dir: str, file: str, dpi: int) -> None:
    for page_number in tqdm(range(doc.page_count), desc="正在裁剪PDF页面", unit="页"):
        pg = doc.load_page(page_number)
        img = _render_page_image(pg, dpi)
        bbox = _get_content_bbox(img)
        if not bbox:
            continue

        page_rect = pg.rect
        media_box = pg.mediabox
        scale_x = page_rect.width / img.width
        scale_y = page_rect.height / img.height
        crop_rect = fitz.Rect(
            page_rect.x0 + (bbox[0] * scale_x),
            page_rect.y0 + (bbox[1] * scale_y),
            page_rect.x0 + (bbox[2] * scale_x),
            page_rect.y0 + (bbox[3] * scale_y),
        )
        crop_rect = fitz.Rect(
            max(media_box.x0, crop_rect.x0),
            max(media_box.y0, crop_rect.y0),
            min(media_box.x1, crop_rect.x1),
            min(media_box.y1, crop_rect.y1),
        )
        if not crop_rect.is_empty:
            pg.set_cropbox(crop_rect)

    filename = os.path.splitext(os.path.basename(file))[0]
    output_path = os.path.join(output_dir, f"{filename}.pdf")
    doc.save(output_path)


def convert_pdf(
    file: str,
    dpi: int = 300,
    file_format: str = "jpg",
    jpg_quality: int = 95,
    webp_compression: str = "auto",
    webp_quality: int = 80,
    tif_compression: str = "lzw",
) -> None:
    """
    将PDF文件转换为图片并自动裁剪空白边距

    Args:
        file (str): PDF文件路径
        dpi (int, optional): 输出图片的DPI. 默认为 300.
        file_format (str, optional): 输出格式 ('jpg', 'png', 'webp', 'avif', 'tif' 或 'pdf'). 默认为 'jpg'.
        jpg_quality (int, optional): JPG质量，范围 0-100。默认为 95.
        webp_compression (str, optional): WebP 压缩方式，可选 'auto', 'lossy', 'lossless'。默认为 'auto'.
        webp_quality (int, optional): WebP 有损压缩质量，范围 0-100。默认为 80.
        tif_compression (str, optional): TIFF 压缩方式，可选 'none', 'lzw', 'jpeg'。默认为 'lzw'.
    """
    file_format = file_format.lower()
    webp_compression = webp_compression.lower()
    tif_compression = tif_compression.lower()

    if not 0 <= jpg_quality <= 100:
        raise ValueError("jpg_quality must be between 0 and 100")

    if webp_compression not in WEBP_COMPRESSIONS:
        raise ValueError(f"Unsupported WebP compression: {webp_compression}")

    if not 0 <= webp_quality <= 100:
        raise ValueError("webp_quality must be between 0 and 100")

    if tif_compression not in TIFF_COMPRESSIONS:
        raise ValueError(f"Unsupported TIFF compression: {tif_compression}")

    if (
        file_format == "tif"
        and tif_compression != "none"
        and not features.check_codec("libtiff")
    ):
        raise RuntimeError("TIFF compression requires libtiff support in Pillow")

    output_dir = _get_output_dir(file)
    doc = fitz.open(file)
    try:
        _print_font_warnings(doc)

        if file_format == "pdf":
            _save_cropped_pdf(doc, output_dir, file, dpi)
            return

        if file_format not in IMAGE_FORMATS:
            raise ValueError(f"Unsupported format: {file_format}")

        for page_number in tqdm(range(doc.page_count), desc="正在转换页面", unit="页"):
            pg = doc.load_page(page_number)
            _save_cropped_image(
                pg,
                page_number,
                output_dir,
                dpi,
                file_format,
                jpg_quality,
                webp_compression,
                webp_quality,
                tif_compression,
            )
    finally:
        doc.close()
