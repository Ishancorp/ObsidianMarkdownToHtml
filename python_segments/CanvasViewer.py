import json
from python_segments.helpers import *

class CanvasViewer:
    def __init__(self, markdown_processor=None, custom_renderer=None, in_directory=None, out_directory=None):
        self.markdown_processor = markdown_processor
        self.custom_renderer = custom_renderer  # Function: (text, offset) -> HTML
        self.canvas_bar = self._load_canvas_bar()
        self.CANVAS_OFFSET_X = 750
        self.CANVAS_OFFSET_Y = 400
        self.MIN_NODE_WIDTH = 50
        self.MIN_NODE_HEIGHT = 30
        self.DEFAULT_NODE_WIDTH = 200
        self.DEFAULT_NODE_HEIGHT = 100
        self.MIN_CANVAS_WIDTH = 1500
        self.MIN_CANVAS_HEIGHT = 1000
        self.CANVAS_PADDING = 1000
        self.VALID_SIDES = {"left", "right", "top", "bottom"}
        self.in_directory = in_directory
        self.out_directory = out_directory

    def _load_canvas_bar(self):
        try:
            with open("svg/canvas_bar.html", encoding='utf-8') as canv_bar:
                return " " + canv_bar.read()
        except:
            return ""

    def canvas_viewer(self, file, offset):
        try:
            file_dir = self.in_directory + file[1:]
            data = self._load_json_file(file_dir)
            if isinstance(data, str):
                return data
            nodes_data = self._validate_and_extract_nodes(data)
            edges_data = self._validate_and_extract_edges(data)
            if isinstance(nodes_data, str):
                return nodes_data
            if isinstance(edges_data, str):
                return edges_data
            nodes_by_id, div_part, max_x, max_y = self._process_nodes(nodes_data, offset)
            svg_part, arrow_part = self._process_edges(edges_data, nodes_by_id, max_x, max_y)
            return self._build_final_html(div_part, svg_part, arrow_part)
        except Exception as e:
            return f'<div class="error">Error processing canvas data: {self._escape_html(str(e))}</div>'

    def _load_json_file(self, file_name):
        try:
            with open(file_name, encoding='utf-8') as json_file:
                data = json.load(json_file)
            if not isinstance(data, dict):
                return '<div class="error">Invalid canvas data: Expected dictionary</div>'
            return data
        except FileNotFoundError:
            return f'<div class="error">File not found: {self._escape_html(file_name)}</div>'
        except json.JSONDecodeError as e:
            return f'<div class="error">Invalid JSON format: {self._escape_html(str(e))}</div>'
        except Exception as e:
            return f'<div class="error">Error loading file: {self._escape_html(str(e))}</div>'

    def _validate_and_extract_nodes(self, data):
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            return '<div class="error">Invalid canvas data: \'nodes\' must be a list</div>'
        return nodes

    def _validate_and_extract_edges(self, data):
        edges = data.get("edges", [])
        if not isinstance(edges, list):
            return '<div class="error">Invalid canvas data: \'edges\' must be a list</div>'
        return edges

    def _process_nodes(self, nodes, offset):
        nodes_by_id = {}
        div_part = ""
        max_x = 0
        max_y = 0
        for i, node in enumerate(nodes):
            try:
                node_data = self._process_single_node(node, i, offset)
                if node_data is None:
                    continue
                node_id, html_content, position_data, node_max_x, node_max_y = node_data
                nodes_by_id[node_id] = position_data
                div_part += html_content
                max_x = max(max_x, node_max_x)
                max_y = max(max_y, node_max_y)
            except:
                continue
        return nodes_by_id, div_part, max_x, max_y

    def _process_single_node(self, node, index, offset):
        if not isinstance(node, dict):
            return None
        node_id = node.get("id")
        if not node_id:
            return None
        x = self._safe_float(node.get("x", 0))
        y = self._safe_float(node.get("y", 0))
        width = max(self._safe_float(node.get("width", self.DEFAULT_NODE_WIDTH)), self.MIN_NODE_WIDTH)
        height = max(self._safe_float(node.get("height", self.DEFAULT_NODE_HEIGHT)), self.MIN_NODE_HEIGHT)
        text = str(node.get("text", ""))
        color = node.get("color", "")
        div_classes = self._generate_node_classes(color)
        left_pos = x + self.CANVAS_OFFSET_X
        top_pos = y + self.CANVAS_OFFSET_Y
        html_content = self._build_node_html(node_id, div_classes, left_pos, top_pos, width, height, text, offset)
        position_data = {
            "left": (x, y + height/2),
            "right": (x + width, y + height/2),
            "top": (x + width/2, y),
            "bottom": (x + width/2, y + height),
        }
        return node_id, html_content, position_data, x + width, y + height

    def _safe_float(self, value) -> float:
        try:
            return float(value)
        except:
            return 0.0

    def _generate_node_classes(self, color):
        div_classes = ["general-boxes"]
        if color and isinstance(color, str):
            sanitized_color = ''.join(c for c in color if c.isalnum() or c in ['-', '_'])
            if sanitized_color:
                div_classes.append(f"color-{sanitized_color}")
        return div_classes

    def _build_node_html(self, node_id, div_classes, left_pos, top_pos, width, height, text, offset):
        html_content = (
            f'<div class="{" ".join(div_classes)}" '
            f'id="{self._escape_html(str(node_id))}" '
            f'style="left:{left_pos}px;top:{top_pos}px;width:{width}px;height:{height}px">\n'
        )
        if text:
            try:
                if self.custom_renderer:
                    processed_content = self.custom_renderer(text, offset)
                    html_content += processed_content
                elif self.markdown_processor:
                    processed_content = self.markdown_processor.process_markdown(text, offset, add_to_header_list=False)
                    html_content += processed_content
                else:
                    html_content += self._escape_html(text)
            except:
                html_content += self._escape_html(text)
        html_content += "\n</div>\n"
        return html_content

    def _process_edges(self, edges, nodes_by_id, max_x, max_y):
        svg_width = max(max_x + self.CANVAS_PADDING, self.MIN_CANVAS_WIDTH)
        svg_height = max(max_y + self.CANVAS_PADDING, self.MIN_CANVAS_HEIGHT)
        svg_part = f'<svg id="svg" width="{svg_width}" height="{svg_height}">\n'
        arrow_part = ""
        for i, edge in enumerate(edges):
            try:
                edge_data = self._process_single_edge(edge, i, nodes_by_id)
                if edge_data is None:
                    continue
                line_html, arrow_html = edge_data
                svg_part += line_html
                arrow_part += arrow_html
            except:
                continue
        svg_part += "</svg>\n"
        return svg_part, arrow_part

    def _process_single_edge(self, edge, index, nodes_by_id):
        if not isinstance(edge, dict):
            return None
        from_node = edge.get("fromNode")
        to_node = edge.get("toNode")
        from_side = self._validate_side(edge.get("fromSide", "right"), "right", index, "fromSide")
        to_side = self._validate_side(edge.get("toSide", "left"), "left", index, "toSide")
        if not from_node or not to_node or from_node not in nodes_by_id or to_node not in nodes_by_id:
            return None
        node_from = nodes_by_id[from_node]
        node_to = nodes_by_id[to_node]
        x1 = node_from[from_side][0] + self.CANVAS_OFFSET_X
        y1 = node_from[from_side][1] + self.CANVAS_OFFSET_Y
        x2 = node_to[to_side][0] + self.CANVAS_OFFSET_X
        y2 = node_to[to_side][1] + self.CANVAS_OFFSET_Y
        line_html = f'<line class="line" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>\n'
        arrow_html = self._generate_arrow_html(to_side, x2, y2)
        return line_html, arrow_html

    def _validate_side(self, side, default, edge_index, side_name):
        return side if side in self.VALID_SIDES else default

    def _generate_arrow_html(self, to_side, arrow_x, arrow_y):
        if to_side == "left":
            return f'<i class="arrow {to_side}" style="left:{arrow_x - 10}px;top:{arrow_y - 5}px;"></i>\n'
        return f'<i class="arrow {to_side}" style="left:{arrow_x - 5}px;top:{arrow_y - 10}px;"></i>\n'

    def _build_final_html(self, div_part, svg_part, arrow_part):
        return (
            "<div id=\"outer-box\">\n"
            "<div id=\"scrollable-box\">\n"
            "<div id=\"innard\">"
            f"{arrow_part}{svg_part}{div_part}"
            "</div>\n"
            "</div>\n"
            f"{self.canvas_bar}"
            "</div>\n"
        )

    def _escape_html(self, text):
        if not isinstance(text, str):
            text = str(text)
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))
