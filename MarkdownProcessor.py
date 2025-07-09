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
    def handleMatch(self, m, data):
        link_text = m.group(1).strip()

        el = etree.Element('a')
        el.set('href', f'/notes/{link_text.replace(" ", "_")}')
        el.set('class', 'wikilink')
        el.text = link_text
        return el, m.start(0), m.end(0)
