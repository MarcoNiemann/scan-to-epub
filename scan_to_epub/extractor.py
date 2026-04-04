import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    DOCLING_LAYOUT_EGRET_MEDIUM,
    EasyOcrOptions,
    LayoutOptions,
    OcrAutoOptions,
    PdfPipelineOptions,
    TableFormerMode,
    TesseractCliOcrOptions,
)
from docling.document_converter import DocumentConverter, ImageFormatOption

from .config import (
    DEFAULT_OCR_LANGUAGES,
    DEFAULT_OCR_LANGUAGES_EASYOCR,
    DEFAULT_OCR_LANGUAGES_TESSERACT,
    DEFAULT_OCR_BACKEND,
    EASYOCR_CONFIDENCE_THRESHOLD,
    EASYOCR_RECOGNITION_NETWORK,
    IMAGE_EXTENSIONS,
    OCR_BITMAP_AREA_THRESHOLD,
    OCR_FORCE_FULL_PAGE,
    OCR_IMAGE_SCALE,
    OCR_LANGUAGE_AUTO,
    OUTPUT_DIRNAME,
)


_thread_local = threading.local()

_SUPPORTED_OCR_BACKENDS = {"tesseract", "easyocr", "auto"}
_LANG_TO_TESSERACT = {
    "de": "deu",
    "fr": "fra",
    "en": "eng",
    "es": "spa",
    "it": "ita",
    "nl": "nld",
    "pt": "por",
}
_TESSERACT_TO_LANG = {value: key for key, value in _LANG_TO_TESSERACT.items()}


def _default_languages_for_backend(backend: str) -> tuple[str, ...]:
    if backend == "tesseract":
        return DEFAULT_OCR_LANGUAGES_TESSERACT
    if backend == "easyocr":
        return DEFAULT_OCR_LANGUAGES_EASYOCR
    return DEFAULT_OCR_LANGUAGES


@dataclass
class ExtractionResult:
    """Outcome of processing a single image page."""

    image_name: str
    markdown_text: str | None
    error: str | None

    @property
    def success(self) -> bool:
        return self.error is None


def _normalize_ocr_config(
    ocr_backend: str | None,
    ocr_languages: str | list[str] | tuple[str, ...] | None,
) -> tuple[str, tuple[str, ...]]:
    """Return normalized OCR backend and language tuple.

    ``None`` backend defaults to Tesseract. ``"auto"`` backend opts into
    Docling's automatic OCR backend selection, which may differ across
    operating systems.

    Backward compatibility: when ``ocr_backend`` is not set and
    ``ocr_languages='auto'`` is passed, this enables backend auto mode.
    """
    backend = (ocr_backend or DEFAULT_OCR_BACKEND).strip().lower()
    if backend not in _SUPPORTED_OCR_BACKENDS:
        raise ValueError(
            f"Unsupported OCR backend '{ocr_backend}'. "
            "Choose one of: tesseract, easyocr, auto"
        )

    if ocr_languages is None:
        if backend == "auto":
            return ("auto", ())
        return (backend, _default_languages_for_backend(backend))

    if isinstance(ocr_languages, str):
        raw_values = [value.strip().lower() for value in ocr_languages.split(",")]
    else:
        raw_values = [value.strip().lower() for value in ocr_languages]

    language_codes = tuple(dict.fromkeys(value for value in raw_values if value))
    if not language_codes:
        raise ValueError("OCR language configuration must not be empty")

    if language_codes == (OCR_LANGUAGE_AUTO,):
        if ocr_backend is not None and backend != "auto":
            raise ValueError(
                "'auto' OCR language cannot be combined with an explicit OCR backend"
            )
        return ("auto", ())

    if OCR_LANGUAGE_AUTO in language_codes:
        raise ValueError(
            "'auto' cannot be combined with explicit OCR language codes"
        )

    if backend == "auto":
        raise ValueError(
            "Explicit language codes are not supported with backend 'auto'. "
            "Set backend to 'tesseract' or 'easyocr', or omit language codes."
        )

    return (backend, language_codes)


def _language_codes_for_backend(
    backend: str,
    language_codes: tuple[str, ...],
) -> list[str]:
    """Map human-friendly language codes to backend-specific formats."""
    if backend == "tesseract":
        mapped: list[str] = []
        for code in language_codes:
            if len(code) == 3:
                mapped.append(code)
            else:
                mapped.append(_LANG_TO_TESSERACT.get(code, code))
        return mapped

    if backend == "easyocr":
        mapped = []
        for code in language_codes:
            if len(code) == 2:
                mapped.append(code)
            else:
                mapped.append(_TESSERACT_TO_LANG.get(code, code))
        return mapped

    return list(language_codes)


