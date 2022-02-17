'''
Created on 15.11.2021

@author: michael
'''
from alexandriabase.daos import DocumentDao, DaoModule, DOCUMENT_TABLE,\
    DocumentFileInfoDao
from injector import Injector, inject
from alexandriabase import AlexBaseModule
from alexandriabase.services import ServiceModule, DocumentFileManager,\
    DocumentFileNotFound, THUMBNAIL, FileProvider, ReferenceService
from sqlalchemy.sql.expression import or_, and_
from alexandriabase.base_exceptions import NoSuchEntityException
from datetime import date
from os.path import exists
import re

def tex_sanitizing(text: str) -> str:
    
    text = text.replace("&", "\\&")
    text = text.replace("#", "\\#")
    return text

class PlakatExporter:
    
    @inject
    def __init__(self, dao: DocumentDao, 
                 file_info_dao: DocumentFileInfoDao, 
                 file_manager: DocumentFileManager, 
                 file_provider: FileProvider,
                 reference_service: ReferenceService):
        
        self.dao = dao
        self.file_info_dao = file_info_dao
        self.file_manager = file_manager
        self.file_provider = file_provider
        self.reference_service = reference_service
        
        self.titel = "Plakate im ASB"
        
       
    def export_to_tex(self):
    
        self.open_file()
        for record in self.fetch_records():
            events = self.reference_service.get_events_referenced_by_document(record)
            self.print_record(record, events)
        self.close_file()
        
    def print_record(self, record, events):
        
        if self.filtered(record, events):
            return
        
        self.file.write("\n\n\\section*{Dokumentnr. %d}" % record.id)
        self.file.write("\n\nBeschreibung: %s" % tex_sanitizing(record.description))
        if record.condition is not None and record.condition.strip() != "":
            self.file.write("\n\nZusätzliche Infos: %s" % tex_sanitizing(record.condition))

        self.print_events(events)
            
        self.print_img(record.id)

    def fetch_records(self):

        condition = DOCUMENT_TABLE.c.doktyp == 9
        return self.dao.find(condition)
    
    def filtered(self, record, events):
        '''
        Returns True, if the record should be filtered out
        from the list. Override in subclasses.
        '''

        return False

    def print_events(self, events):
        
        if len(events) == 0:
            return
        if len(events) == 1:
            self.file.write("\n\n\\subsection*{Verknüpftes Ereignis}")
        else:
            self.file.write("\n\n\\subsection*{Verknüpfte Ereignisse}")
            
        for event in events:
            self.file.write("\n\n%s: %s" % (event.daterange, tex_sanitizing(event.description)))
        
    def print_img(self, id):    
        
        try:
            file_info = self.file_info_dao.get_by_id(id)
            file_name = self.file_manager.get_generated_file_path(file_info, THUMBNAIL)
            if not exists(file_name):
                print("Generating file %s" % file_name)
                self.file_provider.get_thumbnail(file_info)
            self.file.write("\n\n\\vspace{0.5cm}")
            self.file.write("\n\n\\includegraphics[width=7.0cm]{%s}\n" % file_name)
        except NoSuchEntityException:
            self.file.write("\n\nEintrag nicht gefunden!")
        except DocumentFileNotFound:
            self.file.write("\n\nDokumentdatei nicht gefunden!")
        except OSError as e:
            print(e)
            print("Error on document %d" % id)

    def open_file(self):
        
        self.file = open("/tmp/plakate.tex", "w")

        self.file.write("\\documentclass[german, a4paper, 12pt, twocolums]{article}\n")
        self.file.write("\\usepackage[utf8]{inputenc}\n")
        self.file.write("\\usepackage[T1]{fontenc}\n")
        self.file.write("\\usepackage{graphicx}\n")
        self.file.write("\\setlength{\\parindent}{0cm}\n")
        self.file.write("\\special{papersize=29.7cm,21cm}\n")
        self.file.write("\\usepackage{geometry}\n")
        self.file.write("\\geometry{verbose,body={29.7cm,21cm},tmargin=1.5cm,bmargin=1.5cm,lmargin=1cm,rmargin=1cm}\n")
        self.file.write("\\begin{document}\n")
        self.file.write("\\sloppy\n")
        self.file.write("\\title{%s}\n" % self.titel)
        self.file.write("\\author{Archiv Soziale Bewegungen e.V.}\n")
        self.file.write("\\date{Stand: %s}\n" % date.today())
        self.file.write("\\maketitle\n\n")
        self.file.write("\\twocolumn\n\n")
        
    def close_file(self):

        self.file.write("\\end{document}\n")
        self.file.close()


class FemPlakatExporter(PlakatExporter):
    '''
    Katalog für Plakate zur Frauenbewegung.
    '''
        
    def fetch_records(self):

        condition = and_(DOCUMENT_TABLE.c.doktyp == 9, 
                         or_(DOCUMENT_TABLE.c.standort.like("7%"),
                             DOCUMENT_TABLE.c.standort.like("23%")))
        return self.dao.find(condition)
    
class FemOldPlakatExporter(FemPlakatExporter):
    '''
    Katalog für alle Plakate vor 1990 oder ohne Information
    '''
    
    def filtered(self, record, events):

        if record.condition is not None and re.compile(r".*(199\d|20\d\d).*").match(record.condition):
            return True
        
        if len(events) == 0:
            return False
        
        for event in events:
            if event.id < 1990000000:
                return False

        return True


if __name__ == '__main__':
    
    injector = Injector([AlexBaseModule, DaoModule, ServiceModule])
    exporter = injector.get(FemOldPlakatExporter)
    exporter.title = "Plakate zur Frauenbewegung\\linebreak{}vor 1990"
    exporter.export_to_tex()