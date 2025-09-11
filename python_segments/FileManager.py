from collections import deque
import json
from os import listdir, makedirs
from os.path import isfile, isdir, dirname, exists
from pathlib import Path
base_dir = Path(__file__).resolve().parent

class FileManager:
    def __init__(self, in_directory, out_directory):
        self.files = [
            ("styles/omth.css", "style.css"),
            ("scripts/json_canvas.js", "canvas.js"),
            ("scripts/searcher.js", "searcher.js")
        ]
        self.in_directory = in_directory
        self.out_directory = out_directory

    def add_dirs_to_dict(self):
        files = []
        link_to_filepath = {}
        basename_tracker = {}  # Track basename conflicts
        stack = deque([""])
        
        while stack:
            path = stack.popleft()
            nu_dir = self.in_directory + "\\" + path
            files_and_dirs = listdir(nu_dir)
            sep_files = [f for f in files_and_dirs if (isfile(nu_dir+'/'+f) and f[0] != '~')]
            dirs = [f for f in files_and_dirs if (isdir(nu_dir+'/'+f) and f[0] != '.' and f[0] != '~')]
            
            for file in sep_files:
                temp = ".\\" + path + "\\"
                files.append(temp.replace("\\\\", "\\") + file)
            
            for dir in reversed(dirs):
                nu_dr = path + "\\" + dir
                stack.appendleft(nu_dr)
        
            nu_rel_dir = "." + path + "\\"
            for file in sep_files:
                extension = file.split('.')[-1]
                
                if extension == "md":
                    name = file.split('.')[0]
                    html_pruned = (nu_rel_dir + name.replace(" ", "-")).lower() + ".html"
                    
                    # Always store the full path (guaranteed unique)
                    full_key = nu_rel_dir.replace("\\", "/")[2:] + name if path != "" else name
                    link_to_filepath[full_key] = html_pruned
                    
                    # Track basename usage for conflict detection
                    if name not in basename_tracker:
                        basename_tracker[name] = []
                    basename_tracker[name].append((full_key, html_pruned))
                    
                elif extension == "canvas":
                    name = file.split(".")[0] + ".canvas"
                    html_pruned = (nu_rel_dir + name.replace(" ", "-")).lower() + ".html"
                    
                    # Always store the full path (guaranteed unique)  
                    full_key = nu_rel_dir.replace("\\", "/")[2:] + name if path != "" else name
                    link_to_filepath[full_key] = html_pruned
                    
                    # Track basename usage for conflict detection
                    if name not in basename_tracker:
                        basename_tracker[name] = []
                    basename_tracker[name].append((full_key, html_pruned))
                    
                    
                elif extension == "base":
                    name = file.split(".")[0] + ".base"
                    html_pruned = (nu_rel_dir + name.replace(" ", "-")).lower() + ".html"
                    
                    # Always store the full path (guaranteed unique)  
                    full_key = nu_rel_dir.replace("\\", "/")[2:] + name if path != "" else name
                    link_to_filepath[full_key] = html_pruned
                    
                    # Track basename usage for conflict detection
                    if name not in basename_tracker:
                        basename_tracker[name] = []
                    basename_tracker[name].append((full_key, html_pruned))
                    
                else:
                    file_pruned = (nu_rel_dir + file.replace(" ", "-")).lower()
                    
                    # Always store the full path (guaranteed unique)
                    full_key = nu_rel_dir.replace("\\", "/")[2:] + file if path != "" else file
                    link_to_filepath[full_key] = file_pruned
                    
                    # Track basename usage for conflict detection
                    if file not in basename_tracker:
                        basename_tracker[file] = []
                    basename_tracker[file].append((full_key, file_pruned))
        
        # Handle basename mappings - create unique names for conflicts
        for basename, file_list in basename_tracker.items():
            if len(file_list) == 1:
                # No conflict - safe to use basename as key
                link_to_filepath[basename] = file_list[0][1]
            else:
                # Conflict detected - create unique basename mappings
                for i, (full_key, html_path) in enumerate(file_list):
                    # Extract directory path for uniqueness
                    dir_parts = full_key.split('/')[:-1] if '/' in full_key else []
                    
                    if dir_parts:
                        # Create unique key using last directory name
                        unique_basename = f"{dir_parts[-1]}\\{basename}"
                        link_to_filepath[unique_basename] = html_path
                    
                    # Also try creating a numbered variant as fallback
                    numbered_basename = f"{basename}-{i+1}"
                    link_to_filepath[numbered_basename] = html_path
        
        return files, link_to_filepath
    
    def readlines_raw(self, file_dir):
        try:
            with open(file_dir, "r", encoding="utf8") as f:
                return f.readlines()
        except UnicodeDecodeError:
            with open(file_dir, "r", encoding="latin-1") as f:
                return f.readlines()

    def read_raw(self, file):
        file_dir = self.in_directory + file
        try:
            with open(file_dir, "r", encoding="utf8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_dir, "r", encoding="latin-1") as f:
                return f.read()

    def writeToFile(self, export_file, new_file):
        makedirs(dirname(export_file), exist_ok=True)
        
        exp_file = open(export_file, "w", encoding="utf-8")
        exp_file.write(new_file)
        exp_file.close()
    
    def write_files(self, out_directory):
        for src, dst in self.files:
            src_path = (base_dir / ".." / src).resolve()
            dst_path = Path(out_directory) / dst
            with open(src_path, "r") as f_in, open(dst_path, "w") as f_out:
                f_out.write(f_in.read())
    
    def file_viewer(self, file, offset, process_markdown, add_to_header_list=True):
        file_dir = self.in_directory + file[1:]
        try:
            if not exists(file_dir):
                raise FileNotFoundError(f"File not found: {file_dir}")
            file_text = self.read_raw(file[1:])
            opening = 0
            if file_text.startswith("---\n"):
                first_end = file_text.find('\n', 4)
                if first_end != -1:
                    second_marker_pos = file_text.find('---\n', first_end + 1)
                    if second_marker_pos != -1:
                        opening = second_marker_pos + 4
            new_file = process_markdown(file_text[opening:], offset, add_to_header_list)
            return new_file
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            print(f"Error processing {file_dir}: {e}")
            return f"<p>Error loading file: {file_dir}</p>"
