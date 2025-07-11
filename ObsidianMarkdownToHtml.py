import os
import shutil
import datetime
import json
import re
import markdown
from MarkdownProcessor import *
from markdown.extensions import Extension

CLEANR = re.compile('<.*?>') 
external_link = ""
with open("svg/other_extern.html", encoding='utf-8') as other_pages: external_link = " " + other_pages.read()

def make_opening_tag(indicer, newline_end = True):
    return "<" + indicer + ">" + (newline_end * "\n")

def make_closing_tag(indicer):
    return "</" + indicer + ">\n"

def make_op_close_inline_tag(indicer, inner):
    return "<" + indicer + ">" + inner + "</" + indicer + ">\n"
    
def remove_from_id_part(id):
    return re.sub(CLEANR, '', id).lower().replace("[[","").replace("]]","").replace(" ", "-").replace("*", "").replace(":","")

def make_offset(offset):
    if offset == 0:
        return '.'
    elif offset == 1:
        return '..'
    else:
        return ((offset-1) * "../") + ".."

def make_link(link, text, target="_self", className="", extern=False):
    ret_str = "<a class=\"" + className + "\" href=\"" + link +"\" target=\""+ target +"\">" + text + "</a>"
    if extern:
        ret_str += " " + external_link
    return ret_str

