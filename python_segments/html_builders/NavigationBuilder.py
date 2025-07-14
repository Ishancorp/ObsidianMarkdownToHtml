from python_segments.helpers import *

class NavigationBuilder:
    def __init__(self, link_to_filepath):
        self.link_to_filepath = link_to_filepath
        with open("svg/other_pages.html", encoding='utf-8') as other_pages: self.other_pages = other_pages.read()
        with open("svg/other_search.html", encoding='utf-8') as other_search: self.other_search = other_search.read()
        with open("svg/other_headers.html", encoding='utf-8') as other_headers: self.other_headers = other_headers.read()

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

    def generate_navigation_bar(self, offset, header_list, nuwa_file):
        checkbox_prefix = 1
        
        ret_str = make_opening_tag("nav")
        ret_str += "<span>"
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"toggle\">\n"
        ret_str += self.other_pages
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
        ret_str += self.other_search
        ret_str += "</button>"
        ret_str += f"<div id=\"searchbar\" popover><input type=\"text\" id=\"searchInput\" onkeyup=\"searchForArticle()\" placeholder=\"Search..\"><ul id=\"articles\">"
        for key in self.search_dict.keys():
            right_part_link = self.search_dict[key][1:].replace(" ", "-")
            link = make_offset(offset) + right_part_link
            ret_str += f"<li><a searchText=\"{link}\" href=\"{link}\">{key}<br><sub class=\"fileloc\">{right_part_link[1:].replace("\\", " > ")}</sub></a></li>"
        ret_str += "</ul>" + "</div>"
        ret_str += "</span>"
        ret_str += make_op_close_inline_tag("p class=\"top-bar\"", nuwa_file.replace("\\", "<span class=\"file-link\"> > </span>"))

        ret_str += "<button popovertarget=\"table-of-contents\" popovertargetaction=\"toggle\">"
        ret_str += self.other_headers
        ret_str += "</button>"
        if header_list:
            ret_str += "<div id=\"table-of-contents\" popover><div id=\"idk\">"
            for header in header_list:
                ret_str += make_op_close_inline_tag("p class=\"indent-"+str(header[2]-1)+"\"", make_link("#" + header[1], header[0]).replace("[[","").replace("]]",""))
            ret_str += make_closing_tag("div")
        ret_str += make_closing_tag("div")
        ret_str += make_closing_tag("nav")
        return ret_str
