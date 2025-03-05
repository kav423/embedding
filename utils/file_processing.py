import os
import shutil
import logging

_log = logging.getLogger(__name__)

def process_directory_png(output_images_dir, output_embeddings_dir):
    if not os.path.exists(output_embeddings_dir):
        os.makedirs(output_embeddings_dir)

    for filename in os.listdir(output_images_dir):
        file_path = os.path.join(output_images_dir, filename)
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == ".npy":
                try:
                    shutil.move(file_path, output_embeddings_dir)
                    print(f"The file '{filename}' now in '{output_embeddings_dir}'")
                except Exception as e:
                    print(f"Movement error '{filename}': {e}")
            else:
                print(f"The file '{filename}' is not .npy, skipped")