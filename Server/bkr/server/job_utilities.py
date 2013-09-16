#
# Copyright (C) 2010 rmancy@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from bkr.server.model import RetentionTag, Product
from bkr.server.widgets import ProductWidget
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger(__name__)


class Utility:

    _needs_product = 'NEEDS_PRODUCT'
    _needs_no_product = 'NEEDS_NO_PRODUCT'
    _needs_tag = 'NEEDS_TAG'

    @classmethod
    def update_task_product(cls, job, retentiontag_id=None, product_id=None):
        if product_id is ProductWidget.product_deselected:
            product = product_id
        elif product_id is not None:
            try:
                product = Product.by_id(product_id)
            except NoResultFound:
                raise ValueError('%s is not a valid product' % product_id)
        else:
            product=None

        if retentiontag_id:
            try:
                retentiontag = RetentionTag.by_id(retentiontag_id)
            except NoResultFound:
                raise ValueError('%s is not a valid retention tag' % retentiontag_id)
        else:
            retentiontag = None
        if retentiontag is None and product is None:
            return {'success': False}
        if retentiontag is not None and product is None: #trying to update retentiontag only
            return cls.check_retentiontag_job(job, retentiontag)
        elif retentiontag is None and product is not None: #only product
            return cls.check_product_job(job, product)
        else: #updating both
            return cls._update_task_product(job, product, retentiontag)

    @classmethod
    def _update_task_product(cls, job, product, retentiontag):
        if product == ProductWidget.product_deselected:
            the_product = None
        elif product is None:
            the_product = job.product
        else:
            the_product = product

        if retentiontag.requires_product() != bool(the_product):
            if retentiontag.requires_product():
                vars = {cls._needs_product: 1}
            else:
                vars = {cls._needs_no_product: 1}

            return {'success': False,
                    'msg': 'Incompatible product and tags',
                    'vars': vars}

        return {'success':True}

    @classmethod
    def check_retentiontag_job(cls, job, retentiontag):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        #This ensures that we take into account any proposed product change
        the_product = job.product
        new_retentiontag = retentiontag

        if new_retentiontag.requires_product() != bool(the_product):
            if new_retentiontag.requires_product():
                vars = {cls._needs_product: 1,
                        'INVALID_PRODUCTS': [ProductWidget.product_deselected]}
            else:
                vars = {cls._needs_no_product:1}
            return {'success': False,
                    'msg': 'Incompatible product and tags',
                    'vars': vars}
        return {'success': True}

    @classmethod
    def check_product_job(cls, job, product):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        retentiontag = job.retention_tag
        if not retentiontag.requires_product() and \
            product != ProductWidget.product_deselected:
            return{'success': False,
                   'msg': 'Current retention tag does not support a product',
                   'vars': {cls._needs_tag: 1,
                       'VALID_TAGS': [[tag.id,tag.tag] for tag in \
                                       RetentionTag.list_by_requires_product()]}}
        if retentiontag.requires_product() and \
            product == ProductWidget.product_deselected:
            return{'success': False, 
                   'msg': 'Current retention tag requires a product',
                   'vars': {cls._needs_tag: 1,
                       'VALID_TAGS': [[tag.id,tag.tag] for tag in \
                                       RetentionTag.list_by_requires_product(False)]}}
        return {'success': True}
