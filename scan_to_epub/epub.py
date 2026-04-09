from pathlib import Path
from typing import Any

from ebooklib import epub
import markdown


def _flatten_toc_tokens(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return heading tokens in document order (including nested levels)."""
    flattened: list[dict[str, Any]] = []
    for token in tokens:
        flattened.append(token)
        children = token.get("children")
        if isinstance(children, list) and children:
            flattened.extend(_flatten_toc_tokens(children))
    return flattened


def convert_markdown_to_epub(
    markdown_file: Path,
    *,
    output_file: Path | None = None,
    title: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    publication_year: int | None = None,
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
    markdown_converter = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    html_body = markdown_converter.convert(markdown_text)
    toc_tokens = markdown_converter.toc_tokens

    book = epub.EpubBook()
    book.set_identifier(str(output_file.resolve()))
    book.set_title(book_title)
    book.set_language(language)
    if author:
        book.add_author(author)
    if publisher:
        book.add_metadata("DC", "publisher", publisher)
    if publication_year is not None:
        book.add_metadata("DC", "date", str(publication_year))

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

    flattened_tokens = _flatten_toc_tokens(toc_tokens)
    if flattened_tokens:
        book.toc = tuple(
            epub.Link(
                f"content.xhtml#{token['id']}",
                token["name"],
                f"heading_{index}",
            )
            for index, token in enumerate(flattened_tokens, start=1)
            if token.get("id") and token.get("name")
        )
    else:
        book.toc = ()
    book.spine = ["nav", chapter]

    epub.write_epub(str(output_file), book, {})
    return output_file