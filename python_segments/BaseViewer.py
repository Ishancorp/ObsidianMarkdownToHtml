import yaml

class BaseViewer:
    def __init__(self, link_to_filepath=None, in_directory=None, out_directory=None):
        self.link_to_filepath = link_to_filepath
        self.in_directory = in_directory
        self.out_directory = out_directory
    
    def base_viewer(self, file, offset):
        try:
            file_dir = self.in_directory + file[1:]
            data = self._load_yaml_file(file_dir)
            if isinstance(data, str):
                return data
            return_val = ""
            for link in self.link_to_filepath:
                return_val += f"- {link} -- /{'../' * offset}{(self.link_to_filepath)[link]}\n"
            return return_val
        except Exception as e:
            return f'<div class="error">Error processing base data: {self._escape_html(str(e))}</div>'
    
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
