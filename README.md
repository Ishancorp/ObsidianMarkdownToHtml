# Obsidian Markdown To HTML

Obsidian Markdown To HTML is a Python library for exporting Obsidian projects to HTML, in the form of code which will be run in browser.

## Built with

This is built almost exclusively with Python - however, it contains Javascript scripts which are written to target directory to be run by browser.

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
- [x] Add ordered list
- [x] Add unordered list
- [x] Add footnotes
- [x] Add search
- [x] Add LaTeX
- [ ] Add interface
- [-] Work on canvas
  - [x] Make nodes work
  - [x] Make edges work
  - [-] Work on zoom

## License

[MIT](https://choosealicense.com/licenses/mit/)
