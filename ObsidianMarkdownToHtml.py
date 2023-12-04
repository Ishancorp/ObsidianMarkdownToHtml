import os
import shutil
import datetime

class ObsidianMarkdownToHtml:
    def __init__(self, in_directory, out_directory):
        self.in_directory = in_directory
        self.out_directory = out_directory
        self.link_to_filepath = {}
        self.files = []
        self.offset = 0
        self.cached_pages = {}
        
        self.add_dirs_to_dict("")

    def make_link(self, link, text, target="_self"):
        return "<a href=\"" + link +"\" target=\""+ target +"\">" + text + "</a>"

    def make_offset(self):
        if self.offset == 0:
            return '.'
        elif self.offset == 1:
            return '..'
        else:
            return ((self.offset-1) * "../") + ".."
        
    def line_parser(self, line):
        ret_line = ""
        in_link = False
        transclusion = False
        in_bold = False
        in_italics = False
        skip_beginning = -1
        extern_links = [-1, -1,-1]
        for i in range(0, len(line)):
            if line[i] == '*' and line[i-1] == '\\':
                ret_line = ret_line[:-1] + "*"
            elif line[i] == '*' and line[i-1] == '*' and not in_bold:
                in_bold = not in_bold
                in_italics = False
                ret_line = ret_line[:-4]
                ret_line += "<strong>"
            elif line[i] == '*' and line[i-1] == '*' and in_bold:
                in_bold = not in_bold
                in_italics = False
                ret_line = ret_line[:-4]
                ret_line += "</strong>"
            elif (line[i] == '*' or line[i] == '_') and line[i-1] != '\\' and not in_italics:
                in_italics = not in_italics
                ret_line += "<em>"
            elif (line[i] == '*' or line[i] == '_') and line[i-1] != '\\' and in_italics:
                in_italics = not in_italics
                ret_line += "</em>"
            elif line[i] == '[' and line[i-1] == '[' and line[i-2] == '!':
                transclusion = True
                skip_beginning = i+1
                ret_line = ret_line[:-2]
            elif line[i] == '[' and line[i-1] == '[' and not in_link:
                in_link = True
                skip_beginning = i+1
                ret_line = ret_line[:-1]
            elif line[i] == ']' and line[i-1] == ']' and in_link:
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
                ret_line += self.make_link(self.make_offset() + link[1:], text)
            elif line[i] == ']' and line[i-1] == ']' and transclusion:
                transclusion = False
                mk_link = line[skip_beginning:i-1]
                extension = mk_link.split(".")[-1]
                ret_line = ret_line[:-1]
                if extension == "png" or extension == "svg":
                    link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                    ret_line += "<img src=\"" + self.make_offset() + link[1:] + "\">"
                else: #article transclusion
                    ret_line += "<aside>\n"
                    link = (self.link_to_filepath)[mk_link.split("#")[0]]
                    file_paths = [k for k,v in (self.link_to_filepath).items() if v == link]
                    f_p = "\\" + file_paths[-1] + ".md"
                    seen_file = self.file_viewer(self.in_directory+f_p)
                    if "#" in mk_link:
                        #section
                        [gen_link, head_link] = mk_link.split("#")
                        link = ((self.link_to_filepath)[gen_link] + "#" + head_link).lower().replace(" ", "-")

                        ret_line += "<div class=\"transclude-link\">"
                        ret_line += self.make_link(self.make_offset() + link[1:], ">>")
                        ret_line += "</div>"
                        
                        aside_lines = seen_file.split("\n")
                        cue_text = mk_link.split("#")[-1].lower().replace(" ", "-")
                        for i in range (0, len(aside_lines)):
                            if cue_text in aside_lines[i] and "id" in aside_lines[i]:
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
                                            break;
                                        elif len(aside_lines[j].strip()) == "":
                                            break;
                                        ret_line += aside_lines[j] + "\n"
                                else:
                                    ret_line += aside_lines[i] + "\n"
                    else:
                        #entire article
                        link = (self.link_to_filepath)[mk_link].lower().replace(" ", "-")
                        ret_line += self.make_link(self.make_offset() + link[1:], ">>")
                        ret_line += seen_file;
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

    def file_viewer(self, file_dir):
        if file_dir in (self.cached_pages).keys():
            return (self.cached_pages)[file_dir]
        new_file = ""
        open_file = open(file_dir, "r", encoding="utf8")
        file_lines = open_file.readlines()
        
        opening = 0
        in_section = False
        for i in range(2, 5):
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

            if line_to_put.strip() == "":
                if in_section:
                    new_file += "</section>\n"
                    in_section = False
                    section_place = -1
                if in_code:
                    new_file += "</code></pre>\n"
                    in_code = False
                new_file += "<br>\n"
                i += 1
                continue
            elif len(line_to_put) >= 3 and len(line_to_put) == line_to_put.count("-"):
                new_file += "<hr>\n<br>\n"
                i += 1
                continue
            elif not in_code and i >= 1 and line_to_put[0] == "	" and (file_lines[i-1].strip() == "" or file_lines[i-1][0] == "#"):
                new_file += "<pre><code>\n"
                in_code = True
                i -= 1
            elif(line_to_put[0] == "|" and line_to_put[-1] == "|"):
                end_point = 0
                temp_string = ""
                skip_ahead = len(file_lines)
                for k in range (i,len(file_lines)):
                    if line_to_put.count("|") > 2 and line_to_put.count("|") != file_lines[k].count("|"):
                        skip_ahead = k
                        break
                    temp_string += "<tr>\n"
                    t_indicer = "td"
                    if i == k:
                        t_indicer = "th"
                    elif i+1 == k:
                        continue
                    table_line = file_lines[k][:-1].split("|")[1:-1]
                    for elem in table_line:
                        processed_elem = self.line_parser(elem.strip())
                        temp_string += "<" + t_indicer + ">" + processed_elem + "</" + t_indicer + ">\n"
                    temp_string += "</tr>\n"
                if skip_ahead < len(file_lines) and len(file_lines[skip_ahead]) > 3 and file_lines[skip_ahead][0] == "^":
                    new_indice = "<table id=\""
                    new_indice += file_lines[skip_ahead][-8:-1] + "\">"
                    temp_string = new_indice + temp_string
                    skip_ahead += 1
                else:
                    temp_string = "<table>\n" + temp_string
                temp_string += "</table>\n"
                new_file += temp_string
                i = skip_ahead-1
            else:
                if not in_code and i >= 1 and line_to_put[0] == "	":
                    indicer = "p class = \"indent-1\""
                elif not in_code and i >= 1 and line_to_put[:2] == "		":
                    indicer = "p class = \"indent-2\""
                elif not in_code and i >= 1 and line_to_put[:3] == "			":
                    indicer = "p class = \"indent-3\""
                top_part = line_to_put.split(' ', 1)[0]
                if len(top_part) == top_part.count("#") and len(top_part) > 0:
                    indicer = "h" + str(len(top_part))
                    add_tag = True
                    line_to_put = line_to_put.split(' ', 1)[1]

                if indicer == "p" and not in_section:
                    new_file += "<section>\n"
                    section_place = len(new_file) - 3
                    in_section = True
                elif indicer.split(" ")[0] != "p" and in_section:
                    new_file += "</section>\n"
                    in_section = False
                    section_place = -1
                    
                if len(line_to_put) > 6 and line_to_put[-7] == "^" and in_section:
                    temp = " id=\"" + line_to_put[-7:] + "\""
                    new_file = new_file[:section_place] + temp + new_file[section_place:]
                    new_file += "<" + indicer + ">"
                    line_to_put = line_to_put[:-7]
                elif len(line_to_put) > 6 and line_to_put[-7] == "^":
                    new_file += "<" + indicer + " id=\""
                    new_file += line_to_put[-7:] + "\">"
                    line_to_put = line_to_put[:-7]
                elif add_tag:
                    new_file += "<" + indicer + " id=\""
                    new_file += line_to_put.lower().replace("[[","").replace("]]","").replace(" ", "-") + "\">"
                else:
                    new_file += "<" + indicer + ">"
                line_to_put = self.line_parser(line_to_put)
                new_file += line_to_put + "</" + indicer + ">\n"
                
            i += 1
        open_file.close()
        (self.cached_pages)[file_dir] = new_file
        return new_file

    def nav_bar(self):
        ret_str = "<nav>\n"
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"show\">"
        ret_str += """
                   <svg id="navicon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" icon-name="menu" class="lucide lucide-menu svg-navicon">
                   <line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="18" x2="20" y2="18"></line>
                   </svg>'
                   """
        ret_str += "</button>"
        ret_str += "<div id=\"navbar\" popover><div id=\"idk\">"
        ret_str += "<ul class=\"menu\">\n"
        filepaths = list(self.link_to_filepath.values())
        filenames = list(self.link_to_filepath.keys())
        
        for i in range(0, len(filepaths)):
            if i == 0 or (i > 0 and filepaths[i-1] != filepaths[i]):
                link = self.make_offset()+filepaths[i][1:]
                if filepaths[i].rsplit("\\", 1)[0] != filepaths[i-1].rsplit("\\", 1)[0]:
                    # delete pre each slash till slashes are different
                    fileprev = filepaths[i-1].rsplit("\\", 1)[0] + "\\"
                    filecur = filepaths[i].rsplit("\\", 1)[0] + "\\"
                    
                    while fileprev != "" and filecur != "":
                        if fileprev.split("\\",1)[0]  != filecur.split("\\",1)[0]:
                            break
                        fileprev = fileprev.split("\\",1)[-1]
                        filecur = filecur.split("\\",1)[-1]
                    # add close uls corresp to slashes of i-1
                    if(i != 0):
                        if(fileprev != "." and fileprev != ""):
                            ret_str += (fileprev.count("\\"))*"</ul>\n"
                            
                        # add folders, open uls corresp to slashes of i
                        if(filecur != "."):
                            filecur_elems = filecur.split("\\")
                            for j in range(0, len(filecur_elems)-1):
                                ret_str += "<li class=\"parent\">"
                                ret_str += filecur_elems[j].title()
                                ret_str += "<ul class=\"child\">\n"
                                ret_str += "</li>\n"
                #remove indexed
                ret_str += "<li>" + self.make_link(link.replace(" ", "-").lower(), filenames[i].split("/")[-1]) + "</li>\n"
        return ret_str + "</ul>\n" + 3*"</br>\n" + "</div></div>\n</nav>\n"
        
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
        ret_str = "<footer>\n"
        ret_str += "<p>Generated with the Obsidian Markdown to HTML script</p>\n"
        ret_str += "<p>Last updated on " + datetime.datetime.now().strftime("%m/%d/%Y") + "</p>\n"
        ret_str += "</footer>\n"
        return ret_str

    def add_dirs_to_dict(self, path):
        nu_dir = self.in_directory + "\\" + path
        files_and_dirs = os.listdir(nu_dir)
        sep_files = [f for f in files_and_dirs if os.path.isfile(nu_dir+'/'+f)]
        dirs = [f for f in files_and_dirs if (os.path.isdir(nu_dir+'/'+f) and f[0] != '.')]
        
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
                new_file = "<html>\n<head>\n"
                new_file += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
                new_file += "<title>" + file_name + "</title>\n"
                new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/\">\n"
                new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/inter/inter.css\">\n"
                new_file += "<link rel=\"stylesheet\" href=\""+ self.make_offset() + "\\style.css\">\n"
                new_file += "</head>\n"
                new_file += "<body>\n"
                new_file += self.nav_bar()
                new_file += "<h1 class=\"file-title\">" + file_name + "</h1>\n"
                new_file += "<article>\n"

                new_file += self.file_viewer(file_dir)
                
                new_file += "</article>\n"
                new_file += self.footer()
                new_file += "</body>\n"
                new_file += "</html>\n"
                    
                self.writeToFile(full_file_name, new_file)
                # break
            else:
                # write file as-is
                export_file = self.out_directory + file.split(".", 1)[1].replace(" ", "-").lower()
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                shutil.copy(file_dir, export_file)

        print("Compiled")
        
        shutil.copy(".\\style.css", (self.out_directory) + "\\style.css")
