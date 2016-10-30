'''
Created on 11.10.2015

@author: michael
'''
from sqlalchemy.sql.schema import MetaData, Table, Column, ForeignKey, \
    ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.sql.sqltypes import Integer, String, Date

CURRENT_VERSION = '0.4'

ALEXANDRIA_METADATA = MetaData()

CREATOR_TABLE = Table(
    'erfasser',
    ALEXANDRIA_METADATA,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('anzeige', String))
    
REGISTRY_TABLE = Table(
    'registry',
    ALEXANDRIA_METADATA,
    Column('schluessel', String, primary_key=True),
    Column('wert', String))
    
DOCUMENT_TYPE_TABLE = Table(
    'doktyp',
    ALEXANDRIA_METADATA,
    Column('id', Integer, primary_key=True),
    Column('beschreibung', String))

EVENT_TABLE = Table(
    'chrono',
    ALEXANDRIA_METADATA,
    Column('ereignis_id', Integer, primary_key=True),
    Column('ereignis', String),
    Column('ende', Integer),
    Column('status_id', Integer),
    Column('erfasser_id', Integer, ForeignKey('erfasser.id')),
    Column('aufnahme', Date),
    Column('aenderung', Date),
    Column('ort_id', Integer))

DOCUMENT_TABLE = Table(
    'dokument', ALEXANDRIA_METADATA,
    Column('hauptnr', Integer),
    Column('laufnr', Integer, primary_key=True),
    Column('seite', Integer),
    Column('beschreibung', String),
    Column('dateityp', String),
    Column('standort', String),
    Column('zustand', String),
    Column('keywords', String),
    Column('erfasser_id', Integer, ForeignKey('erfasser.id')),
    Column('aufnahme', Date),
    Column('aenderung', Date),
    Column('doktyp', Integer, ForeignKey('doktyp.id')),
    Column('res', Integer))

DOCUMENT_EVENT_REFERENCE_TABLE = Table(
    'dverweis',
    ALEXANDRIA_METADATA,
    Column('ereignis_id', 
           Integer, 
           ForeignKey('chrono.ereignis_id', ondelete="CASCADE"),
           primary_key=True),
    Column('laufnr',
           Integer,
           ForeignKey('dokument.laufnr'),
           primary_key=True))

EVENT_EVENTTYPE_REFERENCE_TABLE = Table(
    'everweis', ALEXANDRIA_METADATA,
    Column('ereignis_id', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")),
    Column('hauptid', Integer),
    Column('unterid', Integer))

EVENTTYPE_TABLE = Table(
    'ereignistyp',
    ALEXANDRIA_METADATA,
    Column('haupt', Integer),
    Column('unter', Integer),
    Column('beschreibung', String))

EVENT_CROSS_REFERENCES_TABLE = Table(
    'qverweis',
    ALEXANDRIA_METADATA,
    Column('id1', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")),
    Column('id2', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")))

def get_foreign_keys(primary_key):
    '''
    Returns the foreign keys that reference a certain primary key.
    '''
    foreign_keys = []
    for table_name in ALEXANDRIA_METADATA.tables:
        table = ALEXANDRIA_METADATA.tables[table_name]
        for foreign_key in table.foreign_keys:
            if foreign_key.column == primary_key:
                foreign_keys.append(foreign_key.parent)
    return foreign_keys
