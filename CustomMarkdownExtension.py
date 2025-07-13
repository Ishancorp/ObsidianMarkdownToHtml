from MarkdownProcessor import *
from markdown.extensions import Extension
from helpers import *
from JSONViewer import *;

class CustomMarkdownExtension(Extension):
    def __init__(self, link_dict, offset, parent_instance, add_to_header_list=True, **kwargs):
        self.link_dict = link_dict
        self.offset = offset
        self.parent_instance = parent_instance
        self.add_to_header_list = add_to_header_list
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        md.parser.blockprocessors.deregister('code')
        md.treeprocessors.register(AnchorSpanTreeProcessor(md, self.parent_instance, self.add_to_header_list), 'anchor_span', 15)
        md.treeprocessors.register(BlockReferenceProcessor(md), 'block_reference', 12)
        md.parser.blockprocessors.register(IndentedParagraphProcessor(md.parser), 'indent_paragraph', 75)
        
        # Regular wiki links
        WIKILINK_RE = r'\[\[([^\]]+)\]\]'
        md.inlinePatterns.register(WikiLinkInlineProcessor(WIKILINK_RE, md, self.link_dict, self.offset), 'wikilink', 175)
        
        # Transclusion links - register with higher priority than wiki links
        TRANSCLUSION_RE = r'!\[\[([^\]]+)\]\]'
        md.inlinePatterns.register(TransclusionInlineProcessor(TRANSCLUSION_RE, md, self.parent_instance), 'transclusion', 180)
