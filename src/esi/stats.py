# coding: utf8

from collections import deque
from datetime import datetime
from itertools import islice
from threading import Lock, Thread
from time import sleep

import logging
import os
import psycopg2
import ujson


class StatsCollector(Thread):
    '''
    Collects simple statistics and aggregates them over the number of minutes
    you choose, up to one hour.
    '''

    max_minutes = 60

    def __init__(self):
        super(StatsCollector, self).__init__()
        self.daemon = True
        self.current = {}
        self.history = {}
        self.datapoints = {}
        self.lock = Lock()
        self.starttime = 0

    def run(self):
        self.starttime = datetime.utcnow()
        while True:
            sleep(60)
            with self.lock:
                for key in self.current.keys():
                    if key not in self.history:
                        self.history[key] = deque(maxlen=self.max_minutes)
                    self.history[key].appendleft(self.current[key])
                    self.current[key] = 0

    def tally(self, key, count=1):
        with self.lock:
            if key not in self.current:
                self.current[key] = count
            else:
                self.current[key] += count

    def datapoint(self, key, value):
        self.datapoints[key] = value

    def getCount(self, key, minutes):
        if key in self.history:
            return sum(islice(self.history[key], 0, min(minutes, self.max_minutes)))
        return 0

    def getSummary(self):
        summary = {}

        for key in self.current.keys():
            summary[key] = {
                "1min": self.getCount(key, 1),
                "5min": self.getCount(key, 5),
                "60min": self.getCount(key, 60)
            }

        for key, value in self.datapoints.iteritems():
            summary[key] = value

        summary['uptime'] = int((datetime.utcnow() - self.starttime).total_seconds())

        return summary


class StatsWriter(Thread):
    def __init__(self, statsCollector, fileName='stats.json'):
        super(StatsWriter, self).__init__()
        self.statsCollector = statsCollector
        self.fileName = fileName
        self.setDaemon(True)
        self.logger = logging.getLogger("stats_writer")

    def run(self):
        while True:
            sleep(60)
            summary = self.statsCollector.getSummary()
            self.logger.info("Statistics update: {0}".format(summary))
            with open(self.fileName, 'w') as f:
                ujson.dump(summary, f)


class StatsDBWriter(Thread):
    def __init__(self, statsCollector):
        super(StatsDBWriter, self).__init__()
        self.statsCollector = statsCollector
        self.setDaemon(True)

    def run(self):
        conn = psycopg2.connect(
            user=os.environ.get("POSTGRES_USER"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            database=os.environ.get("POSTGRES_DB"),
            host=os.environ.get("POSTGRES_HOST", "localhost")
        )

        while True:
            sleep(60)
            summary = self.statsCollector.getSummary()
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE trawler_stats")
                cursor.execute("INSERT INTO trawler_stats(stats, time) VALUES (%s, %s)", (ujson.dumps(summary), datetime.utcnow()))
                conn.commit()


class StatsHandler(object):
    def __init__(self, stats_collector):
        self.stats_collector = stats_collector

    def start_region(self, region):
        self.stats_collector.datapoint('current_region', region)

    def orders(self, orders):
        self.stats_collector.tally('orders_received', len(orders))

    def end_region(self, region):
        self.stats_collector.tally('regions_processed')
        self.stats_collector.datapoint("database_last_updated", datetime.datetime.now().isoformat())
