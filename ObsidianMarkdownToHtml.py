import os
import shutil
import re
import markdown
from python_segments.html_builders.NavigationBuilder import *
from python_segments.html_builders.HTMLBuilder import *
from python_segments.MarkdownProcessor.MarkdownProcessor import *
from python_segments.helpers import *
from python_segments.JSONViewer import *;
from python_segments.MarkdownProcessor.CustomMarkdownExtension import *;
from python_segments.FileManager import *;

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        if not os.path.exists(in_directory):
            raise ValueError(f"Input directory does not exist: {in_directory}")
        self.in_directory = os.path.abspath(in_directory)
        self.out_directory = os.path.abspath(out_directory)
        self.offset = 0
        self.header_list = []
        self.counter = 1
        self.FileManager = FileManager()
        self.files, self.link_to_filepath = self.FileManager.add_dirs_to_dict(self.in_directory)
        self.navigation_builder = NavigationBuilder(self.link_to_filepath)
        self.html_builder = HTMLBuilder()
        self.JSONViewer = JSONViewer(self)
        self.MarkdownProcessor = MarkdownProcessor(self, self.link_to_filepath)
    
    def process_markdown(self, text, add_to_header_list=True):
        return self.MarkdownProcessor.process_markdown(text, self.offset, add_to_header_list)
    
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [__, file_name, extension] = file.split(".")
            file_dir = self.in_directory + file[1:]
            if extension == "md":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.html_builder.top_part(file_name, self.offset)
                viewed_file = self.FileManager.file_viewer(file_dir, self.process_markdown)
                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:-3])
                self.header_list = []
                new_file += self.html_builder.middle_part(file_name, viewed_file)
                new_file += self.html_builder.bottom_part(self.offset)
                self.FileManager.writeToFile(self.out_directory + self.link_to_filepath[full_file_name.replace('\\', '/')].replace(" ", "-"), new_file)
            elif extension == "canvas":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.html_builder.top_part(file_name, self.offset, is_json=True)
                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:] + ".html")
                self.header_list = []
                new_file += self.html_builder.middle_part(file_name, self.JSONViewer.json_viewer(file_dir), is_json=True)
                new_file += self.html_builder.bottom_part(self.offset, is_json=True)
                self.FileManager.writeToFile(self.out_directory + self.link_to_filepath[full_file_name.replace('\\', '/') + ".canvas"].replace(" ", "-"), new_file)
            else:
                # write file as-is
                export_file = self.out_directory + file.split(".", 1)[1].replace(" ", "-").lower()
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        self.FileManager.write_files(self.out_directory)
