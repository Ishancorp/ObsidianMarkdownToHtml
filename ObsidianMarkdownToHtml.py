import os
import shutil
import datetime
from pathlib import Path

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
        
        self.add_dirs_to_dict("")
        self.nuwa_file = ""

        self.stylesheet = """
:root {
  font-family: -apple-system, BlinkMacSystemFont, 
    "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", 
    "Fira Sans", "Droid Sans", "Helvetica Neue", 
    sans-serif;
  font-feature-settings: 'liga' 1, 'calt' 1; /* fix for Chrome */
}
body {
  background-color: #1E1E1E;
  color: #DADADA;
}
@supports (font-variation-settings: normal) {
  h1 { font-family: InterVariable, sans-serif; }
  h2 { font-family: InterVariable, sans-serif; }
  h3 { font-family: InterVariable, sans-serif; }
  h4 { font-family: InterVariable, sans-serif; }
  h5 { font-family: InterVariable, sans-serif; }
}
a {
  text-decoration: underline;
  color: #6086ED;
}
a:visited {
  text-decoration: underline;
  color: #6086ED;
}
a:hover {
  text-decoration: underline;
  color: #87B6F6;
}
a.goto {
  border-radius: 2px;
  padding: 0.25em;
  text-decoration: none;
  color: #1E1E1E;
  background-color: #6086ed;
}
a.goto:hover {
  border: 1px solid #6086ed;
  background-color: #1e1e1e;
  color: #6086ed;
}
pre {
  background-color: #242424;
}
img {
  max-width: 100%;
  object-fit: cover;
}
p {
  margin: 0;
  padding: 0;
}
p.indent-1 {
  margin-left: 0.5em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.indent-2 {
  margin-left: 1em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.indent-3 {
  margin-left: 1.5em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.indent-4 {
  margin-left: 2em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.indent-5 {
  margin-left: 2.5em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.indent-6 {
  margin-left: 3em;
  padding-left: 0.5em;
  border-left: 1px solid #393939;
}
p.top-bar {
  margin-left: 2.75em;
}
span.file-link {
  color: #393939;
}
aside {
  padding-left: 1em;
  border-left: 0.1em solid #6086ED;
}

h1 {
  font-family: Inter, sans-serif;
  font-size: 2rem;
  font-weight: 700;
}
h2 {
  font-family: Inter, sans-serif;
  font-size: 1.6rem;
  font-weight: 600;
}
h3 {
  font-family: Inter, sans-serif;
  font-size: 1.37rem;
  font-weight: 600;
}
h4 {
  font-family: Inter, sans-serif;
  font-size: 1.25rem;
  font-weight: 600;
}
h5 {
  font-family: Inter, sans-serif;
  font-size: 1.12rem;
  font-weight: 600;
}
h6 {
  font-size: 1rem;
  margin-top: 1rem;
  margin-bottom: 1rem;
  font-weight: 600;
}

h1.file-title {
  text-align: center;
}

hr {
  margin-bottom: 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #363636;
}
td, th {
  text-align: left;
  border: 1px solid #363636;
  padding: 0.4em;
}

article {
  max-width: 700px;
  margin: auto;
  padding-left: 0.5em;
  padding-right: 0.5em;
}

nav {
  background-color: #1E1E1E;
  padding-top: 0.5em;
}

nav li {
  list-style-type: none;
  padding: 0;
  margin-left: 0.75rem;
  width: 100%
}

li ul {
  margin: 0;
  padding-left: 0.5rem;
  border-left: 1px solid #393939;
  margin-left: 0.3em;
}

div#navbar {
  border: 0;
  padding: 2ch;
  background-color: #242424;
  color: #DADADA;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  border-radius: 1ch;
  max-width: 50vw;
  max-height: 100vh;
  margin: 0 auto;
  left: 0;
  right: auto;
  overflow-x: hidden;
}

div#table-of-contents {
  border: 0;
  padding: 2ch;
  background-color: #242424;
  color: #DADADA;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  border-radius: 1ch;
  max-width: 50vw;
  max-height: 100vh;
  margin: 2.5em 0;
  left: auto;
  right: 0;
}

div.transclude-link {
  text-align: right;
  margin-top: 0.5em;
  margin-bottom: 0.5em;

}

#navbar:popover-open {
  animation: fadeIn 150ms ease-in-out;
}

div#navbar::backdrop {
  background-color: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(6px);
}

button {
  background-color: #6086ED;
  border: none;
}

button:hover {
  background-color: #87B6F6;
}

svg#navicon {
  height: 2em;
  width: 2em;
}

svg#tocicon {
  height: 2em;
  width: 2em;
}

nav {
  position: -webkit-sticky; /* Safari */
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
}

span.anchor {
  height: 30px;
  margin-top: -30px;
  position: absolute;
}

input[type='checkbox']:not(:checked) + label + ul {
    display: none;
    visibility:hidden;
}

input[type="checkbox"] {
  appearance: none;
  transform-origin: center;
  margin: 0;
  font: inherit;
  width: 1.15em;
  height: 1.15em;
  border: 0;
  border-radius: 0.15em;
  color: #363636;
  bottom: 0.1em;
  position: relative;
}

input[type="checkbox"]::before {
  content: ">";
}

input[type="checkbox"]:checked {
  transform: rotate(90deg);
  bottom: auto;
  top: 0.4em;
}

footer {
  background-color: #242424;
  color: #484848;
  font-size: 1em;
  border-top: 1px solid #6086ED;
  margin-top: 1em;
  margin-left: 1em;
  margin-right: 1em;
  padding-top: 1em;
  padding-bottom: 1em;
}

@media screen and (max-width: 768px) {
  svg#tocicon {
    height: 2rem;
    width: 2rem;
  }
  svg#navicon {
    height: 2rem;
    width: 2rem;
  }
  div#navbar {
    max-width: 100vw;
    max-height: 90vh;
    margin: 0 auto;
    top: 10vh;
  }
  div#table-of-contents {
    max-width: 100vw;
    max-height: 90vh;
    margin: 0 auto;
    top: 10vh;
  }

  article {
    width: 90%;
    margin: auto;
    padding-left: 0.25em;
    padding-right: 0.25em;
  }

  footer {
    margin-top: 4em;
  }
}

"""

    def make_link(self, link, text, target="_self", className=""):
        return "<a class=\"" + className + "\" href=\"" + link +"\" target=\""+ target +"\">" + text + "</a>"

    def make_offset(self):
        if self.offset == 0:
            return '.'
        elif self.offset == 1:
            return '..'
        else:
            return ((self.offset-1) * "../") + ".."

    def make_opening_tag(self, indicer, newline_end = True):
        return "<" + indicer + ">" + (newline_end * "\n")

    def make_closing_tag(self, indicer):
        return "</" + indicer + ">\n"

    def make_op_close_inline_tag(self, indicer, inner):
        return "<" + indicer + ">" + inner + "</" + indicer + ">\n"
        
    def line_parser(self, line, in_code = False):
        ret_line = ""
        in_link = False
        transclusion = False
        in_bold = False
        in_italics = False
        skip_beginning = -1
        extern_links = [-1, -1,-1]
        for i in range(0, len(line)):
            if i > 0 and line[i] == '*' and line[i-1] == '\\':
                ret_line = ret_line[:-1] + "*"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and line[i-2] == '*' and in_bold and not in_link and not transclusion and not in_code:
                in_italics = True
                ret_line = ret_line[:-8]
                ret_line += "<strong><em>"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and line[i-2] == '*' and not in_link and not transclusion and not in_code and self.in_table:
                ret_line = ret_line[:-10]
                ret_line += "<strong>"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and line[i-2] == '*' and not in_link and not transclusion and not in_code:
                ret_line = ret_line[:-10]
                ret_line += "</em></strong>"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and not in_bold and not in_link and not transclusion and not in_code and self.in_table:
                in_bold = not in_bold
                in_italics = False
                ret_line = ret_line[:-5]
                ret_line += "</strong>"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and not in_bold and not in_link and not transclusion and not in_code:
                in_bold = not in_bold
                in_italics = False
                ret_line = ret_line[:-4]
                ret_line += "<strong>"
            elif i > 0 and line[i] == '*' and line[i-1] == '*' and in_bold and not in_link and not transclusion and not in_code:
                in_bold = not in_bold
                in_italics = False
                ret_line = ret_line[:-4]
                ret_line += "</strong>"
            elif (line[i] == '*' or line[i] == '_') and line[i-1] != '\\' and not in_italics and not in_link and not transclusion and not in_code:
                in_italics = not in_italics
                ret_line += "<em>"
            elif (line[i] == '*' or line[i] == '_') and line[i-1] != '\\' and in_italics and not in_link and not transclusion and not in_code:
                in_italics = not in_italics
                ret_line += "</em>"
            elif i > 1 and line[i] == '[' and line[i-1] == '[' and line[i-2] == '!':
                transclusion = True
                skip_beginning = i+1
                ret_line = ret_line[:-2]
            elif i > 0 and line[i] == '[' and line[i-1] == '[' and not in_link:
                in_link = True
                skip_beginning = i+1
                ret_line = ret_line[:-1]
            elif i > 0 and line[i] == ']' and line[i-1] == ']' and in_link:
                in_link = False
                mk_link = line[skip_beginning:i-1]
                text = mk_link
                link = ""
                if "|" in mk_link:
                    [mk_link, text] = mk_link.split("|")
                if "#" in mk_link:
                    [gen_link, head_link] = mk_link.split("#")
                    link = ((self.link_to_filepath)[gen_link] + "#" + head_link).lower().replace(" ", "-")
                    text = gen_link + " > " + head_link
                else:
                    link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                ret_line += self.make_link(self.make_offset() + link[1:].replace("*",""), text)
            elif i > 0 and line[i] == ']' and line[i-1] == ']' and transclusion:
                transclusion = False
                mk_link = line[skip_beginning:i-1]
                extension = mk_link.split(".")[-1]
                ret_line = ret_line[:-1]
                if extension == "png" or extension == "svg" or extension == "jpg":
                    link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                    ret_line += "<img src=\"" + self.make_offset() + link[1:] + "\">"
                else: #article transclusion
                    ret_line += self.make_opening_tag("aside")
                    link = (self.link_to_filepath)[mk_link.split("#")[0]]
                    file_paths = [k for k,v in (self.link_to_filepath).items() if v == link]
                    f_p = "\\" + file_paths[-1] + ".md"
                    seen_file = self.file_viewer(self.in_directory+f_p, add_to_header_list=False)
                    if "#" in mk_link:
                        #section
                        [gen_link, head_link] = mk_link.split("#")
                        link = ((self.link_to_filepath)[gen_link] + "#" + head_link).lower().replace(" ", "-")

                        ret_line += self.make_opening_tag("div class=\"transclude-link\"")
                        ret_line += self.make_link(self.make_offset() + link[1:].replace("*",""), ">>", "_self", "goto")
                        ret_line += self.make_closing_tag("div")
                        
                        aside_lines = seen_file.split("\n")
                        cue_text = mk_link.split("#")[-1].lower().replace(" ", "-")
                        for i in range (0, len(aside_lines)):
                            if cue_text in aside_lines[i] and "id" in aside_lines[i]:
                                if aside_lines[i][:5] == "<span":
                                    i += 1
                                    
                                if aside_lines[i][:2] == "<h":
                                    #read to next h or eod
                                    ret_line += aside_lines[i] + "\n"
                                    for j in range(i+1, len(aside_lines)):
                                        if(len(aside_lines[j]) > 5 and aside_lines[i][:2] == aside_lines[j][:2] and int(aside_lines[i][2]) >= int(aside_lines[j][2])):
                                            break;
                                        elif(len(aside_lines[j]) > 5 and aside_lines[i][1] == aside_lines[j][-3] and int(aside_lines[i][2]) >= int(aside_lines[j][-2])):
                                            break
                                        ret_line += aside_lines[j] + "\n"
                                    break
                                elif len(aside_lines[i]) > 6 and (aside_lines[i][:4] == "<tab" or aside_lines[i][:4] == "<sec"):
                                    ret_line += aside_lines[i] + "\n"
                                    for j in range(i+1, len(aside_lines)):
                                        if len(aside_lines[j]) > 5 and (aside_lines[j][:4] == "</ta" or aside_lines[j][:4] == "</se"):
                                            ret_line += aside_lines[j] + "\n"
                                            break;
                                        elif len(aside_lines[j].strip()) == "":
                                            break;
                                        ret_line += aside_lines[j] + "\n"
                                else:
                                    ret_line += aside_lines[i] + "\n"
                    else:
                        #entire article
                        link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                        ret_line += self.make_link(self.make_offset() + link[1:].replace("*",""), ">>")
                        ret_line += seen_file;
                ret_line += "<br>\n"
                ret_line += "</aside>\n"
            elif line[i-1] == "[" and not in_link:
                extern_links[0] = i
                extern_links[2] = len(ret_line)
                ret_line += line[i]
            elif line[i] == "(" and line[i-1] == "]" and extern_links[0] != -1:
                extern_links[1] = i
            elif line[i-1] == "]" and extern_links[0] != -1:
                extern_links = [-1,-1,-1]
            elif line[i] == ")" and extern_links[1] != -1:
                # make external links
                ret_line = ret_line[:extern_links[2]-1]
                ret_line += self.make_link(line[extern_links[1]+1:i], line[extern_links[0]:extern_links[1]-1], target="_blank")
                extern_links = [-1,-1,-1]
            elif not in_link and not transclusion:
                ret_line += line[i]
        if in_italics:
            ret_line += "</em>"
        if in_bold:
            ret_line += "</strong>"
        return ret_line

    def file_viewer(self, file_dir, add_to_header_list=True):
        if file_dir.replace("/","\\") in (self.cached_pages).keys():
            return (self.cached_pages)[file_dir.replace("/","\\")]
        
        new_file = ""
        open_file = open(file_dir, "r", encoding="utf8")
        file_lines = open_file.readlines()
        
        opening = 0
        if file_lines and file_lines[0] == "---\n":
            for i in range(1, len(file_lines)):
                if file_lines[i] == "---\n":
                    opening = i+1
                    break

        i = opening
        in_section = False
        section_place = -1
        in_code = False
        while i < len(file_lines):
            if i == len(file_lines)-1:
                line_to_put = file_lines[i]
            else:
                line_to_put = file_lines[i][:-1]
            indicer = "p"
            add_tag = False

            if line_to_put.strip() == "" and not (len(line_to_put) > 0 and line_to_put[0] == "	"):
                if in_section:
                    new_file += self.make_closing_tag("section ")
                    in_section = False
                    section_place = -1
                if in_code:
                    new_file += self.make_closing_tag("code")
                    new_file += self.make_closing_tag("pre")
                    in_code = False
                new_file += "<br>\n"
                i += 1
                continue
            elif len(line_to_put) >= 3 and len(line_to_put) == line_to_put.count("-"):
                new_file += "<hr>\n<br>\n"
                i += 1
                continue
            elif not in_code and i >= 1 and line_to_put[0] == "	" and (file_lines[i-1].strip() == "" or file_lines[i-1][0] == "#"):
                new_file += self.make_opening_tag("pre")
                new_file += self.make_opening_tag("code")
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
                    temp_string += self.make_opening_tag("tr")
                    t_indicer = "td"
                    if i == k:
                        t_indicer = "th"
                    elif i+1 == k:
                        continue
                    table_line = file_lines[k][:-1].split("|")[1:-1]
                    for elem in table_line:
                        processed_elem = self.line_parser(elem.strip(), in_code)
                        temp_string += "<" + t_indicer + ">" + processed_elem + "</" + t_indicer + ">\n"
                    temp_string += self.make_closing_tag("tr")
                if skip_ahead < len(file_lines) and len(file_lines[skip_ahead]) > 3 and file_lines[skip_ahead][0] == "^":
                    new_indice = "<span class=\"anchor\" id=\"" + file_lines[skip_ahead][-8:-1] + "\"></span>\n"
                    new_indice += self.make_opening_tag("table")
                    temp_string = new_indice + temp_string
                    skip_ahead += 1
                else:
                    temp_string = self.make_opening_tag("table") + temp_string
                self.in_table = False
                temp_string += self.make_closing_tag("table")
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
                        new_file += self.make_closing_tag("code")
                        new_file += self.make_closing_tag("pre")
                        in_code = False
                    indicer = "h" + str(len(top_part))
                    add_tag = True
                    #print(line_to_put)
                    lines_to_add = line_to_put.split(' ', 1)
                    if len(lines_to_add) > 1:
                        line_to_put = lines_to_add[1]
                    else:
                        line_to_put = lines_to_add[0]
                elif (top_part == "-" or top_part == "*") and len(file_lines[i]) > 2:
                    cur_tabbing = 1
                    new_file += self.make_opening_tag("ul")
                    while i < len(file_lines):
                        if i == len(file_lines)-1:
                            line_to_put = file_lines[i]
                        else:
                            line_to_put = file_lines[i][:-1]

                        tabs = line_to_put.split('- ', 1)[0]
                        tabs_ast = line_to_put.split('* ', 1)[0]
                        if tabs.count("\t") == len(tabs):
                            if (tabs.count("\t")+1) > cur_tabbing:
                                new_file += self.make_opening_tag("ul")*(tabs.count("\t")+1-cur_tabbing)
                            elif (tabs.count("\t")+1) < cur_tabbing:
                                new_file += self.make_closing_tag("ul")*(cur_tabbing-tabs.count("\t")-1)
                            cur_tabbing = tabs.count("\t")+1
                            new_file += "<li>"
                            new_file += self.line_parser(line_to_put[2:], in_code)
                            new_file += self.make_closing_tag("li")
                        elif tabs_ast.count("\t") == len(tabs_ast):
                            if (tabs_ast.count("\t")+1) > cur_tabbing:
                                new_file += self.make_opening_tag("ul")*(tabs_ast.count("\t")+1-cur_tabbing)
                            elif (tabs_ast.count("\t")+1) < cur_tabbing:
                                new_file += self.make_closing_tag("ul")*(cur_tabbing-tabs_ast.count("\t")-1)
                            cur_tabbing = tabs_ast.count("\t")+1
                            new_file += "<li>"
                            new_file += self.line_parser(line_to_put[2:], in_code)
                            new_file += self.make_closing_tag("li")
                        else:
                            break
                        i += 1
                    new_file += self.make_closing_tag("ul")
                    continue

                if indicer == "p" and not in_section:
                    new_file += self.make_opening_tag("section ")
                    section_place = len(new_file) - 3
                    in_section = True
                elif indicer.split(" ")[0] != "p" and in_section:
                    new_file += self.make_closing_tag("section ")
                    in_section = False
                    section_place = -1
                    
                if len(line_to_put) > 6 and line_to_put[-7] == "^" and in_section:
                    temp = " id=\"" + line_to_put[-7:] + "\""
                    new_file = new_file[:section_place] + temp + new_file[section_place:]
                    new_file += self.make_opening_tag(indicer, False)
                    line_to_put = line_to_put[:-7]
                elif len(line_to_put) > 6 and line_to_put[-7] == "^":
                    new_file += "<span class=\"anchor\" id=\"" + line_to_put[-7:] + "\"></span>\n"
                    new_file += self.make_opening_tag(indicer, False)
                    line_to_put = line_to_put[:-7]
                elif add_tag:
                    id_part = line_to_put.lower().replace("[[","").replace("]]","").replace(" ", "-").replace("*", "").replace(":","")
                    if add_to_header_list:
                        self.header_list.append((line_to_put, "#" + id_part, int(indicer[1])))
                    new_file += "<span class=\"anchor\" id=\"" + id_part + "\"></span>\n"
                    new_file += "<" + indicer + ">"
                else:
                    new_file += self.make_opening_tag(indicer, False)
                line_to_put = self.line_parser(line_to_put, in_code)
                new_file += line_to_put + "</" + indicer + ">\n"
                
            i += 1
        open_file.close()
        (self.cached_pages)[file_dir] = new_file
        return new_file

    def nav_bar(self):
        checkbox_prefix = 1
        
        ret_str = self.make_opening_tag("nav")
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"toggle\">"
        ret_str += """
                   <svg id="navicon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" icon-name="menu" class="lucide lucide-menu svg-navicon">
                   <line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="18" x2="20" y2="18"></line>
                   </svg>
                   """
        ret_str += "</button>"
        ret_str += "<div id=\"navbar\" popover><div id=\"idk\">"
        ret_str += self.make_opening_tag("ul class=\"menu\"")
        
        file_tuples = sorted(self.link_to_filepath.items(), key=lambda x: x[1].rsplit("\\", 1))
        
        for i in range(0, len(file_tuples)):
            if i == 0 or (i > 0 and file_tuples[i-1][1] != file_tuples[i][1]):
                link = self.make_offset()+file_tuples[i][1][1:]
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
                            ret_str += (fileprev.count("\\"))*(self.make_closing_tag("ul")+self.make_closing_tag("li"))
                            
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
                ret_str += "<li>" + self.make_link(link.replace(" ", "-").lower(), file_tuples[i][0].split("/")[-1]) + self.make_closing_tag("li")
        ret_str += self.make_closing_tag("ul") + 3*"</br>\n" + "</div>" + self.make_closing_tag("div")
        
        ret_str += self.make_op_close_inline_tag("p class=\"top-bar\"", self.nuwa_file.replace("\\", "<span class=\"file-link\"> > </span>"))

        ret_str += "<button popovertarget=\"table-of-contents\" popovertargetaction=\"toggle\">"
        ret_str += """
                   <svg id="tocicon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" icon-name="menu" class="lucide lucide-menu svg-navicon">
                   <line x1="4" y1="12" x2="5" y2="12"></line><line x1="4" y1="6" x2="5" y2="6"></line><line x1="4" y1="18" x2="5" y2="18"></line>
                   <line x1="10" y1="12" x2="20" y2="12"></line><line x1="10" y1="6" x2="20" y2="6"></line><line x1="10" y1="18" x2="20" y2="18"></line>
                   </svg>
                   """
        ret_str += "</button>"
        ret_str += "<div id=\"table-of-contents\" popover><div id=\"idk\">"
        
        for header in (self.header_list):
            ret_str += self.make_op_close_inline_tag("p class=\"indent-"+str(header[2]-1)+"\"", self.make_link(header[1], header[0]).replace("[[","").replace("]]",""))
        self.header_list = []
        ret_str += 3*"<br/>\n"
        ret_str += self.make_closing_tag("div")
        ret_str += self.make_closing_tag("div")
        return ret_str + self.make_closing_tag("nav")
        
    def add_files_to_dict(self, sep_files, rel_dir):
        nu_rel_dir = "." + rel_dir + "\\"
        for file in sep_files:
            if file.split('.')[-1] == "md":
                name = file.split('.')[0]
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
        ret_str = self.make_opening_tag("footer")
        ret_str += self.make_op_close_inline_tag("p", "Generated with the <a target=\"_blank\" href=\"https://github.com/Ishancorp/ObsidianMarkdownToHtml\">Obsidian Markdown to HTML script</a>")
        ret_str += self.make_op_close_inline_tag("p", "Last updated on " + datetime.datetime.now().strftime("%m/%d/%Y"))
        ret_str += self.make_closing_tag("footer")
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

    def writeToFile(self, file_name, new_file):
        export_file = self.out_directory + self.link_to_filepath[file_name.replace('\\', '/')].replace(" ", "-")
        os.makedirs(os.path.dirname(export_file), exist_ok=True)
        
        exp_file = open(export_file, "w", encoding="utf-8")
        exp_file.write(new_file)
        exp_file.close()
        
    def compile_webpages(self):
        for file in self.files:
            self.offset = file.count("\\")-1
            [thing, file_name, extension] = file.split(".")
            file_dir = self.in_directory + file[1:]
            if extension == "md":
                full_file_name = file_name[1:]
                file_name = file_name.split("\\")[-1]
                new_file = self.make_opening_tag("html")
                new_file += self.make_opening_tag("head")
                new_file += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                new_file += self.make_op_close_inline_tag("title", file_name)
                new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/\">\n"
                new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/inter/inter.css\">\n"
                new_file += "<link rel=\"stylesheet\" href=\""+ self.make_offset() + "\\style.css\">\n"
                new_file += self.make_closing_tag("head")
                new_file += self.make_opening_tag("body")

                scanned_file = self.file_viewer(file_dir)

                self.nuwa_file = file[2:-3]
                new_file += self.nav_bar()
                
                new_file += self.make_op_close_inline_tag("h1 class=\"file-title\"", file_name)
                new_file += self.make_opening_tag("article")

                new_file += scanned_file
                
                new_file += self.make_closing_tag("article")
                
                new_file += self.footer()
                new_file += self.make_closing_tag("body")
                new_file += self.make_closing_tag("html")
                    
                self.writeToFile(full_file_name, new_file)
                # break
            else:
                # write file as-is
                export_file = self.out_directory + file.split(".", 1)[1].replace(" ", "-").lower()
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        
        with open((self.out_directory) + "\\style.css", "w") as text_file:
            text_file.write(self.stylesheet)

