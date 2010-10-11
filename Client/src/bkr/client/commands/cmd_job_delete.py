from bkr.client import BeakerCommand
from optparse import OptionValueError

class Job_Delete(BeakerCommand):
    """Delete Jobs in Beaker """
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

        self.parser.add_option(
            "--dryrun",
            default=False,
            action="store_true",
            help="Test the likely output of job-delete without deleting anything",
        )

        """
        Currently not implemented: Allow degrees of deleteion
        self.parser.add_option(
            "-a",
            "--max-removal",
            action="store_const",
            const=0,
            default = False,
            dest="remove_all",
            help="Remove as much as server will allow us",
        )
        """

    def run(self,*args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        tag = kwargs.pop('tag',None)
        complete_days = kwargs.pop('completeDays', None)
        family = kwargs.pop('family',None)
        dryrun = kwargs.pop('dryrun',None)

        if len(args) < 1 and tag is None and complete_days is None and family is None:
            self.parser.error('Please specify either a job,recipeset, tag, family or complete days')
        if len(args) > 0 and (tag is not None or complete_days is not None):
            self.parser.error('Please either delete by job or tag/complete/family, not by both')

        self.set_hub(username,password)
        jobs = []
        if args:
            for job in args:
                jobs.append(job)
        print self.hub.jobs.delete_jobs(jobs,tag,complete_days,family,dryrun)

