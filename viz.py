    #!/bin/python3

import sys
import yaml
import logging
from uuid import uuid4 as uuid
import re

# instantiate logging
log = logging.getLogger()
ch = logging.StreamHandler()
fm = logging.Formatter('%(name)s %(levelname)s: %(message)s')
ch.setFormatter(fm)
log.addHandler(ch)
log.setLevel(logging.DEBUG)

class Builder:
    def __init__(self, filename='viz.yml'):
        # read settings
        with open(filename, encoding='utf-8') as settings_file:
            self.specs = yaml.load(settings_file.read())

        self.nodes = []

        self.log = logging.getLogger('Builder')
        self.log.setLevel(logging.DEBUG)
        self.log.debug('object {} created'.format(self))

    def get_nodes(self, filename):
        parser = Parser(filename)

        for i in self.specs:
            self.nodes += parser.get_nodes(i)
        self.log.debug('parsed {} nodes total'.format(len(self.nodes)))

    def get_links(self):
        for n, i in enumerate(self.nodes):
            left = self.nodes[n+1:]
            for j in left:
                if i.check_connection(j): self.log.debug('found link from {} to {}'.format(i, j))
                if j.check_connection(i): self.log.debug('found link from {} to {}'.format(j, i))

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

        self.log = logging.getLogger('Parser')
        self.log.setLevel(logging.DEBUG)
        self.log.debug('object {} created'.format(self))

    def get_nodes(self, node_spec):
        pattern = '^' + node_spec.replace('{{name}}', '(?P<name>[-\w]+)').replace('{%...%}', ' ?.*$')
        self.log.debug('got "{}" node_spec, using "{}" regex pattern'.format(node_spec, pattern))
        regex = re.compile(pattern)
        nodes = []

        conf_pos = 0
        conf_end = len(self.config) - 1

        while conf_pos <= conf_end:
            self.log.debug('looking for block from {} position'.format(conf_pos))
            block_name = ''
            block_pos = 0
            started = False

            for num, line in enumerate(self.config[conf_pos:]):
                match_obj = regex.search(line)
                if not started:
                    if match_obj:
                        block_name = match_obj.group('name')
                        block_pos = conf_pos + num
                        started = True
                        self.log.debug('found block start at {}: "{}", block_name: {}'.format(conf_pos + num, line, block_name))
                    elif conf_pos + num == conf_end:
                        self.log.debug('end of file'.format(conf_pos))
                        conf_pos = conf_pos + num + 1
                        break

                else:
                    if match_obj and block_name != match_obj.group('name'):
                        conf_pos += num
                        self.log.debug('found block end at {}: "{}", block_name mismatch'.format(conf_pos, line))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        break
                    elif not match_obj and not line.startswith(' '):
                        conf_pos += num
                        self.log.debug('found block end at {}: "{}", line without space'.format(conf_pos, line))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        break
                    elif conf_pos + num == conf_end:
                        conf_pos += num
                        self.log.debug('found block end at {}: "{}", end of file'.format(conf_pos, line))
                        nodes.append(ConfigNode(block_name, self.config[block_pos:conf_pos]))
                        conf_pos += 1
                        break
        self.log.debug('sending {} nodes'.format(len(nodes)))
        return nodes


class ConfigNode:
    def __init__(self, name, text):
        self.id = uuid()
        self.text = text
        self.name = name
        self.header = text[0]
        self.type = self.header[:self.header.find(self.name)].strip()
        self.links = []

        self.log = logging.getLogger('ConfigNode')
        self.log.setLevel(logging.DEBUG)
        self.log.debug('object {} created'.format(self))

    def __repr__(self):
        return '<ConfigNode type: "{}" name: "{}">'.format(self.type, self.name)

    def check_connection(self, other):
        found_link = False
        if self.type != other.type:
            for line in other.text:
                for word in line.split(' '):
                    if self.name == word:
                        found_link = True
                        if self.id not in other.links:
                            other.links.append(self.id)
        return found_link


if __name__ == '__main__':
    viz = Builder()
    viz.get_nodes('config.txt')
    viz.get_links()
    print(str(viz.build_tree()))    # create graphml object, vizualize it
    viz.export_tree()               # save graphml to file
