
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import re
from lxml import etree
from lxml.builder import E
from sqlalchemy import Column, Integer, DateTime, UnicodeText, ForeignKey
from sqlalchemy.orm import relationship
from bkr.server.util import absolute_url
from .base import DeclarativeMappedObject
from .distrolibrary import DistroTree, Arch
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
            name='installation_distro_tree_id_fk'), nullable=True)
    distro_tree = relationship(DistroTree)
    kernel_options = Column(UnicodeText)
    rendered_kickstart_id = Column(Integer, ForeignKey('rendered_kickstart.id',
            name='installation_rendered_kickstart_id_fk', ondelete='SET NULL'))
    rendered_kickstart = relationship('RenderedKickstart')
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    rebooted = Column(DateTime)
    install_started = Column(DateTime)
    install_finished = Column(DateTime)
    postinstall_finished = Column(DateTime)
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
    tree_url = Column(UnicodeText)
    initrd_path = Column(UnicodeText)
    kernel_path = Column(UnicodeText)
    arch = relationship(Arch)
    arch_id = Column(Integer, ForeignKey('arch.id', name='installation_arch_id_fk'))
    distro_name = Column(UnicodeText)
    osmajor = Column(UnicodeText)
    osminor = Column(UnicodeText)
    variant = Column(UnicodeText)

    def distro_to_xml(self):
        distro_xml = E.distro(
            E.tree(url=self.tree_url),
            E.kernel(url=self.kernel_path),
            E.initrd(url=self.initrd_path),
            E.arch(value=self.arch.arch),
            E.osversion(major=self.osmajor, minor=self.osminor)
        )
        if self.distro_name:
            distro_xml.append(E.name(value=self.distro_name))
        if self.variant:
            distro_xml.append(E.variant(value=self.variant))
        return distro_xml

    def __repr__(self):
        return ('%s(created=%r, system=%r, distro_tree=%r, kernel_options=%r, '
                'rendered_kickstart=%r, rebooted=%r, install_started=%r, '
                'install_finished=%r, postinstall_finished=%r, tree_url=%r,'
                ' initrd_path=%r, kernel_path=%r, arch=%r, distro_name=%r, osmajor=%r, osminor=%r,'
                ' variant=%r)' % (self.__class__.__name__, self.created, self.system,
                self.distro_tree, self.kernel_options, self.rendered_kickstart,
                self.rebooted, self.install_started, self.install_finished,
                self.postinstall_finished, self.tree_url, self.initrd_path,
                self.kernel_path, self.arch, self.distro_name, self.osmajor, self.osminor,
                self.variant))

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
            'tree_url': self.tree_url,
            'initrd_path': self.initrd_path,
            'kernel_path': self.kernel_path,
            'arch': self.arch,
            'distro_name': self.distro_name,
            'osmajor': self.osmajor,
            'osminor': self.osminor,
            'variant': self.variant,
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
    kickstart = Column(UnicodeText(length=2**18-1))
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
