import os
import shutil
from pathlib import Path
from python_segments.html_builders.NavigationBuilder import NavigationBuilder
from python_segments.FileManager import FileManager
from python_segments.helpers import *
from python_segments.JSONViewer import JSONViewer
import json
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

        # Initialize navigation builder
        self.navigation_builder = NavigationBuilder(self.link_to_filepath)

        # Initialize JSONViewer with custom renderer
        self.JSONViewer = JSONViewer(
            markdown_processor=None,
            custom_renderer=lambda text, offset: self.process_markdown_for_client_side(text),
            in_directory=self.in_directory,
            out_directory=self.out_directory
        )

        self.image_types = {'png', 'svg', 'jpg', 'jpeg', 'gif', 'webp'}

        # Create file content mapping for client-side access
        self.create_file_content_mapping()

        self.write_renderer()

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
        content = content.replace("{/*file_contents*/}", json.dumps(self.file_content_map))
        content = content.replace("/*in_directory*/0", json.dumps(self.in_directory))
        content = content.replace("/*out_directory*/0", json.dumps(self.out_directory))

        with open(dst_path, "w") as f_out:
            f_out.write(content)

    def create_file_content_mapping(self):
        """Create a mapping of file paths to their content for client-side access"""
        self.file_content_map = {}
        filename_counts = {}  # Track how many times each filename appears
        
        for file_path in self.files:
            if file_path.endswith('.md'):
                # Get the actual file path
                if file_path.startswith('.\\') or file_path.startswith('./'):
                    relative_path = file_path[2:]
                else:
                    relative_path = file_path
                
                full_path = os.path.join(self.in_directory, relative_path.replace('/', os.sep))
                
                # Read file content
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Remove frontmatter
                        if content.startswith('---\n'):
                            end_idx = content.find('\n---\n', 4)
                            if end_idx != -1:
                                content = content[end_idx + 5:]
                        
                        # Get filename components
                        filename_with_ext = os.path.basename(relative_path)
                        filename_without_ext = os.path.splitext(filename_with_ext)[0]
                        
                        # Always store the full relative path (this is unique)
                        self.file_content_map[relative_path] = content
                        self.file_content_map[os.path.splitext(relative_path)[0]] = content
                        
                        # For basename keys, check for conflicts
                        if filename_with_ext not in filename_counts:
                            filename_counts[filename_with_ext] = []
                        filename_counts[filename_with_ext].append((relative_path, content))
                        
                        if filename_without_ext not in filename_counts:
                            filename_counts[filename_without_ext] = []
                        filename_counts[filename_without_ext].append((relative_path, content))
                
                except Exception as e:
                    print(f"Error reading file {full_path}: {e}")
        
        # Now handle basename mappings - only create them if there's no conflict
        for basename, file_list in filename_counts.items():
            if len(file_list) == 1:
                # No conflict - safe to use basename as key
                self.file_content_map[basename] = file_list[0][1]
            else:
                # Conflict detected - don't create basename mapping
                self.file_content_map.pop(basename, None)

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

    def build_html_with_raw_markdown(self, title, offset, content, file_path, headers, is_json=False):
        """Build HTML page with raw markdown that will be processed by marked.js"""
        # Prepare data for client-side processing
        
        json_styles = ""
        json_script = ""
        if is_json:
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
        <h1 class="file-title">{title}{'.CANVAS' if is_json else ''}</h1>
        <{'div' if is_json else f'article data-current-file="{data_current_file}"'}>
            <div id="markdown-content" style="display:none;">{self.escape_html(content)}</div>
            <div id="rendered-content"></div>
        </{'div' if is_json else 'article'}>
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
        <script type="module">
            import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";

            mermaid.initialize({{
                startOnLoad: true,
                theme: "default"
            }});

            document.addEventListener("DOMContentLoaded", () => {{
                // Replace only ```mermaid fences
                document.body.innerHTML = document.body.innerHTML.replace(
                    /```mermaid([\s\S]*?)```/g,
                    (match, code) => `<pre class="mermaid">${{code.trim()}}</pre>`
                );
                mermaid.run();
            }});
        </script>
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
        """Compile all files (.md and .canvas) to HTML - unified pipeline with custom renderer"""
        for file in self.files:
            self.offset = self.calculate_file_depth(file)
            parts = file.rsplit(".", 1)
            if len(parts) != 2:
                continue

            file_path, extension = parts
            file_name = os.path.basename(file_path)

            # Determine output path - preserve directory structure
            relative_path = file[2:] if file.startswith('./') else file  # Remove ./ prefix
            relative_dir = str(Path(relative_path).parent) if Path(relative_path).parent != Path('.') else ""
            
            if extension == "md":
                output_file_name = self.link_to_filepath.get(file_name, file_name + '.html').replace(" ", "-").lower()
            elif extension == "canvas":
                output_file_name = self.link_to_filepath.get(file_name, file_name).replace(" ", "-").lower()[:-5] + ".canvas.html"
            else:
                output_file_name = self.link_to_filepath.get(file_name, file_name).replace(" ", "-").lower()
            
            if relative_dir:
                transformed_dir = "/".join(part.lower().replace(" ", "-") for part in relative_dir.split("/"))
                output_path = Path(self.out_directory) / transformed_dir / output_file_name.split("\\")[-1]
            else:
                output_path = Path(self.out_directory) / output_file_name

            try:
                if extension == "md":
                    # Use the full relative path for data-current-file to avoid conflicts
                    current_file_identifier = relative_path  # This is the full relative path like "folder1/notes.md"

                    # Build HTML
                    html_content = self.build_html_with_raw_markdown(
                        title=file_name,
                        offset=self.offset,
                        content="",
                        file_path=current_file_identifier,  # Pass full path instead of just basename
                        headers=[],
                        is_json=False
                    )

                elif extension == "canvas":
                    # Process canvas JSON via JSONViewer (uses custom renderer)
                    json_content = self.JSONViewer.json_viewer(file, self.offset)
                    current_file_identifier = relative_path

                    # Build HTML
                    html_content = self.build_html_with_raw_markdown(
                        title=file_name,
                        offset=self.offset,
                        content=json_content,  # Already processed HTML
                        file_path=current_file_identifier,
                        headers=[],
                        is_json=True
                    )

                else:
                    # Copy other files (images, etc.)
                    self.copy_non_markdown_file(file)
                    continue

                # Write to output
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
