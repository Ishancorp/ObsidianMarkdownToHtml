import os
import shutil
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
        self.FileManager = FileManager()
        self.files, self.link_to_filepath = self.FileManager.add_dirs_to_dict(self.in_directory)
        self.navigation_builder = NavigationBuilder(self.link_to_filepath)
        self.html_builder = HTMLBuilder()
        self.MarkdownProcessor = MarkdownProcessor(self, self.link_to_filepath)
        self.JSONViewer = JSONViewer(self.MarkdownProcessor)
    
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [__, file_name, extension] = file.split(".")
            file_dir = self.in_directory + file[1:]
            if extension == "md":
                seg_file_name = os.path.basename(file_name)
                new_file = self.html_builder.top_part(seg_file_name, self.offset)
                viewed_file = self.FileManager.file_viewer(file_dir, self.offset, self.MarkdownProcessor.process_markdown)
                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:-3])
                new_file += self.html_builder.middle_part(seg_file_name, viewed_file)
                new_file += self.html_builder.bottom_part(self.offset)
                self.FileManager.writeToFile(Path(self.out_directory) / self.link_to_filepath[file_name[1:].replace('\\', '/')].replace(" ", "-"), new_file)
                self.header_list = []
            elif extension == "canvas":
                seg_file_name = os.path.basename(file_name)
                new_file = self.html_builder.top_part(seg_file_name, self.offset, is_json=True)
                new_file += self.navigation_builder.generate_navigation_bar(self.offset, self.header_list, file[2:] + ".html")
                new_file += self.html_builder.middle_part(seg_file_name, self.JSONViewer.json_viewer(file_dir, self.offset), is_json=True)
                new_file += self.html_builder.bottom_part(self.offset, is_json=True)
                self.FileManager.writeToFile(Path(self.out_directory) / self.link_to_filepath[file_name[1:].replace('\\', '/') + ".canvas"].replace(" ", "-"), new_file)
            else:
                export_file = Path(self.out_directory) / file.split(".", 1)[1].replace(" ", "-").lower()
                export_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        self.FileManager.write_files(self.out_directory)
