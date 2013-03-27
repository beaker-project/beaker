
import unittest
from bkr.labcontroller.log_storage import LogStorage

def test_log_storage_paths():
    log_storage = LogStorage('/dummy', 'http://dummy/', object())
    cases = [
        ('recipe', '1', 'console.log', '/dummy/recipes/0+/1/console.log'),
        ('recipe', '1', '/console.log', '/dummy/recipes/0+/1/console.log'),
        ('recipe', '1', '//console.log', '/dummy/recipes/0+/1/console.log'),
        ('recipe', '1', 'debug/beah_raw', '/dummy/recipes/0+/1/debug/beah_raw'),
        ('recipe', '1001', 'console.log', '/dummy/recipes/1+/1001/console.log'),
        ('task', '1', 'TESTOUT.log', '/dummy/tasks/0+/1/TESTOUT.log'),
        ('task', '1', '/TESTOUT.log', '/dummy/tasks/0+/1/TESTOUT.log'),
        ('task', '1', '//TESTOUT.log', '/dummy/tasks/0+/1/TESTOUT.log'),
        ('task', '1', 'debug/beah_raw', '/dummy/tasks/0+/1/debug/beah_raw'),
        ('task', '1001', 'TESTOUT.log', '/dummy/tasks/1+/1001/TESTOUT.log'),
        ('result', '1', 'TESTOUT.log', '/dummy/results/0+/1/TESTOUT.log'),
        ('result', '1', '/TESTOUT.log', '/dummy/results/0+/1/TESTOUT.log'),
        ('result', '1', '//TESTOUT.log', '/dummy/results/0+/1/TESTOUT.log'),
        ('result', '1', 'debug/beah_raw', '/dummy/results/0+/1/debug/beah_raw'),
        ('result', '1001', 'TESTOUT.log', '/dummy/results/1+/1001/TESTOUT.log'),
    ]
    for log_type, id, path, expected in cases:
        actual = getattr(log_storage, log_type)(id, path).path
        assert actual == expected, actual
