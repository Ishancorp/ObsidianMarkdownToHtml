import unicodedata
from markdown.blockprocessors import BlockProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import InlineProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree
from xml.etree.ElementTree import fromstring
import re
from python_segments.helpers import *
from python_segments.FileManager import *

def clean_input(text):
    return ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')

def slugify(text):
    if not text:
        return ""
    
    text = clean_input(text)
    text = re.sub(r'\x02?wzxhzdk:\d+', '', text)
    text = text.strip().lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\-\[\]\(\),†\"\'“”‘’‡.;]', '', text)
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
            match = self.INDENT_RE.match(line)
            if not match:
                continue

            indent_raw = match.group(1)
            level = indent_raw.count('    ') + indent_raw.count('\t')

            para = etree.SubElement(section, 'p')
            para.set('class', f'indent-{level}')

            stripped_lines = []
            stripped = re.sub(rf'^(?: {{4}}|\t){{{level}}}', '', line)
            stripped_lines.append(stripped)

            para.text = '\n'.join(stripped_lines)

class ObsidianFootnoteInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md, prefix):
        super().__init__(pattern, md)
        self.RE = re.compile(r'\[\^([^\]]+)\]')
        self.prefix = prefix
    
    def handleMatch(self, m, matcher):
        footnote_id = m.group(1)
        
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
    def __init__(self, parser):
        super().__init__(parser)
        self.RE = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)')
        self.footnotes = {}
    
    def test(self, parent, block):
        return bool(self.RE.match(block))
    
    def run(self, parent, blocks):
        block = blocks.pop(0)
        lines = block.split('\n')
        
        match = self.RE.match(lines[0])
        if not match:
            return
        
        for line in lines:
            if line.strip():
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
        
        footnotes_copy = dict(self.footnote_processor.footnotes)

        self.set_placeholders(root)
        
        footnotes_div = etree.Element('div')
        footnotes_div.set('class', 'footnotes')
        
        hr = etree.SubElement(footnotes_div, 'hr')
        
        ol = etree.SubElement(footnotes_div, 'ol')
        
        for footnote_id, content in footnotes_copy.items():
            li = etree.SubElement(ol, 'li')
            li.set('id', f'fn:{footnote_id}')
            
            footnote_root = etree.Element('div')
            self.md.parser.parseChunk(footnote_root, content)
            
            for child in footnote_root:
                li.append(child)
            
            backref = etree.SubElement(li, 'a')
            backref.set('href', f'#fnref:{footnote_id}')
            backref.set('class', 'footnote-backref')
            backref.text = '↩'
        
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
            
            if elem.text:
                text_parts.append(elem.text.strip())
            
            for child in elem:
                child_text = get_text_content(child)
                if child_text:
                    text_parts.append(child_text)
                
                if child.tail:
                    text_parts.append(child.tail.strip())
            
            return ' '.join(text_parts).strip()
        
        def process_element(parent):
            i = 0
            while i < len(parent):
                elem = parent[i]
                if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    text = get_text_content(elem)
                    
                    header_id = slugify(text)
                    
                    if header_id:
                        span = etree.Element('span')
                        span.set('class', 'anchor')
                        span.set('id', header_id)

                        parent.insert(i, span)
                        i += 1
                        
                        if self.add_to_header_list and self.parent_instance:
                            header_level = int(elem.tag[1])
                            self.parent_instance.header_list.append([text, header_id, header_level])

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
        self.transclusion_counter = 0 
        self.FileManager = FileManager()

    def handleMatch(self, m, matcher):
        link_text = m.group(1).strip()
        
        extension = link_text.split(".")[-1].lower()
        if extension in ["png", "svg", "jpg", "jpeg", "gif", "webp"]:
            return self.handle_image_transclusion(link_text, m)
        else:
            return self.handle_content_transclusion(link_text, m)
    
    def handle_image_transclusion(self, link_text, match):
        """Handle image transclusion"""
        if link_text in self.parent_instance.link_to_filepath:
            link = self.parent_instance.link_to_filepath[link_text].lower().replace(" ", "-")
            
            img = etree.Element('img')
            img.set('src', make_offset(self.parent_instance.offset) + link[1:])
            img.set('alt', link_text)
            
            return img, match.start(0), match.end(0)
        else:
            span = etree.Element('span')
            span.set('class', 'broken-link')
            span.text = f'![[{link_text}]]'
            return span, match.start(0), match.end(0)
    
    def handle_content_transclusion(self, link_text, match):
        if link_text.split("#")[0] not in self.parent_instance.link_to_filepath:
            span = etree.Element('span')
            span.set('class', 'broken-link')
            span.text = f'![[{link_text}]]'
            return span, match.start(0), match.end(0)
        
        aside = etree.Element('aside')
        
        transcl_div = etree.Element('div')
        transcl_div.set('class', 'transclsec')
        
        transcluded_content = self.get_transcluded_content(link_text)
        
        if transcluded_content:
            self.transclusion_counter += 1
            unique_prefix = f"{self.parent_instance.MarkdownProcessor.counter}-t{self.transclusion_counter}"
            
            cleaned_content = self.clean_content(transcluded_content)
            
            transcluded_footnotes = self.scan_for_footnotes(link_text, cleaned_content)
            
            transcluded_md = self.create_transclusion_markdown(unique_prefix)
            
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
                        return match.group(0)

                    processed_content = re.sub(
                        r'fn-tooltip-(\d+)-t\d+-(\d+)%',
                        replace_footnote,
                        processed_content
                    )
                    match_fn = re.search(r'fn-tooltip-(\d+)-t\d+-(\d+)%', processed_content)
            
            cleaned_html = self.clean_html_spacing(processed_content)
            
            try:
                wrapped_content = f"<div>{cleaned_html}</div>"
                temp_root = fromstring(wrapped_content.replace('&', '&amp;'))
                
                for child in temp_root:
                    transcl_div.append(child)
                    
            except Exception as e:
                p = etree.SubElement(transcl_div, 'p')
                p.text = f"Error processing transcluded content: {str(e)}"
        else:
            p = etree.SubElement(transcl_div, 'p')
            p.text = f"Content not found: {link_text}"
        
        aside.append(transcl_div)
        
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
        footnotes = {}
        
        page_name = link_text.split("#")[0]
        if page_name not in self.parent_instance.link_to_filepath:
            return footnotes
        
        link = self.parent_instance.link_to_filepath[page_name]
        file_paths = [k for k, v in self.parent_instance.link_to_filepath.items() if v == link]
        f_p = "\\" + file_paths[-1] + ".md"
        
        try:
            full_content = self.FileManager.read_raw(self.parent_instance.in_directory + f_p)
            
            footnote_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*?)(?=^\[\^|\Z)', re.MULTILINE | re.DOTALL)
            
            for match in footnote_pattern.finditer(full_content):
                footnote_id = match.group(1)
                footnote_content = match.group(2).strip()
                
                header_match = re.search(r'^#{1,6}\s.*', footnote_content, re.MULTILINE)
                cutoff_index = header_match.start() if header_match else len(footnote_content)

                double_newline_match = re.search(r'\n\s*\n', footnote_content)
                if double_newline_match and double_newline_match.start() < cutoff_index:
                    cutoff_index = double_newline_match.start()

                footnote_content = footnote_content[:cutoff_index]

                footnote_content = re.sub(r'\n+', ' ', footnote_content)
                footnote_content = re.sub(r'\s+', ' ', footnote_content)

                if f'[^{footnote_id}]' in content:
                    footnotes[footnote_id] = footnote_content
            
            section_footnote_pattern = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)', re.MULTILINE)
            for match in section_footnote_pattern.finditer(content):
                footnote_id = match.group(1)
                footnote_content = match.group(2).strip()
                footnotes[footnote_id] = footnote_content
        
        except (IOError, IndexError):
            pass
        
        return footnotes
    
    def clean_content(self, content):
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        empty_line_count = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                empty_line_count += 1
                if empty_line_count <= 2:
                    cleaned_lines.append(line)
            else:
                empty_line_count = 0
                cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines).strip()
        
        cleaned = re.sub(r'^[ \t]+', '', cleaned, flags=re.MULTILINE)
        
        return cleaned
    
    def clean_html_spacing(self, html):
        if not html:
            return ""
        
        html = re.sub(r'>\s+<', '><', html)
        
        html = re.sub(r'\n\s*\n\s*\n+', '\n\n', html)
        
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'</p>\s*<p>', '</p><p>', html)
        
        html = re.sub(r'<br\s*/?>\s*<br\s*/?>', '<br>', html)
        
        return html.strip()
    
    def create_transclusion_markdown(self, unique_prefix):
        import markdown
        
        extensions = [
            ObsidianFootnoteExtension(unique_prefix),
            "sane_lists",
            "tables", 
            ImprovedLaTeXExtension(),
        ]
        
        transcluded_md = markdown.Markdown(extensions=extensions)
        
        return transcluded_md
    
    def get_transcluded_content(self, mk_link):
        link = self.parent_instance.link_to_filepath[mk_link.split("#")[0]]
        file_paths = [k for k, v in self.parent_instance.link_to_filepath.items() if v == link]
        f_p = "\\" + file_paths[-1] + ".md"
        
        if "#" in mk_link:
            gen_link, head_link = mk_link.split("#", 1)
            
            if head_link.startswith('^'):
                return self.get_block_reference_content_improved(gen_link, head_link, f_p)
            else:
                return self.get_section_content(f_p, head_link)
        else:
            return self.get_full_article_content(f_p, mk_link)
    
    def get_block_reference_content_improved(self, page_name, block_ref, file_path):
        try:
            examined_lines = self.FileManager.readlines_raw(self.parent_instance.in_directory + file_path)
            
            if block_ref[0] == '^':
                for i in range(len(examined_lines) - 1, -1, -1):
                    if examined_lines[i].strip().endswith(block_ref):
                        line_content = examined_lines[i-1].strip() + examined_lines[i].strip()
                        if line_content.endswith(block_ref):
                            line_content = line_content[:-len(block_ref)].strip()
                        
                        if '|' in line_content:
                            return self.extract_table_block(examined_lines, i, block_ref)
                        else:
                            return self.extract_paragraph_block(examined_lines, i, block_ref)
            
            return None
        except (IOError, IndexError):
            return None
    
    def extract_table_block(self, lines, ref_line_idx, block_ref):
        table_lines = []
        
        line_content = lines[ref_line_idx].strip()
        if line_content.endswith(block_ref):
            line_content = line_content[:-len(block_ref)].strip()
        
        table_start = ref_line_idx
        table_end = ref_line_idx
        
        for j in range(ref_line_idx - 1, -1, -1):
            prev_line = lines[j].strip()
            if self.is_table_line(prev_line):
                table_start = j
            elif prev_line == "":
                continue
            else:
                break
        
        for j in range(ref_line_idx + 1, len(lines)):
            next_line = lines[j].strip()
            if self.is_table_line(next_line):
                table_end = j
            elif next_line == "":
                k = j + 1
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines) and self.is_table_line(lines[k].strip()):
                    continue
                else:
                    break
            else:
                break
        
        for i in range(table_start, table_end + 1):
            line = lines[i].strip()
            if line:
                if line.endswith(block_ref):
                    line = line[:-len(block_ref)].strip()
                table_lines.append(line)
        
        return '\n'.join(table_lines)
    
    def extract_paragraph_block(self, lines, ref_line_idx, block_ref):
        content_lines = []
        
        line_content = lines[ref_line_idx].strip()
        if line_content.endswith(block_ref):
            line_content = line_content[:-len(block_ref)].strip()
        content_lines.append(line_content)
        
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
        
        return '\n'.join(content_lines)
    
    def is_table_line(self, line):
        if not line:
            return False
        
        if re.match(r'^\s*\|.*\|\s*$', line):
            return True
        
        if re.match(r'^\s*\|?\s*[-:]+\s*(\|\s*[-:]+\s*)*\|?\s*$', line):
            return True
        return False
    
    def get_section_content(self, file_path, section_name):
        try:
            examined_lines = self.FileManager.readlines_raw(self.parent_instance.in_directory + file_path)
            
            new_lines = []
            
            for i in range(len(examined_lines)):
                line = examined_lines[i]
                if (line.startswith('#') and 
                    section_name in re.sub(CLEANR, '', line).replace("[[","").replace("]]","").replace(":","").replace("*", "")):
                    
                    header_size = len(line.split("# ", 1)[0]) + 1
                    new_lines.append(line)
                    
                    for j in range(i + 1, len(examined_lines)):
                        next_line = examined_lines[j]
                        if (next_line.startswith('#') and 
                            len(next_line.split("# ", 1)[0]) > 0 and
                            len(next_line.split("# ", 1)[0]) + 1 <= header_size):
                            break
                        new_lines.append(next_line)
                    break
            
            content = ''.join(new_lines)
            return content.strip()
        except (IOError, IndexError):
            return None
    
    def get_full_article_content(self, file_path, page_name):
        try:
            raw_text = self.FileManager.read_raw(self.parent_instance.in_directory + file_path)
            title_line = f"**{page_name.split('/')[-1]}**\n\n"
            
            start_idx = 0
            if raw_text.startswith('---\n'):
                first_marker_end = raw_text.find('\n', 4)
                if first_marker_end != -1:
                    second_marker_pos = raw_text.find('---\n', first_marker_end + 1)
                    if second_marker_pos != -1:
                        start_idx = second_marker_pos + 4

            content = raw_text[start_idx:]
            content = fix_table_spacing(content)
            return title_line + content.strip()
        except (IOError, IndexError):
            return None

