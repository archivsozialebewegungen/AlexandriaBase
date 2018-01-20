
'''
Created on 18.10.2015

@author: michael
'''
from xml.dom.minidom import parse, getDOMImplementation

import os


class NoSuchConfigValue(Exception):
    '''
    Exception thrown when the configuration is missing a value
    '''

    def __init__(self, message):
        super().__init__(message)
        self.message = message

class Config:
    '''
    Class for handling xml configuration files.
    
    There are three types of configuration nodes possible:
    Single values ("entry" nodes), lists ("list" nodes) and maps
    ("map" nodes). All these nodes have a "key" attribute to
    identify them. Lists and maps have child elements named
    "listentry" or "mapentry". The map entries also have the
    "key" attribute. The actual value is always the text node of
    the entry node.
    '''

    def __init__(self, config_file=None):
        if config_file is not None:
            self.config_file = config_file
        else:
            self.config_file = os.environ['ALEX_CONFIG']
        self.entries = {}
        self.lists = {}
        self.maps = {}
        if self.config_file != None:
            self._read_config()

    def _read_config(self):
        '''
        Parses the configuration file and calls the handles for the nodes.
        '''
        dom = parse(self.config_file)
        configuration_nodes = dom.getElementsByTagName("configuration")
        if len(configuration_nodes) != 1:
            raise Exception("Configuration needs exactly 1 configuration node")
        self._configuration_handler(configuration_nodes[0])

    def write_config(self, output_file_name=None):
        '''
        Writes the configuration to a given file. If no file
        is given, the configuration will be written to the file it was
        read from.
        '''
        impl = getDOMImplementation()
        dom = impl.createDocument(None, "configuration", None)
        root = dom.documentElement

        for key, entry in self.entries.items():
            element = dom.createElement("entry")
            element.setAttribute("key", key)
            if entry:
                element.appendChild(dom.createTextNode(entry))
            root.appendChild(element)

        for key, entry_list in self.lists.items():
            element = dom.createElement("list")
            element.setAttribute("key", key)
            for entry in entry_list:
                sub_element = dom.createElement("listentry")
                sub_element.appendChild(dom.createTextNode(entry))
                element.appendChild(sub_element)
            root.appendChild(element)

        for key, entry_map in self.maps.items():
            element = dom.createElement("map")
            element.setAttribute("key", key)
            for entry_key, entry in entry_map.items():
                sub_element = dom.createElement("mapentry")
                sub_element.setAttribute("key", entry_key)
                sub_element.appendChild(dom.createTextNode(entry))
                element.appendChild(sub_element)
            root.appendChild(element)

        if output_file_name:
            file = open(output_file_name, 'wb')
        else:
            file = open(self.config_file, 'wb')
        file.write(dom.toprettyxml(indent="    ", encoding="UTF-8"))
        file.close()

    def _configuration_handler(self, configuration_node):
        '''
        Handler for the root node ("configuration")
        '''
        handlers = {'entry': self._entry_handler,
                    'list': self._list_handler,
                    'map': self._map_handler}

        for node in configuration_node.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                handlers[node.tagName](node)

    def _entry_handler(self, entry_node):
        '''
        Handler for a single value entry.
        '''

        key = entry_node.getAttribute("key")
        value = self._get_node_text(entry_node)
        self.entries[key] = value

    def _list_handler(self, list_node):
        '''
        Handler for a list entry
        '''
        key = list_node.getAttribute("key")
        values = []
        for child in list_node.childNodes:
            if child.nodeName == "listentry":
                values.append(self._get_node_text(child))
        self.lists[key] = values

    def _map_handler(self, map_node):
        '''
        Handler for a map entry
        '''
        key = map_node.getAttribute("key")
        values = {}
        for child in map_node.childNodes:
            if child.nodeName == "mapentry":
                values[child.getAttribute("key")] = self._get_node_text(child)
        self.maps[key] = values

    def _get_node_text(self, node):
        '''
        Extracts the text from a node.
        '''
        # pylint: disable=no-self-use
        node.normalize()
        for child in node.childNodes:
            if child.nodeType == node.TEXT_NODE:
                return child.data

    def _get_string_value(self, key):
        '''
        Gets the raw single value for a key.
        
        It is always a string that must be converted, if it should be
        something different.
        '''
        try:
            return self.entries[key]
        except KeyError:
            raise NoSuchConfigValue("No config for key %s" % key)

    def _set_string_value(self, key, value):
        '''
        Sets a single value.
        
        Does no conversion to string, so it
        must be serialized in advance.
        '''
        self.entries[key] = value
        
    def _get_list_value(self, key):
        '''
        Gets the list associated to a key
        '''
        try:
            return self.lists[key]
        except KeyError:
            raise NoSuchConfigValue("No config for key %s" % key)

    def _set_list_value(self, key, list_value):
        '''
        Sets the list associated to a key
        '''
        self.lists[key] = list_value
        
    def _get_map_value(self, key):
        '''
        Gets the map associated to a key
        '''
        try:
            return self.maps[key]
        except KeyError:
            raise NoSuchConfigValue("No config for key %s" % key)

    def _set_map_value(self, key, map_value):
        '''
        Sets the map associated to a key
        '''
        self.maps[key] = map_value
        
    def _get_db_connection_string(self):
        '''
        Helper method to compose a sql alchemy connections string from
        various configuration variables.
        '''
        connection_string = "%s://" % self._get_string_value("dbengine")
        if self.dbuser:
            connection_string = "%s%s" % (connection_string, self.dbuser)
        if self._get_string_value("dbpassword"):
            connection_string = "%s:%s" % (connection_string, self._get_string_value("dbpassword"))
        if self._get_string_value("dbhost"):
            connection_string = "%s@%s" % (connection_string, self._get_string_value("dbhost"))
        if self._get_string_value("dbport"):
            connection_string = "%s:%s" % (connection_string, self._get_string_value("dbport"))
        connection_string = "%s/%s" % (connection_string, self._get_string_value("dbname"))
        return connection_string
    
    connection_string = property(_get_db_connection_string)
    document_dir = property(lambda self: self._get_string_value('documentbasedir'), 
                            lambda self, value: self._set_string_value('documentbasedir', value))
    archive_dirs = property(lambda self: self._get_list_value('documentarchives'), 
                            lambda self, value: self._set_list_value('documentarchives', value))
    dbuser = property(lambda self: self._get_string_value('dbuser'), 
                      lambda self, value: self._set_string_value('dbuser', value))
    dbpassword = property(lambda self: self._get_string_value('dbpassword'), 
                          lambda self, value: self._set_string_value('dbpassword', value))
    dbhost = property(lambda self: self._get_string_value('dbhost'), 
                      lambda self, value: self._set_string_value('dbhost', value))
    dbport = property(lambda self: self._get_string_value('dbport'), 
                      lambda self, value: self._set_string_value('dbport', value))
    dbengine = property(lambda self: self._get_string_value('dbengine'), 
                        lambda self, value: self._set_string_value('dbengine', value))
    dbname = property(lambda self: self._get_string_value('dbname'), 
                      lambda self, value: self._set_string_value('dbname', value))
    filetypes = property(lambda self: self._get_list_value('filetypes'), 
                         lambda self, value: self._set_list_value('filetypes', value))
    filetypealiases = property(lambda self: self._get_map_value('filetypealiases'), 
                               lambda self, value: self._set_map_value('filetypealiases', value))
    filetypeviewers = property(lambda self: self._get_map_value('filetypeviewers'), 
                               lambda self, value: self._set_map_value('filetypeviewers', value))
    logdir = property(lambda self: self._get_string_value('logdir'), 
                               lambda self, value: self._set_string_value('logdir', value))
    djangodb = property(lambda self: self._get_string_value('djangodb'), 
                               lambda self, value: self._set_string_value('djangodb', value))
    additional_modules = property(lambda self: self._get_list_value('additional_modules'), 
                         lambda self, value: self._set_list_value('additional_modules', value))