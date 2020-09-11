#!/usr/bin/env python
'''
Generate table for the demo.
'''
import datetime
import sys
from random import randint

print('''\
-- demo03 sample
-- Create a set of hard-coded metrics value to give users
-- a feel for how to generate them.
DROP TABLE IF EXISTS ts1;
CREATE TABLE ts1 (
   id   SERIAL NOT NULL UNIQUE, -- primary key
   tstamp TIMESTAMPTZ NOT NULL,
   metric TEXT NOT NULL,
   value REAL NOT NULL
);

COMMENT ON TABLE ts1 IS 'Basic timeseries data';
COMMENT ON COLUMN ts1.tstamp IS 'The record timestamp.';
COMMENT ON COLUMN ts1.metric IS 'The metric name.';
COMMENT ON COLUMN ts1.value IS 'The metric value [0..100].';

-- Populate the table.
INSERT INTO ts1 (tstamp, metric, value)
VALUES\
''')

sec = 0
for vnum in range(1, 11):
    vname = f'proc{vnum:>02}'
    for day in range(1, 9):
        sdate = f'2020-09-{day:>02}'
        for hour in range(0, 24):
            minute = int(sec / 60)
            second = sec % 60
            stime = f' {hour:>02}:{minute:>02}:{second:>02}-07'
            sts = sdate + stime
            val = randint(0, 100)
            record = f"  ('{sts}', '{vname}', {val})"
            if sec:
                print(f',\n{record}', end='')
            else:
                print(f'{record}', end='')
            sec += 1
print(';')
