# Obsidian Markdown To HTML

Obsidian Markdown To HTML is a Python library for exporting Obsidian projects to HTML. Note that this is very much in its early development phase, and I am still working on it.

### Built with

This is built exclusively with Python.

## Installation

Install the module ObsidianMarkdownToHtml to Python, and keep style.css in the same directory.

## Usage

```from ObsidianMarkdownToHtml import *

in_directory = input("Input dir: ")
out_directory = input("Output dir: ")

om2html = ObsidianMarkdownToHtml(in_directory, out_directory)

om2html.compile_webpages()
```

## Roadmap

- [x] Add navbar
    - [ ] Make folders collapsible
- [ ] Add back to top links
- [ ] Add table of contents
- [ ] Add interface

## License

[MIT](https://choosealicense.com/licenses/mit/)