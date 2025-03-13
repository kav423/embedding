import subprocess
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

def generate_pdf(html_file, pdf_file, wkhtmltopdf_path, disable_javascript=False):
    """
    Конвертирует HTML в PDF с помощью wkhtmltopdf.
    """
    try:
        command = [wkhtmltopdf_path, '--enable-local-file-access', html_file, pdf_file]
        if disable_javascript:
            command.append("--disable-javascript")

        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        print(f"PDF successfully created: {pdf_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during execution wkhtmltopdf: {e}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        return False
    except FileNotFoundError:
        print(f"error: wkhtmltopdf not found at path {wkhtmltopdf_path}")
        return False