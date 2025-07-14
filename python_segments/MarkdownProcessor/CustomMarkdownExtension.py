from python_segments.MarkdownProcessor.MarkdownExtensions import AnchorSpanTreeProcessor, BlockReferenceProcessor, IndentedParagraphProcessor, WikiLinkInlineProcessor, TransclusionInlineProcessor
from markdown.extensions import Extension
from python_segments.helpers import *
from python_segments.JSONViewer import *;

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
        
        WIKILINK_RE = r'\[\[([^\]]+)\]\]'
        md.inlinePatterns.register(WikiLinkInlineProcessor(WIKILINK_RE, md, self.link_dict, self.offset), 'wikilink', 175)
        
        TRANSCLUSION_RE = r'!\[\[([^\]]+)\]\]'
        md.inlinePatterns.register(TransclusionInlineProcessor(TRANSCLUSION_RE, md, self.parent_instance), 'transclusion', 180)
