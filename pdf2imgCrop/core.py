import fitz
from PIL import Image, ImageOps
import os
from typing import Iterable
from tqdm import tqdm
from fitz import Page


def convert_pdf(
    file: str,
    dpi: int = 300,
    file_format: str = "jpg",
    page: str = None,
    tiff_compression: str = None,
) -> None:
    """
    将PDF文件转换为图片并自动裁剪空白边距

    Args:
        file (str): PDF文件路径
        dpi (int, optional): 输出图片的DPI. 默认为 300.
        file_format (str, optional): 输出图片格式 ('jpg' 或 'png'). 默认为 'jpg'.
        page (str): 指定转换的页面编号. 默认为 None, 表示转换所有页面.
    """
    pages_to_handle = []
    if page is not None:
        pg_list = page.split(",")
        for pg in pg_list:
            if "-" in pg:
                start, end = map(int, pg.split("-"))
                if start > end:
                    raise ValueError(f"错误的页面范围: {pg}")
                pages_to_handle.extend(range(start, end + 1))
            else:
                try:
                    page_num = int(pg)
                except ValueError:
                    raise ValueError(f"错误的页面编号: {pg}")
                pages_to_handle.append(page_num)
        for i in range(len(pages_to_handle)):
            pages_to_handle[i] -= 1
    # 打开PDF文件
    if not os.path.exists(file):
        raise FileNotFoundError(f"文件不存在: {file}")
    if not file.lower().endswith(".pdf"):
        raise ValueError("文件必须是PDF格式！(The file must be a PDF format!)")
    doc = fitz.open(file)
    if not doc:
        raise ValueError(f"无法打开PDF文件: {file}")
    for pg_number, pg in enumerate(tqdm(doc, desc="正在转换页面", unit="页")):
        if page is not None:
            if pg.number not in pages_to_handle:
                continue
        # 获取页面的宽高
        pg_width = pg.rect.width / 72  # in inch
        pg_height = pg.rect.height / 72  # in inch
        # 计算对应dpi对应的像素
        pix_dpi_width = int(pg_width * dpi)
        pix_dpi_height = int(pg_height * dpi)
        zoom = 16
        mat = fitz.Matrix(zoom, zoom).prerotate(0)
        pix = pg.get_pixmap(matrix=mat, alpha=False)

        # 准备输出目录
        filename, _ = os.path.splitext(file)
        output_dir = filename + "output"
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # 裁剪空白区域
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # 将图片大小转为目标DPI大小
        img = img.resize((pix_dpi_width, pix_dpi_height), Image.LANCZOS)
        img_inverse = ImageOps.invert(img)
        bbox = img_inverse.getbbox()
        cropped_img = img.crop(bbox)

        # 保存处理后的图片
        output_path = os.path.join(output_dir, f"{pg.number + 1}.{file_format}")
        if file_format.lower() == "jpg" or file_format.lower() == "jpeg":
            cropped_img.save(
                output_path,
                quality=95,
                dpi=(dpi, dpi),
            )
        elif file_format.lower().startswith("tif") or file_format.lower().startswith("tiff"):
            cropped_img.save(
                output_path,
                compression=tiff_compression,
                dpi=(dpi, dpi),
            )
        else:
            cropped_img.save(
                output_path,
                dpi=(dpi, dpi),
            )

    doc.close()
