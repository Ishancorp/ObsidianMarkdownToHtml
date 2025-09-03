from collections import deque
from python_segments.helpers import *

class NavigationBuilder:
    def __init__(self, link_to_filepath):
        self.link_to_filepath = link_to_filepath

        self.search_dict = self.link_to_filepath.copy()
        seen_values = set()
        keys_to_delete = []

        for key, value in list(self.search_dict.items()):
            if value in seen_values:
                keys_to_delete.append(key)
            else:
                seen_values.add(value)

        for key in keys_to_delete:
            del self.search_dict[key]

    def generate_navigation_bar(self, offset, nuwa_file):
        """Generate navigation bar without headers - headers will be populated client-side"""
        checkbox_prefix = 1
        
        ret_str = make_opening_tag("nav")
        ret_str += "<span>"
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"toggle\">\n"
        ret_str += "<i data-lucide=\"align-justify\"></i>"
        ret_str += "</button>"
        ret_str += "<div id=\"navbar\" popover><div id=\"idk\">"
        ret_str += make_opening_tag("ul class=\"menu\"")
        
        file_tuples = sorted(self.link_to_filepath.items(), key=lambda x: x[1].rsplit("\\", 1))
        
        for i in range(0, len(file_tuples)):
            if i == 0 or (i > 0 and file_tuples[i-1][1] != file_tuples[i][1]):
                link = make_offset(offset)+file_tuples[i][1][1:]
                if file_tuples[i][1].rsplit("\\", 1)[0] != file_tuples[i-1][1].rsplit("\\", 1)[0]:
                    fileprev = file_tuples[i-1][1].rsplit("\\", 1)[0] + "\\"
                    filecur = file_tuples[i][1].rsplit("\\", 1)[0] + "\\"
                    
                    while fileprev != "" and filecur != "":
                        if fileprev.split("\\",1)[0]  != filecur.split("\\",1)[0]:
                            break
                        fileprev = fileprev.split("\\",1)[-1]
                        filecur = filecur.split("\\",1)[-1]
                    if(i != 0):
                        if(fileprev != "." and fileprev != ""):
                            ret_str += (fileprev.count("\\"))*(make_closing_tag("ul")+make_closing_tag("li"))
                            
                        if(filecur != "."):
                            filecur_elems = filecur.split("\\")
                            for j in range(0, len(filecur_elems)-1):
                                ret_str += "<li class=\"parent\">\n"
                                checkbox_tag = f"{checkbox_prefix}-{filecur_elems[j].replace(" ", "-")}"
                                checkbox_prefix += 1
                                ret_str += f"<input type=\"checkbox\" id={checkbox_tag} name={checkbox_tag}>\n"
                                ret_str += f"<label id=\"checkbox\" for={checkbox_tag}>{filecur_elems[j].title()}</label>\n"
                                ret_str += "<ul class=\"child\">\n"
                ret_str += "<li>" + make_link(link.replace(" ", "-").lower(), file_tuples[i][0].split("/")[-1]) + make_closing_tag("li")
        ret_str += make_closing_tag("ul") + "</div>" + make_closing_tag("div")

        ret_str += "<button popovertarget=\"searchbar\" popovertargetaction=\"toggle\">\n"
        ret_str += "<i data-lucide=\"search\"></i>"
        ret_str += "</button>"
        ret_str += f"<div id=\"searchbar\" popover><input type=\"text\" id=\"searchInput\" onkeyup=\"searchForArticle()\" placeholder=\"Search..\"><ul id=\"articles\">"
        for key in self.search_dict.keys():
            right_part_link = self.search_dict[key][1:].replace(" ", "-")
            link = make_offset(offset) + right_part_link
            ret_str += f"<li><a searchText=\"{link}\" href=\"{link}\">{key.split('/')[-1]}<br><sub class=\"fileloc\">{right_part_link[1:].replace("\\", " > ")}</sub></a></li>"
        ret_str += "</ul>" + "</div>"
        ret_str += "</span>"
        if nuwa_file.split('.')[-1] == "md": nuwa_file = nuwa_file.split('.')[0] + '.html'
        else: nuwa_file = nuwa_file + '.html'
        ret_str += make_op_close_inline_tag("p class=\"top-bar\"", nuwa_file.replace("\\", "<span class=\"file-link\"> > </span>"))

        # Placeholder for headers - will be populated client-side
        ret_str += "<button id=\"toc-button\" popovertarget=\"table-of-contents\" popovertargetaction=\"toggle\">"
        ret_str += "<i data-lucide=\"table-of-contents\"></i>"
        ret_str += "</button>"
        ret_str += "<div id=\"table-of-contents\" style=\"display: none\" popover><div id=\"toc-content\"></div></div>"
        ret_str += make_closing_tag("nav")
        return ret_str
