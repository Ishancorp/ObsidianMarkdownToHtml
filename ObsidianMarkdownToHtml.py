import os
import shutil
from python_segments.html_builders.HTMLBuilder import *
from python_segments.MarkdownProcessor.MarkdownProcessor import *
from python_segments.JSONViewer import *;
from python_segments.FileManager import *;

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        if not os.path.exists(in_directory):
            raise ValueError(f"Input directory does not exist: {in_directory}")
        self.in_directory = os.path.abspath(in_directory)
        self.out_directory = os.path.abspath(out_directory)
        self.offset = 0
        self.header_list = []
        self.FileManager = FileManager(self.in_directory, self.out_directory)
        self.files, self.link_to_filepath = self.FileManager.add_dirs_to_dict()
        self.html_builder = HTMLBuilder(self.link_to_filepath)
        self.MarkdownProcessor = MarkdownProcessor(self, self.link_to_filepath)
        self.JSONViewer = JSONViewer(self.MarkdownProcessor, self.in_directory, self.out_directory)
    
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [__, file_name, extension] = file.split(".")
            if extension == "md":
                viewed_file = self.FileManager.file_viewer(file, self.offset, self.MarkdownProcessor.process_markdown)
                self.FileManager.writeToFile(
                    Path(self.out_directory) / self.link_to_filepath[file_name[1:].replace('\\', '/')].replace(" ", "-"), 
                    self.html_builder.build_HTML(
                        os.path.basename(file_name), 
                        self.offset, 
                        self.header_list, 
                        file[2:-3], 
                        viewed_file,
                    )
                )
                self.header_list = []
            elif extension == "canvas":
                json_content = self.JSONViewer.json_viewer(file, self.offset)
                self.FileManager.writeToFile(
                    Path(self.out_directory) / self.link_to_filepath[file_name[1:].replace('\\', '/') + ".canvas"].replace(" ", "-"), 
                    self.html_builder.build_HTML(
                        os.path.basename(file_name), 
                        self.offset, 
                        self.header_list, 
                        file[2:] + ".html", 
                        json_content, 
                        is_json=True,
                    )
                )
            else:
                if file.startswith(".\\") or file.startswith("./"):
                    relative_path = file[2:]
                elif file.startswith("."):
                    relative_path = file[1:]
                else:
                    relative_path = file

                source_file = Path(self.in_directory) / relative_path
                export_file = Path(self.out_directory) / relative_path.replace(" ", "-")

                export_file.parent.mkdir(parents=True, exist_ok=True)

                if source_file.exists():
                    shutil.copy(source_file, export_file)
                else:
                    print(f"ERROR: Source file not found: {source_file}")

        print("Compiled")
        self.FileManager.write_files(self.out_directory)
