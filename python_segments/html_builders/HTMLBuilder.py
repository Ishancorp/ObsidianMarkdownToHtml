import datetime
from python_segments.helpers import *

class HTMLBuilder:
    def __init__(self):
        with open("styles/json_canvas.css") as json_stylesheet: self.json_stylesheet = json_stylesheet.read()

    def top_part(self, file_name, offset, is_json=False):
        new_file = make_opening_tag("html")
        new_file += make_opening_tag("head")
        new_file += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        new_file += make_op_close_inline_tag("title", file_name)
        new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/\">\n"
        new_file += "<link rel=\"preconnect\" href=\"https://rsms.me/inter/inter.css\">\n"
        new_file += "<link rel=\"stylesheet\" href=\""+ make_offset(offset) + "\\style.css\">\n"
        if is_json:
                new_file += make_opening_tag("style")
                new_file += self.json_stylesheet
                new_file += make_closing_tag("style")
        new_file += make_closing_tag("head")
        new_file += make_opening_tag("body")
        return new_file

    def footer(self):
        ret_str = make_opening_tag("footer")
        ret_str += make_op_close_inline_tag("p", "Generated with the <a target=\"_blank\" href=\"https://github.com/Ishancorp/ObsidianMarkdownToHtml\">Obsidian Markdown to HTML script</a>")
        ret_str += make_op_close_inline_tag("p", "Last updated on " + datetime.datetime.now().strftime("%m/%d/%Y"))
        ret_str += make_closing_tag("footer")
        return ret_str

    def middle_part(self, file_name, content, is_json=False):
        if is_json:
            new_file = make_op_close_inline_tag("h1 class=\"file-title\"", file_name + ".CANVAS")
            new_file += content
            return new_file
        else:
            new_file = make_op_close_inline_tag("h1 class=\"file-title\"", file_name)
            new_file += make_opening_tag("article")
            new_file += content
            new_file += make_closing_tag("article")
            return new_file

    def bottom_part(self, offset, is_json=False):
        new_file = self.footer()
        if is_json:
            new_file += "<script src=\""+ make_offset(offset) + "\\canvas.js\"></script>\n"
        new_file += "<script src=\""+ make_offset(offset) + "\\searcher.js\"></script>\n"
        new_file += """
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']]
  }
};
</script>"""
        new_file += make_closing_tag("body")
        new_file += make_closing_tag("html")
        return new_file
