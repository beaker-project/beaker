import os
import subprocess
import unittest


class TestBkrClient(unittest.TestCase):

    def test_bkr(self):

        tests_to_pass = ['job-clone J:1',
            'job-clone RS:1',
            'job-results J:1',
            'job-results RS:1',
            'job-results T:1',]
    
        tests_to_fail = ['job-cancel R:1',]

        client_dir = 'build/lib/bkr/client/main.py'
        failures = []
        for test in tests_to_pass:
            cmd = ['python',client_dir] + test.split(" ")
            p =  subprocess.Popen(cmd)
            p.communicate()
            if p.returncode != 0:
                failures.append('Failed test %s: should have passed' % test)

        for test in tests_to_fail:
            cmd = ['python',client_dir] + test.split(" ")
            p =  subprocess.Popen(cmd,stdout=subprocess.PIPE)
            output,stderr = p.communicate()
            if 'Exception' not in output:
                failures.append('Passed test %s: should have failed' % test)

        print failures or 'No Failures'
