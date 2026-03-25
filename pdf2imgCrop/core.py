import os

import fitz
from PIL import Image, ImageOps, features
from fitz import Page
from tqdm import tqdm

IMAGE_FORMATS = {"jpg", "png", "webp", "avif", "tif"}
TIFF_COMPRESSIONS = {
    "none": None,
    "lzw": "tiff_lzw",
    "jpeg": "jpeg",
}


def _get_output_dir(file: str) -> str:
    filename, _ = os.path.splitext(file)
    output_dir = filename + "output"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _render_page_image(pg: Page, dpi: int) -> Image.Image:
    pg_width = pg.rect.width / 72
    pg_height = pg.rect.height / 72
    pix_dpi_width = int(pg_width * dpi)
    pix_dpi_height = int(pg_height * dpi)
    zoom = 16
    mat = fitz.Matrix(zoom, zoom).prerotate(0)
    pix = pg.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img.resize((pix_dpi_width, pix_dpi_height), Image.Resampling.LANCZOS)


def _get_content_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    img_inverse = ImageOps.invert(img)
    return img_inverse.getbbox()


def _save_cropped_image(
    pg: Page,
    page_number: int,
    output_dir: str,
    dpi: int,
    file_format: str,
    jpg_quality: int,
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
        cropped_img.save(output_path, quality=95, method=6)
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
    tif_compression: str = "lzw",
) -> None:
    """
    将PDF文件转换为图片并自动裁剪空白边距

    Args:
        file (str): PDF文件路径
        dpi (int, optional): 输出图片的DPI. 默认为 300.
        file_format (str, optional): 输出格式 ('jpg', 'png', 'webp', 'avif', 'tif' 或 'pdf'). 默认为 'jpg'.
        jpg_quality (int, optional): JPG质量，范围 0-100。默认为 95.
        tif_compression (str, optional): TIFF 压缩方式，可选 'none', 'lzw', 'jpeg'。默认为 'lzw'.
    """
    file_format = file_format.lower()
    tif_compression = tif_compression.lower()

    if not 0 <= jpg_quality <= 100:
        raise ValueError("jpg_quality must be between 0 and 100")

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
                tif_compression,
            )
    finally:
        doc.close()
