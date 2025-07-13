import os
import shutil
from collections import deque
import re
import markdown
from python_segments.html_builders.NavigationBuilder import *
from python_segments.html_builders.HTMLBuilder import *
from python_segments.MarkdownProcessor import *
from python_segments.helpers import *
from python_segments.JSONViewer import *;
from python_segments.CustomMarkdownExtension import *;
from python_segments.FileManager import *;

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        if not os.path.exists(in_directory):
            raise ValueError(f"Input directory does not exist: {in_directory}")
        self.in_directory = os.path.abspath(in_directory)
        self.out_directory = os.path.abspath(out_directory)
        self.link_to_filepath = {}
        self.files = []
        self.offset = 0
        self.cached_pages = {}
        self.header_list = []
        self.in_table = False
        self.counter = 1
        
        self.add_dirs_to_dict("")
        self.navigation_builder = NavigationBuilder(self.link_to_filepath)
        self.html_builder = HTMLBuilder()

        self.JSONViewer = JSONViewer(self)
        self.FileManager = FileManager()
    
    def process_markdown(self, text, add_to_header_list=True):
        extensions = [
            CustomMarkdownExtension(self.link_to_filepath, make_offset(self.offset), self, add_to_header_list),
            ObsidianFootnoteExtension(self.counter),
            "sane_lists",
            "tables", 
            "nl2br"
        ]
        text = fix_table_spacing(text)
        processed_html = markdown.markdown(text, extensions=extensions)
        
        processed_html = re.sub(r'</p>\s*<p', '</p>\n<br>\n<p', processed_html)

        self.counter += 1
        
        return processed_html
    
    def read_lines(self, file_lines, opening, add_to_header_list=True):
        processed_content = self.process_markdown("".join(file_lines[opening:]), add_to_header_list)
        
        return processed_content

    def file_viewer(self, file_dir, add_to_header_list=True):
        try:
            if file_dir.replace("/","\\") in self.cached_pages:
                return self.cached_pages[file_dir.replace("/","\\")]
            
            if not os.path.exists(file_dir):
                raise FileNotFoundError(f"File not found: {file_dir}")
                
            file_lines = self.FileManager.readlines_raw(file_dir)
        
            opening = 0
            if file_lines and file_lines[0] == "---\n":
                for i in range(1, len(file_lines)):
                    if file_lines[i] == "---\n":
                        opening = i+1
                        break
            
            new_file = self.read_lines(file_lines, opening, add_to_header_list=add_to_header_list)
            (self.cached_pages)[file_dir] = new_file
            return new_file
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            print(f"Error processing {file_dir}: {e}")
            return f"<p>Error loading file: {file_dir}</p>"
        
    def add_files_to_dict(self, sep_files, rel_dir):
        nu_rel_dir = "." + rel_dir + "\\"
        for file in sep_files:
            extension = file.split('.')[-1]
            if extension == "md":
                name = file.split('.')[0]
                html_pruned = (nu_rel_dir + name.replace(" ", "-")).lower() + ".html"
                (self.link_to_filepath)[name] = html_pruned
                if(rel_dir != ""):
                    (self.link_to_filepath)[nu_rel_dir.replace("\\", "/")[2:]+name] = html_pruned
            elif extension == "canvas":
                name = file.split(".")[0] + ".canvas"
                html_pruned = (nu_rel_dir + name.replace(" ", "-")).lower() + ".html"
                (self.link_to_filepath)[name] = html_pruned
                if(rel_dir != ""):
                    (self.link_to_filepath)[nu_rel_dir.replace("\\", "/")[2:]+name] = html_pruned
            else:
                file_pruned = (nu_rel_dir + file.replace(" ", "-")).lower()
                (self.link_to_filepath)[file] = file_pruned
                if(rel_dir != ""):
                    (self.link_to_filepath)[nu_rel_dir.replace("\\", "/")[2:]+file] = file_pruned

    def add_dirs_to_dict(self, path):
        stack = deque([path])
        while stack:
            path = stack.popleft()
            nu_dir = self.in_directory + "\\" + path
            files_and_dirs = os.listdir(nu_dir)
            sep_files = [f for f in files_and_dirs if (os.path.isfile(nu_dir+'/'+f) and f[0] != '~')]
            dirs = [f for f in files_and_dirs if (os.path.isdir(nu_dir+'/'+f) and f[0] != '.' and f[0] != '~')]
            
            self.add_files_to_dict(sep_files, path)
            for file in sep_files:
                temp = ".\\" + path + "\\"
                (self.files).append(temp.replace("\\\\", "\\") + file)

            for dir in reversed(dirs):
                nu_dr = path + "\\" + dir
                stack.appendleft(nu_dr)
        
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [__, file_name, extension] = file.split(".")
            file_dir = self.in_directory + file[1:]
            if extension == "md":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.html_builder.top_part(file_name, self.offset)

                viewed_file = self.file_viewer(file_dir)

                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:-3])
                self.header_list = []
                
                new_file += make_op_close_inline_tag("h1 class=\"file-title\"", file_name)
                new_file += make_opening_tag("article")

                new_file += viewed_file
                
                new_file += make_closing_tag("article")
                
                new_file += self.html_builder.bottom_part()
                    
                self.FileManager.writeToFile(self.out_directory + self.link_to_filepath[full_file_name.replace('\\', '/')].replace(" ", "-"), new_file)
                # break
            elif extension == "canvas":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.html_builder.top_part(file_name, self.offset, is_json=True)

                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:] + ".html")
                self.header_list = []
                
                new_file += make_op_close_inline_tag("h1 class=\"file-title\"", file_name + ".CANVAS")

                new_file += self.JSONViewer.json_viewer(file_dir)
                
                new_file += self.html_builder.bottom_part(is_json=True)
                    
                self.FileManager.writeToFile(self.out_directory + self.link_to_filepath[full_file_name.replace('\\', '/') + ".canvas"].replace(" ", "-"), new_file)
            else:
                # write file as-is
                export_file = self.out_directory + file.split(".", 1)[1].replace(" ", "-").lower()
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        
        self.FileManager.write_files(self.out_directory)
