from bkr.client import BeakerCommand
from bkr.client.commands.cmd_job_list import Job_List
from optparse import OptionValueError

class Job_Delete(Job_List):
    """Delete Jobs in Beaker """
    enabled = True

    def options(self):
        super(Job_Delete,self).options()
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name

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

        if len(args) < 1 and tag is None and complete_days is None and family is None:
            self.parser.error('Please specify either a job,recipeset, tag, family or complete days')
        if len(args) > 0 and (tag is not None or complete_days is not None):
            self.parser.error('Please either delete by job or tag/complete/family, not by both')

        self.set_hub(username,password)
        jobs = []
        if args:
            for job in args:
                jobs.append(job)
        print self.hub.jobs.delete_jobs(jobs,tag,complete_days,family)

