#!/bin/python3

import logging
import logging.config
import yaml
import re
import hashlib
import jinja2
import time
import sys
import os
from subprocess import call, DEVNULL


def read_settings(filename):
    try:
        with open(filename, encoding='utf-8') as settings_file:
            return yaml.load(settings_file.read())
    except FileNotFoundError:
        print('CRITICAL: SETTINGS_FILE "{}" not found!'.format(filename), file=sys.stderr)
        sys.exit(1)


# parameters
SETTINGS_FILE = 'viz.yml'
TEMPLATE_FILE = 'viz.j2'
SETTINGS = read_settings(SETTINGS_FILE)


# instantiate logging
logging.config.dictConfig(SETTINGS['logging'])


colors = {}
def get_color(string):
    try:
        color = colors[string]
    except KeyError:
        color = '#' + hashlib.sha1(string.encode()).hexdigest()[0:6]
        colors[string] = color
    return color


class Builder:
    def __init__(self, filename):
        logging.debug('object {} created'.format(self))
        self.parser = Parser(filename)
        self.nodes = []

        logging.info('parsing config for nodes')
        for node in SETTINGS['schema']:
            block_type, nodes = self.parser.parse_nodes(**node)
            block_color = get_color(block_type)
            logging.info('parsed {} {} nodes'.format(len(nodes), block_type))

            new_data = {'type': block_type,
                        'color': block_color,
                        'nodes': [i.get_dict() for i in nodes]
                        }
            self.nodes.append(new_data)

    def export_gv(self, filename):
        logging.debug('rendering jinja2 template from file "{}"'.format(TEMPLATE_FILE))
        env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.FileSystemLoader('./'))
        template = env.get_template(TEMPLATE_FILE)
        source = template.render(subgraphs=self.nodes)
        logging.debug('template rendered successfully')

        logging.info('saving as "{}"'.format(filename))
        with open(filename, 'w', encoding='utf-8') as gv_file:
            gv_file.write(source)
        logging.info('done')

    def export_pdf(self, filename):
        self.export_gv('viz.tmp.gv')

        logging.info('saving as "{}"'.format(filename))
        call('dot -Tpdf -o {} viz.tmp.gv'.format(filename), stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(2)
        logging.debug('removing viz.tmp.gv file')
        os.remove('viz.tmp.gv')
        logging.info('done')


def config_load(filename):
    try:
        with open(filename, encoding='utf-8') as config_file:
            return config_file.readlines()
    except FileNotFoundError:
        pass

def config_filter(unfiltered_config):
    config = []
    for line in unfiltered_config:
        if not line.startswith('!') or not line.startswith(':') or not line.strip() == '':
            config.append(line.rstrip())
    return config

def get_type_regex(string):
    block_type = string.split('{{')[1].split('}}')[0]
    pattern = string.replace('{{' + block_type + '}}', '(?P<name>[-\w]+)')
    pattern = pattern.replace('{%...%}', '.*?')
    pattern = '^' + pattern + '$'

    logging.debug('got string: "{}", type: "{}", regex: "{}"'.format(string, block_type, pattern))
    regex = re.compile(pattern)
    return block_type, regex


class Parser:
    def __init__(self, filename):
        self.config = config_load(filename)
        self.config = config_filter(self.config)

    def parse_nodes(self, node, links=None):
        block_type, regex = get_type_regex(node)
        
        nodes = []

        conf_pos = 0
        conf_end = len(self.config) - 1

        while conf_pos <= conf_end:
            logging.debug('looking for block from {} position'.format(conf_pos))
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
                        logging.debug('found block start at {}: "{}", block_name: {}'.format(conf_pos + num, line, block_name))
                    elif conf_pos + num == conf_end:
                        logging.debug('end of file'.format(conf_pos))
                        conf_pos = conf_pos + num + 1
                        break

                else:
                    if match_obj and block_name != match_obj.group('name'):
                        conf_pos += num
                        logging.debug('found block end at {}: "{}", block_name mismatch'.format(conf_pos, line))
                        new_node = ConfigNode(block_name, block_type, self.config[block_pos:conf_pos])
                        nodes.append(new_node)
                        break
                    elif not match_obj and not line.startswith(' '):
                        conf_pos += num
                        logging.debug('found block end at {}: "{}", line without space'.format(conf_pos, line))
                        new_node = ConfigNode(block_name, block_type, self.config[block_pos:conf_pos])
                        nodes.append(new_node)
                        break
                    elif conf_pos + num == conf_end:
                        conf_pos += num
                        logging.debug('found block end at {}: "{}", end of file'.format(conf_pos, line))
                        new_node = ConfigNode(block_name, block_type, self.config[block_pos:conf_pos])
                        nodes.append(new_node)
                        conf_pos += 1
                        break
        
        if links:
            for node in nodes:
                logging.debug('looking for links in node {}'.format(node))
                for link in links:
                    link_type, regex = get_type_regex(link)

                    for line in node.text:
                        match_obj = regex.search(line)
                        if match_obj:
                            logging.debug('found match for link type "{}" in node {}'.format(link_type, node))
                            link_name = match_obj.group('name')
                            node.add_link(link_type + ' ' + link_name)

        return block_type, nodes


class ConfigNode:
    def __init__(self, block_name, block_type, block_text):       
        self.name = block_name
        self.type = block_type
        self.text = block_text
        self.id = self.type + ' ' + self.name
        self.links = []

        logging.debug('object {} created'.format(self))

    def __repr__(self):
        return '<ConfigNode: {} {}>'.format(self.type, self.name)

    def add_link(self, string):
        if string not in self.links:
            self.links.append(string)

    def get_dict(self):
        return {'id': self.id,
                'links': self.links
                }
    

if __name__ == '__main__':
    viz = Builder('config.txt')
    viz.export_gv('viz.gv')
    viz.export_pdf('viz.pdf')
    
