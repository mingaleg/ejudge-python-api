#!/usr/bin/env python3
from ejudge_api import *
from sys import argv
from os import system

CONTEST_ID = None
if len(argv) > 1:
    CONTEST_ID = int(argv[1])

run_id = 0

def proceed_contest(CONTEST_ID):
    old_log = ''
    try:
        with open('%06d.log' % CONTEST_ID) as fl:
            old_log = fl.read()
    except:
        pass
    log = open('%06d.log' % CONTEST_ID, 'a')
    c = Contest(CONTEST_ID)
    run_id = 0
    while True:
        run_id += 1
        if ('%4d@%06d' % (run_id, CONTEST_ID)) in old_log:
            print('RUN %4d@%06d: Alredy viewed' % (run_id, CONTEST_ID))
            continue
        print('RUN %4d@%06d' % (run_id, CONTEST_ID))
        try:
            run = c.Run(run_id)
            if run.status in ('Pending review', 'OK'):
                with open('%d@%06d.py' % (run_id, CONTEST_ID), 'w') as fh:
                    fh.write(run.source)
                system('py.test --pep8 %d@%06d.py' % (run_id, CONTEST_ID))
                print('REJECT %4d@%06d? ' % (run_id, CONTEST_ID), end='')
                comment = input()
                if comment:
                    log.write('%4d@%06d: Rejected [%s]\n' % (run_id, CONTEST_ID, comment))
                    run.Reject(comment)
                else:
                    log.write('%4d@%06d: OK\n' % (run_id, CONTEST_ID))
                    run.OK()
            else:
                log.write('%4d@%06d: Skipped\n' % (run_id, CONTEST_ID))
        except Exception as E:
            print(E)
            print('CONTEST END')
            log.close()
            return
if CONTEST_ID:
    proceed_contest(CONTEST_ID)
else:
    for CONTEST_ID in range(17501, 17513):
        proceed_contest(CONTEST_ID)
