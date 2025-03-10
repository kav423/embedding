import pypandoc
import logging
from pathlib import Path

_log = logging.getLogger(__name__)


def convert_markdown_to_html(markdown_file, html_file):
    """
    Конвертирует Markdown в HTML с помощью pypandoc.
    Встроенные CSS-стили добавляются для разрывов страниц.
    """
    if not markdown_file.exists():
        _log.error(f"Markdown file not found: {markdown_file}")
        return False

    # Встроенные CSS-стили
    css_styles = """
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
        }

        h1 {
            page-break-before: always; /* Начинать новую страницу перед каждым h1 */
        }

        h1:first-of-type {
            page-break-before: avoid; /* Не начинать новую страницу перед первым h1 */
        }

        img {
            max-width: 100%;
            height: auto;
        }
    </style>
    """

    try:
        _log.info(f"Converting {markdown_file} to {html_file}")

        # Конвертируем Markdown в HTML
        html_content = pypandoc.convert_file(
            str(markdown_file),
            'html',
            format='md',
            extra_args=['-s']  # standalone HTML
        )

        # Добавляем встроенные CSS-стили
        html_content = html_content.replace('</head>', f'{css_styles}</head>')

        # Сохраняем HTML-файл
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        _log.info(f"Successfully converted {markdown_file} to {html_file}")
        return True
    except Exception as e:
        _log.error(f"Error converting {markdown_file} to {html_file}: {e}")
        return False