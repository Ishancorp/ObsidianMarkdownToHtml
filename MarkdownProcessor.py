import hashlib
import unicodedata
from markdown.blockprocessors import BlockProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import InlineProcessor
from markdown.extensions.footnotes import FootnoteExtension, FootnoteInlineProcessor, FootnoteBlockProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree
from xml.etree.ElementTree import fromstring
import re
from helpers import *

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
    text = re.sub(r'[^\w\-\[\]\(\),]', '', text)
    
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
    
    def __init__(self, pattern, md, prefix):
        super().__init__(pattern, md)
        self.RE = re.compile(r'\[\^([^\]]+)\]')
        self.prefix = prefix
    
    def handleMatch(self, m, matcher):
        footnote_id = m.group(1)
        
        # Create footnote reference in standard markdown format
        el = etree.Element('span')
        el.set('id', f'fn-{self.prefix}-{footnote_id}')
        el.set('class', f'fn fn-{self.prefix}-{footnote_id}')
        link = etree.SubElement(el, 'a')
        link.set('href', f'#fn:{footnote_id}')
        link.set('class', 'fn-link')
        link.set('id', f'fnref:{footnote_id}')
        link.text = f'<sup>[{footnote_id}]</sup>'
        tooltip = etree.SubElement(el, 'span')
        tooltip.set('class', 'fn-tooltip')
        tooltip.text = f'fn-tooltip-{self.prefix}-{footnote_id}%'
        
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
    
    def __init__(self, md, footnote_processor, prefix):
        super().__init__(md)
        self.footnote_processor = footnote_processor
        self.prefix = prefix
    
    def run(self, root):
        if not hasattr(self.footnote_processor, 'footnotes') or not self.footnote_processor.footnotes:
            return
        
        # Create a copy of the footnotes dictionary to avoid modification during iteration
        footnotes_copy = dict(self.footnote_processor.footnotes)

        self.set_placeholders(root)
        
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
    
    def set_placeholders(self, parent):
        for child in parent:
            self.set_placeholders(child)
        
        if parent.text and f'fn-tooltip-{self.prefix}-' in parent.text:
            snip_stuff = parent.text.split('-')[-1][:-1]
            if snip_stuff in self.footnote_processor.footnotes.keys():
                parent.text = self.footnote_processor.footnotes[snip_stuff]

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
    def __init__(self, md, parent_instance=None, add_to_header_list=True):
        super().__init__(md)
        self.parent_instance = parent_instance
        self.add_to_header_list = add_to_header_list
    
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
                    
                    header_id = slugify(text)
                    
                    # Only create anchor if we have a valid ID
                    if header_id:
                        # Create <span class="anchor" id="...">
                        span = etree.Element('span')
                        span.set('class', 'anchor')
                        span.set('id', header_id)

                        # Insert span before header
                        parent.insert(i, span)
                        i += 1  # Skip over inserted span
                        
                        # Add to header list if enabled and parent_instance exists
                        if self.add_to_header_list and self.parent_instance:
                            header_level = int(elem.tag[1])  # Extract number from h1, h2, etc.
                            self.parent_instance.header_list.append([text, header_id, header_level])

                # Recurse into children
                process_element(elem)
                i += 1

        process_element(root)

class ObsidianFootnoteExtension(Extension):
    def __init__(self, prefix):
        self.prefix = str(prefix)

    def extendMarkdown(self, md):
        footnote_processor = ObsidianFootnoteBlockProcessor(md.parser)
        
        md.parser.blockprocessors.register(footnote_processor, 'obsidian_footnote', 80)
        md.inlinePatterns.register(ObsidianFootnoteInlineProcessor(r'\[\^([^\]]+)\]', md, self.prefix), 'obsidian_footnote_ref', 180)
        md.treeprocessors.register(FootnoteTreeProcessor(md, footnote_processor, self.prefix), 'footnote_tree', 10)

