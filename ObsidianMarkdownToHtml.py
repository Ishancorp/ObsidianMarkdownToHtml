import os
import shutil
from pathlib import Path
import uuid
from python_segments.html_builders.NavigationBuilder import NavigationBuilder
from python_segments.FileManager import FileManager
from python_segments.helpers import *
import json
import yaml
import re

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        if not os.path.exists(in_directory):
            raise ValueError(f"Input directory does not exist: {in_directory}")

        self.in_directory = os.path.abspath(in_directory)
        self.out_directory = os.path.abspath(out_directory)
        self.offset = 0
        self.header_list = []

        # Initialize FileManager and gather files
        self.FileManager = FileManager(self.in_directory, self.out_directory)
        self.files, self.link_to_filepath = self.FileManager.add_dirs_to_dict()

        # Create file content mapping for client-side access
        self.create_file_content_mapping()

        self.write_renderer()

        # Initialize navigation builder
        self.navigation_builder = NavigationBuilder(self.link_to_filepath)

        self.image_types = {'png', 'svg', 'jpg', 'jpeg', 'gif', 'webp'}

    def extract_headers_from_markdown(self, content):
        """Extract headers for navigation"""
        headers = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                if level <= 6:
                    header_text = line[level:].strip()
                    header_id = self.slugify(header_text)
                    headers.append([header_text, header_id, level])
        return headers
    
    def write_renderer(self):
        src_path = (Path(__file__).resolve().parent / "scripts/renderer.js").resolve()
        dst_path = Path(self.out_directory) / 'renderer.js'
        with open(src_path, "r") as f_in:
            content = f_in.read()

        # Replace placeholders
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
        filename_counts = {}  # Track how many times each filename appears
        
        for file_path in self.files:
            unique_id = str(uuid.uuid4())
            self.file_properties[unique_id] = {}
            self.file_properties[unique_id]["path"] = file_path[2:]
            self.file_properties[unique_id]["file"] = file_path.split('\\')[-1]
            self.file_properties[unique_id]["folder"] = file_path[2:].rsplit('\\', 1)[0]
            self.file_properties[unique_id]["ext"] = file_path.split('.')[-1]
            # Get the actual file path
            if file_path.startswith('.\\') or file_path.startswith('./'):
                    relative_path = file_path[2:]
            else:
                relative_path = file_path
            
            # Always store the full relative path (this is unique)
            self.file_content_map[relative_path] = unique_id
            self.file_content_map[os.path.splitext(relative_path)[0]] = unique_id

            # Get filename components
            filename_with_ext = os.path.basename(relative_path)
            filename_without_ext = os.path.splitext(filename_with_ext)[0]
            
            # For basename keys, track all occurrences
            if filename_with_ext not in filename_counts:
                filename_counts[filename_with_ext] = []
            filename_counts[filename_with_ext].append((relative_path, unique_id))
            
            if filename_without_ext not in filename_counts:
                filename_counts[filename_without_ext] = []
            filename_counts[filename_without_ext].append((relative_path, unique_id))

            full_path = os.path.join(self.in_directory, relative_path.replace('/', os.sep))
            if file_path.endswith('.base'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()
                        parsed_yaml = yaml.load(yaml_content, Loader=yaml.FullLoader)
                        # Store both raw and parsed content
                        self.file_contents[unique_id] = json.dumps(parsed_yaml)  # Store as JSON string
                except Exception as e:
                    print(f"Error parsing YAML file {full_path}: {e}")
                    self.file_contents[unique_id] = "{}"  # Fallback empty object
            elif file_path.endswith(('.md', '.canvas')):
                
                # Read file content
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
        
        # Handle basename mappings - for conflicts, map to the first occurrence
        # but ensure ALL files remain accessible via their full paths
        for basename, file_list in filename_counts.items():
            if len(file_list) == 1:
                # No conflict - safe to use basename as key
                self.file_content_map[basename] = file_list[0][1]
            else:
                # Conflict detected - map basename to first occurrence
                # This preserves backward compatibility while ensuring access
                self.file_content_map[basename] = file_list[0][1]
                
                # Optionally, you could add a warning or logging here
                print(f"Warning: Multiple files with basename '{basename}' found. Using: {file_list[0][0]}")
                print(f"  Conflicting files: {[item[0] for item in file_list]}")
                print(f"  Access non-primary files using their full relative paths.")

    def slugify(self, text):
        """Convert text to URL-friendly slug"""
        if not text:
            return ""
        text = text.strip().lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'\s+', '-', text)
        return text

    def calculate_file_depth(self, file_path):
        """Calculate the correct depth/offset for a file"""
        if file_path.startswith('.\\') or file_path.startswith('./'):
            clean_path = file_path[2:]
        else:
            clean_path = file_path
        
        depth = clean_path.count('/') + clean_path.count('\\')
        return depth

    def process_markdown_for_client_side(self, content):
        """Basic markdown preprocessing - transclusions will be handled client-side"""
        # Handle frontmatter
        if content.startswith('---\n'):
            end_idx = content.find('\n---\n', 4)
            if end_idx != -1:
                content = content[end_idx + 5:]
        
        return content.strip()

    def build_html_with_raw_markdown(self, title, offset, content, file_path, headers, type="md"):
        """Build HTML page with raw markdown that will be processed by marked.js"""
        # Prepare data for client-side processing
        
        json_styles = ""
        json_script = ""
        if type == "canvas":
            try:
                with open("styles/json_canvas.css") as json_stylesheet:
                    json_styles = f"<style>{json_stylesheet.read()}</style>"
                json_script = f'<script src="{make_offset(offset)}\\canvas.js"></script>'
            except:
                pass

        # Use the full file_path for data-current-file attribute
        # This ensures each file has a unique identifier even if filenames are duplicated
        data_current_file = file_path[2:]

        html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="preconnect" href="https://rsms.me/">
        <link rel="preconnect" href="https://rsms.me/inter/inter.css">
        <link rel="stylesheet" href="{make_offset(offset)}\\style.css">
        {json_styles}
        <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.3.0/marked.min.js"></script>
    </head>
    <body>
        {self.navigation_builder.generate_navigation_bar(offset, file_path[2:])}
        <h1 class="file-title">{title}{'.' + type if type ==  "canvas" or type == "base" else ''}</h1>
        <article data-current-file="{data_current_file}">
            <div id="markdown-content" style="display:none;">{self.escape_html(content)}</div>
            <div id="rendered-content"></div>
        </article>
        <footer>
            <p>Generated with the <a target="_blank" href="https://github.com/Ishancorp/ObsidianMarkdownToHtml">Obsidian Markdown to HTML script</a></p>
            <p>Last updated on {self.get_current_date()}</p>
        </footer>
        <script src="{make_offset(offset)}\\renderer.js"></script>
        <script src="{make_offset(offset)}\\searcher.js"></script>
        {json_script}
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
        </script
    </body>
    </html>"""
        return html

    def escape_html(self, text):
        """Escape HTML special characters in markdown content"""
        return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))

    def get_current_date(self):
        """Get current date formatted"""
        from datetime import datetime
        return datetime.now().strftime("%m/%d/%Y")

    def compile_webpages(self):
        """Compile all files (.md, .canvas, .base) to HTML - unified pipeline with client-side processing"""
        for file in self.files:
            self.offset = self.calculate_file_depth(file)
            parts = file.rsplit(".", 1)
            if len(parts) != 2:
                continue

            file_path, extension = parts
            file_name = os.path.basename(file_path)

            # Determine output path
            relative_path = file[2:] if file.startswith('./') else file
            relative_dir = str(Path(relative_path).parent) if Path(relative_path).parent != Path('.') else ""
            
            if extension == "md":
                output_file_name = self.link_to_filepath.get(file_name, file_name + '.html').replace(" ", "-").lower()
            elif extension == "canvas":
                output_file_name = self.link_to_filepath.get(file_name, file_name).replace(" ", "-").lower()[:-5] + ".canvas.html"
            elif extension == "base":
                output_file_name = self.link_to_filepath.get(file_name, file_name).replace(" ", "-").lower() + ".base.html"
            else:
                # Copy non-processed files
                self.copy_non_markdown_file(file)
                continue
            
            if relative_dir:
                transformed_dir = "/".join(part.lower().replace(" ", "-") for part in relative_dir.split("/"))
                output_path = Path(self.out_directory) / transformed_dir / output_file_name.split("\\")[-1]
            else:
                output_path = Path(self.out_directory) / output_file_name

            try:
                current_file_identifier = relative_path
                
                # All types use the same HTML structure - processing happens client-side
                html_content = self.build_html_with_raw_markdown(
                    title=file_name,
                    offset=self.offset,
                    content="",  # Empty - content comes from fileContents
                    file_path=current_file_identifier,
                    headers=[],
                    type=extension  # Pass the extension as type
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
        export_file = Path(self.out_directory) / relative_path.replace(" ", "-")

        export_file.parent.mkdir(parents=True, exist_ok=True)

        if source_file.exists():
            shutil.copy(source_file, export_file)
        else:
            print(f"ERROR: Source file not found: {source_file}")