class BlockReferenceProcessor(Treeprocessor):
    def __init__(self, md):
        super().__init__(md)
        self.block_ref_pattern = re.compile(r'\s*\^([a-zA-Z0-9]{6})\s*$')
    
    def run(self, root):
        def process_element(parent):
            i = 0
            while i < len(parent):
                elem = parent[i]
                
                if elem.tag == 'p':
                    text_content = self.get_full_text(elem)
                    
                    match = self.block_ref_pattern.search(text_content)
                    if match:
                        block_id = match.group(1)
                        
                        self.remove_block_reference(elem, match.group(0))

                        anchor_span = etree.Element('span')
                        anchor_span.set('class', 'anchor')
                        anchor_span.set('id', f'^{block_id}')
                        parent.insert(i, anchor_span)
                        i += 1
                
                elif elem.tag == 'table':
                    table_text = self.get_full_text(elem)
                    match = self.block_ref_pattern.search(table_text)
                    if match:
                        block_id = match.group(1)
                        
                        self.remove_block_reference(elem, match.group(0))
                        
                        anchor_span = etree.Element('span')
                        anchor_span.set('class', 'anchor')
                        anchor_span.set('id', f'^{block_id}')
                        parent.insert(i, anchor_span)
                        i += 1
                
                process_element(elem)
                i += 1
        
        process_element(root)
    
    def get_full_text(self, elem):
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
        if elem.text and block_ref_text in elem.text:
            elem.text = elem.text.replace(block_ref_text, '').rstrip()
            return
        
        for child in elem:
            if child.tail and block_ref_text in child.tail:
                child.tail = child.tail.replace(block_ref_text, '').rstrip()
                return
            
            self.remove_block_reference_from_child(child, block_ref_text)
    
    def remove_block_reference_from_child(self, elem, block_ref_text):
        if elem.text and block_ref_text in elem.text:
            elem.text = elem.text.replace(block_ref_text, '').rstrip()
            return
        
        for child in elem:
            if child.tail and block_ref_text in child.tail:
                child.tail = child.tail.replace(block_ref_text, '').rstrip()
                return
            self.remove_block_reference_from_child(child, block_ref_text)

class ImprovedLaTeXInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md):
        super().__init__(pattern, md)
        self.RE = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')
    
    def handleMatch(self, m, matcher):
        latex_content = m.group(1).strip()
        
        if not latex_content or len(latex_content) < 1:
            return None
        
        span = etree.Element('span')
        span.set('class', 'latex-inline')
        span.set('data-latex', latex_content)
        
        span.text = f'${latex_content}$'
        
        return span, m.start(0), m.end(0)

class ImprovedLaTeXBlockProcessor(BlockProcessor):
    def __init__(self, parser):
        super().__init__(parser)
        self.RE = re.compile(r'^\$\$(.*?)\$\$\s*$', re.MULTILINE | re.DOTALL)
    
    def test(self, parent, block):
        return bool(self.RE.search(block))
    
    def run(self, parent, blocks):
        block = blocks.pop(0)
        
        lines = block.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            start_match = re.match(r'^\$\$(.*)', line)
            if start_match:
                latex_content = start_match.group(1)
                
                end_match = re.search(r'(.*)\$\$$', latex_content)
                if end_match:
                    latex_content = end_match.group(1).strip()
                    self.create_latex_element(parent, latex_content)
                else:
                    latex_lines = [latex_content]
                    i += 1
                    
                    while i < len(lines):
                        line = lines[i]
                        end_match = re.search(r'(.*)\$\$$', line)
                        if end_match:
                            latex_lines.append(end_match.group(1))
                            break
                        else:
                            latex_lines.append(line)
                        i += 1
                    
                    latex_content = '\n'.join(latex_lines).strip()
                    self.create_latex_element(parent, latex_content)
            else:
                processed_lines.append(line)
            
            i += 1
        
        if processed_lines:
            remaining_content = '\n'.join(processed_lines).strip()
            if remaining_content:
                blocks.insert(0, remaining_content)
        
        return True
    
    def create_latex_element(self, parent, latex_content):
        div = etree.SubElement(parent, 'div')
        div.set('class', 'latex-display')
        div.set('data-latex', latex_content)
        div.text = f'$${latex_content}$$'

class ImprovedLaTeXExtension(Extension):
    def extendMarkdown(self, md):
        latex_block_processor = ImprovedLaTeXBlockProcessor(md.parser)
        md.parser.blockprocessors.register(latex_block_processor, 'latex_block', 75)
        
        latex_inline_processor = ImprovedLaTeXInlineProcessor(r'(?<!\$)\$([^$\n]+?)\$(?!\$)', md)
        md.inlinePatterns.register(latex_inline_processor, 'latex_inline', 175)