class TransclusionInlineProcessor(InlineProcessor):
    """Enhanced transclusion processor that handles footnotes with unique prefixes"""
    
    def __init__(self, pattern, md, parent_instance):
        super().__init__(pattern, md)
        self.parent_instance = parent_instance
        self.transclusion_counter = 0  # Add counter for unique prefixes

    def handleMatch(self, m, matcher):
        link_text = m.group(1).strip()
        
        # Check if this is an image by extension
        extension = link_text.split(".")[-1].lower()
        if extension in ["png", "svg", "jpg", "jpeg", "gif", "webp"]:
            return self.handle_image_transclusion(link_text, m)
        else:
            return self.handle_content_transclusion(link_text, m)
    
    def handle_image_transclusion(self, link_text, match):
        """Handle image transclusion"""
        if link_text in self.parent_instance.link_to_filepath:
            link = self.parent_instance.link_to_filepath[link_text].lower().replace(" ", "-")
            
            # Create image element
            img = etree.Element('img')
            img.set('src', make_offset(self.parent_instance.offset) + link[1:])
            img.set('alt', link_text)
            
            return img, match.start(0), match.end(0)
        else:
            # If image not found, return broken link indicator
            span = etree.Element('span')
            span.set('class', 'broken-link')
            span.text = f'![[{link_text}]]'
            return span, match.start(0), match.end(0)
    
    def handle_content_transclusion(self, link_text, match):
        """Handle content transclusion (articles/sections)"""
        if link_text.split("#")[0] not in self.parent_instance.link_to_filepath:
            # If page not found, return broken link indicator
            span = etree.Element('span')
            span.set('class', 'broken-link')
            span.text = f'![[{link_text}]]'
            return span, match.start(0), match.end(0)
        
        # Create aside element for transclusion
        aside = etree.Element('aside')
        
        # Create transclude section div
        transcl_div = etree.Element('div')
        transcl_div.set('class', 'transclsec')
        
        # Get the transcluded content
        transcluded_content = self.get_transcluded_content(link_text)
        
        if transcluded_content:
            # Generate unique prefix for this transclusion
            self.transclusion_counter += 1
            unique_prefix = f"{self.parent_instance.counter}-t{self.transclusion_counter}"
            
            # Clean up the content before processing
            cleaned_content = self.clean_content(transcluded_content)
            
            # Scan for footnotes in the transcluded content
            transcluded_footnotes = self.scan_for_footnotes(link_text, cleaned_content)
            
            # Create a separate markdown instance with unique footnote prefix
            transcluded_md = self.create_transclusion_markdown(unique_prefix)
            
            # Process the transcluded content with the separate markdown instance
            processed_content = transcluded_md.convert(cleaned_content)

            if transcluded_footnotes:
                match_fn = re.search(r'fn-tooltip-(\d+)-t\d+-(\d+)%', processed_content)
                while match_fn:
                    last_number = match_fn.group(2)
                    replacement_text = transcluded_footnotes.get(last_number, '')
                    def replace_footnote(match):
                        current_last = match.group(2)
                        if current_last == last_number:
                            return replacement_text
                        return match.group(0)  # return original match unchanged

                    processed_content = re.sub(
                        r'fn-tooltip-(\d+)-t\d+-(\d+)%',
                        replace_footnote,
                        processed_content
                    )
                    match_fn = re.search(r'fn-tooltip-(\d+)-t\d+-(\d+)%', processed_content)
            
            # Clean up the processed HTML
            cleaned_html = self.clean_html_spacing(processed_content)
            
            # Parse the processed HTML and add to transclude div
            try:
                # Wrap in a temporary div to ensure valid XML parsing
                wrapped_content = f"<div>{cleaned_html}</div>"
                temp_root = fromstring(wrapped_content)
                
                # Move all parsed content to transclude div
                for child in temp_root:
                    transcl_div.append(child)
                    
            except Exception as e:
                # Fallback: add as text if XML parsing fails
                p = etree.SubElement(transcl_div, 'p')
                p.text = f"Error processing transcluded content: {str(e)}"
        else:
            # Add error message if content not found
            p = etree.SubElement(transcl_div, 'p')
            p.text = f"Content not found: {link_text}"
        
        aside.append(transcl_div)
        
        # Add link to original
        link_div = etree.Element('div')
        link_div.set('class', 'transclude-link')
        
        if "#" in link_text:
            gen_link, head_link = link_text.split("#", 1)
            href = self.parent_instance.link_to_filepath[gen_link] + "#" + head_link.lower().replace(" ", "-")
        else:
            href = self.parent_instance.link_to_filepath[link_text]
        
        link_a = etree.SubElement(link_div, 'a')
        link_a.set('href', make_offset(self.parent_instance.offset) + href[1:].replace("*", "").replace(" ", "-"))
        link_a.set('class', 'goto')
        link_a.set('target', '_self')
        link_a.text = '>>'
        
        aside.append(link_div)
        
        return aside, match.start(0), match.end(0)
    
    def scan_for_footnotes(self, link_text, content):
        """Scan transcluded content for footnotes and return them as a dictionary"""
        footnotes = {}
        
        # Get the file path for the transcluded content
        page_name = link_text.split("#")[0]
        if page_name not in self.parent_instance.link_to_filepath:
            return footnotes
        
        link = self.parent_instance.link_to_filepath[page_name]
        file_paths = [k for k, v in self.parent_instance.link_to_filepath.items() if v == link]
        f_p = "\\" + file_paths[-1] + ".md"
        
        try:
            # Read the full file content to scan for footnotes
            full_file_content = self.parent_instance.readlines_raw(self.parent_instance.in_directory + f_p)
            full_content = ''.join(full_file_content)
            
            # Pattern to match footnote definitions [^id]: content
            footnote_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*?)(?=^\[\^|\Z)', re.MULTILINE | re.DOTALL)
            
            # Find all footnote definitions in the file
            for match in footnote_pattern.finditer(full_content):
                footnote_id = match.group(1)
                footnote_content = match.group(2).strip()
                
                # Cut off the footnote at the first Markdown header
                header_match = re.search(r'^#{1,6}\s.*', footnote_content, re.MULTILINE)
                cutoff_index = header_match.start() if header_match else len(footnote_content)

                # Cut off at the first occurrence of two newlines
                double_newline_match = re.search(r'\n\s*\n', footnote_content)
                if double_newline_match and double_newline_match.start() < cutoff_index:
                    cutoff_index = double_newline_match.start()

                # Truncate the content accordingly
                footnote_content = footnote_content[:cutoff_index]

                # Clean up the footnote content
                footnote_content = re.sub(r'\n+', ' ', footnote_content)  # Replace newlines with spaces
                footnote_content = re.sub(r'\s+', ' ', footnote_content)  # Normalize whitespace

                # Check if this footnote is referenced in the transcluded content
                if f'[^{footnote_id}]' in content:
                    footnotes[footnote_id] = footnote_content
            
            # Also check for footnotes that might be in the transcluded section itself
            section_footnote_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)', re.MULTILINE)
            for match in section_footnote_pattern.finditer(content):
                footnote_id = match.group(1)
                footnote_content = match.group(2).strip()
                footnotes[footnote_id] = footnote_content
        
        except (IOError, IndexError):
            pass
        
        return footnotes
    
    def clean_content(self, content):
        """Clean up content before markdown processing"""
        if not content:
            return ""
        
        # Remove excessive empty lines but preserve paragraph breaks
        lines = content.split('\n')
        cleaned_lines = []
        empty_line_count = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                empty_line_count += 1
                # Only allow up to 2 consecutive empty lines (for paragraph breaks)
                if empty_line_count <= 2:
                    cleaned_lines.append(line)
            else:
                empty_line_count = 0
                cleaned_lines.append(line)
        
        # Join back and strip leading/trailing whitespace
        cleaned = '\n'.join(cleaned_lines).strip()
        
        # Remove excessive spaces at the beginning of lines
        cleaned = re.sub(r'^[ \t]+', '', cleaned, flags=re.MULTILINE)
        
        return cleaned
    
    def clean_html_spacing(self, html):
        """Clean up HTML spacing issues"""
        if not html:
            return ""
        
        # Remove excessive whitespace between tags
        html = re.sub(r'>\s+<', '><', html)
        
        # Remove excessive newlines
        html = re.sub(r'\n\s*\n\s*\n+', '\n\n', html)
        
        # Clean up paragraph spacing
        html = re.sub(r'<p>\s*</p>', '', html)  # Remove empty paragraphs
        html = re.sub(r'</p>\s*<p>', '</p><p>', html)  # Remove space between paragraphs
        
        # Clean up line breaks
        html = re.sub(r'<br\s*/?>\s*<br\s*/?>', '<br>', html)  # Remove duplicate breaks
        
        return html.strip()
    
    def create_transclusion_markdown(self, unique_prefix):
        """Create a separate markdown instance for processing transcluded content"""
        import markdown
        
        # Create extensions for transclusion processing
        extensions = [
            # Use the unique prefix for footnotes in transcluded content
            ObsidianFootnoteExtension(unique_prefix),
            "sane_lists",
            "tables", 
            # Remove "nl2br" extension as it might be adding unwanted line breaks
        ]
        
        # Create a new markdown instance
        transcluded_md = markdown.Markdown(extensions=extensions)
        
        return transcluded_md
    
    def get_transcluded_content(self, mk_link):
        """Get content for transclusion with proper table boundary handling"""
        link = self.parent_instance.link_to_filepath[mk_link.split("#")[0]]
        file_paths = [k for k, v in self.parent_instance.link_to_filepath.items() if v == link]
        f_p = "\\" + file_paths[-1] + ".md"
        
        if "#" in mk_link:
            # Handle section transclusion
            gen_link, head_link = mk_link.split("#", 1)
            
            if head_link.startswith('^'):
                # Block reference - use improved block reference handling
                return self.get_block_reference_content_improved(gen_link, head_link, f_p)
            else:
                # Section reference
                return self.get_section_content(f_p, head_link)
        else:
            # Entire article transclusion
            return self.get_full_article_content(f_p, mk_link)
    
    def get_block_reference_content_improved(self, page_name, block_ref, file_path):
        """Get content for a block reference with improved table boundary detection"""
        try:
            examined_lines = self.parent_instance.readlines_raw(self.parent_instance.in_directory + file_path)
            
            if block_ref[0] == '^':
                # Find the line with the block reference
                for i in range(len(examined_lines) - 1, -1, -1):
                    if examined_lines[i].strip().endswith(block_ref):
                        # Found the line with block reference
                        line_content = examined_lines[i-1].strip() + examined_lines[i].strip()
                        if line_content.endswith(block_ref):
                            line_content = line_content[:-len(block_ref)].strip()
                        
                        # Check if this is part of a table
                        if '|' in line_content:
                            return self.extract_table_block(examined_lines, i, block_ref)
                        else:
                            return self.extract_paragraph_block(examined_lines, i, block_ref)
            
            return None
        except (IOError, IndexError):
            return None
    
    def extract_table_block(self, lines, ref_line_idx, block_ref):
        """Extract a complete table that contains the block reference"""
        table_lines = []
        
        # Get the line with block reference (without the reference)
        line_content = lines[ref_line_idx].strip()
        if line_content.endswith(block_ref):
            line_content = line_content[:-len(block_ref)].strip()
        
        # Find table boundaries
        table_start = ref_line_idx
        table_end = ref_line_idx
        
        # Go backwards to find table start
        for j in range(ref_line_idx - 1, -1, -1):
            prev_line = lines[j].strip()
            if self.is_table_line(prev_line):
                table_start = j
            elif prev_line == "":
                continue  # Skip empty lines within table
            else:
                break  # Hit non-table content
        
        # Go forwards to find table end
        for j in range(ref_line_idx + 1, len(lines)):
            next_line = lines[j].strip()
            if self.is_table_line(next_line):
                table_end = j
            elif next_line == "":
                # Check if the next non-empty line is still part of the table
                k = j + 1
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines) and self.is_table_line(lines[k].strip()):
                    continue  # Still part of table
                else:
                    break  # End of table
            else:
                break  # Hit non-table content
        
        # Extract table content and clean up spacing
        for i in range(table_start, table_end + 1):
            line = lines[i].strip()
            if line:  # Skip empty lines
                # Remove block reference if it's on this line
                if line.endswith(block_ref):
                    line = line[:-len(block_ref)].strip()
                table_lines.append(line)
        
        # Join with single newlines only
        return '\n'.join(table_lines)
    
    def extract_paragraph_block(self, lines, ref_line_idx, block_ref):
        """Extract a paragraph block that contains the block reference"""
        content_lines = []
        
        # Get the line with block reference (without the reference)
        line_content = lines[ref_line_idx].strip()
        if line_content.endswith(block_ref):
            line_content = line_content[:-len(block_ref)].strip()
        content_lines.append(line_content)
        
        # Collect related lines going backwards
        for j in range(ref_line_idx - 1, -1, -1):
            prev_line = lines[j].strip()
            if (prev_line.startswith('#') or 
                prev_line == "" or 
                prev_line.startswith('- ') or
                prev_line.startswith('* ') or
                prev_line.startswith('+ ') or
                re.match(r'^\d+\.\s', prev_line) or
                self.is_table_line(prev_line)):
                break
            content_lines.insert(0, prev_line)
        
        # Join with single newlines only
        return '\n'.join(content_lines)
    
    def is_table_line(self, line):
        """Check if a line is part of a table"""
        if not line:
            return False
        
        # Check for table row (contains |)
        if re.match(r'^\s*\|.*\|\s*$', line):
            return True
        
        # Check for table separator line (contains only -, :, |, and spaces)
        if re.match(r'^\s*\|?\s*[-:]+\s*(\|\s*[-:]+\s*)*\|?\s*$', line):
            return True
        return False
    
    def get_section_content(self, file_path, section_name):
        """Get content of a specific section"""
        try:
            examined_lines = self.parent_instance.readlines_raw(self.parent_instance.in_directory + file_path)
            
            new_lines = []
            
            for i in range(len(examined_lines)):
                line = examined_lines[i]
                if (line.startswith('#') and 
                    section_name in re.sub(self.parent_instance.CLEANR, '', line).replace("[[","").replace("]]","").replace(":","").replace("*", "")):
                    
                    header_size = len(line.split("# ", 1)[0]) + 1
                    new_lines.append(line)
                    
                    # Collect lines until next header of same or higher level
                    for j in range(i + 1, len(examined_lines)):
                        next_line = examined_lines[j]
                        if (next_line.startswith('#') and 
                            len(next_line.split("# ", 1)[0]) > 0 and
                            len(next_line.split("# ", 1)[0]) + 1 <= header_size):
                            break
                        new_lines.append(next_line)
                    break
            
            # Join and clean up the content
            content = ''.join(new_lines)
            return content.strip()
        except (IOError, IndexError):
            return None
    
    def get_full_article_content(self, file_path, page_name):
        """Get content of entire article"""
        try:
            examined_lines = self.parent_instance.readlines_raw(self.parent_instance.in_directory + file_path)
            
            # Add title
            title_line = f"**{page_name.split('/')[-1]}**\n\n"
            
            # Skip frontmatter if present
            start_idx = 0
            if examined_lines and examined_lines[0].strip() == "---":
                for i in range(1, len(examined_lines)):
                    if examined_lines[i].strip() == "---":
                        start_idx = i + 1
                        break
            
            content = ''.join(examined_lines[start_idx:])
            content = fix_table_spacing(content)
            return title_line + content.strip()
        except (IOError, IndexError):
            return None

