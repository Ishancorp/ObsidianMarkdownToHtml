from ObsidianMarkdownToHtml import *

in_directory = input("Input dir: ")
out_directory = input("Output dir: ")

om2html = ObsidianMarkdownToHtml(in_directory, out_directory)

om2html.compile_webpages()
