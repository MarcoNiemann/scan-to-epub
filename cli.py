"""Command-line entry point for scan-to-epub."""

import argparse
import os
from pathlib import Path

from scan_to_epub import (
    ExtractionResult,
    combine_pages,
    convert_markdown_to_epub,
    extract_pages,
    find_images,
)
from scan_to_epub.config import DEFAULT_OCR_BACKEND, OUTPUT_DIRNAME


def _print_result(result: ExtractionResult) -> None:
    print(f"\nProcessing complete: {result.image_name}")
    print("-" * 50)
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Saved markdown to: {result.image_name}.md")
        print(result.markdown_text)


def _parse_ocr_languages(values: list[str] | None) -> str | list[str] | None:
    """Normalize CLI OCR language arguments.

    ``None`` keeps extractor defaults. ``auto`` opts into Docling's automatic
    OCR mode. Otherwise values are treated as language codes and may be
    provided repeatedly or comma-separated.
    """
    if not values:
        return None

    language_codes: list[str] = []
    for value in values:
        language_codes.extend(
            code.strip().lower() for code in value.split(",") if code.strip()
        )

    if not language_codes:
        raise ValueError("--ocr-language requires at least one language code")

    if "auto" in language_codes:
        if len(language_codes) > 1:
            raise ValueError(
                "--ocr-language auto cannot be combined with explicit language codes"
            )
        return "auto"

    return language_codes


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract text from scanned page images and save Markdown output.",
    )
    parser.add_argument(
        "directory",
        help="Directory containing scanned page images.",
    )
    parser.add_argument(
        "--no-combine",
        action="store_true",
        help="Skip creating a combined markdown file after per-page extraction.",
    )
    parser.add_argument(
        "--combined-output",
        default="combined.md",
        help="Filename for the combined markdown output inside the output directory.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Maximum number of worker threads. Defaults to min(pages, cpu*2).",
    )
    parser.add_argument(
        "--ocr-backend",
        choices=["tesseract", "easyocr", "auto"],
        default=DEFAULT_OCR_BACKEND,
        help=(
            "OCR backend to use. 'tesseract' is the default, 'easyocr' is "
            "optional, and 'auto' lets Docling choose based on the environment."
        ),
    )
    parser.add_argument(
        "--ocr-language",
        dest="ocr_languages",
        action="append",
        default=None,
        help=(
            "OCR language code, e.g. 'de' or 'de,en'. Repeat the flag for "
            "multiple codes. Default depends on backend (tesseract: de, easyocr: de,fr). Use 'auto' to delegate "
            "OCR backend/language selection to Docling."
        ),
    )
    parser.add_argument(
        "--no-epub",
        action="store_true",
        help="Skip converting the combined markdown file to EPUB.",
    )
    parser.add_argument(
        "--epub-output",
        default="combined.epub",
        help="Filename for the EPUB output inside the output directory.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional title metadata for the generated EPUB.",
    )
    parser.add_argument(
        "--author",
        default=None,
        help="Optional author metadata for the generated EPUB.",
    )
    parser.add_argument(
        "--publisher",
        default=None,
        help="Optional publisher metadata for the generated EPUB.",
    )
    parser.add_argument(
        "--publication-year",
        type=int,
        default=None,
        help="Optional publication year metadata for the generated EPUB (e.g. 1872).",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        parser.error(f"'{directory}' is not a valid directory")

    image_files = find_images(directory)
    if not image_files:
        parser.error("No image files found in the directory")

    if args.workers is not None and args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.publication_year is not None and args.publication_year < 1:
        parser.error("--publication-year must be at least 1")

    try:
        ocr_languages = _parse_ocr_languages(args.ocr_languages)
    except ValueError as exc:
        parser.error(str(exc))

    if args.ocr_backend == "auto" and ocr_languages not in (None, "auto"):
        parser.error("--ocr-backend auto does not accept explicit --ocr-language values")
    if args.ocr_backend in {"tesseract", "easyocr"} and ocr_languages == "auto":
        parser.error(
            "--ocr-language auto requires --ocr-backend auto (or omit --ocr-backend)"
        )

    output_dir = directory / OUTPUT_DIRNAME
    max_workers = args.workers
    if max_workers is None:
        max_workers = min(len(image_files), max(1, (os.cpu_count() or 1) * 2))

    print(f"Markdown output directory: {output_dir}")
    print(f"Processing {len(image_files)} image(s) with up to {max_workers} worker(s)")
    print(f"OCR backend: {args.ocr_backend}")
    if ocr_languages == "auto":
        print("OCR language mode: auto (Docling backend auto selection)")
    elif ocr_languages:
        print(f"OCR languages: {', '.join(ocr_languages)}")
    else:
        if args.ocr_backend == "easyocr":
            print("OCR languages: de, fr (default for easyocr)")
        elif args.ocr_backend == "tesseract":
            print("OCR languages: de (default for tesseract)")
        else:
            print("OCR languages: backend default (auto mode)")

    results = extract_pages(
        image_files,
        output_dir,
        max_workers=max_workers,
        ocr_backend=args.ocr_backend,
        ocr_languages=ocr_languages,
        progress_callback=_print_result,
    )

    combined_file: Path | None = None
    if not args.no_combine or not args.no_epub:
        combined_file = combine_pages(
            results,
            image_files,
            output_dir,
            output_filename=args.combined_output,
        )
        print(f"\nCombined markdown saved to: {combined_file}")

    if not args.no_epub:
        if combined_file is None:
            combined_file = output_dir / args.combined_output
            if not combined_file.is_file():
                combined_file = combine_pages(
                    results,
                    image_files,
                    output_dir,
                    output_filename=args.combined_output,
                )

        epub_file = convert_markdown_to_epub(
            combined_file,
            output_file=output_dir / args.epub_output,
            title=args.title or directory.name,
            author=args.author,
            publisher=args.publisher,
            publication_year=args.publication_year,
        )
        print(f"EPUB saved to: {epub_file}")


if __name__ == "__main__":
    main()
