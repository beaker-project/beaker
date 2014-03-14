
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

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
    def update_retention_tag_and_product(cls, job, retentiontag, product):
        if retentiontag.requires_product() != bool(product):
            if retentiontag.requires_product():
                vars = {cls._needs_product: 1}
            else:
                vars = {cls._needs_no_product: 1}

            return {'success': False,
                    'msg': 'Incompatible product and tags',
                    'vars': vars}
        job.retention_tag = retentiontag
        job.product = product
        return {'success':True}

    @classmethod
    def update_retention_tag(cls, job, retentiontag):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
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
        job.retention_tag = new_retentiontag
        return {'success': True}

    @classmethod
    def update_product(cls, job, product):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        retentiontag = job.retention_tag
        if not retentiontag.requires_product() and \
            product != None:
            return{'success': False,
                   'msg': 'Current retention tag does not support a product',
                   'vars': {cls._needs_tag: 1,
                       'VALID_TAGS': [[tag.id,tag.tag] for tag in \
                                       RetentionTag.list_by_requires_product()]}}
        if retentiontag.requires_product() and \
            product == None:
            return{'success': False, 
                   'msg': 'Current retention tag requires a product',
                   'vars': {cls._needs_tag: 1,
                       'VALID_TAGS': [[tag.id,tag.tag] for tag in \
                                       RetentionTag.list_by_requires_product(False)]}}
        job.product = product
        return {'success': True}
