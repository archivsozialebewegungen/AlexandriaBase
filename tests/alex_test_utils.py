'''
Created on 01.03.2015

@author: michael
'''
import os
import shutil
import sys
import tempfile

from tempfile import NamedTemporaryFile

from sqlalchemy import text
from alexandriabase.config import Config
from alexandriabase.daos import ALEXANDRIA_METADATA
from alexandriabase.domain import DocumentFileInfo


MODE_SIMPLE = "simple"
MODE_FULL = "full"

class TestEnvironment():
    
    def __init__(self, mode=MODE_SIMPLE, additional_modules=[]):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_file_name = os.path.join(self.tmpdir.name, "config.xml")
        os.environ['ALEX_CONFIG'] = self.config_file_name

        config_file = os.path.join(get_testfiles_dir(), "testconfig.xml")
        self.config = Config(config_file)
        self.config.additional_modules = additional_modules
        self.file_paths = []
        self.document_file_infos = []
        self.document_dir = None
        self.archive_dirs = []
        if mode == MODE_FULL:
            self.setup_files()
        self.config.write_config(self.config_file_name)
        self.config = Config(self.config_file_name)

    def setup_files(self):
        self.setup_input_files()
        self.setup_storage_files()
        
    def setup_input_files(self):
        test_files_dir = get_testfiles_dir()
        
        jpg_input_src = os.path.join(test_files_dir, 'testfile.jpg')
        self.jpg_input_file = os.path.join(self.tmpdir.name, 'testfile.jpg')
        shutil.copy(jpg_input_src, self.jpg_input_file)
        
        tif_input_src = os.path.join(test_files_dir, 'testfile.tif')
        self.tif_input_file = os.path.join(self.tmpdir.name, 'testfile.tif')
        shutil.copy(tif_input_src, self.tif_input_file)

        input_src = os.path.join(test_files_dir, 'testfile.tif')
        self.illegal_input_file = os.path.join(self.tmpdir.name, 'testfile.foo')
        shutil.copy(input_src, self.illegal_input_file)

    def setup_storage_files(self):
        
        source_dir = os.path.join(get_testfiles_dir(), "filestorage")
        target_dir = os.path.join(self.tmpdir.name, "filestorage")
        shutil.copytree(source_dir, target_dir)
    
        self.document_dir = os.path.join(target_dir, "docs")
        self.archive_dirs = [os.path.join(target_dir, "archive")]
    
        document_tif_dir = os.path.join(self.document_dir, 'tif')
        document_gif_dir = os.path.join(self.document_dir, 'gif')
        document_pdf_dir = os.path.join(self.document_dir, 'pdf')
        document_txt_dir = os.path.join(self.document_dir, 'txt')
        document_mpg_dir = os.path.join(self.document_dir, 'mpg')

        archive_1000_dir = os.path.join(self.archive_dirs[0], "1000")
        archive_tif_dir = os.path.join(archive_1000_dir, 'tif')
        archive_jpg_dir = os.path.join(archive_1000_dir, 'jpg')
        
        self.file_paths.append(None)
        self.document_file_infos.append(None)
        self.file_paths.append(os.path.join(archive_tif_dir, "00000001.tif"))
        self.append_file_info(1, 'tif', 400, 1, 1)
        self.file_paths.append(os.path.join(archive_tif_dir, "00000002.tif"))
        self.append_file_info(2, 'tif', 400, 3, 1)
        self.file_paths.append(os.path.join(document_gif_dir, "00000003.gif"))
        self.append_file_info(3, 'gif', None, 2, 1)
        self.file_paths.append(os.path.join(archive_jpg_dir, "00000004.jpg"))
        self.append_file_info(4, 'jpg', None, 1, 2)
        self.file_paths.append(os.path.join(document_txt_dir, "00000005.txt"))
        self.append_file_info(5, 'txt', None, 2, 2)
        self.file_paths.append(os.path.join(archive_jpg_dir, "00000006.jpg"))
        self.append_file_info(6, 'jpg', None, 3, 2)
        self.file_paths.append(os.path.join(archive_jpg_dir, "00000007.jpg"))
        self.append_file_info(7, 'jpg', None, 4, 2)
        self.file_paths.append(os.path.join(document_pdf_dir, "00000008.pdf"))
        self.append_file_info(8, 'pdf', None, 1, 3)
        self.file_paths.append(os.path.join(document_tif_dir, "00000009.tif"))
        self.append_file_info(9, 'tif', 400, 3, 3)
        self.file_paths.append(os.path.join(document_tif_dir, "00000010.tif"))
        self.append_file_info(10, 'tif', 400, 2, 3)
        self.file_paths.append(os.path.join(document_txt_dir, "00000011.txt"))
        self.append_file_info(11, 'txt', None, 1, 4)
        self.file_paths.append(os.path.join(document_txt_dir, "00000012.txt"))
        self.append_file_info(12, 'txt', None, 1, 5)
        self.file_paths.append(os.path.join(document_mpg_dir, "00000013.mpg"))
        self.append_file_info(13, 'mpg', None, 1, 6)
        self.file_paths.append(os.path.join(archive_jpg_dir, "00000014.jpg"))
        self.append_file_info(14, 'jpg', None, 1, 7)
    
        self.config.document_dir = self.document_dir
        self.config.archive_dirs = self.archive_dirs
        
        self.gif_file_path = self.file_paths[3]
        self.tif_file_path = self.file_paths[1]
        self.jpg_file_path = self.file_paths[4]
        self.pdf_file_path = self.file_paths[8]
        self.txt_file_path = self.file_paths[5]
        self.mpg_file_path = self.file_paths[13]
        
    def append_file_info(self, id, filetype, resolution, page, document_id):
        
        info = DocumentFileInfo(id)
        info.filetype = filetype
        info.resolution = resolution
        info.page = page
        info.document_id = document_id
        self.document_file_infos.append(info)
        
    def cleanup(self):
        
        self.tmpdir.cleanup()

def get_test_base_dir():
    this_module = get_test_base_dir.__module__
    return get_path_for_module(this_module)

def get_pdf_samples_dir():
    return os.path.join(get_testfiles_dir(), "pdf_samples")

def get_path_for_module(module):
    this_file = os.path.abspath(sys.modules[module].__file__)
    this_dir = os.path.split(this_file)[0]
    return this_dir
    
def get_testfiles_dir():
    return os.path.join(get_test_base_dir(), "files")

def get_dbfixtures_dir():
    return os.path.join(get_test_base_dir(), "dbfixtures")

def load_fixture(name, engine):
    connection = engine.connect()
    with open(os.path.join(get_dbfixtures_dir(), '%s.sql' % name), 'r') as file_input:
        for cmd in file_input:
            connection.execute(text(cmd))
    connection.close()

def clear_table(name, engine):
    connection = engine.connect()
    connection.execute(text("DELETE FROM %s;" % name))
    connection.close()

def setup_database_schema(engine):
    #load_fixture("schema", engine)
    ALEXANDRIA_METADATA.create_all(engine)

def drop_database_schema(engine):
    #load_fixture("schema", engine)
    ALEXANDRIA_METADATA.drop_all(engine)

def load_table_data(tables, engine):
    for table in tables:
        load_fixture(table, engine)
        
def clear_table_data(tables, engine):
    for table in tables:
        clear_table(table, engine)
        
def create_temporary_test_file_name():
    
    test_file = NamedTemporaryFile()
    test_file_name = test_file.name
    test_file.close()
    return test_file_name
