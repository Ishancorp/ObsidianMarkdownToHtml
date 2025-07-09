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


md = markdown.Markdown(extensions=[])
md.parser.blockprocessors.deregister('code')
md.parser.blockprocessors.register(IndentedParagraphProcessor(md.parser), 'indent_paragraph', 75)


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

    class CustomMarkdownExtension(Extension):
        def __init__(self, link_dict, offset, **kwargs):
            self.link_dict = link_dict
            self.offset = offset
            super().__init__(**kwargs)

        def extendMarkdown(self, md):
            md.parser.blockprocessors.deregister('code')
            md.parser.blockprocessors.register(IndentedParagraphProcessor(md.parser), 'indent_paragraph', 75)
            WIKILINK_RE = r'\[\[([^\]]+)\]\]'
            md.inlinePatterns.register(WikiLinkInlineProcessor(WIKILINK_RE, md, self.link_dict, self.offset), 'wikilink', 175)
    
    def transclude_article(self, mk_link):
        ret_line = make_opening_tag("aside")
        link = (self.link_to_filepath)[mk_link.split("#")[0]]
        file_paths = [k for k,v in (self.link_to_filepath).items() if v == link]
        f_p = "\\" + file_paths[-1] + ".md"
        ret_line += make_opening_tag("div class=\"transclsec\"")
        if "#" in mk_link:
            #section
            transcl_sec = ""
            [gen_link, head_link] = mk_link.split("#")
            link = ((self.link_to_filepath)[gen_link] + "#" + head_link).lower().replace(" ", "-")
                        
            cue_text = mk_link.split("#")[-1].lower().replace(" ", "-")
            examined_lines = self.readlines_raw(self.in_directory+f_p)
            footnotes = []
            if cue_text[0] == '^':
                new_lines = []
                for i in range(len(examined_lines) - 1, -1, -1):
                    if examined_lines[i].split("\n")[0][-7:] == cue_text:
                        new_lines = [self.line_parser(examined_lines[i].split("\n")[0][:-7])]
                        for j in range(i-1,  -1, -1):
                            if examined_lines[j][:2] == "# " or examined_lines[j][:3] == "## " \
                                or examined_lines[j][:4] == "### " or examined_lines[j][:5] == "#### " \
                                or examined_lines[j][:6] == "##### " or examined_lines[j][:7] == "###### "\
                                or examined_lines[j].strip() == "":
                                break
                            new_lines.insert(0, examined_lines[j])
                        break
                    top_part = examined_lines[i].split(' ', 1)[0]
                    if len(top_part) > 4 and top_part[:2] == "[^" and top_part[-2:] == "]:":
                        parsed_line = self.line_parser(examined_lines[i][len(top_part)+1:], in_code=False, canvas=False)
                        footnotes.insert(0, parsed_line)
                transcl_sec += self.read_lines(new_lines, 0, add_to_header_list=False)
            else:
                new_lines = []
                for i in range(0, len(examined_lines)):
                    if examined_lines[i][0] == '#' and head_link in re.sub(self.CLEANR, '', examined_lines[i]).replace("[[","").replace("]]","").replace(":","").replace("*", ""):
                        header_size = len(examined_lines[i].split("# ", 1)[0]) + 1
                        new_lines.append(examined_lines[i])
                        for j in range(i+1, len(examined_lines)):
                            if examined_lines[j][0] == '#' and len(examined_lines[j].split("# ", 1)[0]) > 0 \
                                and len(examined_lines[j].split("# ", 1)[0]) + 1 <= header_size:
                                break
                            new_lines.append(examined_lines[j])
                        break
                    top_part = examined_lines[i].split(' ', 1)[0]
                    if len(top_part) > 4 and top_part[:2] == "[^" and top_part[-2:] == "]:":
                        parsed_line = self.line_parser(examined_lines[i][len(top_part)+1:], in_code=False, canvas=False)
                        footnotes.append(parsed_line)
                transcl_sec += self.read_lines(new_lines, 0, add_to_header_list=False)
            
            fn_index = 1
            for footnote in footnotes:
                transcl_sec = transcl_sec.replace(f"include-fn-[{fn_index}]", footnote)
                fn_index += 1

            ret_line += transcl_sec
        else:
            #entire article
            link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
            ret_line += make_op_close_inline_tag("p", make_op_close_inline_tag("strong", mk_link.split('/')[-1]))
            ret_line += "<br>\n"
            ret_line += self.file_viewer(self.in_directory+f_p, add_to_header_list=False)

        ret_line += make_closing_tag("div")

        ret_line += make_opening_tag("div class=\"transclude-link\"")
        ret_line += make_link(make_offset(self.offset) + link[1:].replace("*",""), ">>", "_self", "goto")
        ret_line += make_closing_tag("div")
        return ret_line
        
    def line_parser(self, line, in_code = False, canvas=False):
        ret_line = ""
        footnote = -1
        skip_beginning = -1
        i = 0

        while i < len(line):
            if i > 1 and line[i] == '[' and line[i-1] == '[' and line[i-2] == '!':
                skip_beginning = i+1
                ret_line = ret_line[:-2]
                j = i+1
                while not (line[j] == ']' and line[j-1] == ']'):
                    j += 1
                mk_link = line[skip_beginning:j-1]
                extension = mk_link.split(".")[-1]
                ret_line = ret_line[:-1]
                if extension == "png" or extension == "svg" or extension == "jpg":
                    link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                    ret_line += "<img src=\"" + make_offset(self.offset) + link[1:] + "\">"
                else:
                    ret_line += self.transclude_article(mk_link)
                ret_line += "<br>\n"
                ret_line += "</aside>\n"
                i = j
            elif line[i-1] == "[" and line[i] == "^":
                footnote = i
                ret_line += line[i]
            elif line[i] == "]" and footnote != -1:
                footnote_num = ret_line[footnote+1:]
                footnote_tag = make_op_close_inline_tag(
                    f"span id=\"fn-{footnote_num}\" class=\"fn fn-{footnote_num}\"", 
                    make_op_close_inline_tag(
                        f"a class=\"fn-link\" href=\"#fn-index-{footnote_num}\"",
                        make_op_close_inline_tag("sup", f"[{footnote_num}]")
                    ) + make_op_close_inline_tag("span class=\"fn-tooltip\"", f"include-fn-[{footnote_num}]")
                )
                ret_line = ret_line[:footnote-1] + footnote_tag
                footnote = -1
            else:
                ret_line += line[i]
            
            i += 1
        ret_line = markdown.markdown(ret_line, extensions=[self.CustomMarkdownExtension(self.link_to_filepath, make_offset(self.offset))])
        return ret_line
    
    def read_lines(self, file_lines, opening, add_to_header_list=True, canvas=False):
        i = opening
        in_section = False
        section_place = -1
        in_code = False
        new_file = ""
        footnotes = []
        while i < len(file_lines):
            if i == len(file_lines)-1 or canvas:
                line_to_put = file_lines[i]
            else:
                line_to_put = file_lines[i][:-1]
            indicer = "p"
            add_tag = False

            if line_to_put.strip() == "" and not (len(line_to_put) > 0 and line_to_put[0] == "	"):
                if in_section:
                    new_file += make_closing_tag("section ")
                    in_section = False
                    section_place = -1
                if in_code:
                    new_file += make_closing_tag("code")
                    new_file += make_closing_tag("pre")
                    in_code = False
                new_file += "<br>\n"
                i += 1
                continue
            elif len(line_to_put) >= 3 and len(line_to_put) == line_to_put.count("-"):
                new_file += "<hr>\n<br>\n"
                i += 1
                continue
            elif not in_code and i >= 1 and line_to_put[0] == "	" and (file_lines[i-1].strip() == "" or file_lines[i-1][0] == "#"):
                new_file += make_opening_tag("pre")
                new_file += make_opening_tag("code")
                in_code = True
                i -= 1
            elif(line_to_put[0] == "|" and line_to_put[-1] == "|"):
                self.in_table = True
                end_point = 0
                temp_string = ""
                skip_ahead = len(file_lines)
                for k in range (i,len(file_lines)):
                    if line_to_put.count("|") > 2 and line_to_put.count("|") != file_lines[k].count("|"):
                        skip_ahead = k
                        break
                    temp_string += make_opening_tag("tr")
                    t_indicer = "td"
                    if i == k:
                        t_indicer = "th"
                    elif i+1 == k:
                        continue
                    table_line = file_lines[k][:-1].split("|")[1:-1]
                    for elem in table_line:
                        processed_elem = self.line_parser(elem.strip(), in_code, canvas)
                        temp_string += "<" + t_indicer + ">" + processed_elem + "</" + t_indicer + ">\n"
                    temp_string += make_closing_tag("tr")
                if skip_ahead < len(file_lines) and len(file_lines[skip_ahead]) > 3 and file_lines[skip_ahead][0] == "^":
                    new_indice = "<span class=\"anchor\" id=\"" + file_lines[skip_ahead][-8:-1] + "\"></span>\n"
                    new_indice += make_opening_tag("table")
                    temp_string = new_indice + temp_string
                    skip_ahead += 1
                else:
                    temp_string = make_opening_tag("table") + temp_string
                self.in_table = False
                temp_string += make_closing_tag("table")
                new_file += temp_string
                i = skip_ahead-1
            else:
                if not in_code and i >= 1 and line_to_put[:3] == "			":
                    indicer = "p class = \"indent-3\""
                elif not in_code and i >= 1 and line_to_put[:2] == "		":
                    indicer = "p class = \"indent-2\""
                elif not in_code and i >= 1 and line_to_put[0] == "	":
                    indicer = "p class = \"indent-1\""
                top_part = line_to_put.split(' ', 1)[0]
                if len(top_part) == top_part.count("#") and len(top_part) > 0:
                    if in_code:
                        new_file += make_closing_tag("code")
                        new_file += make_closing_tag("pre")
                        in_code = False
                    indicer = "h" + str(len(top_part))
                    add_tag = True
                    lines_to_add = line_to_put.split(' ', 1)
                    if len(lines_to_add) > 1:
                        line_to_put = lines_to_add[1]
                    else:
                        line_to_put = lines_to_add[0]
                elif (top_part == "-" or top_part == "*") and len(file_lines[i]) > 2:
                    cur_tabbing = 1
                    new_file += make_opening_tag("ul")
                    while i < len(file_lines):
                        if i == len(file_lines)-1 or canvas:
                            line_to_put = file_lines[i]
                        else:
                            line_to_put = file_lines[i][:-1]

                        tabs = line_to_put.split('- ', 1)[0]
                        tabs_ast = line_to_put.split('* ', 1)[0]
                        if tabs.count("\t") == len(tabs):
                            if (tabs.count("\t")+1) > cur_tabbing:
                                new_file += make_opening_tag("ul")*(tabs.count("\t")+1-cur_tabbing)
                            elif (tabs.count("\t")+1) < cur_tabbing:
                                new_file += make_closing_tag("ul")*(cur_tabbing-tabs.count("\t")-1)
                            cur_tabbing = tabs.count("\t")+1
                            new_file += "<li>"
                            new_file += self.line_parser(line_to_put[2:], in_code, canvas)
                            new_file += make_closing_tag("li")
                        elif tabs_ast.count("\t") == len(tabs_ast):
                            if (tabs_ast.count("\t")+1) > cur_tabbing:
                                new_file += make_opening_tag("ul")*(tabs_ast.count("\t")+1-cur_tabbing)
                            elif (tabs_ast.count("\t")+1) < cur_tabbing:
                                new_file += make_closing_tag("ul")*(cur_tabbing-tabs_ast.count("\t")-1)
                            cur_tabbing = tabs_ast.count("\t")+1
                            new_file += "<li>"
                            new_file += self.line_parser(line_to_put[2:], in_code, canvas)
                            new_file += make_closing_tag("li")
                        else:
                            break
                        i += 1
                    new_file += make_closing_tag("ul")
                    continue
                elif top_part == "1." and len(file_lines[i]) > 2:
                    new_file += make_opening_tag("ol")
                    cur_num = 1
                    while i < len(file_lines):
                        if i == len(file_lines)-1 or canvas:
                            line_to_put = file_lines[i]
                        else:
                            line_to_put = file_lines[i][:-1]
                        cur_prefix = str(cur_num) + ". "
                        if line_to_put[:len(cur_prefix)] == cur_prefix:
                            new_file += "<li>"
                            new_file += self.line_parser(line_to_put[len(cur_prefix):], in_code, canvas)
                            new_file += make_closing_tag("li")
                        else:
                            break
                        cur_num += 1
                        i += 1
                    new_file += make_closing_tag("ol")
                    continue
                elif len(top_part) > 4 and top_part[:2] == "[^" and top_part[-2:] == "]:":
                    footnote_part = top_part[2:-3]
                    parsed_line = self.line_parser(file_lines[i][len(top_part)+1:], in_code, canvas)
                    footnotes.append([footnote_part, parsed_line])
                    i += 1
                    continue

                if indicer == "p" and not in_section:
                    new_file += make_opening_tag("section ")
                    section_place = len(new_file) - 3
                    in_section = True
                elif indicer.split(" ")[0] != "p" and in_section:
                    new_file += make_closing_tag("section ")
                    in_section = False
                    section_place = -1
                    
                if len(line_to_put) > 6 and line_to_put[-7] == "^" and in_section:
                    temp = " id=\"" + line_to_put[-7:] + "\""
                    new_file = new_file[:section_place] + temp + new_file[section_place:]
                    new_file += make_opening_tag(indicer, False)
                    line_to_put = line_to_put[:-7]
                elif len(line_to_put) > 6 and line_to_put[-7] == "^":
                    new_file += "<span class=\"anchor\" id=\"" + line_to_put[-7:] + "\"></span>\n"
                    new_file += make_opening_tag(indicer, False)
                    line_to_put = line_to_put[:-7]
                elif add_tag:
                    id_part = remove_from_id_part(line_to_put)
                    if add_to_header_list:
                        self.header_list.append((re.sub(self.CLEANR, '', line_to_put), "#" + id_part, int(indicer[1])))
                    new_file += "<span class=\"anchor\" id=\"" + id_part + "\"></span>\n"
                    new_file += "<" + indicer + ">"
                else:
                    new_file += make_opening_tag(indicer, False)
                line_to_put = self.line_parser(line_to_put, in_code, canvas)
                new_file += line_to_put + "</" + indicer + ">\n"
                
            i += 1
        
        if len(footnotes) > 0:
            new_file += "<br>\n<hr>\n<br>\n"
            new_file += make_opening_tag("ol class=\"footnotes\"")
            fn_index = 1
            for footnote in footnotes:
                new_file = new_file.replace(f"include-fn-[{fn_index}]", footnote[1])
                new_file += f"<li id=\"fn-index-{fn_index}\">"
                new_file += footnote[1] + " "
                new_file += make_op_close_inline_tag(f"a class=\"fn-link\" href=\"#fn-{fn_index}\"", "⮐")
                new_file += make_closing_tag("li")
                fn_index += 1
            new_file += make_closing_tag("ol")

        return new_file
    
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

