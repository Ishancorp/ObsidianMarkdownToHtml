import re

CLEANR = re.compile('<.*?>') 
external_link = ""
with open("svg/other_extern.html", encoding='utf-8') as other_pages: external_link = " " + other_pages.read()

def make_opening_tag(indicer, newline_end = True):
    return "<" + indicer + ">" + (newline_end * "\n")

def make_closing_tag(indicer):
    return "</" + indicer + ">\n"

def make_op_close_inline_tag(indicer, inner):
    return "<" + indicer + ">" + inner + "</" + indicer + ">\n"

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

def fix_table_spacing(markdown_text):
    table_pattern = re.compile(r'''
        (?:(?<=\n)|\A)               # Start of string or after a newline
        (?P<table>                   # Named group for the full table
            (?:\|.*\|\n)            # Header row
            (?:\|[-:| ]+\|\n)       # Divider row
            (?:\|.*\|\n?)*          # Optional body rows
        )
        (?P<tag_line>               # Named group for an optional tag line
            \^([a-zA-Z0-9]{6})[ \t]*\n  # Line with ^ + 6 alphanumeric characters
        )?
    ''', re.VERBOSE)

    def replacement(match):
        table = match.group('table').rstrip()
        tag_line = match.group('tag_line')
        if tag_line:
            tag = tag_line.strip()
            return f"\n{table}\n{tag} \n\n"
        else:
            return f"\n{table}\n\n"

    result = table_pattern.sub(replacement, markdown_text)
    return result