from pathlib import Path

from ebooklib import epub
import markdown


def convert_markdown_to_epub(
    markdown_file: Path,
    *,
    output_file: Path | None = None,
    title: str | None = None,
    language: str = "en",
) -> Path:
    """Convert a Markdown file into an EPUB file.

    The Markdown content is rendered into a single XHTML chapter. The caller is
    expected to provide a combined Markdown file that already contains the page
    order they want reflected in the EPUB.
    """
    if not markdown_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {markdown_file}")

    if output_file is None:
        output_file = markdown_file.with_suffix(".epub")

    book_title = title or markdown_file.stem.replace("_", " ").replace("-", " ").title()
    markdown_text = markdown_file.read_text(encoding="utf-8")
    html_body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists", "toc"])

    book = epub.EpubBook()
    book.set_identifier(str(output_file.resolve()))
    book.set_title(book_title)
    book.set_language(language)

    chapter = epub.EpubHtml(title=book_title, file_name="content.xhtml", lang=language)
    chapter.content = (
        "<html><head><meta charset='utf-8'></head><body>"
        f"{html_body}"
        "</body></html>"
    )

    nav = epub.EpubNav()
    ncx = epub.EpubNcx()

    style = epub.EpubItem(
        uid="style_nav",
        file_name="style/style.css",
        media_type="text/css",
        content=(
            "body { font-family: Georgia, serif; line-height: 1.5; }\n"
            "h1, h2, h3 { margin-top: 1.4em; }\n"
            "p { margin: 0.6em 0; }\n"
        ),
    )

    chapter.add_item(style)
    book.add_item(chapter)
    book.add_item(nav)
    book.add_item(ncx)
    book.add_item(style)

    book.toc = (epub.Link("content.xhtml", book_title, "content"),)
    book.spine = ["nav", chapter]

    epub.write_epub(str(output_file), book, {})
    return output_file