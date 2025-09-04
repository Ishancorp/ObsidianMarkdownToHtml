import yaml

class BaseViewer:
    def __init__(self, link_to_filepath=None, file_properties=None, file_content_map=None, in_directory=None, out_directory=None):
        self.link_to_filepath = link_to_filepath
        self.file_properties = file_properties
        self.file_content_map = file_content_map
        self.in_directory = in_directory
        self.out_directory = out_directory
    
    def base_viewer(self, file, offset):
        try:
            file_dir = self.in_directory + file[1:]
            data = self._load_yaml_file(file_dir)
            if isinstance(data, str):
                return data
            if data['views'][0]['type'] == "table":
                return self.table_viewer(offset, data)
            elif data['views'][0]['type'] == "cards":
                return self.cards_viewer(offset, data)
        except Exception as e:
            return f'<div class="error">Error processing base data: {self._escape_html(str(e))}</div>'
    
    def table_viewer(self, offset, data):
        try:
            props = self._get_props(data)
            return_val = "|"
            for key in props:
                return_val += props[key] + '|'
            return_val += f"\n|{"----|" * len(props)}\n"
            filtered_links = {}
            for link in self.link_to_filepath:
                include = True
                if 'filters' in data['views'][0]:
                    for filter in data['views'][0]['filters']['and']:
                        include = include and self._evaluate_filter(filter, link)
                if include:
                    filtered_links[link] = self.link_to_filepath[link]
            filtered_links = self._sort_links(data, filtered_links)
            for link in filtered_links:
                return_val += "|"
                for key in props:
                    return_val += self._add_val(link, offset, key) + "|"
                return_val += '\n'
            return return_val
        except Exception as e:
            return f'<div class="error">Error processing table data: {self._escape_html(str(e))}</div>'
    
    def cards_viewer(self, offset, data):
        try:
            # Get the view configuration
            view_config = data['views'][0]
            props = self._get_props(data)
            
            # Filter links based on the view filters
            filtered_links = {}
            for link in self.link_to_filepath:
                include = True
                if 'filters' in view_config:
                    for filter_condition in view_config['filters']['and']:
                        include = include and self._evaluate_filter(filter_condition, link)
                if include:
                    filtered_links[link] = self.link_to_filepath[link]
            
            filtered_links = self._sort_links(data, filtered_links)
            # Start building the cards HTML
            cards_html = '<div class="cards-container">\n'
            
            for link in filtered_links:
                file_link = f"{'../' * offset}{self.link_to_filepath[link].replace(' ', '-').lower()}"
                cards_html += f'  <div class="card" data-href={file_link}>\n'
                
                # Add card content
                cards_html += '    <div class="card-content">\n'
                
                # Add image if specified
                if 'image' in view_config and view_config['image']:
                    image_prop = view_config['image']
                    image_url = self._add_val(link, offset, image_prop)
                    if image_url:
                        image_url = image_url
                        image_fit = view_config.get('imageFit', 'cover')
                        cards_html += f'    <div class="card-image" style="object-fit: {image_fit};">\n'
                        cards_html += f'      <img src="{self._escape_html(image_url)}" alt="{self._escape_html(link)}" style="object-fit: {image_fit};" />\n'
                        cards_html += '    </div>\n'
                    else:
                        cards_html += '    <div class="card-image card-image-placeholder"></div>\n'
                
                # Add title (using file name as default)
                cards_html += f'      <h3 class="card-title"><a href="{file_link}">{self._escape_html(link)}</a></h3>\n'
                
                # Add other properties
                for prop_key in props:
                    if prop_key != 'file.name':  # Skip file name since we already used it as title
                        prop_display_name = props[prop_key]
                        prop_value = self._add_val(link, offset, prop_key)
                        if prop_value:
                            cards_html += f'      <div class="card-property">\n'
                            cards_html += f'        <span class="property-label">{self._escape_html(prop_display_name)}:</span>\n'
                            cards_html += f'        <span class="property-value">{self._escape_html(prop_value)}</span>\n'
                            cards_html += f'      </div>\n'
                
                cards_html += '    </div>\n'
                cards_html += '  </div>\n'
            
            cards_html += '</div>\n'
            return cards_html
        except Exception as e:
            return f'<div class="error">Error processing card data: {self._escape_html(str(e))}</div>'
    
    def _sort_links(self, data, links):
        if 'sort' in data['views'][0]:
            for sortation in data['views'][0]['sort'][::-1]:
                def key(link):
                    if sortation['property'] == 'file.basename':
                        return self.file_properties[self.file_content_map[link]]['file']
                    return None  # fallback if needed
                links = sorted(links, key=key, reverse=(sortation['direction'] != "ASC"))
        return links
    
    def _add_val(self, link, offset, prop):
        if prop == 'file.name':
            return f"<a href=\"{'../' * offset}{(self.link_to_filepath)[link].replace(" ", "-").lower()}\">{link}</a>"
        elif prop[:5] == 'file.':
            return self.file_properties[self.file_content_map[link]][prop[5:]]
        elif prop[:5] == 'note.':
            if "notes" in self.file_properties[self.file_content_map[link]] and prop[5:] in self.file_properties[self.file_content_map[link]]["notes"]:
                return f"{'../' * offset}{(self.link_to_filepath)[self.file_properties[self.file_content_map[link]]["notes"][prop[5:]][3:-3]].replace(" ", "-").lower()}"
            else:
                return ""
        return self.file_properties[self.file_content_map[link]]["notes"][prop]
    
    def _evaluate_filter(self, filter, link):
        if link not in self.file_content_map:
            return False
        if " == " in filter:
            pre, post = filter.split(" == ")
            if self.file_content_map[link] not in self.file_properties:
                return False
            elif not self.file_properties[self.file_content_map[link]]:
                return False
            elif pre.split(".")[-1] not in self.file_properties[self.file_content_map[link]]:
                return True
            elif not self.file_properties[self.file_content_map[link]][pre.split(".")[-1]]:
                return False
            elif self.file_properties[self.file_content_map[link]][pre.split(".")[-1]] != post[1:-1]:
                return False
        elif " != " in filter:
            pre, post = filter.split(" != ")
            if self.file_content_map[link] not in self.file_properties:
                return False
            elif not self.file_properties[self.file_content_map[link]]:
                return False
            if "." in pre:
                if pre.split(".")[-1] not in self.file_properties[self.file_content_map[link]]:
                    return True
                elif not self.file_properties[self.file_content_map[link]][pre.split(".")[-1]]:
                    return False
                elif self.file_properties[self.file_content_map[link]][pre.split(".")[-1]] == post:
                    return False
            else:
                if 'notes' not in self.file_properties[self.file_content_map[link]]:
                    return True
                elif pre not in self.file_properties[self.file_content_map[link]]['notes']:
                    return True
                elif not self.file_properties[self.file_content_map[link]]['notes'][pre]:
                    return False
                elif self.file_properties[self.file_content_map[link]]['notes'][pre] == post:
                    return False
        elif ".startsWith(" in filter:
            pre, post = filter.split(".startsWith(")
            left = ""
            right = post[1:-2]
            if pre == "file.path":
                left = self.file_properties[self.file_content_map[link]]["path"][1:]
                return left.startswith(right)
        return True
    
    def _get_props(self, data):
        if 'properties' in data:
            props = data['properties']
            for key in props:
                props[key] = props[key]['displayName']
            return props
        else:
            return {}
    
    def _load_yaml_file(self, file_name):
        try:
            with open(file_name, encoding='utf-8') as yaml_file:
                data = yaml.load(yaml_file, Loader=yaml.FullLoader)
            if not isinstance(data, dict):
                return '<div class="error">Invalid base data: Expected dictionary</div>'
            return data
        except FileNotFoundError:
            return f'<div class="error">File not found: {self._escape_html(file_name)}</div>'
        except yaml.YAMLError as e:
            return f'<div class="error">Invalid YAML format: {self._escape_html(str(e))}</div>'
        except Exception as e:
            return f'<div class="error">Error loading file: {self._escape_html(str(e))}</div>'

    def _escape_html(self, text):
        if not isinstance(text, str):
            text = str(text)
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))
