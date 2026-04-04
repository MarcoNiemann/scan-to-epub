"""Streamlit interface for scan-to-epub."""

from pathlib import Path

import streamlit as st

from scan_to_epub import (
    ExtractionResult,
    combine_pages,
    convert_markdown_to_epub,
    extract_pages,
    find_images,
)
from scan_to_epub.config import DEFAULT_OCR_BACKEND


def _resolve_ocr_languages(mode: str, language_codes_text: str) -> str | list[str] | None:
    """Translate Streamlit OCR controls to extractor input."""
    if mode == "German (default)":
        return None
    if mode == "Auto detect":
        return "auto"

    language_codes = [
        code.strip().lower() for code in language_codes_text.split(",") if code.strip()
    ]
    if not language_codes:
        raise ValueError(
            "Enter at least one OCR language code or switch back to the default."
        )
    return language_codes


def _list_subdirectories(directory: Path) -> list[Path]:
    """Return readable direct child directories sorted by name."""
    try:
        return sorted(
            [child for child in directory.iterdir() if child.is_dir()],
            key=lambda child: child.name.lower(),
        )
    except OSError:
        return []


def _render_folder_picker(key_prefix: str, label: str) -> str:
    """Render a self-contained folder picker block.

    Uses ``{key_prefix}_browse`` and ``{key_prefix}_selected`` in
    ``st.session_state``.  Returns the currently selected path string.
    """
    browse_key = f"{key_prefix}_browse"
    selected_key = f"{key_prefix}_selected"

    if browse_key not in st.session_state:
        st.session_state[browse_key] = str(Path.home())
    if selected_key not in st.session_state:
        st.session_state[selected_key] = ""

    browse_dir = Path(st.session_state[browse_key])
    if not browse_dir.is_dir():
        browse_dir = Path.home()
        st.session_state[browse_key] = str(browse_dir)

    st.subheader(label)

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 2])
    with nav_col_1:
        if st.button("🏠 Home", key=f"{key_prefix}_home"):
            st.session_state[browse_key] = str(Path.home())
            st.rerun()
    with nav_col_2:
        if st.button("⬆ Up", key=f"{key_prefix}_up"):
            st.session_state[browse_key] = str(browse_dir.parent)
            st.rerun()
    with nav_col_3:
        if st.button("✅ Use current folder", key=f"{key_prefix}_use"):
            st.session_state[selected_key] = str(browse_dir)
            st.session_state[f"{key_prefix}_text"] = str(browse_dir)
            st.rerun()

    st.caption(f"Browsing: `{browse_dir}`")

    subdirectories = _list_subdirectories(browse_dir)
    selected_subdirectory = st.selectbox(
        "Subfolders",
        options=subdirectories,
        format_func=lambda path: path.name,
        index=None,
        placeholder="Choose a subfolder to open…",
        key=f"{key_prefix}_selectbox",
    )
    if st.button("📂 Open selected folder", disabled=selected_subdirectory is None, key=f"{key_prefix}_open"):
        st.session_state[browse_key] = str(selected_subdirectory)
        st.rerun()

    selected = st.text_input(
        "Selected path",
        value=st.session_state[selected_key],
        placeholder="/path/to/folder",
        key=f"{key_prefix}_text",
    )
    st.session_state[selected_key] = selected
    return selected


# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Scan to EPUB", layout="wide")
st.title("Scan to EPUB")
st.caption("Extract text from scanned book pages using OCR.")

# ── Input folder ──────────────────────────────────────────────────────────────
with st.container(border=True):
    directory_input = _render_folder_picker("input", "Input folder")

# ── Output folder ─────────────────────────────────────────────────────────────
with st.container(border=True):
    copy_col, _ = st.columns([2, 3])
    with copy_col:
        if st.button("📋 Copy from input folder", disabled=not directory_input):
            st.session_state["output_selected"] = directory_input
            st.session_state["output_browse"] = directory_input
            st.rerun()

    output_input = _render_folder_picker("output", "Output folder")

# ── Options ───────────────────────────────────────────────────────────────────
st.divider()

