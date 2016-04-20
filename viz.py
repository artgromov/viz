    #!/bin/python3

import sys
import logging
import yaml
import re
from uuid import uuid4
import jinja2
import blockdiag.parser
import blockdiag.builder
import blockdiag.drawer

# constants
SETTINGS_FILE = 'viz.yml'
TEMPLATE_FILE = 'viz.j2'

# instantiate logging
log = logging.getLogger()
ch = logging.StreamHandler()
fm = logging.Formatter('%(name)s %(levelname)s: %(message)s')
ch.setFormatter(fm)
log.addHandler(ch)
log.setLevel(logging.DEBUG)


class Driver:
    def __init__(self):
        # read settings
        self.log = logging.getLogger('Driver')
        self.log.debug('object {} created'.format(self))
        
        self.log.info('reading settings file "{}"'.format(SETTINGS_FILE))
        with open(SETTINGS_FILE, encoding='utf-8') as settings_file:
            self.settings = yaml.load(settings_file.read())

        self.nodes = []

    def parse_nodes(self, filename):
        self.log.info('parsing config for nodes')
        parser = Parser(filename)
        for i in self.settings['node_specs']:
            self.nodes += parser.get_nodes(i)
        self.log.debug('parsed {} nodes'.format(len(self.nodes)))

    def get_node_by_id(self, id):
        for node in self.nodes:
            if node.id == id:
                return node

    def collect_links(self):
        self.log.info('collecting links between objects')
        for n, i in enumerate(self.nodes):
            left = self.nodes[n+1:]
            for j in left:
                if i.check_connection(j): self.log.debug('found link from {:40} to {:40}'.format(i, j))
                if j.check_connection(i): self.log.debug('found link from {:40} to {:40}'.format(j, i))

    def build_diag(self,filename='viz.png', filetype='PNG'):
        self.log.info('collecting diagram config data')
        config = settings['blockdiag']
        config['nodes'] = [i.get_diag_config for i in self.nodes]
        self.log.debug('config collected from {} nodes'.format(len(self.nodes)))

        self.log.info('rendering jinja template from file "{}"'.format(TEMPLATE_FILE))
        env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.FileSystemLoader('./'))
        template = env.get_template(TEMPLATE_FILE)
        source = template.render(**config)
        self.log.debug('rendered template:\n{}'.format(source))

        self.log.info('building diagram and saving it into "{}"'.format(filename))
        builder = Builder(source)
        builder.export_diag(filename, filetype)
        self.log.info('done'.format(filename))

class Parser:
    def __init__(self, filename):
        self.log = logging.getLogger('Parser')
        self.log.debug('object {} created'.format(self))
            
        with open(filename, encoding='utf-8') as config_file:
            config = config_file.readlines()

        self.config = []
        for line in config:
            if not line.startswith('!') or not line.startswith(':') or not line.strip() == '':
                self.config.append(line.rstrip())



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
        self.id = uuid4()
        self.text = text
        self.name = name
        self.header = text[0]
        self.type = self.header[:self.header.find(self.name)].strip()
        self.links = []

        self.log = logging.getLogger('ConfigNode')
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

    def get_diag_config(self):
        config = {'id': self.id,
                  'label': '\n'.join(self.text),
                  'color': '#' + hashlib.md5(self.type.encode()).hexdigest()[0:6],
                  'links': self.links
                  }
        return config


class Builder:
    def __init__(self, source):
        self.log = logging.getLogger('Builder')
        self.log.debug('object {} created'.format(self))

        self.tree = blockdiag.parser.parse_string(source)
        self.diagram = blockdiag.builder.ScreenNodeBuilder.build(self.tree)

    def export_diag(self, filename, filetype):
        self.draw = blockdiag.drawer.DiagramDraw(filetype.upper(), self.diagram, filename)
        self.draw.draw()
        self.draw.save()
        self.log.debug('diagram saved as "{}"'.format(filename))


if __name__ == '__main__':
    viz = Driver()
    viz.parse_nodes('config.txt')
    viz.collect_links()
    viz.build_diag()
