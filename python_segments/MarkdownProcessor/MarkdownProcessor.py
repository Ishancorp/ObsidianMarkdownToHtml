import markdown
import re
from python_segments.MarkdownProcessor.CustomMarkdownExtension import *
from python_segments.helpers import *

class MarkdownProcessor:
    def __init__(self, parent_instance, link_to_filepath):
        self.counter = 1
        self.parent_instance = parent_instance
        self.link_to_filepath = link_to_filepath
    
    def process_markdown(self, text, offset, add_to_header_list=True):
        extensions = [
            CustomMarkdownExtension(self.link_to_filepath, make_offset(offset), self.parent_instance, add_to_header_list),
            ObsidianFootnoteExtension(self.counter),
            "sane_lists",
            "tables", 
            "nl2br",
            ImprovedLaTeXExtension(),
        ]
        text = fix_table_spacing(text)
        processed_html = markdown.markdown(text, extensions=extensions)
        processed_html = re.sub(r'</p>\s*<p', '</p>\n<br>\n<p', processed_html)
        self.counter += 1
        return processed_html
