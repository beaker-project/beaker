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

from bkr.server.model import Job

class Utility:

    @classmethod
    def check_retentiontag_job(cls, job_id, retentiontag_id):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        try: 
            job = Job.by_id(job_id)
        except InvalidRequestError, e:
            log.error('%s' % e)
            return {'error' : 'Please specify a valid job' }
        
        try: 
            old_retentiontag = job.retention_tag.tag
        except AttributeError, e:
            log.error('Trying to access a retention_tag on a job failed, every instantiated Job \
                have a rentention_tag')

        try: 
            new_retentiontag = RetentionTag.by_id(retentiontag_id)  # will throw an error here if retentiontag id is invalid 
        except InvalidRequestError, (e):
            log.error('%s' % (e)) 
            return { 'error' : 'Retention Tag not found'} 
        return True

    @classmethod
    def check_product_job(cls, job_id, product_id):
        """
        performs logic needed to determine if changing a retention_tag is valid, returns an
        error fit for displaying in widget
        """
        try:
            job = Job.by_id(job_id)
        except InvalidRequest, e:
            log.error('%s' % e)
            return {'error' : 'Please specify a valid job' }

        if not job.requires_product():
            return { 'error' : 'Tag %s does not require product' % job.retention_tag.tag } 

        try:
            new_product = Product.by_id(product_id)  # will throw an error here if product id is invalid 
        except InvalidRequestError, (e):
            if '%s' % e == 'No rows returned for one()':
                log.error('%s' % e) 
                return { 'error' : 'Product not found'} 
          
        return True 