combine_option = st.checkbox(
    "Combine all pages into a single markdown file after extraction",
    value=True,
)
epub_option = st.checkbox(
    "Convert the combined markdown file to EPUB",
    value=True,
)

ocr_mode = st.radio(
    "OCR language",
    options=["German (default)", "Explicit language codes", "Auto detect"],
    help=(
        "German default is backend-specific: tesseract uses de, easyocr uses "
        "de+fr. Auto detect delegates OCR backend selection to Docling."
    ),
)
backend_options = ["tesseract", "easyocr", "auto"]
ocr_backend = st.selectbox(
    "OCR backend",
    options=backend_options,
    index=backend_options.index(DEFAULT_OCR_BACKEND),
    help=(
        "Choose the OCR engine. Tesseract is the default. EasyOCR is available "
        "as an optional backend. Auto lets Docling pick based on your system."
    ),
)
ocr_language_codes = st.text_input(
    "OCR language codes",
    value="de",
    disabled=ocr_mode != "Explicit language codes",
    help="Comma-separated language codes, for example: de or de,en.",
)

st.divider()

# ── Extraction ────────────────────────────────────────────────────────────────
can_start = bool(directory_input and output_input)
if st.button("Start extraction", disabled=not can_start):
    directory = Path(directory_input)
    output_dir = Path(output_input)

    try:
        ocr_languages = _resolve_ocr_languages(ocr_mode, ocr_language_codes)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if ocr_backend == "auto" and ocr_languages not in (None, "auto"):
        st.error("OCR backend 'auto' does not accept explicit OCR language codes.")
        st.stop()
    if ocr_backend in {"tesseract", "easyocr"} and ocr_languages == "auto":
        st.error("OCR language mode 'Auto detect' requires OCR backend 'auto'.")
        st.stop()

    if not directory.is_dir():
        st.error(f"Input folder '{directory}' is not a valid directory.")
    elif not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except OSError as exc:
            st.error(f"Could not create output folder '{output_dir}': {exc}")
            st.stop()

    image_files = find_images(directory)
    if not image_files:
        st.warning("No supported image files found in the input folder.")
    else:
        st.info(
            f"Found **{len(image_files)}** image(s). "
            f"Output will be saved to `{output_dir}`."
        )
        if ocr_languages == "auto":
            st.caption("OCR mode: auto detect via Docling.")
        elif ocr_languages:
            st.caption(f"OCR languages: {', '.join(ocr_languages)}")
        else:
            if ocr_backend == "easyocr":
                st.caption("OCR languages: de, fr (default for easyocr)")
            elif ocr_backend == "tesseract":
                st.caption("OCR languages: de (default for tesseract)")
            else:
                st.caption("OCR languages: backend default (auto mode)")
        st.caption(f"OCR backend: {ocr_backend}")

        progress_bar = st.progress(0, text="Starting…")
        results_container = st.container()
        completed = {"count": 0}

        def _on_result(result: ExtractionResult) -> None:
            completed["count"] += 1
            fraction = completed["count"] / len(image_files)
            progress_bar.progress(
                fraction,
                text=f"Processed {completed['count']} / {len(image_files)}",
            )
            with results_container:
                if result.success:
                    with st.expander(f"✅ {result.image_name}"):
                        st.markdown(result.markdown_text)
                else:
                    st.error(f"❌ {result.image_name}: {result.error}")

        results = extract_pages(
            image_files,
            output_dir,
            ocr_backend=ocr_backend,
            ocr_languages=ocr_languages,
            progress_callback=_on_result,
        )
        progress_bar.progress(1.0, text="Done!")
        st.success(f"All pages saved to `{output_dir}`.")

        combined_file = None
        if combine_option or epub_option:
            combined_file = combine_pages(results, image_files, output_dir)
            st.success(f"Combined file saved to `{combined_file}`.")

        if epub_option:
            if combined_file is None:
                combined_file = output_dir / "combined.md"
                if not combined_file.is_file():
                    combined_file = combine_pages(results, image_files, output_dir)

            epub_file = convert_markdown_to_epub(
                combined_file,
                output_file=output_dir / "combined.epub",
                title=directory.name,
            )
            st.success(f"EPUB saved to `{epub_file}`.")
