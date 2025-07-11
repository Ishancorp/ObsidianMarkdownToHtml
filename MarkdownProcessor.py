import unicodedata
from markdown.blockprocessors import BlockProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import InlineProcessor
from markdown.extensions.footnotes import FootnoteExtension, FootnoteInlineProcessor, FootnoteBlockProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree
import re

def clean_input(text):
    # Remove control characters and non-printables
    return ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')

def slugify(text):
    """Convert text to a URL-friendly slug"""
    if not text:
        return ""
    
    text = clean_input(text)

    text = re.sub(r'\x02?wzxhzdk:\d+', '', text)
    
    # Convert to lowercase and strip whitespace
    text = text.strip().lower()
    
    # Replace spaces and multiple whitespace with single hyphens
    text = re.sub(r'\s+', '-', text)
    
    # Remove special characters but keep alphanumeric, hyphens, and some safe chars
    text = re.sub(r'[^\w\-\[\]\(\)]', '', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    return text

class IndentedParagraphProcessor(BlockProcessor):
    INDENT_RE = re.compile(r'^((?: {4}|\t)+)(.*)')

    def test(self, parent, block):
        return bool(self.INDENT_RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        lines = block.split('\n')
        
        section = etree.SubElement(parent, 'section')

        for line in lines:
            # Determine indent level from the first indented line
            match = self.INDENT_RE.match(line)
            if not match:
                continue

            indent_raw = match.group(1)
            level = indent_raw.count('    ') + indent_raw.count('\t')

            # Create paragraph with class "indent-{level}"
            para = etree.SubElement(section, 'p')
            para.set('class', f'indent-{level}')

            # Remove leading indentation for each line
            stripped_lines = []
            stripped = re.sub(rf'^(?: {{4}}|\t){{{level}}}', '', line)
            stripped_lines.append(stripped)

            para.text = '\n'.join(stripped_lines)

class ObsidianFootnoteInlineProcessor(InlineProcessor):
    """Process Obsidian-style footnotes [^1] and convert them to standard markdown footnotes"""
    
    def __init__(self, pattern, md):
        super().__init__(pattern, md)
        self.RE = re.compile(r'\[\^([^\]]+)\]')
    
    def handleMatch(self, m, matcher):
        footnote_id = m.group(1)
        
        # Create footnote reference in standard markdown format
        el = etree.Element('sup')
        link = etree.SubElement(el, 'a')
        link.set('href', f'#fn:{footnote_id}')
        link.set('class', 'footnote-ref')
        link.set('id', f'fnref:{footnote_id}')
        link.text = f'[{footnote_id}]'
        
        return el, m.start(0), m.end(0)

class ObsidianFootnoteBlockProcessor(BlockProcessor):
    """Process Obsidian-style footnote definitions [^1]: content"""
    
    def __init__(self, parser):
        super().__init__(parser)
        self.RE = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)')
        self.footnotes = {}
    
    def test(self, parent, block):
        return bool(self.RE.match(block))
    
    def run(self, parent, blocks):
        block = blocks.pop(0)
        lines = block.split('\n')
        
        # Parse the first line
        match = self.RE.match(lines[0])
        if not match:
            return
        
        # Process continuation lines
        for line in lines:
            if line.strip():  # Non-empty line
                #footnote_content.append(line)
                match = self.RE.match(line)
                if not match:
                    return
                footnote_id = match.group(1)
                line_content = match.group(2)
                self.footnotes[footnote_id] = line_content
            else:
                break
        return True

class FootnoteTreeProcessor(Treeprocessor):
    """Process stored footnotes and add them to the document"""
    
    def __init__(self, md, footnote_processor):
        super().__init__(md)
        self.footnote_processor = footnote_processor
    
    def run(self, root):
        if not hasattr(self.footnote_processor, 'footnotes') or not self.footnote_processor.footnotes:
            return
        
        # Create a copy of the footnotes dictionary to avoid modification during iteration
        footnotes_copy = dict(self.footnote_processor.footnotes)
        
        # Create footnotes section
        footnotes_div = etree.Element('div')
        footnotes_div.set('class', 'footnotes')
        
        # Add horizontal rule
        hr = etree.SubElement(footnotes_div, 'hr')
        
        # Create ordered list for footnotes
        ol = etree.SubElement(footnotes_div, 'ol')
        
        # Iterate over the copy instead of the original
        for footnote_id, content in footnotes_copy.items():
            # Create list item
            li = etree.SubElement(ol, 'li')
            li.set('id', f'fn:{footnote_id}')
            
            # Process footnote content through markdown
            footnote_root = etree.Element('div')
            self.md.parser.parseChunk(footnote_root, content)
            
            # Move processed content to list item
            for child in footnote_root:
                li.append(child)
            
            # Add back-reference link
            backref = etree.SubElement(li, 'a')
            backref.set('href', f'#fnref:{footnote_id}')
            backref.set('class', 'footnote-backref')
            backref.text = '↩'
        
        # Add footnotes section to the end of the document
        root.append(footnotes_div)

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
        def get_text_content(elem):
            """Extract clean text content from an element"""
            text_parts = []
            
            # Get direct text content
            if elem.text:
                text_parts.append(elem.text.strip())
            
            # Get text from child elements
            for child in elem:
                child_text = get_text_content(child)
                if child_text:
                    text_parts.append(child_text)
                
                # Get tail text after child elements
                if child.tail:
                    text_parts.append(child.tail.strip())
            
            return ' '.join(text_parts).strip()
        
        def process_element(parent):
            i = 0
            while i < len(parent):
                elem = parent[i]
                # Check for headers
                if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Extract text content for slug
                    text = get_text_content(elem)
                    
                    # Debug: print what text we're getting
                    #print(f"Header text extracted: '{text}'")
                    
                    header_id = slugify(text)
                    
                    # Debug: print the resulting ID
                    #print(f"Generated ID: '{header_id}'")
                    
                    # Only create anchor if we have a valid ID
                    if header_id:
                        # Create <span class="anchor" id="...">
                        span = etree.Element('span')
                        span.set('class', 'anchor')
                        span.set('id', header_id)

                        # Insert span before header
                        parent.insert(i, span)
                        i += 1  # Skip over inserted span

                # Recurse into children
                process_element(elem)
                i += 1

        process_element(root)

class ObsidianFootnoteExtension(Extension):
    """Extension to handle Obsidian-style footnotes"""
    
    def extendMarkdown(self, md):
        # Create footnote processor instance
        footnote_processor = ObsidianFootnoteBlockProcessor(md.parser)
        
        # Register processors
        md.parser.blockprocessors.register(footnote_processor, 'obsidian_footnote', 80)
        md.inlinePatterns.register(ObsidianFootnoteInlineProcessor(r'\[\^([^\]]+)\]', md), 'obsidian_footnote_ref', 180)
        md.treeprocessors.register(FootnoteTreeProcessor(md, footnote_processor), 'footnote_tree', 10)