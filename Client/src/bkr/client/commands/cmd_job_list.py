from bkr.client import BeakerCommand
from optparse import OptionValueError

class Job_List(BeakerCommand):
    """List Beaker jobs """
    enabled = True
    
    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "-f",
            "--family",
            help="Family for which the Job is run against"
        )

        self.parser.add_option(
            "-c",
            "--completeDays",
            type='int',
            help="Number of days job has been completed for"
        )

        self.parser.add_option(
            "-t",
            "--tag",
            action="append",
            help="RecipeSets with a particular Tag"
        )

    def run(self,*args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        family = kwargs.pop('family',None)
        tag = kwargs.pop('tag',None)
        complete_days = kwargs.pop('completeDays', None)

        if complete_days is None and tag is None and family is None:
            self.parser.error('Please pass either the complete time delta, a tag or family')

        self.set_hub(username,password)
        jobs = []
        print self.hub.jobs.list(tag,complete_days,family)

