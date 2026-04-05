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


UI_LANGUAGE_OPTIONS = ["en", "de"]

UI_TEXT: dict[str, dict[str, str]] = {
    "page_title": {"en": "Scan to EPUB", "de": "Scan zu EPUB"},
    "page_caption": {
        "en": "Extract text from scanned book pages using OCR.",
        "de": "Extrahieren Sie Text aus gescannten Buchseiten mit OCR.",
    },
    "interface_language": {"en": "Interface language", "de": "Sprache"},
    "input_folder": {"en": "Input folder", "de": "Eingabeordner"},
    "output_folder": {"en": "Output folder", "de": "Ausgabeordner"},
    "home": {"en": "🏠 Home", "de": "🏠 Start"},
    "up": {"en": "⬆ Up", "de": "⬆ Hoch"},
    "use_current_folder": {
        "en": "✅ Use current folder",
        "de": "✅ Aktuellen Ordner verwenden",
    },
    "browsing": {"en": "Browsing", "de": "Aktueller Ordner"},
    "subfolders": {"en": "Subfolders", "de": "Unterordner"},
    "choose_subfolder": {
        "en": "Choose a subfolder to open...",
        "de": "Unterordner zum Oeffnen auswaehlen...",
    },
    "open_selected_folder": {
        "en": "📂 Open selected folder",
        "de": "📂 Ausgewaehlten Ordner oeffnen",
    },
    "selected_path": {"en": "Selected path", "de": "Ausgewaehlter Pfad"},
    "selected_path_placeholder": {
        "en": "/path/to/folder",
        "de": "/pfad/zum/ordner",
    },
    "copy_from_input": {
        "en": "📋 Copy from input folder",
        "de": "📋 Aus Eingabeordner uebernehmen",
    },
    "combine_checkbox": {
        "en": "Combine all pages into a single markdown file after extraction",
        "de": "Alle Seiten nach der Extraktion in einer Markdown-Datei zusammenfassen",
    },
    "epub_checkbox": {
        "en": "Convert the combined markdown file to EPUB",
        "de": "Zusammengefuehrte Markdown-Datei in EPUB umwandeln",
    },
    "ocr_language": {"en": "OCR language", "de": "OCR-Sprache"},
    "ocr_mode_default": {"en": "German (default)", "de": "Deutsch (Standard)"},
    "ocr_mode_explicit": {
        "en": "Explicit language codes",
        "de": "Explizite Sprachcodes",
    },
    "ocr_mode_auto": {"en": "Auto detect", "de": "Automatisch erkennen"},
    "ocr_language_help": {
        "en": (
            "German default is backend-specific: tesseract uses de, easyocr uses "
            "de+fr. Auto detect delegates OCR backend selection to Docling."
        ),
        "de": (
            "Der deutsche Standard ist backend-abhaengig: tesseract nutzt de, "
            "easyocr nutzt de+fr. Automatisch erkennen uebergibt die Auswahl an Docling."
        ),
    },
    "ocr_backend": {"en": "OCR backend", "de": "OCR-Backend"},
    "ocr_backend_help": {
        "en": (
            "Choose the OCR engine. Tesseract is the default. EasyOCR is available "
            "as an optional backend. Auto lets Docling pick based on your system."
        ),
        "de": (
            "Waehlen Sie die OCR-Engine. Tesseract ist Standard. EasyOCR ist optional. "
            "Auto laesst Docling je nach System entscheiden."
        ),
    },
    "ocr_codes": {"en": "OCR language codes", "de": "OCR-Sprachcodes"},
    "ocr_codes_help": {
        "en": "Comma-separated language codes, for example: de or de,en.",
        "de": "Kommagetrennte Sprachcodes, zum Beispiel: de oder de,en.",
    },
    "start_extraction": {"en": "Start extraction", "de": "Extraktion starten"},
    "err_enter_code": {
        "en": "Enter at least one OCR language code or switch back to the default.",
        "de": "Geben Sie mindestens einen OCR-Sprachcode ein oder wechseln Sie zum Standardmodus.",
    },
    "err_backend_auto_codes": {
        "en": "OCR backend 'auto' does not accept explicit OCR language codes.",
        "de": "OCR-Backend 'auto' akzeptiert keine expliziten OCR-Sprachcodes.",
    },
    "err_mode_auto_backend": {
        "en": "OCR language mode 'Auto detect' requires OCR backend 'auto'.",
        "de": "OCR-Sprachmodus 'Automatisch erkennen' erfordert das OCR-Backend 'auto'.",
    },
    "err_invalid_input_dir": {
        "en": "Input folder '{directory}' is not a valid directory.",
        "de": "Eingabeordner '{directory}' ist kein gueltiges Verzeichnis.",
    },
    "err_create_output_dir": {
        "en": "Could not create output folder '{output_dir}': {error}",
        "de": "Ausgabeordner '{output_dir}' konnte nicht erstellt werden: {error}",
    },
    "warn_no_images": {
        "en": "No supported image files found in the input folder.",
        "de": "Keine unterstuetzten Bilddateien im Eingabeordner gefunden.",
    },
    "found_images": {
        "en": "Found **{count}** image(s). Output will be saved to `{output_dir}`.",
        "de": "**{count}** Bild(er) gefunden. Ausgabe wird in `{output_dir}` gespeichert.",
    },
    "ocr_mode_auto_caption": {
        "en": "OCR mode: auto detect via Docling.",
        "de": "OCR-Modus: automatische Erkennung ueber Docling.",
    },
    "ocr_languages_caption": {
        "en": "OCR languages: {languages}",
        "de": "OCR-Sprachen: {languages}",
    },
    "ocr_easy_default_caption": {
        "en": "OCR languages: de, fr (default for easyocr)",
        "de": "OCR-Sprachen: de, fr (Standard fuer easyocr)",
    },
    "ocr_tess_default_caption": {
        "en": "OCR languages: de (default for tesseract)",
        "de": "OCR-Sprachen: de (Standard fuer tesseract)",
    },
    "ocr_backend_default_caption": {
        "en": "OCR languages: backend default (auto mode)",
        "de": "OCR-Sprachen: Backend-Standard (Auto-Modus)",
    },
    "ocr_backend_caption": {
        "en": "OCR backend: {backend}",
        "de": "OCR-Backend: {backend}",
    },
    "progress_starting": {"en": "Starting...", "de": "Starte..."},
    "progress_processed": {
        "en": "Processed {done} / {total}",
        "de": "Verarbeitet {done} / {total}",
    },
    "result_error": {
        "en": "❌ {image}: {error}",
        "de": "❌ {image}: {error}",
    },
    "progress_done": {"en": "Done!", "de": "Fertig!"},
    "success_pages_saved": {
        "en": "All pages saved to `{output_dir}`.",
        "de": "Alle Seiten wurden in `{output_dir}` gespeichert.",
    },
    "success_combined_saved": {
        "en": "Combined file saved to `{combined_file}`.",
        "de": "Zusammengefuehrte Datei wurde in `{combined_file}` gespeichert.",
    },
    "success_epub_saved": {
        "en": "EPUB saved to `{epub_file}`.",
        "de": "EPUB wurde in `{epub_file}` gespeichert.",
    },
}


