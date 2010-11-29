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

from bkr.server.model import Job, RetentionTag, Product
from bkr.server.widgets import ProductWidget
from sqlalchemy.exceptions import InvalidRequestError

import logging
log = logging.getLogger(__name__)


class Utility:

    _needs_product = 'NEEDS_PRODUCT'
    _needs_no_product = 'NEEDS_NO_PRODUCT'
    _needs_tag = 'NEEDS_TAG'

    @classmethod
    def update_task_product(cls,job_id,retentiontag_id=None, product_id=None):
        if retentiontag_id is None and product_id is None:
            return {'success' : False }

        try: 
            job = Job.by_id(job_id)
        except InvalidRequestError, e:
            log.error('%s' % e)
            return {'success':False}

        if retentiontag_id is not None and product_id is None: #trying to update retentiontag only
            return cls.check_retentiontag_job(job,retentiontag_id)
        elif retentiontag_id is None and product_id is not None: #only product
            return cls.check_product_job(job,product_id)
        else: #updating both
           return cls._update_task_product(job,product_id,retentiontag_id)
        

    @classmethod
    def _update_task_product(cls,job,product_id,retentiontag_id):
        if product_id:
            try:
                the_product = Product.by_id(product_id) 
            except InvalidRequestError, e:
                log.error('%s' % e)
                return {'success':False}
        elif product_id == ProductWidget.product_deselected:
            the_product = None
        else:
            the_product = job.product
        
        try: 
            retentiontag = RetentionTag.by_id(retentiontag_id)  # will throw an error here if retentiontag id is invalid 
        except InvalidRequestError, (e):
            log.error('%s' % (e)) 
            return {'success' : False} 

        if retentiontag.requires_product() != bool(the_product):
            if retentiontag.requires_product():
                vars = {cls._needs_product: 1}
            else:
                vars = {cls._needs_no_product:1}

            return {'success':False, 'msg':'Incompatible product and tags', 'vars' : vars} 

        return {'success':True}
        
    @classmethod
    def check_retentiontag_job(cls, job, retentiontag_id):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        #This ensures that we take into account any proposed product change
         
        the_product = job.product
                   
        try: 
            old_retentiontag = job.retention_tag.tag
        except AttributeError, e:
            log.error('Trying to access a retention_tag on a job failed, every instantiated Job \
                have a rentention_tag')
            return {'success':False}

        try: 
            new_retentiontag = RetentionTag.by_id(retentiontag_id)  # will throw an error here if retentiontag id is invalid 
        except InvalidRequestError, (e):
            log.error('%s' % (e)) 
            return {'success' : False, 'msg' : 'Could not find that retention tag' }

        if new_retentiontag.requires_product() != bool(the_product):
            if new_retentiontag.requires_product(): 
                vars = {cls._needs_product: 1, 'INVALID_PRODUCTS': [ProductWidget.product_deselected]}
            else:
                vars = {cls._needs_no_product:1}

            return {'success':False, 'msg':'Incompatible product and tags', 'vars' : vars} 

        return {'success' : True}

    @classmethod
    def check_product_job(cls, job, product_id):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        retentiontag = job.retention_tag

        if not retentiontag.requires_product() and product_id != ProductWidget.product_deselected:
            return{'success':False, 
                    'vars': {cls._needs_tag:1,
                             'VALID_TAGS': [[tag.id,tag.tag] for tag in RetentionTag.list_by_requires_product()]
                             }
                    }
        
        if retentiontag.requires_product and product_id == ProductWidget.product_deselected:
            return{'success':False, 
                    'vars': {cls._needs_tag:1,
                             'VALID_TAGS': [[tag.id,tag.tag] for tag in RetentionTag.list_by_requires_product(False)]
                             }
                    }

        try:
            new_product = Product.by_id(product_id)  # will throw an error here if product id is invalid 
        except InvalidRequestError, (e):
            if '%s' % e == 'No rows returned for one()' and product_id != ProductWidget.product_deselected:
                log.error('%s' % e) 
                return {'success':False, 'msg':'Could not find that product'}
          
        return {'success':True}
