import os
from pathlib import Path
base_dir = Path(__file__).resolve().parent

class FileManager:
    def __init__(self):
        self.files = [
            ("styles/omth.css", "style.css"),
            ("scripts/json_canvas.js", "canvas.js"),
            ("scripts/searcher.js", "searcher.js")
        ]
    
    def readlines_raw(self, file_dir):
        try:
            with open(file_dir, "r", encoding="utf8") as f:
                return f.readlines()
        except UnicodeDecodeError:
            # Fallback to different encoding
            with open(file_dir, "r", encoding="latin-1") as f:
                return f.readlines()

    def read_raw(self, file_dir):
        try:
            with open(file_dir, "r", encoding="utf8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_dir, "r", encoding="latin-1") as f:
                return f.read()

    def writeToFile(self, export_file, new_file):
        os.makedirs(os.path.dirname(export_file), exist_ok=True)
        
        exp_file = open(export_file, "w", encoding="utf-8")
        exp_file.write(new_file)
        exp_file.close()
    
    def write_files(self, out_directory):
        for src, dst in self.files:
            src_path = (base_dir / ".." / src).resolve()
            dst_path = Path(out_directory) / dst
            with open(src_path, "r") as f_in, open(dst_path, "w") as f_out:
                f_out.write(f_in.read())
