from esi import Credentials, ESI
import logging
import os
import random
from esi.market.postgres import PostgresHandler
from esi.stats import StatsHandler, StatsCollector, StatsWriter, StatsDBWriter


class Trawler(object):
    log = logging.getLogger(__name__)

    def __init__(self, handlers=[], credentials=None):
        self._esi = ESI(credentials)
        self._handlers = handlers

    def _each_handler(self, method, *args, **kwargs):
        for handler in self._handlers:
            if hasattr(handler, method) and callable(getattr(handler, method)):
                getattr(handler, method)(*args, **kwargs)

    def trawl(self):
        regions = self._esi.get('universe/regions')
        random.shuffle(regions)
        region_count = len(regions)

        while True:
            self._each_handler('start_trawl')
            for idx, region in enumerate(regions):
                self.log.info('Trawling for region {} [{}/{}]'.format(region, idx + 1, region_count))
                self._each_handler('start_region', region)
                market_url = 'markets/{}/orders'.format(region)
                last_had_orders = True
                page = 1
                while last_had_orders:
                    orders = self._esi.get(market_url, page=page)
                    last_had_orders = len(orders) > 0
                    self.log.info('Retrieved {} orders from region {} page {}'.format(len(orders), region, page))
                    self._each_handler('orders', orders)
                    page += 1
                self._each_handler('end_region', region)
            self._each_handler('finish_trawl')


def main():
    logging.basicConfig(level=logging.INFO)

    s = StatsCollector()
    sw = StatsWriter(s)
    s.start()
    sw.start()

    handlers = [
        StatsHandler(s)
    ]

    if 'POSTGRES_USER' in os.environ:
        logging.info("Using postgres")
        handlers.append(
            PostgresHandler.create(
                os.environ.get("POSTGRES_USER"),
                os.environ.get("POSTGRES_PASSWORD"),
                os.environ.get("POSTGRES_HOST", "localhost"),
                os.environ.get("POSTGRES_DB")
            )
        )

        sdw = StatsDBWriter(s)
        sdw.start()

    trawler = Trawler(
        handlers=handlers,
        credentials=Credentials.from_environ()
    )
    trawler.trawl()

if __name__ == '__main__':
    main()
