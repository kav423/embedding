import os
import pypandoc
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

def convert_markdown_to_html(markdown_file, html_file, css_file=None):
    if not os.path.exists(markdown_file):
        print(f"Error: Markdown file not found: {markdown_file}")
        return False

    extra_args = ['-s']
    if css_file:
        if not os.path.exists(css_file):
            print(f"Error: CSS file not found: {css_file}")
            return False
        extra_args.extend(['--css', css_file])

    try:
        pypandoc.convert_file(
            markdown_file,
            'html',
            outputfile=html_file,
            extra_args=extra_args
        )
        print(f"Successfully converted {markdown_file} to {html_file}")
        return True
    except Exception as e:
        print(f"Error converting {markdown_file} to {html_file}: {e}")
        return False