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
from scan_to_epub.config import OUTPUT_DIRNAME


def _print_result(result: ExtractionResult) -> None:
    print(f"\nProcessing complete: {result.image_name}")
    print("-" * 50)
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Saved markdown to: {result.image_name}.md")
        print(result.markdown_text)


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

    output_dir = directory / OUTPUT_DIRNAME
    max_workers = args.workers
    if max_workers is None:
        max_workers = min(len(image_files), max(1, (os.cpu_count() or 1) * 2))

    print(f"Markdown output directory: {output_dir}")
    print(f"Processing {len(image_files)} image(s) with up to {max_workers} worker(s)")

    results = extract_pages(
        image_files,
        output_dir,
        max_workers=max_workers,
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
        )
        print(f"EPUB saved to: {epub_file}")


if __name__ == "__main__":
    main()
