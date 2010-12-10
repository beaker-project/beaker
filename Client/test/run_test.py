import os
import subprocess

tests = ['job-clone J:1',
         'job-clone RS:1',
         'job-results J:1',
         'job-results RS:1',
         'job-results T:1',]


client_dir = '../build/lib/bkr/client/main.py'
failures = []
for test in tests:
    cmd = ['python',client_dir] + test.split(" ")
    p =  subprocess.Popen(cmd)
    p.communicate()
    if p.returncode != 0:
        failures.append('Failed test %s' % test)

print failures or 'No Failures'
