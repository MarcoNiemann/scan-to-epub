import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from docling.document_converter import DocumentConverter

from .config import IMAGE_EXTENSIONS, OUTPUT_DIRNAME


@dataclass
class ExtractionResult:
    """Outcome of processing a single image page."""

    image_name: str
    markdown_text: str | None
    error: str | None

    @property
    def success(self) -> bool:
        return self.error is None


def find_images(directory: Path) -> list[Path]:
    """Return all supported image files in *directory*, sorted by name."""
    return sorted(
        f
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def _process_single_image(image_file: Path, output_dir: Path) -> ExtractionResult:
    """Convert one image to Markdown and write it to *output_dir*."""
    try:
        # Each worker gets its own converter to avoid shared mutable state.
        converter = DocumentConverter()
        result = converter.convert(str(image_file))
        markdown_text = result.document.export_to_markdown()

        output_file = output_dir / f"{image_file.name}.md"
        output_file.write_text(markdown_text, encoding="utf-8")

        return ExtractionResult(
            image_name=image_file.name,
            markdown_text=markdown_text,
            error=None,
        )
    except Exception as exc:
        return ExtractionResult(
            image_name=image_file.name,
            markdown_text=None,
            error=str(exc),
        )


def extract_pages(
    image_files: list[Path],
    output_dir: Path | None = None,
    *,
    max_workers: int | None = None,
    progress_callback: Callable[[ExtractionResult], None] | None = None,
) -> list[ExtractionResult]:
    """Convert *image_files* to Markdown in parallel.

    Args:
        image_files: Ordered list of image paths to process.
        output_dir: Directory where .md files are written.  When *None* the
            ``extracted_markdown`` sub-folder inside the parent of the first
            image is used.
        max_workers: Thread-pool size.  Defaults to ``min(pages, cpu*2)``.
        progress_callback: Called in the main thread after each page completes.
            Receives the :class:`ExtractionResult` for that page.

    Returns:
        List of :class:`ExtractionResult` objects (order matches completion,
        not necessarily input order).
    """
    if not image_files:
        return []

    if output_dir is None:
        output_dir = image_files[0].parent / OUTPUT_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)

    if max_workers is None:
        max_workers = min(len(image_files), max(1, (os.cpu_count() or 1) * 2))

    results: list[ExtractionResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_image = {
            executor.submit(_process_single_image, image_file, output_dir): image_file
            for image_file in image_files
        }

        for future in as_completed(future_to_image):
            result = future.result()
            results.append(result)
            if progress_callback is not None:
                progress_callback(result)

    return results


def combine_pages(
    results: list[ExtractionResult],
    image_files: list[Path],
    output_dir: Path,
    output_filename: str = "combined.md",
) -> Path:
    """Merge per-page Markdown into one file, ordered by *image_files*.

    Pages are separated by a Markdown horizontal rule and annotated with a
    comment carrying the source filename so the origin of each section stays
    traceable.

    Args:
        results: Extraction results (may be in any order).
        image_files: The original sorted input list – defines page order.
        output_dir: Directory where the combined file is written.
        output_filename: Name of the output file.

    Returns:
        Path to the written combined file.
    """
    result_map = {r.image_name: r for r in results if r.success}

    parts: list[str] = []
    for image_file in image_files:
        result = result_map.get(image_file.name)
        if result is None or not result.markdown_text:
            continue
        parts.append(f"<!-- {image_file.name} -->\n\n{result.markdown_text}")

    combined = "\n\n---\n\n".join(parts)
    output_file = output_dir / output_filename
    output_file.write_text(combined, encoding="utf-8")
    return output_file
