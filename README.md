# Scan to EPUB

Convert scanned page images into Markdown and EPUB.

This project is designed for two audiences:
- Users who just want to convert scanned pages without coding.
- Developers who want to extend the pipeline (OCR, post-processing, UI, export formats).

As of now this is more of a hobby project and should not be used for any productive settings.

## Features

- OCR extraction from image folders using `docling` with selectable backends (`tesseract` default, optional `easyocr`, or `auto`).
- German OCR by default, with backend-specific defaults (tesseract: de, easyocr: de+fr), plus optional explicit language codes or a Docling auto-detect mode.
- High-quality OCR defaults for scanned pages: higher render resolution and full-page OCR.
- Parallel image processing for faster extraction.
- Per-page Markdown output (`<image-name>.md`).
- Combined Markdown output in source page order.
- EPUB generation from the combined Markdown file.
- Streamlit web interface with input/output folder pickers.
- CLI for automation and scripting.

## Supported Input Formats

The extractor currently scans these file extensions:
- `.png`
- `.jpg`
- `.jpeg`
- `.tif`
- `.tiff`
- `.bmp`
- `.gif`

## Installation

### Requirements

- Python `>= 3.11`
- Tesseract OCR runtime (default OCR backend)

### Install Tesseract + Language Data

The default backend is `tesseract`, so install the engine and language packs
before first extraction.

#### macOS (Homebrew)

```bash
brew install tesseract tesseract-lang
```

#### Linux (apt-get, Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-spa
```

If the Latin package is available in your distro repo, install it too:

```bash
sudo apt-get install -y tesseract-ocr-lat
```

#### Windows

Option A (`winget`):

```powershell
winget install UB-Mannheim.TesseractOCR
```

Option B (`choco`):

```powershell
choco install tesseract
```

After installation, ensure these language files are available in your
Tesseract `tessdata` directory:

- `deu.traineddata` (German)
- `fra.traineddata` (French, optional but recommended for mixed content)
- `eng.traineddata` (English)
- `spa.traineddata` (Spanish)
- `lat.traineddata` (Latin, if available)

You can verify installed languages with:

```bash
tesseract --list-langs
```

### Option A: Install with `uv` (recommended)

```bash
uv sync
```

### Option B: Install with `venv` and `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start (No Coding)

### Run the Streamlit app

```bash
streamlit run app.py
```

### In the UI

1. Pick the **Input folder** (where your scanned images are).
2. Pick the **Output folder**.
3. Optional: click **Copy from input folder** in the output block.
4. Keep **OCR backend** on **tesseract** (default), switch to **easyocr** if needed.
5. Keep **OCR language** on **German (default)** for the common case, enter explicit language codes when needed, or switch to **Auto detect** together with backend `auto`.
6. Leave options enabled to produce:
   - per-page Markdown
   - combined Markdown
   - EPUB
7. Click **Start extraction**.

## Command Line Usage

You can also run conversion from the terminal.

### Run via project script

```bash
scan-to-epub /path/to/images
```

```bash
scan-to-epub /path/to/images --ocr-language de
scan-to-epub /path/to/images --ocr-language de,en
scan-to-epub /path/to/images --ocr-language auto
scan-to-epub /path/to/images --ocr-backend easyocr --ocr-language de,fr
```

### Run via Python directly

```bash
python cli.py /path/to/images
```

### CLI options

```text
--no-combine             Skip combined markdown output.
--combined-output NAME   Combined markdown filename (default: combined.md).
--ocr-backend NAME       OCR backend: tesseract (default), easyocr, auto.
--ocr-language CODE      OCR language code, comma-separated codes, or 'auto'.
--title TITLE            EPUB title metadata.
```

### Important behavior

- EPUB is created only from the combined Markdown file.
- If EPUB is requested and combined Markdown does not exist yet, the tool creates it first.
- CLI currently writes outputs to: `<input-folder>/extracted_markdown`.
- OCR backend defaults to `tesseract`.
- Default OCR language is backend-specific: `tesseract -> de`, `easyocr -> de,fr`.
- `easyocr` remains available via `--ocr-backend easyocr` or the UI backend selector.
- `--ocr-backend auto` delegates OCR backend selection to Docling, so behavior may vary by platform.
- `--ocr-language auto` is intended for backend `auto`.
- The default OCR profile favors extraction quality over speed and uses higher-resolution page rendering plus full-page OCR.

## License

This project is licensed under `AGPL-3.0-or-later`. See `LICENSE`.

Reason: the project uses `EbookLib`, which is licensed under AGPLv3+.

## Output Structure

Typical output directory contents:

```text
extracted_markdown/
  IMG_0001.jpg.md
  IMG_0002.jpg.md
  ...
  combined.md
  combined.epub
```

## Project Structure

```text
scan-to-epub/
  app.py                  # Streamlit UI
  cli.py                  # Command line entry point
  pyproject.toml          # Packaging and dependencies
  scan_to_epub/
    __init__.py
    config.py             # Supported formats and constants
    extractor.py          # OCR extraction + combining logic
    epub.py               # Markdown -> EPUB conversion
```

## Development Guide

### Run in editable mode

```bash
pip install -e .
```

### Suggested workflow

1. Add or modify logic in `scan_to_epub/` first.
2. Keep `cli.py` and `app.py` as thin orchestration layers.
3. Validate both interfaces after changes:
   - `python cli.py <folder>`
   - `streamlit run app.py`

### Architecture notes

- `extract_pages(...)` performs OCR in parallel and writes per-page Markdown.
- `extract_pages(..., ocr_languages=...)` defaults to German, accepts explicit language codes, and supports `"auto"` for Docling's automatic OCR mode.
- `combine_pages(...)` merges successful page outputs in source image order.
- `convert_markdown_to_epub(...)` takes a single Markdown file and produces EPUB.

This separation makes it easy to add new frontends (API, desktop app) without rewriting conversion logic.

## Troubleshooting

### No images found

Check that your files use supported extensions and are inside the selected input folder.

### Missing package errors

Reinstall dependencies:

```bash
pip install -e .
```

### First run takes longer

`EasyOCR` downloads model data on first use. That initial run is slower, but later runs reuse the cached models.

The current default OCR profile also renders pages at higher resolution to improve recognition quality, so processing can be slower and use more memory than before.

### Streamlit not found

Install dependencies in the active environment, then rerun:

```bash
streamlit run app.py
```

## Note on AI-Usage

The code present in this repository is partially created by AI coding tools.
Corresponding changes and contributions are welcome, but changes should be reviewed by humans and actually contribute value for potential users (_value over masses of codes or features or exceptionally artisan code_).

If you deem it fit you may highlight AI contributions as such.
Especially if the review has been brief - or in case you lack the expertise for review - corresponding hints are appreciated.

## Roadmap Ideas

- Better chapter detection for EPUB TOC.
- Metadata editor (author, language, publisher).
- Optional post-processing/clean-up rules for OCR text.
- Automated tests for extraction and EPUB generation.

## Contributing

Contributions are welcome.

For substantial changes, open an issue first to discuss scope and design.

When submitting a pull request:
- Describe the user-facing behavior change.
- Include reproduction steps.
- Include CLI and/or UI validation notes.
