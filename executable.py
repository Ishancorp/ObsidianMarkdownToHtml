import sys
from ObsidianMarkdownToHtml import *

in_directory = sys.argv[1]
out_directory = sys.argv[2]

om2html = ObsidianMarkdownToHtml(in_directory, out_directory)

om2html.compile_webpages()
