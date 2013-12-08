
from sqlalchemy import (Table, Column, ForeignKey, Integer, Unicode, Boolean,
        DateTime)
from sqlalchemy.orm import mapper, relation, relationship, backref
from turbogears.database import session, metadata
from .base import DeclBase, MappedObject, SystemObject
from .activity import Activity, activity_table
from .identity import User

lab_controller_table = Table('lab_controller', metadata,
    Column('id', Integer, autoincrement=True,
           nullable=False, primary_key=True),
    Column('fqdn',Unicode(255), unique=True),
    Column('disabled', Boolean, nullable=False, default=False),
    Column('removed', DateTime, nullable=True, default=None),
    Column('user_id', Integer,
           ForeignKey('tg_user.user_id'), nullable=False),
    mysql_engine='InnoDB',
)

lab_controller_activity_table = Table('lab_controller_activity', metadata,
    Column('id', Integer, ForeignKey('activity.id'), primary_key=True),
    Column('lab_controller_id', Integer, ForeignKey('lab_controller.id'),
        nullable=False),
    mysql_engine='InnoDB',
)

class LabController(SystemObject):
    def __repr__(self):
        return "%s" % (self.fqdn)

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).one()

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(fqdn=name).one()

    @classmethod
    def get_all(cls, valid=False):
        """
        Desktop, Server, Virtual
        """
        all = cls.query
        if valid:
            all = cls.query.filter_by(removed=None)
        return [(lc.id, lc.fqdn) for lc in all]

class LabControllerDataCenter(DeclBase, MappedObject):
    """
    A mapping from a lab controller to an oVirt data center.
    """
    __tablename__ = 'lab_controller_data_center'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, autoincrement=True,
            nullable=False, primary_key=True)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id',
            name='lab_controller_data_center_lab_controller_id_fk'),
            nullable=False)
    lab_controller = relationship(LabController, backref='data_centers')
    data_center = Column(Unicode(255), nullable=False)
    storage_domain = Column(Unicode(255))

class LabControllerActivity(Activity):
    def object_name(self):
        return 'LabController: %s' % self.object.fqdn

mapper(LabController, lab_controller_table,
        properties = {'user'        : relation(User, backref=backref('lab_controller', uselist=False)),
                      'write_activity': relation(LabControllerActivity, lazy='noload'),
                      'activity' : relation(LabControllerActivity,
                                            order_by=[activity_table.c.created.desc(), activity_table.c.id.desc()],
                                            cascade='all, delete',
                                            backref='object'),
                     }
      )

mapper(LabControllerActivity, lab_controller_activity_table, inherits=Activity,
    polymorphic_identity=u'lab_controller_activity')