def fix_table_spacing(markdown_text):
    table_pattern = re.compile(r'''
        (?:(?<=\n)|\A)               # Start of string or after a newline
        (?P<table>                   # Named group for the full table
            (?:\|.*\|\n)            # Header row
            (?:\|[-:| ]+\|\n)       # Divider row
            (?:\|.*\|\n?)*          # Optional body rows
        )
        (?P<tag_line>               # Named group for an optional tag line
            \^([a-zA-Z0-9]{6})[ \t]*\n  # Line with ^ + 6 alphanumeric characters
        )?
    ''', re.VERBOSE)

    def replacement(match):
        table = match.group('table').rstrip()
        tag_line = match.group('tag_line')
        if tag_line:
            tag = tag_line.strip()
            return f"\n{table}\n{tag} \n\n"
        else:
            return f"\n{table}\n\n"

    result = table_pattern.sub(replacement, markdown_text)
    return result

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        self.in_directory = in_directory
        self.out_directory = out_directory
        self.link_to_filepath = {}
        self.files = []
        self.offset = 0
        self.cached_pages = {}
        self.header_list = []
        self.in_table = False
        self.CLEANR = re.compile('<.*?>') 
        
        self.add_dirs_to_dict("")
        self.nuwa_file = ""

        with open("styles/omth.css") as stylesheet: self.stylesheet = stylesheet.read()
        with open("scripts/json_canvas.js") as script: self.script = script.read()
        with open("svg/canvas_bar.html", encoding='utf-8') as canv_bar: self.canvas_bar = " " + canv_bar.read()
        with open("svg/other_pages.html", encoding='utf-8') as other_pages: self.other_pages = other_pages.read()
        with open("svg/other_headers.html", encoding='utf-8') as other_headers: self.other_headers = other_headers.read()
        with open("styles/json_canvas.css") as json_stylesheet: self.json_stylesheet = json_stylesheet.read()

    def get_block_reference_content(self, page_name, block_ref):
        """Extract content for a block reference"""
        if page_name not in self.link_to_filepath:
            return None
            
        link = self.link_to_filepath[page_name]
        file_paths = [k for k, v in self.link_to_filepath.items() if v == link]
        if not file_paths:
            return None
            
        f_p = "\\" + file_paths[-1] + ".md"
        cue_text = block_ref.lower().replace(" ", "-")
        
        try:
            examined_lines = self.readlines_raw(self.in_directory + f_p)
            
            if cue_text[0] == '^':
                # Find the line with the block reference
                for i in range(len(examined_lines) - 1, -1, -1):
                    if examined_lines[i].strip().endswith(cue_text):
                        # Found the line with block reference
                        content_lines = []
                        
                        # Get the content of this line (without the block reference)
                        line_content = examined_lines[i].strip()
                        if line_content.endswith(cue_text):
                            line_content = line_content[:-len(cue_text)].strip()
                        
                        content_lines.append(line_content)
                        
                        # Check if this is part of a table
                        if '|' in line_content:
                            # This might be a table row, collect the entire table
                            table_lines = [line_content]
                            
                            # Go backwards to find table start
                            j = i - 1
                            while j >= 0:
                                prev_line = examined_lines[j].strip()
                                if '|' in prev_line or re.match(r'^\s*\|?\s*[-:]+\s*(\|\s*[-:]+\s*)*\|?\s*$', prev_line):
                                    table_lines.insert(0, prev_line)
                                    j -= 1
                                elif prev_line == "":
                                    j -= 1
                                    continue
                                else:
                                    break
                            
                            # Go forwards to find table end
                            j = i + 1
                            empty_line_count = 0
                            while j < len(examined_lines):
                                next_line = examined_lines[j].strip()
                                if '|' in next_line or re.match(r'^\s*\|?\s*[-:]+\s*(\|\s*[-:]+\s*)*\|?\s*$', next_line):
                                    # Reset empty line count when we find table content
                                    empty_line_count = 0
                                    table_lines.append(next_line)
                                    j += 1
                                elif next_line == "":
                                    empty_line_count += 1
                                    # Allow up to 1 empty line within a table, but stop after that
                                    if empty_line_count <= 1:
                                        j += 1
                                        continue
                                    else:
                                        break
                                else:
                                    # Non-table content found, stop here
                                    break
                            
                            return '\n'.join(table_lines)
                        else:
                            # Regular paragraph, collect related lines
                            for j in range(i - 1, -1, -1):
                                prev_line = examined_lines[j].strip()
                                if (prev_line.startswith('#') or 
                                    prev_line == "" or 
                                    prev_line.startswith('- ') or
                                    prev_line.startswith('* ') or
                                    prev_line.startswith('+ ') or
                                    re.match(r'^\d+\.\s', prev_line)):
                                    break
                                content_lines.insert(0, prev_line)
                            
                            return '\n'.join(content_lines)
                        
                        break
        except (IOError, IndexError):
            return None
        
        return None

    class CustomMarkdownExtension(Extension):
        def __init__(self, link_dict, offset, parent_instance, **kwargs):
            self.link_dict = link_dict
            self.offset = offset
            self.parent_instance = parent_instance
            super().__init__(**kwargs)

        def extendMarkdown(self, md):
            md.parser.blockprocessors.deregister('code')
            md.treeprocessors.register(AnchorSpanTreeProcessor(md), 'anchor_span', 15)
            md.treeprocessors.register(BlockReferenceProcessor(md), 'block_reference', 12)  # Add this line
            md.parser.blockprocessors.register(IndentedParagraphProcessor(md.parser), 'indent_paragraph', 75)
            
            # Regular wiki links
            WIKILINK_RE = r'\[\[([^\]]+)\]\]'
            md.inlinePatterns.register(WikiLinkInlineProcessor(WIKILINK_RE, md, self.link_dict, self.offset), 'wikilink', 175)
            
            # Transclusion links - register with higher priority than wiki links
            TRANSCLUSION_RE = r'!\[\[([^\]]+)\]\]'
            md.inlinePatterns.register(TransclusionInlineProcessor(TRANSCLUSION_RE, md, self.parent_instance), 'transclusion', 180)
    
    def make_offset(self, offset):
        return make_offset(offset)
    
    def process_markdown(self, text):
        # Create markdown instance with all extensions
        extensions = [
            self.CustomMarkdownExtension(self.link_to_filepath, make_offset(self.offset), self),
            ObsidianFootnoteExtension(),
            "sane_lists",
            "tables", 
            "nl2br"
        ]
        text = fix_table_spacing(text)
        processed_html = markdown.markdown(text, extensions=extensions)
        
        # Add newlines between adjacent paragraph tags
        processed_html = re.sub(r'</p>\s*<p', '</p>\n<br>\n<p', processed_html)
        
        return processed_html
    
    def read_lines(self, file_lines, opening, add_to_header_list=True, canvas=False):
        """Process lines while preserving line breaks"""
        processed_content = self.process_markdown("".join(file_lines[opening:]))
        
        return processed_content
    
    def readlines_raw(self, file_dir):
        open_file = open(file_dir, "r", encoding="utf8")
        file_lines = open_file.readlines()
        open_file.close()
        return file_lines

    def file_viewer(self, file_dir, add_to_header_list=True):
        if file_dir.replace("/","\\") in (self.cached_pages).keys():
            return (self.cached_pages)[file_dir.replace("/","\\")]
        
        file_lines = self.readlines_raw(file_dir)
        
        opening = 0
        if file_lines and file_lines[0] == "---\n":
            for i in range(1, len(file_lines)):
                if file_lines[i] == "---\n":
                    opening = i+1
                    break
        
        new_file = self.read_lines(file_lines, opening, add_to_header_list=add_to_header_list)
        (self.cached_pages)[file_dir] = new_file
        return new_file

    def nav_bar(self):
        checkbox_prefix = 1
        
        ret_str = make_opening_tag("nav")
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"toggle\">\n"
        ret_str += self.other_pages
        ret_str += "</button>"
        ret_str += "<div id=\"navbar\" popover><div id=\"idk\">"
        ret_str += make_opening_tag("ul class=\"menu\"")
        
        file_tuples = sorted(self.link_to_filepath.items(), key=lambda x: x[1].rsplit("\\", 1))
        
        for i in range(0, len(file_tuples)):
            if i == 0 or (i > 0 and file_tuples[i-1][1] != file_tuples[i][1]):
                link = make_offset(self.offset)+file_tuples[i][1][1:]
                if file_tuples[i][1].rsplit("\\", 1)[0] != file_tuples[i-1][1].rsplit("\\", 1)[0]:
                    # delete pre each slash till slashes are different
                    fileprev = file_tuples[i-1][1].rsplit("\\", 1)[0] + "\\"
                    filecur = file_tuples[i][1].rsplit("\\", 1)[0] + "\\"
                    
                    while fileprev != "" and filecur != "":
                        if fileprev.split("\\",1)[0]  != filecur.split("\\",1)[0]:
                            break
                        fileprev = fileprev.split("\\",1)[-1]
                        filecur = filecur.split("\\",1)[-1]
                    # add close uls corresp to slashes of i-1
                    if(i != 0):
                        if(fileprev != "." and fileprev != ""):
                            ret_str += (fileprev.count("\\"))*(make_closing_tag("ul")+make_closing_tag("li"))
                            
                        # add folders, open uls corresp to slashes of i
                        if(filecur != "."):
                            filecur_elems = filecur.split("\\")
                            for j in range(0, len(filecur_elems)-1):
                                ret_str += "<li class=\"parent\">\n"
                                checkbox_tag = str(checkbox_prefix) + "-" + filecur_elems[j].replace(" ", "-")
                                checkbox_prefix += 1
                                ret_str += "<input type=\"checkbox\" id=" + checkbox_tag + " name=" + checkbox_tag + ">\n"
                                ret_str += "<label id=\"checkbox\" for=" + checkbox_tag + ">" + filecur_elems[j].title() + "</label>\n"
                                ret_str += "<ul class=\"child\">\n"
                #remove indexed
                ret_str += "<li>" + make_link(link.replace(" ", "-").lower(), file_tuples[i][0].split("/")[-1]) + make_closing_tag("li")
        ret_str += make_closing_tag("ul") + 3*"</br>\n" + "</div>" + make_closing_tag("div")

        ret_str += make_op_close_inline_tag("p class=\"top-bar\"", self.nuwa_file.replace("\\", "<span class=\"file-link\"> > </span>"))

        ret_str += "<button popovertarget=\"table-of-contents\" popovertargetaction=\"toggle\">"
        ret_str += self.other_headers
        ret_str += "</button>"
        ret_str += "<div id=\"table-of-contents\" popover><div id=\"idk\">"
        
        for header in (self.header_list):
            ret_str += make_op_close_inline_tag("p class=\"indent-"+str(header[2]-1)+"\"", make_link(header[1], header[0]).replace("[[","").replace("]]",""))
        self.header_list = []
        ret_str += 3*"<br/>\n"
        ret_str += make_closing_tag("div")
        ret_str += make_closing_tag("div")
        ret_str += make_closing_tag("nav")
        return ret_str
        
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

    def footer(self):
        ret_str = make_opening_tag("footer")
        ret_str += make_op_close_inline_tag("p", "Generated with the <a target=\"_blank\" href=\"https://github.com/Ishancorp/ObsidianMarkdownToHtml\">Obsidian Markdown to HTML script</a>")
        ret_str += make_op_close_inline_tag("p", "Last updated on " + datetime.datetime.now().strftime("%m/%d/%Y"))
        ret_str += make_closing_tag("footer")
        return ret_str

    def add_dirs_to_dict(self, path):
        nu_dir = self.in_directory + "\\" + path
        files_and_dirs = os.listdir(nu_dir)
        sep_files = [f for f in files_and_dirs if (os.path.isfile(nu_dir+'/'+f) and f[0] != '~')]
        dirs = [f for f in files_and_dirs if (os.path.isdir(nu_dir+'/'+f) and f[0] != '.' and f[0] != '~')]
        
        self.add_files_to_dict(sep_files, path)
        for file in sep_files:
            temp = ".\\" + path + "\\"
            (self.files).append(temp.replace("\\\\", "\\") + file)

        for dir in dirs:
            nu_dr = path + "\\" + dir
            self.add_dirs_to_dict(nu_dr)
        
    def read_json(self, file_name):
        with open(file_name, encoding='utf-8') as json_data:
            return json.load(json_data)
    
    def json_viewer(self, data):
        nodes_by_id = {}
        max_x = 0
        max_y = 0
        div_part = ""
        arrow_part = ""
        for node in data["nodes"]:
            div_part += f"<div class=\"general-boxes"
            if "color" in node:
                div_part += f" color-{node["color"]}"
            div_part += f"\" id=\"{node["id"]}\" style=\"left:{str(node["x"]+750)}px;top:{str(node["y"]+400)}px;width:{str(node["width"])}px;height:{str(node["height"])}px\">\n"
            read_lines = node["text"].splitlines()
            div_part += self.read_lines(read_lines, 0, add_to_header_list=False, canvas=True)
            nodes_by_id[node["id"]] = {
                "left": (node["x"], node["y"]+(node["height"]/2)),
                "right": (node["x"]+node["width"], node["y"]+(node["height"]/2)),
                "top": (node["x"]+(node["width"]/2), node["y"]),
                "bottom": (node["x"]+(node["width"]/2), node["y"]+node["height"]),
            }
            max_x = max(max_x, node["x"])
            max_y = max(max_y, node["y"])
            div_part += "\n</div>\n"
        svg_part = f"<svg id=\"svg\" width=\"{max_x+1000}\" height=\"{max_y+1000}\">\n"
        for edge in data["edges"]:
            node_from = nodes_by_id[edge["fromNode"]]
            node_to = nodes_by_id[edge["toNode"]]
            svg_part += f"<line class=\"line\" x1=\"{node_from[edge["fromSide"]][0]+750}\" y1=\"{node_from[edge["fromSide"]][1]+400}\" x2=\"{node_to[edge["toSide"]][0]+750}\" y2=\"{node_to[edge["toSide"]][1]+400}\"/>\n"
            arrow_side = edge["toSide"]
            if arrow_side == "left":
                arrow_part += f"<i class=\"arrow {arrow_side}\" style=\"left:{node_to[arrow_side][0]+740}px;top:{node_to[arrow_side][1]+395}px;\"></i>\n"
            else:
                arrow_part += f"<i class=\"arrow {arrow_side}\" style=\"left:{node_to[arrow_side][0]+745}px;top:{node_to[arrow_side][1]+390}px;\"></i>\n"
        svg_part += "</svg>\n"
        return "<div id=\"outer-box\">\n" + "<div id=\"scrollable-box\">\n" + "<div id=\"innard\">" + arrow_part + svg_part + div_part + (2 * "</div>\n") + self.canvas_bar + "</div>\n"

    def writeToFile(self, file_name, new_file):
        export_file = self.out_directory + self.link_to_filepath[file_name.replace('\\', '/')].replace(" ", "-")
        os.makedirs(os.path.dirname(export_file), exist_ok=True)
        
        exp_file = open(export_file, "w", encoding="utf-8")
        exp_file.write(new_file)
        exp_file.close()

    def top_part(self, file_name):
        new_file = make_opening_tag("html")
        new_file += make_opening_tag("head")
        new_file += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        new_file += make_op_close_inline_tag("title", file_name)
        new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/\">\n"
        new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/inter/inter.css\">\n"
        new_file += "<link rel=\"stylesheet\" href=\""+ make_offset(self.offset) + "\\style.css\">\n"
        return new_file
        
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [__, file_name, extension] = file.split(".")
            file_dir = self.in_directory + file[1:]
            if extension == "md":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.top_part(file_name)
                new_file += make_closing_tag("head")
                new_file += make_opening_tag("body")

                viewed_file = self.file_viewer(file_dir)

                self.nuwa_file = file[2:-3]
                new_file += self.nav_bar()
                
                new_file += make_op_close_inline_tag("h1 class=\"file-title\"", file_name)
                new_file += make_opening_tag("article")

                new_file += viewed_file
                
                new_file += make_closing_tag("article")
                
                new_file += self.footer()
                new_file += make_closing_tag("body")
                new_file += make_closing_tag("html")
                    
                self.writeToFile(full_file_name, new_file)
                # break
            elif extension == "canvas":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.top_part(file_name)

                new_file += make_opening_tag("style")
                new_file += self.json_stylesheet
                new_file += make_closing_tag("style")

                new_file += make_closing_tag("head")
                new_file += make_opening_tag("body")

                self.nuwa_file = file[2:] + ".html"
                new_file += self.nav_bar()
                
                new_file += make_op_close_inline_tag("h1 class=\"file-title\"", file_name + ".CANVAS")

                canvas_dict = self.read_json(file_dir)
                new_file += self.json_viewer(canvas_dict)
                
                new_file += self.footer()
                new_file += "<script src=\""+ make_offset(self.offset) + "\\canvas.js\"></script>\n"
                new_file += make_closing_tag("body")
                new_file += make_closing_tag("html")
                    
                self.writeToFile(full_file_name + ".canvas", new_file)
            else:
                # write file as-is
                export_file = self.out_directory + file.split(".", 1)[1].replace(" ", "-").lower()
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        
        with open((self.out_directory) + "\\style.css", "w") as text_file:
            text_file.write(self.stylesheet)
        
        with open((self.out_directory) + "\\canvas.js", "w") as text_file:
            text_file.write(self.script)
