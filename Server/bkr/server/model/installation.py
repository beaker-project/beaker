
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from sqlalchemy import Column, Integer, DateTime, UnicodeText, ForeignKey
from sqlalchemy.orm import relationship
from bkr.server.util import absolute_url
from .base import DeclarativeMappedObject
from .distrolibrary import DistroTree
from .inventory import System, Command


class Installation(DeclarativeMappedObject):
    """
    Represents a single occurrence of installing a new operating system onto 
    a system.
    """

    __tablename__ = 'installation'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    distro_tree_id = Column(Integer, ForeignKey('distro_tree.id',
            name='installation_distro_tree_id_fk'), nullable=False)
    distro_tree = relationship(DistroTree)
    kernel_options = Column(UnicodeText, nullable=False)
    rendered_kickstart_id = Column(Integer, ForeignKey('rendered_kickstart.id',
            name='installation_rendered_kickstart_id_fk', ondelete='SET NULL'))
    rendered_kickstart = relationship('RenderedKickstart')
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    rebooted = Column(DateTime, default=None)
    install_started = Column(DateTime, default=None)
    install_finished = Column(DateTime, default=None)
    postinstall_finished = Column(DateTime, default=None)
    # System where this installation was done. Note that this is optional, the 
    # installation might have been done on a dynamically created VM instead.
    system_id = Column(Integer, ForeignKey('system.id',
            name='installation_system_id_fk'))
    system = relationship(System, back_populates='installations')
    # Power commands which were triggered to perform this installation. Note 
    # that this list might be empty, if the installation was done on 
    # a dynamically created VM instead of a real system.
    commands = relationship(Command, back_populates='installation')
    # Installation can be associated with a recipe. Note this is optional, 
    # installations can also be requested by hand outside of a recipe 
    # ("manual provision").
    recipe_id = Column(Integer, ForeignKey('recipe.id',
            name='installation_recipe_id_fk'))
    recipe = relationship('Recipe', back_populates='installation')

    def __repr__(self):
        return ('%s(created=%r, system=%r, distro_tree=%r, kernel_options=%r, '
                'rendered_kickstart=%r, rebooted=%r, install_started=%r, '
                'install_finished=%r, postinstall_finished=%r)'
                % (self.__class__.__name__, self.created, self.system,
                self.distro_tree, self.kernel_options, self.rendered_kickstart,
                self.rebooted, self.install_started, self.install_finished,
                self.postinstall_finished))

    def __json__(self):
        return {
            'id': self.id,
            'distro_tree': self.distro_tree,
            'kernel_options': self.kernel_options,
            'kickstart': self.rendered_kickstart,
            'created': self.created,
            'rebooted': self.rebooted,
            'install_started': self.install_started,
            'install_finished': self.install_finished,
            'postinstall_finished': self.postinstall_finished,
            'commands': self.commands,
        }


class RenderedKickstart(DeclarativeMappedObject):

    # This is for storing final generated kickstarts to be provisioned,
    # not user-supplied kickstart templates or anything else like that.

    __tablename__ = 'rendered_kickstart'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    # Either kickstart or url should be populated -- if url is present,
    # it means fetch the kickstart from there instead
    kickstart = Column(UnicodeText)
    url = Column(UnicodeText)

    def __repr__(self):
        return '%s(id=%r, kickstart=%s, url=%r)' % (self.__class__.__name__,
                self.id, '<%s chars>' % len(self.kickstart)
                if self.kickstart is not None else 'None', self.url)

    def __json__(self):
        return {
            'id': self.id,
            'href': self.link,
        }

    @property
    def link(self):
        if self.url:
            return self.url
        assert self.id is not None, 'not flushed?'
        url = absolute_url('/kickstart/%s' % self.id, scheme='http',
                           labdomain=True)
        return url