def find_images(directory: Path) -> list[Path]:
    """Return all supported image files in *directory*, sorted by name."""
    return sorted(
        f
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def _create_converter(
    ocr_backend: str | None = None,
    ocr_languages: str | list[str] | tuple[str, ...] | None = None,
) -> DocumentConverter:
    """Create a Docling converter with a predictable OCR configuration.

    By default the pipeline uses Tesseract CLI with German+French.
    EasyOCR remains available as an optional backend. Setting backend to
    ``"auto"`` delegates engine selection to Docling.

    The pipeline is tuned for OCR quality on scanned book pages rather than
    raw throughput: higher page render resolution, full-page OCR, lower
    recognition threshold, and a more accurate layout model for correct
    reading order detection.
    """
    ocr_mode, language_codes = _normalize_ocr_config(ocr_backend, ocr_languages)
    backend_languages = _language_codes_for_backend(ocr_mode, language_codes)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.images_scale = OCR_IMAGE_SCALE
    # Use higher-accuracy layout model for better text ordering
    pipeline_options.layout_options = LayoutOptions(
        model_spec=DOCLING_LAYOUT_EGRET_MEDIUM
    )
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    if ocr_mode == "auto":
        pipeline_options.ocr_options = OcrAutoOptions(
            force_full_page_ocr=OCR_FORCE_FULL_PAGE,
            bitmap_area_threshold=OCR_BITMAP_AREA_THRESHOLD,
        )
    elif ocr_mode == "easyocr":
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=backend_languages,
            force_full_page_ocr=OCR_FORCE_FULL_PAGE,
            bitmap_area_threshold=OCR_BITMAP_AREA_THRESHOLD,
            confidence_threshold=EASYOCR_CONFIDENCE_THRESHOLD,
            recog_network=EASYOCR_RECOGNITION_NETWORK,
            use_gpu=True,
            download_enabled=True,
            suppress_mps_warnings=True,
        )
    else:
        pipeline_options.ocr_options = TesseractCliOcrOptions(
            lang=backend_languages,
            force_full_page_ocr=OCR_FORCE_FULL_PAGE,
            bitmap_area_threshold=OCR_BITMAP_AREA_THRESHOLD,
        )

    return DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
        }
    )


def _get_converter(
    ocr_backend: str | None = None,
    ocr_languages: str | list[str] | tuple[str, ...] | None = None,
) -> DocumentConverter:
    """Return a per-thread converter instance.

    EasyOCR model initialization is comparatively expensive. Reusing one
    converter per worker thread avoids reloading the model for every image while
    still keeping thread-local state isolated. The cache key includes the OCR
    language configuration so different runs cannot accidentally share a
    converter with stale language settings.
    """
    cache_key = _normalize_ocr_config(ocr_backend, ocr_languages)
    converter_cache = getattr(_thread_local, "converter_cache", None)
    if converter_cache is None:
        converter_cache = {}
        _thread_local.converter_cache = converter_cache

    converter = converter_cache.get(cache_key)
    if converter is None:
        converter = _create_converter(ocr_backend, ocr_languages)
        converter_cache[cache_key] = converter
    return converter


def _process_single_image(
    image_file: Path,
    output_dir: Path,
    ocr_backend: str | None,
    ocr_languages: str | list[str] | tuple[str, ...] | None,
) -> ExtractionResult:
    """Convert one image to Markdown and write it to *output_dir*."""
    normalized_backend, normalized_languages = _normalize_ocr_config(
        ocr_backend, ocr_languages
    )
    backend_languages = _language_codes_for_backend(
        normalized_backend, normalized_languages
    )

    try:
        converter = _get_converter(ocr_backend, ocr_languages)
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
        error_message = str(exc)
        if (
            normalized_backend == "tesseract"
            and "document was empty" in error_message.lower()
        ):
            error_message = (
                f"{error_message}. Tesseract OCR used languages "
                f"{', '.join(backend_languages)}. Make sure these language "
                "packs are installed (for German use 'deu')."
            )
        return ExtractionResult(
            image_name=image_file.name,
            markdown_text=None,
            error=error_message,
        )


def extract_pages(
    image_files: list[Path],
    output_dir: Path | None = None,
    *,
    max_workers: int | None = None,
    ocr_backend: str | None = None,
    ocr_languages: str | list[str] | tuple[str, ...] | None = None,
    progress_callback: Callable[[ExtractionResult], None] | None = None,
) -> list[ExtractionResult]:
    """Convert *image_files* to Markdown in parallel.

    Args:
        image_files: Ordered list of image paths to process.
        output_dir: Directory where .md files are written.  When *None* the
            ``extracted_markdown`` sub-folder inside the parent of the first
            image is used.
        max_workers: Thread-pool size.  Defaults to ``min(pages, cpu*2)``.
        ocr_backend: OCR backend to use: ``"tesseract"`` (default),
            ``"easyocr"``, or ``"auto"``.
        ocr_languages: OCR language codes for EasyOCR, e.g. ``"de"`` or
            ``["de", "en"]``. ``None`` defaults to German+French.
            Use 2-letter codes for EasyOCR and 3-letter codes for Tesseract
            (common 2-letter codes are mapped automatically).
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
            executor.submit(
                _process_single_image,
                image_file,
                output_dir,
                ocr_backend,
                ocr_languages,
            ): image_file
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
