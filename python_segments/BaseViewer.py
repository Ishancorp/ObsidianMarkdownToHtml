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
            prop_keys = data['properties'].keys()
            return_val = "|"
            for key in prop_keys:
                return_val += data['properties'][key]['displayName'] + '|'
            return_val += f"\n|{"----|" * len(prop_keys)}\n"
            filtered_links = {}
            for link in self.link_to_filepath:
                include = True
                for filter in data['views'][0]['filters']['and']:
                    include = include and self._evaluate_filter(filter, link)
                if include:
                    filtered_links[link] = self.link_to_filepath[link]
            for link in filtered_links:
                return_val += "|"
                for key in data['properties']:
                    return_val += self._add_val(link, offset, key) + "|"
                return_val += '\n'
            return return_val
        except Exception as e:
            return f'<div class="error">Error processing base data: {self._escape_html(str(e))}</div>'
    
    def _add_val(self, link, offset, prop):
        if prop == 'file.name':
            return f"<a href=\"{'../' * offset}{(self.link_to_filepath)[link].replace(" ", "-").lower()}\">{link}</a>"
        elif prop[:5] == 'file.':
            return self.file_properties[self.file_content_map[link]][prop[5:]]
        return ""
    
    def _evaluate_filter(self, filter, link):
        if link not in self.file_content_map:
            return False
        pre, post = filter.split(" == ")
        if self.file_content_map[link] not in self.file_properties:
            return False
        elif not self.file_properties[self.file_content_map[link]]:
            return False
        elif not self.file_properties[self.file_content_map[link]][pre.split(".")[-1]]:
            return False
        elif self.file_properties[self.file_content_map[link]][pre.split(".")[-1]] != post[1:-1]:
            return False
        return True
    
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
