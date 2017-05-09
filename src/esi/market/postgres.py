import datetime
import dateutil.parser
import io
import logging
import psycopg2
import sys


# Taken from https://gist.github.com/jsheedy/ed81cdf18190183b3b7d
class IteratorFile(io.TextIOBase):
    """ given an iterator which yields strings,
    return a file like object for reading those strings """

    def __init__(self, it):
        self._it = it
        self._f = io.StringIO()

    def read(self, length=sys.maxsize):

        try:
            while self._f.tell() < length:
                self._f.write(next(self._it) + "\n")
        except StopIteration as e:
            # soak up StopIteration. this block is not necessary because
            # of finally, but just to be explicit
            pass

        except Exception as e:
            print("uncaught exception: {}".format(e))
        finally:
            self._f.seek(0)
            data = self._f.read(length)

            # save the remainder for next read
            remainder = self._f.read()
            self._f.seek(0)
            self._f.truncate(0)
            self._f.write(remainder)
            return data

    def readline(self):
        return next(self._it)


def map_range(rangeStr):
    if rangeStr == "station":
        return -1
    if rangeStr == "solarsystem":
        return 0
    if rangeStr == "region":
        return 32767
    return int(rangeStr)


def map_order_for(region):
    def map_order(order):
        realIssueDate = dateutil.parser.parse(order['issued'])
        expiry = realIssueDate + datetime.timedelta(days=order['duration'])
        return [
            order['order_id'],
            order['type_id'],
            region,
            order['price'],
            order['volume_remain'],
            map_range(order['range']),
            order['volume_total'],
            order['min_volume'],
            order['is_buy_order'],
            order['issued'],
            order['duration'],
            order['location_id'],
            expiry
        ]
    return map_order


class PostgresHandler(object):
    log = logging.getLogger(__name__)

    def __init__(self, connection):
        self.connection = connection

    def start_region(self, region):
        self.cursor = self.connection.cursor()
        self.cursor.execute("DELETE FROM live_orders WHERE regionID=%s", [region])
        self.current_region = region

    def orders(self, orders):
        try:
            itf = IteratorFile((
                u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(*x) for x in map(map_order_for(self.current_region), orders)
            ))

            with self.connection.cursor() as cur:

                cur.copy_from(
                    itf,
                    'live_orders',
                    columns=(
                        'orderid',
                        'typeid',
                        'regionid',
                        'price',
                        'volRemaining',
                        'range',
                        'volEntered',
                        'minVolume',
                        'isBid',
                        'issueDate',
                        'duration',
                        'locationid',
                        'expiry'
                    ),
                    null="None"
                )
        except psycopg2.IntegrityError:
            # https://github.com/ccpgames/esi-issues/issues/194
            self.log.warn('Discarding page as it contains a duplicated order ID')

    @staticmethod
    def create(username, password, host, database):
        conn = psycopg2.connect(
            user=username,
            password=password,
            host=host,
            database=database
        )
        conn.autocommit = True
        return PostgresHandler(conn)
