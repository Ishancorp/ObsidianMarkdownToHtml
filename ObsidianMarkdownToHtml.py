import os
import shutil
from pathlib import Path
import uuid
from python_segments.FileManager import FileManager
import json
import yaml

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        if not os.path.exists(in_directory):
            raise ValueError(f"Input directory does not exist: {in_directory}")

        self.in_directory = os.path.abspath(in_directory)
        self.out_directory = os.path.abspath(out_directory)

        self.FileManager = FileManager(self.in_directory, self.out_directory)
        self.files, self.link_to_filepath = self.FileManager.add_dirs_to_dict()

        self.create_file_content_mapping()

        self.write_renderer()

    def make_offset(self, file_path):
        if file_path.startswith('.\\') or file_path.startswith('./'):
            clean_path = file_path[2:]
        else:
            clean_path = file_path
        offset = clean_path.count('/') + clean_path.count('\\')

        if offset == 0:
            return '.'
        elif offset == 1:
            return '..'
        else:
            return ((offset-1) * "../") + ".."
    
    def write_renderer(self):
        src_path = (Path(__file__).resolve().parent / "scripts/renderer.js").resolve()
        dst_path = Path(self.out_directory) / 'renderer.js'
        with open(src_path, "r") as f_in:
            content = f_in.read()

        content = content.replace("{/*file_links*/}", json.dumps(self.link_to_filepath))
        content = content.replace("{/*file_content_map*/}", json.dumps(self.file_content_map))
        content = content.replace("{/*file_contents*/}", json.dumps(self.file_contents))
        content = content.replace("{/*file_properties*/}", json.dumps(self.file_properties))
        content = content.replace("/*in_directory*/0", json.dumps(self.in_directory))
        content = content.replace("/*out_directory*/0", json.dumps(self.out_directory))

        with open(dst_path, "w") as f_out:
            f_out.write(content)

    def create_file_content_mapping(self):
        """Create a mapping of file paths to their content for client-side access"""
        self.file_properties = {}
        self.file_content_map = {}
        self.file_contents = {}
        filename_counts = {}
        basename_counts = {}  # Track basenames separately
        
        for file_path in self.files:
            unique_id = str(uuid.uuid4())
            self.file_properties[unique_id] = {}
            self.file_properties[unique_id]["path"] = file_path[2:]
            self.file_properties[unique_id]["file"] = file_path.split('\\')[-1]
            self.file_properties[unique_id]["folder"] = file_path[2:].rsplit('\\', 1)[0].replace("\\", "/")
            self.file_properties[unique_id]["ext"] = file_path.split('.')[-1]
            if file_path.startswith('.\\') or file_path.startswith('./'):
                    relative_path = file_path[2:]
            else:
                relative_path = file_path
            
            # Always map the full relative path
            self.file_content_map[relative_path] = unique_id
            
            # Track filename with extension
            filename_with_ext = os.path.basename(relative_path)
            filename_without_ext = os.path.splitext(filename_with_ext)[0]
            
            if filename_with_ext not in filename_counts:
                filename_counts[filename_with_ext] = []
            filename_counts[filename_with_ext].append((relative_path, unique_id))
            
            if filename_without_ext not in basename_counts:
                basename_counts[filename_without_ext] = []
            basename_counts[filename_without_ext].append((relative_path, unique_id))

            full_path = os.path.join(self.in_directory, relative_path.replace('/', os.sep))
            if file_path.endswith('.base'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()
                        parsed_yaml = yaml.load(yaml_content, Loader=yaml.FullLoader)
                        self.file_contents[unique_id] = json.dumps(parsed_yaml)
                except Exception as e:
                    print(f"Error parsing YAML file {full_path}: {e}")
                    self.file_contents[unique_id] = "{}"
            elif file_path.endswith(('.md', '.canvas')):
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        if content.startswith('---\n'):
                            end_idx = content.find('\n---\n', 4)
                            if end_idx != -1:
                                prop_set = {}
                                for line in content[:end_idx + 5].split('\n')[1:-2]:
                                    key, val = line.split(": ")
                                    prop_set[key] = val
                                self.file_properties[unique_id]["notes"] = prop_set
                                content = content[end_idx + 5:]

                        self.file_contents[unique_id] = content
                
                except Exception as e:
                    print(f"Error reading file {full_path}: {e}")
            else:
                # For non-markdown files, store empty content but keep the mapping
                self.file_contents[unique_id] = ""
        
        # Handle filename mappings - prefer full filename with extension
        for filename_with_ext, file_list in filename_counts.items():
            if len(file_list) == 1:
                self.file_content_map[filename_with_ext] = file_list[0][1]
            else:
                # Multiple files with same name+extension - use first one and warn
                self.file_content_map[filename_with_ext] = file_list[0][1]
                print(f"Warning: Multiple files with name '{filename_with_ext}' found. Using: {file_list[0][0]}")
                print(f"  Conflicting files: {[item[0] for item in file_list]}")
        
        # Handle basename mappings - only if no conflicts with extensions
        for basename, file_list in basename_counts.items():
            if len(file_list) == 1:
                # Only one file with this basename - safe to map without extension
                self.file_content_map[basename] = file_list[0][1]
            else:
                # Multiple files with same basename - check if any are .md
                md_files = [item for item in file_list if item[0].endswith('.md')]
                if len(md_files) == 1:
                    # Only one .md file with this basename - use it for extension-less mapping
                    self.file_content_map[basename] = md_files[0][1]
                    print(f"Info: Multiple files with basename '{basename}' found. Using .md file for extension-less access: {md_files[0][0]}")
                    print(f"  Other files: {[item[0] for item in file_list if item != md_files[0]]}")
                    print(f"  Access non-md files using their full names with extensions.")
                else:
                    # Multiple files, no single .md - use first one but warn
                    self.file_content_map[basename] = file_list[0][1]
                    print(f"Warning: Multiple files with basename '{basename}' found. Using: {file_list[0][0]}")
                    print(f"  Conflicting files: {[item[0] for item in file_list]}")
                    print(f"  Access other files using their full names with extensions.")

    def build_html_with_raw_markdown(self, title, offset, data_current_file, type="md"):
        """Build HTML page with raw markdown that will be processed by marked.js"""

        return f"""<!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" charset="UTF-8">
        <title>{title}</title>
        <link rel="preconnect" href="https://rsms.me/">
        <link rel="preconnect" href="https://rsms.me/inter/inter.css">
        <link rel="stylesheet" href="{offset}\\style.css">
        {f'<link rel="stylesheet" href="{offset}\\canvas.css">' if type == "canvas" else ''}
        <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.3.0/marked.min.js"></script>
    </head>
    <body>
        <nav>
            <span>
                <button popovertarget="navbar" popovertargetaction="toggle"><i data-lucide="align-justify"></i></button>
                <div id="navbar" popover></div>
                <button popovertarget="searchbar" popovertargetaction="toggle"><i data-lucide="search"></i></button>
                <div id="searchbar" popover></div>
            </span>
            <p class="top-bar">{(data_current_file.split('.')[0] + '.html' if data_current_file.split('.')[-1] == "md" else data_current_file + '.html').replace("\\", "<span class=\"file-link\"> > </span>")}</p>
            <button popovertarget="table-of-contents" popovertargetaction="toggle"><i data-lucide="table-of-contents"></i></button>
            <div id=\"table-of-contents\" style=\"display: none\" popover><div id=\"toc-content\"></div></div>
        </nav>
        <h1 class="file-title">{title}{'.' + type if type ==  "canvas" or type == "base" else ''}</h1>
        <article data-current-file="{data_current_file}" data-type="{type}"></article>
        <footer>
            <p>Generated with the <a target="_blank" href="https://github.com/Ishancorp/ObsidianMarkdownToHtml">Obsidian Markdown to HTML script</a></p>
            <p>Last updated on {self.get_current_date()}</p>
        </footer>
        <script src="{offset}\\renderer.js"></script>
        <script src="{offset}\\searcher.js"></script>
        {f'<script src="{offset}\\canvas.js"></script>' if type == "canvas" else ''}
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <script>
            MathJax = {{
                tex: {{
                    inlineMath: [['$', '$']],
                    displayMath: [['$$', '$$']]
                }}
            }};
        </script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <script>
            lucide.createIcons();
        </script>
        <script type="module">
            import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";

            mermaid.initialize({{
                startOnLoad: true,
                theme: "default"
            }});

            document.addEventListener("DOMContentLoaded", () => {{
                // Replace only ```mermaid fences
                document.body.innerHTML = document.body.innerHTML.replace(
                    /```mermaid([\\s\\S]*?)```/g,
                    (match, code) => `<pre class="mermaid">${{code.trim()}}</pre>`
                );
                mermaid.run();
            }});
        </script>
        <script>
            document.addEventListener('click', function(e) {{
                const card = e.target.closest('.card[data-href]');
                if (card) {{
                    window.location.href = card.dataset.href;
                }}
            }});
        </script>
    </body>
    </html>"""

    def get_current_date(self):
        """Get current date formatted"""
        from datetime import datetime
        return datetime.now().strftime("%m/%d/%Y")

    def compile_webpages(self):
        """Compile all files (.md, .canvas, .base) to HTML - unified pipeline with client-side processing"""
        for file in self.files:
            offset = self.make_offset(file)
            parts = file.rsplit(".", 1)
            if len(parts) != 2:
                continue

            file_path, extension = parts
            file_name = os.path.basename(file_path)

            relative_path = file[2:] if file.startswith('./') else file
            relative_dir = str(Path(relative_path).parent) if Path(relative_path).parent != Path('.') else ""
            
            if extension == "md":
                output_file_name = self.normalize(self.link_to_filepath.get(file_name, file_name + '.html'))
            elif extension == "canvas":
                output_file_name = self.normalize(self.link_to_filepath.get(file_name, file_name))[:-5] + ".canvas.html"
            elif extension == "base":
                output_file_name = self.normalize(self.link_to_filepath.get(file_name, file_name))[:-5] + ".base.html"
            else:
                self.copy_non_markdown_file(file)
                continue
            
            if relative_dir:
                transformed_dir = "/".join(self.normalize(part) for part in relative_dir.split("/"))
                output_path = Path(self.out_directory) / transformed_dir / output_file_name.split("\\")[-1]
            else:
                output_path = Path(self.out_directory) / output_file_name

            try:
                current_file_identifier = relative_path
                
                html_content = self.build_html_with_raw_markdown(
                    title=file_name,
                    offset=offset,
                    data_current_file=current_file_identifier[2:],
                    type=extension
                )

                self.FileManager.writeToFile(output_path, html_content)

            except Exception as e:
                print(f"Error processing file {file}: {e}")

        print("Compiled")
        self.FileManager.write_files(self.out_directory)

    def copy_non_markdown_file(self, file):
        """Copy non-markdown files to output directory"""
        if file.startswith(".\\") or file.startswith("./"):
            relative_path = file[2:]
        elif file.startswith("."):
            relative_path = file[1:]
        else:
            relative_path = file

        source_file = Path(self.in_directory) / relative_path
        export_file = Path(self.out_directory) / self.normalize(relative_path)

        export_file.parent.mkdir(parents=True, exist_ok=True)

        if source_file.exists():
            shutil.copy(source_file, export_file)
        else:
            print(f"ERROR: Source file not found: {source_file}")

    def normalize(self, s):
        return s.replace(" ", "-").lower()
