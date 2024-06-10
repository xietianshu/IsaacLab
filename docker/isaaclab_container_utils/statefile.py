import yaml

def load_yaml_file(statefile):
    if statefile.exists():
        with open(statefile, 'r') as file:
            return yaml.safe_load(file) or {}
    else:
        statefile.touch()
        return {}

def save_yaml_file(statefile, data):
    with open(statefile, 'w') as file:
        yaml.safe_dump(data, file)

class Statefile(object):
    def __init__(self, statefile):
        self.statefile = statefile

    def set_variable(self, key, value):
        data = load_yaml_file(self.statefile)
        data[key] = value
        save_yaml_file(self.statefile, data)

    def load_variable(self, key):
        data = load_yaml_file(self.statefile)
        return data.get(key, "null")

    def delete_variable(self, key):
        data = load_yaml_file(self.statefile)
        if key in data:
            del data[key]
        save_yaml_file(self.statefile, data)