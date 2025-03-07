import subprocess
import logging
from pathlib import Path
from bs4 import BeautifulSoup

_log = logging.getLogger(__name__)

def generate_pdf(html_file_to_pdf, output_file_pdf, wkhtmltopdf_path, disable_javascript=False):
    try:
        command = [wkhtmltopdf_path, '--enable-local-file-access', html_file_to_pdf, output_file_pdf]
        if disable_javascript:
            command.append("--disable-javascript")

        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        print(f"PDF successfully created: {output_file_pdf}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during execution wkhtmltopdf: {e}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        return False
    except FileNotFoundError:
        print(f"error: wkhtmltopdf not found at path {wkhtmltopdf_path}")
        return False

def replace_char_in_links_bs4(html_file_path: Path, old_char: str, new_char: str, output_file_path: Path):
    """
    Заменяет символы в ссылках HTML-файла.
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        for img_tag in soup.find_all('img'):
            for attribute in ['src', 'srcset']:
                if attribute in img_tag.attrs:
                    attr_value = img_tag[attribute]
                    if old_char in attr_value:
                        img_tag[attribute] = attr_value.replace(old_char, new_char)

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        _log.info(f"Successfully replaced '{old_char}' with '{new_char}' in {html_file_path}")
        return True
    except Exception as e:
        _log.error(f"Error replacing characters in {html_file_path}: {e}")
        return False