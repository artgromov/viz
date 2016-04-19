    #!/bin/python3

import sys
import yaml
import logging
from uuid import uuid4 as uuid
import re

# instantiate logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


class Builder:
    def __init__(self, filename='viz.yml'):
        # read settings
        with open(filename, encoding='utf-8') as settings_file:
            self.specs = yaml.load(settings_file.read())

        self.nodes = []

    def get_nodes(self, filename):
        parser = Parser(filename)

        for i in self.specs:
            self.nodes += parser.get_nodes(i)

    def get_links(self):
        for n, i in enumerate(self.nodes):
            left = self.nodes[n+1:]
            for j in left:
                i.check_connection(j)
                j.check_connection(i)

    def build_tree(self):
        return {i: i.links for i in self.nodes}

    def export_tree(self):
        pass


class Parser:
    def __init__(self, filename):
        with open(filename, encoding='utf-8') as config_file:
            config = config_file.readlines()

        self.config = []
        for line in config:
            if not line.startswith('!') or not line.startswith(':') or not line.strip() == '':
                self.config.append(line.rstrip())

        logging.debug('Created object {}'.format(self))

    def get_nodes(self, node_spec):
        pattern = '^' + node_spec.replace('{{name}}', '(?P<name>[-\w]+)').replace('{%...%}', ' ?.*$')
        logging.debug('Parser: using {} regex pattern'.format(pattern))
        regex = re.compile(pattern)
        nodes = []

        conf_pos = 0
        conf_end = len(self.config) - 1

        while conf_pos <= conf_end:
            #logging.debug('Parser: looking for block from {} position'.format(conf_pos))
            block_name = ''
            block_pos = 0
            started = False

            for num, line in enumerate(self.config[conf_pos:]):
                #logging.debug('Parser: parsing line {}: "{}"'.format(conf_pos + num, line))
                match_obj = regex.search(line)
                if not started:
                    if match_obj:
                        block_name = match_obj.group('name')
                        block_pos = conf_pos + num
                        started = True
                        #logging.debug('Parser: found block start at {} position, block_name: {}'.format(conf_pos + num, block_name))
                    elif conf_pos + num == conf_end:
                        #logging.debug('Parser: end of file'.format(conf_pos))
                        conf_pos = conf_pos + num + 1
                        break

                else:
                    if match_obj and block_name != match_obj.group('name'):
                        conf_pos += num
                        #logging.debug('Parser: found block end at {} position, block_name mismatch'.format(conf_pos))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        break
                    elif not match_obj and not line.startswith(' '):
                        conf_pos += num
                        #logging.debug('Parser: found block end at {} position, line without space'.format(conf_pos))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        break
                    elif conf_pos + num == conf_end:
                        conf_pos += num
                        #logging.debug('Parser: found block end at {} position, end of file'.format(conf_pos))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        conf_pos += 1
                        break
        return nodes


class ConfigNode:
    def __init__(self, name, text):
        self.id = uuid()
        self.text = text
        self.name = name
        self.type = ''
        self.links = []
        logging.debug('Created object {}'.format(self))

    def __repr__(self):
        return '<ConfigNode, type: {} name: {}>'.format(self.type, self.name)

    def check_connection(self, other):
        found_link = False
        for line in other.text:
            for word in line.split(' '):
                if self.name == word:
                    found_link = True
        if found_link:
            if self.id not in other.links:
                other.links.append(self.id)


if __name__ == '__main__':
    viz = Builder()
    viz.get_nodes('config.txt')
    viz.get_links()
    print(str(viz.build_tree()))    # create graphml object, vizualize it
    viz.export_tree()               # save graphml to file
