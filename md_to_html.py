import os
import pypandoc
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

def convert_markdown_to_html(markdown_file: Path, html_file: Path, css_file: Path = None):
    """
    Конвертирует Markdown в HTML с сохранением разделителей страниц.
    """
    if not markdown_file.exists():
        _log.error(f"Markdown file not found: {markdown_file}")
        return False

    # Добавляем разделители страниц в Markdown
    with open(markdown_file, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Заменяем разделители страниц на HTML-комментарии
    markdown_content = markdown_content.replace("<!-- Page", "<div style='page-break-before: always;'></div><!-- Page")

    # Сохраняем измененный Markdown
    modified_markdown_file = markdown_file.with_name(f"{markdown_file.stem}_modified.md")
    with open(modified_markdown_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    # Конвертируем Markdown в HTML
    extra_args = ['-s']
    if css_file:
        if not css_file.exists():
            _log.error(f"CSS file not found: {css_file}")
            return False
        extra_args.extend(['--css', str(css_file)])

    try:
        pypandoc.convert_file(
            str(modified_markdown_file),
            'html',
            outputfile=str(html_file),
            extra_args=extra_args
        )
        _log.info(f"Successfully converted {markdown_file} to {html_file}")
        return True
    except Exception as e:
        _log.error(f"Error converting {markdown_file} to {html_file}: {e}")
        return False