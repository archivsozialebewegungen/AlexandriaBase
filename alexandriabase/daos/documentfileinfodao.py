'''
Created on 02.11.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, update, delete, and_, insert
from sqlalchemy.sql.functions import func

from alexandriabase import baseinjectorkeys
from alexandriabase.base_exceptions import NoSuchEntityException
from alexandriabase.daos.basedao import EntityDao
from alexandriabase.daos.metadata import DOCUMENT_TABLE
from alexandriabase.domain import DocumentFileInfo


class DocumentFileInfoDao(EntityDao):
    '''
    Dao for the document files. At the moment
    needs to use the document table also used
    by the document dao, because the data of these
    two are mixed into one table.
    '''

    @inject(db_engine=baseinjectorkeys.DBEngineKey,
            creator_provider=baseinjectorkeys.CreatorProvider)
    def __init__(self, db_engine, creator_provider):
        super().__init__(db_engine, DOCUMENT_TABLE)
        self.creator_provider = creator_provider
        self.table = DOCUMENT_TABLE

    def get_by_id(self, document_file_id):
        query = select([self.table])\
            .where(and_(self.table.c.laufnr == document_file_id,  
                        self.table.c.seite != None))  
        return self._get_exactly_one(query)

    def get_file_infos_for_document(self, document_id):
        '''
        Gets a list of all the document files for a certain document.
        '''
        query = select([self.table]).where(
            and_(self.table.c.hauptnr == document_id,  
                 self.table.c.seite != None)).\
                 order_by(self.table.c.seite)  
        return self._get_list(query)

    def create_new_file_info(self, document_id, filetype=None, resolution=None):
        '''
        Transaction wrapper method for _create_new_file_info.
        '''
        return self.transactional(
            self._create_new_file_info,
            document_id, filetype, resolution)

    def _create_new_file_info(self, document_id, filetype, resolution):
        '''
        Creates a new entry into the document table for this document file.
        '''
        page = self._get_next_page(document_id)
        if page == 1:
            file_info = DocumentFileInfo(document_id)
        else:
            file_info = DocumentFileInfo()
        file_info.document_id = document_id
        file_info.page = page
        file_info.filetype = filetype
        file_info.resolution = resolution
        return self.save(file_info)

    def _get_next_page(self, document_id):
        '''
        Searches for the bigges page number and adds 1.
        '''
        function = func.max(self.table.c.seite)  
        query = select([function])\
        .where(self.table.c.hauptnr == document_id)  
        row = self._get_exactly_one_row(query)
        if row[0] is None:
            return 1
        else:
            return row[0] + 1  

    def _get_next_id(self):
        '''
        Searches for the maximum id and adds 1.
        '''
        query = select([func.max(self.table.c.laufnr)])  
        row = self._get_exactly_one_row(query)
        return row[0] + 1  

    def _insert(self, file_info):
        # pylint: disable=protected-access
        file_info._id = self._get_next_id()
        insert_statement = insert(self.table).values(
            hauptnr=file_info.document_id,
            laufnr=file_info.id,
            erfasser_id=self.creator_provider.creator.id,
            seite=file_info.page,
            res=file_info.resolution,
            dateityp=file_info.filetype,
            aufnahme=func.now(),
            aenderung=func.now())
        self.connection.execute(insert_statement)
        return file_info

    def _update(self, file_info):
        update_statement = update(self.table).\
            where(self.table.c.laufnr == file_info.id).\
            values(hauptnr=file_info.document_id,
                   erfasser_id=self.creator_provider.creator.id,
                   seite=file_info.page,
                   res=file_info.resolution,
                   dateityp=file_info.filetype,
                   aenderung=func.now())
        self.connection.execute(update_statement)
        return file_info

    def _delete(self, document_file_id):
        '''
        Deletes a file info. Might result in deleting a record,
        but also may update the master document record and set
        the page to 0, if it is the last document file for
        the document entry.
        '''
        try:
            info = self.get_by_id(document_file_id)
        except NoSuchEntityException:
            # Already deleted or did not exist in the first place
            return
        if info.document_id == info.id:
            update_statement = update(self.table).where(
                self.table.c.laufnr == info.id  
            ).values(seite=None)
            self.connection.execute(update_statement)
        else:
            delete_statement = delete(self.table).where(
                self.table.c.laufnr == info.id  
            )
            self.connection.execute(delete_statement)

    def _row_to_entity(self, row):
        info = DocumentFileInfo(row[self.table.c.laufnr])  
        info.document_id = row[self.table.c.hauptnr]  
        info.resolution = row[self.table.c.res]  
        info.filetype = row[self.table.c.dateityp]  
        info.page = row[self.table.c.seite]  
        return info
