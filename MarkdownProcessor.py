from markdown.blockprocessors import BlockProcessor
from markdown.treeprocessors import Treeprocessor
import xml.etree.ElementTree as etree
from markdown.inlinepatterns import InlineProcessor
import re

def slugify(text):
    text = re.sub(r'\s+', '-', text.strip().lower())   # Replace spaces with hyphens
    text = re.sub(r'[^\w,\-\[\]\(\)]', '', text)                # Remove special characters
    return text

class IndentedParagraphProcessor(BlockProcessor):
    INDENT_RE = re.compile(r'^((?: {4}|\t)+)(.*)')

    def test(self, parent, block):
        return bool(self.INDENT_RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        lines = block.split('\n')

        # Determine indent level from the first indented line
        match = self.INDENT_RE.match(lines[0])
        if not match:
            return

        indent_raw = match.group(1)
        level = indent_raw.count('    ') + indent_raw.count('\t')

        # Create paragraph with class "indent-{level}"
        para = etree.SubElement(parent, 'p')
        para.set('class', f'indent-{level}')

        # Remove leading indentation for each line
        stripped_lines = []
        for line in lines:
            stripped = re.sub(rf'^(?: {{4}}|\t){{{level}}}', '', line)
            stripped_lines.append(stripped)

        para.text = '\n'.join(stripped_lines)

class SectionBlockProcessor(BlockProcessor):
    HEADER_RE = re.compile(r'^(#{1,6})\s+(.*)')  # Header regex (for markdown headers)
    BLANK_LINE_RE = re.compile(r'^\s*$')  # Blank line regex

    def test(self, parent, block):
        # Process any block
        return True

    def run(self, parent, blocks):
        section = None  # Will hold the current section
        buffer = []  # Will accumulate blocks (paragraphs, lists, etc.)

        # Deregister to prevent recursion during block processing
        self.parser.blockprocessors.deregister('section_block')

        try:
            while blocks:
                block = blocks.pop(0)

                # Handle header (new section)
                if self.HEADER_RE.match(block):
                    # If we have accumulated blocks in the previous section, append it
                    if section is not None:
                        parent.append(section)
                        section = None  # Start a new section

                    # Process the header and create the corresponding HTML header
                    header_match = self.HEADER_RE.match(block)
                    header_level = len(header_match.group(1))
                    header_text = header_match.group(2)
                    header = etree.SubElement(parent, f'h{header_level}')
                    header.text = header_text
                    continue  # Skip to the next block

                # Handle blank line (this ends the current section)
                if self.BLANK_LINE_RE.match(block):
                    if section is not None:
                        parent.append(section)  # Finalize the current section
                        section = None  # Start a new section
                    continue  # Skip to the next block

                # If we haven't started a section yet, create one
                if section is None:
                    section = etree.Element('section')

                # Add the block (could be a paragraph, list, etc.) to the current section
                self.parser.parseBlocks(section, [block])

            # Add any remaining section to the parent if exists
            if section is not None:
                parent.append(section)

        finally:
            # Re-register the processor to avoid recursion issues
            self.parser.blockprocessors.register(self, 'section_block', 76)

class WikiLinkInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md, link_dict, offset):
        super().__init__(pattern, md)
        self.link_dict = link_dict
        self.offset = offset

    def handleMatch(self, m, matcher):
        link_text = m.group(1).strip()

        if '|' in link_text:
            page_name, alias = map(str.strip, link_text.split('|', 1))
        else:
            page_name = link_text
            alias = link_text
            alias = alias.replace('#', '&nbsp;>&nbsp;')
        
        if '#' in page_name:
            page_name, next_part = map(str.strip, link_text.split('#', 1))
            href = self.link_dict[page_name] + "#" + next_part
        else:        
            href = self.link_dict[page_name]

        el = etree.Element('a')
        el.set('href', self.offset + href[1:].replace(" ", "-").lower())
        el.set('class', 'wikilink')
        el.text = alias
        return el, m.start(0), m.end(0)

class AnchorSpanTreeProcessor(Treeprocessor):
    def run(self, root):
        def process_element(parent):
            i = 0
            while i < len(parent):
                elem = parent[i]
                # Check for headers
                if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Extract text content for slug
                    text = ''.join(elem.itertext())
                    header_id = slugify(text)

                    # Create <span class="anchor" id="...">
                    span = etree.Element('span')
                    span.set('class', 'anchor')
                    span.set('id', header_id)
                    #print(header_id)
                    #print(span)

                    # Insert span before header
                    parent.insert(i, span)
                    i += 1  # Skip over inserted span

                # Recurse into children
                process_element(elem)
                i += 1

        process_element(root)
