IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}
)

OUTPUT_DIRNAME = "extracted_markdown"

# OCR backend configuration.
DEFAULT_OCR_BACKEND = "tesseract"
OCR_BACKEND_AUTO = "auto"

# Default OCR languages per backend.
# Tesseract defaults to German-only for reliability when optional language data
# (e.g. French) is not installed locally.
DEFAULT_OCR_LANGUAGES_TESSERACT: tuple[str, ...] = ("de",)
# EasyOCR can keep German+French to improve special character support.
DEFAULT_OCR_LANGUAGES_EASYOCR: tuple[str, ...] = ("de", "fr")
# Backward-compatible alias used by existing callers.
DEFAULT_OCR_LANGUAGES: tuple[str, ...] = DEFAULT_OCR_LANGUAGES_TESSERACT
OCR_LANGUAGE_AUTO = "auto"

# OCR quality profile tuned for scanned book pages.
OCR_IMAGE_SCALE = 2.0
OCR_FORCE_FULL_PAGE = True
OCR_BITMAP_AREA_THRESHOLD = 0.0
EASYOCR_CONFIDENCE_THRESHOLD = 0.3
# Use standard recognition network (default, balanced, works reliably)
EASYOCR_RECOGNITION_NETWORK = "standard"

# Layout analysis model: EGRET provides higher accuracy for reading order detection
# Alternatives: DOCLING_LAYOUT_HERON (faster but less accurate), DOCLING_LAYOUT_EGRET_LARGE (slower but more accurate)
LAYOUT_MODEL_NAME = "docling_layout_egret_medium"