def _t(key: str, language: str, **kwargs: str | int) -> str:
    text = UI_TEXT[key][language]
    if kwargs:
        return text.format(**kwargs)
    return text


def _resolve_ocr_languages(
    mode: str,
    language_codes_text: str,
    ui_language: str,
) -> str | list[str] | None:
    """Translate Streamlit OCR controls to extractor input."""
    if mode == "default":
        return None
    if mode == "auto":
        return "auto"

    language_codes = [
        code.strip().lower() for code in language_codes_text.split(",") if code.strip()
    ]
    if not language_codes:
        raise ValueError(_t("err_enter_code", ui_language))
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


def _render_folder_picker(key_prefix: str, label: str, ui_language: str) -> str:
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
        if st.button(_t("home", ui_language), key=f"{key_prefix}_home"):
            st.session_state[browse_key] = str(Path.home())
            st.rerun()
    with nav_col_2:
        if st.button(_t("up", ui_language), key=f"{key_prefix}_up"):
            st.session_state[browse_key] = str(browse_dir.parent)
            st.rerun()
    with nav_col_3:
        if st.button(_t("use_current_folder", ui_language), key=f"{key_prefix}_use"):
            st.session_state[selected_key] = str(browse_dir)
            st.session_state[f"{key_prefix}_text"] = str(browse_dir)
            st.rerun()

    st.caption(f"{_t('browsing', ui_language)}: `{browse_dir}`")

    subdirectories = _list_subdirectories(browse_dir)
    selected_subdirectory = st.selectbox(
        _t("subfolders", ui_language),
        options=subdirectories,
        format_func=lambda path: path.name,
        index=None,
        placeholder=_t("choose_subfolder", ui_language),
        key=f"{key_prefix}_selectbox",
    )
    if st.button(
        _t("open_selected_folder", ui_language),
        disabled=selected_subdirectory is None,
        key=f"{key_prefix}_open",
    ):
        st.session_state[browse_key] = str(selected_subdirectory)
        st.rerun()

    selected = st.text_input(
        _t("selected_path", ui_language),
        value=st.session_state[selected_key],
        placeholder=_t("selected_path_placeholder", ui_language),
        key=f"{key_prefix}_text",
    )
    st.session_state[selected_key] = selected
    return selected


# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Scan to EPUB", layout="wide")
ui_language = st.selectbox(
    "Interface language / Sprache",
    options=UI_LANGUAGE_OPTIONS,
    format_func=lambda value: "English" if value == "en" else "Deutsch",
)

st.title(_t("page_title", ui_language))
st.caption(_t("page_caption", ui_language))

# ── Input folder ──────────────────────────────────────────────────────────────
with st.container(border=True):
    directory_input = _render_folder_picker(
        "input",
        _t("input_folder", ui_language),
        ui_language,
    )

