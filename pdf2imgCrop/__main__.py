import argparse
from .core import convert_pdf


def main():
    parser = argparse.ArgumentParser(
        description="将PDF文件转换为图片并自动裁剪空白边距",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "file",
        help="PDF文件路径,(Path to the PDF file)",
    )

    parser.add_argument(
        "-d",
        "--dpi",
        type=int,
        default=300,
        help="输出图片的DPI, 默认为 300, (DPI for output images, default is 300)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["jpg", "jpeg", "png", "tif", "tiff"],
        default="jpg",
        help="输出图片格式, 默认为 'jpg', (Format of output images, default is 'jpg')",
    )

    parser.add_argument(
        "-p",
        "--page",
        type=str,
        default=None,
        help="指定转换的页面编号(例如1,3-5,7), 默认为 None, 表示转换1、3、4、5、7页, (Specify page numbers to convert, e.g., 1,3-5,7. Default is None, which converts pages 1, 3, 4, 5, and 7)",
    )

    parser.add_argument(
        "-t",
        "--tiff-compression",
        choices=[
            None,
            "group3",
            "group4",
            "jpeg",
            "lzma",
            "packbits",
            "tiff_adobe_deflate",
            "tiff_ccitt",
            "tiff_lzw",
            "tiff_raw_16",
            "tiff_sgilog",
            "tiff_sgilog24",
            "tiff_thunderscan",
            "webp",
            "zstd",
        ],
        default=None,
        help="TIFF压缩方式, 默认为 None, (TIFF compression method, default is None)",
    )
    args = parser.parse_args()

    try:
        if not args.file.lower().endswith(".pdf"):
            raise ValueError("文件必须是PDF格式！(The file must be a PDF format!)")
        convert_pdf(args.file, args.dpi, args.format, args.page, args.tiff_compression)
        print(f"\n转换完成！输出目录: {args.file}output")
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
