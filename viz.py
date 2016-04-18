    #!/bin/python3

import sys
import yaml
import logging
from uuid import uuid4 as uuid
import re

# instantiate logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


class debug:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        logging.debug('Call ' + self.func.__name__)
        self.func(self, *args, **kwargs)
        logging.debug('Exit ' + self.func.__name__)

class Builder:
    @debug
    def __init__(self, filename='viz.yml'):
        # read settings
        with open(filename, encoding='utf-8') as settings_file:
            settings = yaml.load(settings_file.read())
            for k, v in settings.items():
                self.__setattr__(k, v)

    @debug
    def get_nodes(self):

        self.config_file = ''
        self.nodes = []

    @debug
    def get_links(self):
        pass

    @debug
    def build_tree(self):
        pass

    @debug
    def export_tree(self):
        pass



class Parser:
    def __init__(self, blockname, blockrules):
        pass

class ConfigNode:
    def __init__(self):
        self.id = uuid()

if __name__ == '__main__':
    viz = Builder()
    viz.get_nodes()
    viz.get_links()
    viz.build_tree()
    viz.export_tree()

    testnode = ConfigNode()
    print(testnode.id)