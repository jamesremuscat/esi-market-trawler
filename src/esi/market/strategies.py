import datetime
import logging
import time


def _wait_until(endtime):
    log = logging.getLogger(__name__)
    log.info('Next scheduled trawl at {}'.format(endtime))
    now = datetime.datetime.utcnow
    while endtime > now():
        sleeptime = (endtime - now()).total_seconds()
        log.info('Sleeping for {} seconds'.format(sleeptime))
        time.sleep(sleeptime)


def CONTINUOUS(_):
    '''Continue on to the next trawl without pausing.'''
    pass


def HOURLY(prev_start):
    '''Commence the next trawl no earlier than one hour after the start of the previous.'''
    next_start = prev_start + datetime.timedelta(hours=1)
    _wait_until(next_start)


def IN_ADVANCE_OF_HOUR(prev_start):
    '''Time the next trawl to end just before the start of the next hour, based on the previous duration.'''
    now = datetime.datetime.utcnow()
    prev_duration = now - prev_start
    next_hour = now.replace(minutes=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    next_start = next_hour - prev_duration - datetime.timedelta(minutes=5)
    _wait_until(next_start)


by_name = {
    'continuous': CONTINUOUS,
    'hourly': HOURLY,
    'advance': IN_ADVANCE_OF_HOUR
}
