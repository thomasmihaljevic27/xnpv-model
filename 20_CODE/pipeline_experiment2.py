"""pipeline_experiment2.py -- second sweep on the same harness: age in the
pull-back, and the strongest combinations. See pipeline_experiment.py for
the design, scoring and limits; everything here is that script with a
different variant list and output prefix.
"""
from pipeline_experiment import main

VARIANTS2 = {
    'prod':            ('prod', False, 'prod', False),
    'L':               ('L',    False, 'prod', False),
    'LA':              ('LA',   False, 'prod', False),
    'LB3':             ('LB3',  False, 'prod', False),
    'LB3A':            ('LB3A', False, 'prod', False),
    'L+H':             ('L',    False, 'H',    False),
    'LA+H':            ('LA',   False, 'H',    False),
    'LB3+H':           ('LB3',  False, 'H',    False),
    'LB3A+H':          ('LB3A', False, 'H',    False),
    'LB3+H+top50':     ('LB3',  True,  'H',    False),
    'LB3A+H+top50':    ('LB3A', True,  'H',    False),
}

if __name__ == '__main__':
    print('SCRIPT_VERSION=1.0 (harness pipeline_experiment v1.1)', flush=True)
    main(VARIANTS2, 'pipeline_experiment2')
