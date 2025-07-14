import json
from python_segments.MarkdownProcessor import *
from python_segments.helpers import *

class JSONViewer:
    def __init__(self, parent_instance):
        self.parent_instance = parent_instance
        with open("svg/canvas_bar.html", encoding='utf-8') as canv_bar: self.canvas_bar = " " + canv_bar.read()

    def json_viewer(self, file_name):
        with open(file_name, encoding='utf-8') as json_data:
            data = json.load(json_data)
        nodes_by_id = {}
        max_x = 0
        max_y = 0
        div_part = ""
        arrow_part = ""
        
        if not isinstance(data, dict):
            return "<div class=\"error\">Invalid canvas data: Expected dictionary</div>"
        
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        if not isinstance(nodes, list):
            return "<div class=\"error\">Invalid canvas data: 'nodes' must be a list</div>"
        
        if not isinstance(edges, list):
            return "<div class=\"error\">Invalid canvas data: 'edges' must be a list</div>"
        
        for i, node in enumerate(nodes):
            try:
                if not isinstance(node, dict):
                    print(f"Warning: Node {i} is not a dictionary, skipping")
                    continue
                    
                node_id = node.get("id")
                if not node_id:
                    print(f"Warning: Node {i} missing 'id', skipping")
                    continue
                    
                x = float(node.get("x", 0))
                y = float(node.get("y", 0))
                width = max(float(node.get("width", 200)), 50)  # Minimum width
                height = max(float(node.get("height", 100)), 30)  # Minimum height
                text = str(node.get("text", ""))
                color = node.get("color", "")
                
                div_classes = ["general-boxes"]
                if color and isinstance(color, str):
                    sanitized_color = ''.join(c for c in color if c.isalnum() or c in ['-', '_'])
                    if sanitized_color:
                        div_classes.append(f"color-{sanitized_color}")
                
                left_pos = x + 750
                top_pos = y + 400
                
                div_part += (
                    f'<div class="{" ".join(div_classes)}" '
                    f'id="{self._escape_html(str(node_id))}" '
                    f'style="left:{left_pos}px;top:{top_pos}px;width:{width}px;height:{height}px">\n'
                )
                
                if text:
                    try:
                        processed_content = self.parent_instance.process_markdown(text, add_to_header_list=False)
                        div_part += processed_content
                    except Exception as e:
                        print(f"Warning: Error processing text for node {node_id}: {e}")
                        div_part += self._escape_html(text)
                
                nodes_by_id[node_id] = {
                    "left": (x, y + height/2),
                    "right": (x + width, y + height/2),
                    "top": (x + width/2, y),
                    "bottom": (x + width/2, y + height),
                }
                
                max_x = max(max_x, x + width)
                max_y = max(max_y, y + height)
                
                div_part += "\n</div>\n"
                
            except (ValueError, TypeError) as e:
                print(f"Warning: Error processing node {i}: {e}")
                continue
        
        svg_width = max(max_x + 1000, 1500)
        svg_height = max(max_y + 1000, 1000)
        
        svg_part = f'<svg id="svg" width="{svg_width}" height="{svg_height}">\n'
        
        valid_sides = {"left", "right", "top", "bottom"}
        
        for i, edge in enumerate(edges):
            try:
                if not isinstance(edge, dict):
                    print(f"Warning: Edge {i} is not a dictionary, skipping")
                    continue
                    
                from_node = edge.get("fromNode")
                to_node = edge.get("toNode")
                from_side = edge.get("fromSide", "right")
                to_side = edge.get("toSide", "left")
                
                if not from_node or not to_node:
                    print(f"Warning: Edge {i} missing node references, skipping")
                    continue
                    
                if from_node not in nodes_by_id or to_node not in nodes_by_id:
                    print(f"Warning: Edge {i} references non-existent nodes, skipping")
                    continue
                    
                if from_side not in valid_sides:
                    print(f"Warning: Edge {i} has invalid fromSide '{from_side}', using 'right'")
                    from_side = "right"
                    
                if to_side not in valid_sides:
                    print(f"Warning: Edge {i} has invalid toSide '{to_side}', using 'left'")
                    to_side = "left"
                
                node_from = nodes_by_id[from_node]
                node_to = nodes_by_id[to_node]
                
                x1 = node_from[from_side][0] + 750
                y1 = node_from[from_side][1] + 400
                x2 = node_to[to_side][0] + 750
                y2 = node_to[to_side][1] + 400
                
                svg_part += (
                    f'<line class="line" '
                    f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>\n'
                )
                
                arrow_x = node_to[to_side][0] + 750
                arrow_y = node_to[to_side][1] + 400
                
                if to_side == "left":
                    arrow_part += (
                        f'<i class="arrow {to_side}" '
                        f'style="left:{arrow_x - 10}px;top:{arrow_y - 5}px;"></i>\n'
                    )
                else:
                    arrow_part += (
                        f'<i class="arrow {to_side}" '
                        f'style="left:{arrow_x - 5}px;top:{arrow_y - 10}px;"></i>\n'
                    )
                    
            except (KeyError, TypeError) as e:
                print(f"Warning: Error processing edge {i}: {e}")
                continue
        
        svg_part += "</svg>\n"
        
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
        """Helper method to escape HTML characters"""
        if not isinstance(text, str):
            text = str(text)
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))