class BlockReferenceProcessor(Treeprocessor):
    """Process block references and attach them as IDs to paragraphs"""
    
    def __init__(self, md):
        super().__init__(md)
        self.block_ref_pattern = re.compile(r'\s*\^([a-zA-Z0-9]{6})\s*$')
    
    def run(self, root):
        def process_element(parent):
            i = 0
            while i < len(parent):
                elem = parent[i]
                
                # Check if this is a paragraph element
                if elem.tag == 'p':
                    # Get the text content of the paragraph
                    text_content = self.get_full_text(elem)
                    
                    # Check if it ends with a block reference
                    match = self.block_ref_pattern.search(text_content)
                    if match:
                        block_id = match.group(1)
                        
                        # Remove the block reference from the text
                        self.remove_block_reference(elem, match.group(0))

                        anchor_span = etree.Element('span')
                        anchor_span.set('class', 'anchor')
                        anchor_span.set('id', f'^{block_id}')
                        parent.insert(i, anchor_span)
                        i += 1
                
                # Handle table elements with block references
                elif elem.tag == 'table':
                    # Check if any cell in the table has a block reference
                    table_text = self.get_full_text(elem)
                    match = self.block_ref_pattern.search(table_text)
                    if match:
                        block_id = match.group(1)
                        
                        # Remove the block reference from the table
                        self.remove_block_reference(elem, match.group(0))
                        
                        # Add anchor span before the table
                        anchor_span = etree.Element('span')
                        anchor_span.set('class', 'anchor')
                        anchor_span.set('id', f'^{block_id}')
                        parent.insert(i, anchor_span)
                        i += 1
                
                # Recurse into children
                process_element(elem)
                i += 1
        
        process_element(root)
    
    def get_full_text(self, elem):
        """Get the full text content of an element including children"""
        text_parts = []
        
        if elem.text:
            text_parts.append(elem.text)
        
        for child in elem:
            child_text = self.get_full_text(child)
            if child_text:
                text_parts.append(child_text)
            
            if child.tail:
                text_parts.append(child.tail)
        
        return ''.join(text_parts)
    
    def remove_block_reference(self, elem, block_ref_text):
        """Remove the block reference text from the element"""
        # Check if it's in the direct text
        if elem.text and block_ref_text in elem.text:
            elem.text = elem.text.replace(block_ref_text, '').rstrip()
            return
        
        # Check children and their tails
        for child in elem:
            if child.tail and block_ref_text in child.tail:
                child.tail = child.tail.replace(block_ref_text, '').rstrip()
                return
            
            # Recursively check child elements
            self.remove_block_reference_from_child(child, block_ref_text)
    
    def remove_block_reference_from_child(self, elem, block_ref_text):
        """Recursively remove block reference from child elements"""
        if elem.text and block_ref_text in elem.text:
            elem.text = elem.text.replace(block_ref_text, '').rstrip()
            return
        
        for child in elem:
            if child.tail and block_ref_text in child.tail:
                child.tail = child.tail.replace(block_ref_text, '').rstrip()
                return
            self.remove_block_reference_from_child(child, block_ref_text)
