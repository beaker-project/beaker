
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os.path
import datetime
import logging
import imp
import pkg_resources
from sqlalchemy import Column, Integer, Unicode, DateTime
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.inspection import inspect
from turbogears.database import session, get_engine
from .base import DeclarativeMappedObject

logger = logging.getLogger(__name__)

class DataMigration(DeclarativeMappedObject):
    """
    An online data migration which has already been completed on this database.
    Similar to the alembic_version table, when a data migration has been 
    completed we add a row to this table with the name of the completed 
    migration, so we know not to bother performing it again.
    """

    __tablename__ = 'data_migration'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), nullable=False, unique=True)
    finish_time = Column(DateTime)

    @classmethod
    def all_names(cls):
        names = []
        for filename in pkg_resources.resource_listdir('bkr.server', 'data-migrations'):
            name, extension = os.path.splitext(filename)
            if extension != '.py':
                continue
            name = name.decode(sys.getfilesystemencoding())
            names.append(name)
        return names

    @classmethod
    def all(cls):
        """
        Returns a list of all defined migrations, whether or not they have been 
        applied to this database yet.
        """
        migrations = []
        for name in cls.all_names():
            try:
                migration = cls.query.filter(cls.name == name).one()
            except NoResultFound:
                migration = cls(name=name)
            migrations.append(migration)
        return migrations

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

    @property
    def module(self):
        if not hasattr(self, '_module'):
            module_path = pkg_resources.resource_filename('bkr.server',
                    'data-migrations/%s.py' % self.name.encode(sys.getfilesystemencoding()))
            logger.debug('Loading data migration %s from %s', self.name, module_path)
            self._module = imp.load_source(self.name.encode(sys.getfilesystemencoding()), module_path)
        return self._module

    def migrate_one_batch(self, engine):
        return self.module.migrate_one_batch(engine)

    @property
    def is_finished(self):
        return self.finish_time is not None

    def mark_as_finished(self):
        self.finish_time = datetime.datetime.utcnow()
        session.add(self)
        session.flush()
