
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, Unicode
from sqlalchemy.orm import relationship
from bkr.server.model.base import DeclarativeMappedObject
from bkr.server.model.lab import LabController
from .types import UUID

# Currently Beaker does not understand OpenStack regions, so there should only 
# be one row in this table, created by the administrator. In future this can be 
# expanded to track multiple regions associated with different lab controllers.
class OpenStackRegion(DeclarativeMappedObject):

    __tablename__ = 'openstack_region'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, autoincrement=True, nullable=False, primary_key=True)
    lab_controller_id = Column(Integer, ForeignKey('lab_controller.id',
            name='openstack_region_lab_controller_id_fk'), nullable=False)
    lab_controller = relationship(LabController, back_populates='openstack_regions')
    # NULL ipxe_image_id means not uploaded yet
    ipxe_image_id = Column(UUID)