# ── Output folder ─────────────────────────────────────────────────────────────
with st.container(border=True):
    copy_col, _ = st.columns([2, 3])
    with copy_col:
        if st.button(_t("copy_from_input", ui_language), disabled=not directory_input):
            st.session_state["output_selected"] = directory_input
            st.session_state["output_browse"] = directory_input
            st.rerun()

    output_input = _render_folder_picker(
        "output",
        _t("output_folder", ui_language),
        ui_language,
    )

# ── Options ───────────────────────────────────────────────────────────────────
st.divider()

combine_option = st.checkbox(
    _t("combine_checkbox", ui_language),
    value=True,
)
epub_option = st.checkbox(
    _t("epub_checkbox", ui_language),
    value=True,
)

ocr_mode = st.radio(
    _t("ocr_language", ui_language),
    options=["default", "explicit", "auto"],
    format_func=lambda option: {
        "default": _t("ocr_mode_default", ui_language),
        "explicit": _t("ocr_mode_explicit", ui_language),
        "auto": _t("ocr_mode_auto", ui_language),
    }[option],
    help=_t("ocr_language_help", ui_language),
)
backend_options = ["tesseract", "easyocr", "auto"]
ocr_backend = st.selectbox(
    _t("ocr_backend", ui_language),
    options=backend_options,
    index=backend_options.index(DEFAULT_OCR_BACKEND),
    help=_t("ocr_backend_help", ui_language),
)
ocr_language_codes = st.text_input(
    _t("ocr_codes", ui_language),
    value="de",
    disabled=ocr_mode != "explicit",
    help=_t("ocr_codes_help", ui_language),
)

st.divider()

# ── Extraction ────────────────────────────────────────────────────────────────
can_start = bool(directory_input and output_input)
if st.button(_t("start_extraction", ui_language), disabled=not can_start):
    directory = Path(directory_input)
    output_dir = Path(output_input)

    try:
        ocr_languages = _resolve_ocr_languages(
            ocr_mode,
            ocr_language_codes,
            ui_language,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if ocr_backend == "auto" and ocr_languages not in (None, "auto"):
        st.error(_t("err_backend_auto_codes", ui_language))
        st.stop()
    if ocr_backend in {"tesseract", "easyocr"} and ocr_languages == "auto":
        st.error(_t("err_mode_auto_backend", ui_language))
        st.stop()

    if not directory.is_dir():
        st.error(_t("err_invalid_input_dir", ui_language, directory=directory))
    elif not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except OSError as exc:
            st.error(
                _t(
                    "err_create_output_dir",
                    ui_language,
                    output_dir=output_dir,
                    error=exc,
                )
            )
            st.stop()

    image_files = find_images(directory)
    if not image_files:
        st.warning(_t("warn_no_images", ui_language))
    else:
        st.info(
            _t("found_images", ui_language, count=len(image_files), output_dir=output_dir)
        )
        if ocr_languages == "auto":
            st.caption(_t("ocr_mode_auto_caption", ui_language))
        elif ocr_languages:
            st.caption(
                _t(
                    "ocr_languages_caption",
                    ui_language,
                    languages=", ".join(ocr_languages),
                )
            )
        else:
            if ocr_backend == "easyocr":
                st.caption(_t("ocr_easy_default_caption", ui_language))
            elif ocr_backend == "tesseract":
                st.caption(_t("ocr_tess_default_caption", ui_language))
            else:
                st.caption(_t("ocr_backend_default_caption", ui_language))
        st.caption(_t("ocr_backend_caption", ui_language, backend=ocr_backend))

        progress_bar = st.progress(0, text=_t("progress_starting", ui_language))
        results_container = st.container()
        completed = {"count": 0}

        def _on_result(result: ExtractionResult) -> None:
            completed["count"] += 1
            fraction = completed["count"] / len(image_files)
            progress_bar.progress(
                fraction,
                text=_t(
                    "progress_processed",
                    ui_language,
                    done=completed["count"],
                    total=len(image_files),
                ),
            )
            with results_container:
                if result.success:
                    with st.expander(f"✅ {result.image_name}"):
                        st.markdown(result.markdown_text)
                else:
                    st.error(
                        _t(
                            "result_error",
                            ui_language,
                            image=result.image_name,
                            error=result.error,
                        )
                    )

        results = extract_pages(
            image_files,
            output_dir,
            ocr_backend=ocr_backend,
            ocr_languages=ocr_languages,
            progress_callback=_on_result,
        )
        progress_bar.progress(1.0, text=_t("progress_done", ui_language))
        st.success(_t("success_pages_saved", ui_language, output_dir=output_dir))

        combined_file = None
        if combine_option or epub_option:
            combined_file = combine_pages(results, image_files, output_dir)
            st.success(
                _t(
                    "success_combined_saved",
                    ui_language,
                    combined_file=combined_file,
                )
            )

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
            st.success(_t("success_epub_saved", ui_language, epub_file=epub_file))
