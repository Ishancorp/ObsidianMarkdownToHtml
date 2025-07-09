from markdown.blockprocessors import BlockProcessor
import xml.etree.ElementTree as etree
from markdown.inlinepatterns import InlineProcessor
import re

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
