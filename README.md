# Obsidian Markdown To HTML

Obsidian Markdown To HTML is a Python library for exporting Obsidian projects to HTML. Note that this is very much in its early development phase, and I am still working on it.

### Built with

This is built exclusively with Python.

## Installation

Install the module ObsidianMarkdownToHtml to Python.

## Usage

```from ObsidianMarkdownToHtml import *

in_directory = input("Input dir: ")
out_directory = input("Output dir: ")

om2html = ObsidianMarkdownToHtml(in_directory, out_directory)

om2html.compile_webpages()
```

## Roadmap

- [x] Add navbar
    - [x] Make folders collapsible
- [ ] Add back to top links
- [x] Add table of contents
- [ ] Add ordered list
- [x] Add unordered list
- [ ] Add interface

## License

[MIT](https://choosealicense.com/licenses/mit/)