#!/usr/bin/python
__requires__ = ['TurboGears']
import sys
import logging
from turbogears.database import session
from sqlalchemy.sql import and_, not_
from bkr import __version__ as bkr_version
from bkr.server.util import load_config, log_to_stream
from bkr.server.model import RecipeSet, Recipe, TaskStatus
from optparse import OptionParser

log = logging.getLogger(__name__)

def main():
    parser = OptionParser('usage: %prog [options]',
        description='Complete erroneously incompleted recipsets/jobs due to BZ#807237',
        version=bkr_version)
    parser.add_option('-c', '--config', metavar='FILENAME',
        help='Read configuration from FILENAME')
    parser.add_option('-v', '--verbose', action='store_true',
        help='Print the recipes that need updating')
    parser.add_option('--debug', action='store_true',
        help='Print debugging messages to stderr')
    parser.add_option('--dry-run', action='store_true',
        help='Do not update any recipes')
    parser.set_defaults(verbose=False, debug=False, dry_run=False)

    options, args = parser.parse_args()
    load_config(options.config)
    log_to_stream(sys.stderr, level=logging.DEBUG if options.debug else logging.WARNING)
    complete_unfinished_recipe(options.verbose, options.dry_run)

def complete_unfinished_recipe(verbose, dry_run):
    """
    Finds any recipes where all recipes are completed
    whilst the recipeset remains uncompleted.

    The query should look something like this:

    SELECT rs1.id,
    FROM recipe_set AS rs1
    WHERE NOT EXISTS (SELECT 1 FROM recipe AS r1
                      WHERE r1.finish_time IS NULL AND r1.recipe_set_id = rs1.id)
        AND rs1.status = 'Running')
    """
    query = session.query(RecipeSet.id). \
        filter(and_(not_(RecipeSet.recipes.any(Recipe.finish_time == None)),
                    RecipeSet.status == TaskStatus.running))
    rows = query.values(RecipeSet.id)
    for row in rows:
        rs_id = row[0]
        session.begin()
        try:
            if verbose:
                log.debug('Updating status of RS:%s' % rs_id)
            recipeset = session.query(RecipeSet).filter(RecipeSet.id == rs_id). \
                with_lockmode('update').one()
            recipeset.update_status()
            if not dry_run:
                session.commit()
        except Exception, e:
            log.exception('Failed to update status of RS:%s' % rs_id)
            session.rollback()
        finally:
            session.close()

if __name__ in ('main', '__main__'):
    main()
