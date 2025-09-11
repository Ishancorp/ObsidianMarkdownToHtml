class NavigationBuilder:
    def generate_navigation_bar(self, nuwa_file):
        """Generate navigation bar without headers - headers will be populated client-side"""
        ret_str = "<nav>"
        ret_str += "<span>"
        ret_str += "<button popovertarget=\"navbar\" popovertargetaction=\"toggle\">\n"
        ret_str += "<i data-lucide=\"align-justify\"></i>"
        ret_str += "</button>"
        ret_str += "<div id=\"navbar\" popover>"
        ret_str += "</div>"

        ret_str += "<button popovertarget=\"searchbar\" popovertargetaction=\"toggle\">\n"
        ret_str += "<i data-lucide=\"search\"></i>"
        ret_str += "</button>"
        ret_str += f"<div id=\"searchbar\" popover><input type=\"text\" id=\"searchInput\" onkeyup=\"searchForArticle()\" placeholder=\"Search..\"></div>"
        ret_str += "</span>"
        if nuwa_file.split('.')[-1] == "md": nuwa_file = nuwa_file.split('.')[0] + '.html'
        else: nuwa_file = nuwa_file + '.html'
        ret_str += f"<p class=\"top-bar\">{nuwa_file.replace("\\", "<span class=\"file-link\"> > </span>")}</p>"

        ret_str += "<button id=\"toc-button\" popovertarget=\"table-of-contents\" popovertargetaction=\"toggle\">"
        ret_str += "<i data-lucide=\"table-of-contents\"></i>"
        ret_str += "</button>"
        ret_str += "<div id=\"table-of-contents\" style=\"display: none\" popover><div id=\"toc-content\"></div></div>"
        ret_str += "</nav>"
        return ret_str
