from datetime import datetime, timedelta
from esi._version import VERSION

import base64
import logging
import os
import requests
import time
import backoff


USER_AGENT_STRING = 'esi-market-trawler/{} (muscaat@eve-markets.net)'.format(VERSION)


class TokenStore(object):
    def __init__(self, credentials):
        self.refresh_token = credentials.refresh_token
        self.client_id = credentials.client_id
        self.secret = credentials.secret
        self.expiry = datetime.fromtimestamp(0)
        self.authToken = None

    def get_token(self):
        if self.expiry < datetime.now():
            self._refresh()
        return self.authToken

    def _refresh(self):
        rt = requests.post(
            'https://login.eveonline.com/oauth/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            },
            headers={
                'Authorization': 'Basic {}'.format(self._get_bearer(self.client_id, self.secret)),
                'User-Agent': USER_AGENT_STRING
            }
        )
        rt.raise_for_status()
        if rt.status_code == requests.codes.ok:
            data = rt.json()
            self.authToken = data['access_token']
            self.expiry = datetime.now() + timedelta(seconds=data['expires_in'])

    def _get_bearer(self, clientID, secret):
        return base64.b64encode(
            '{}:{}'.format(
                clientID,
                secret
            )
        )


class Credentials(object):
    def __init__(self, client_id, secret, refresh_token):
        self.client_id = client_id
        self.secret = secret
        self.refresh_token = refresh_token

    @staticmethod
    def from_environ(env=os.environ):
        if "ESI_CLIENT_ID" in os.environ:
            return Credentials(
                os.environ.get("ESI_CLIENT_ID", None),
                os.environ.get("ESI_SECRET", None),
                os.environ.get("ESI_REFRESH_TOKEN", None)
            )
        else:
            return None


# http://stackoverflow.com/a/667706/11643
def rate_limited(max_per_second):
    minInterval = 1.0 / float(max_per_second)

    def decorate(func):
        last_time_called = [0.0]

        def rate_limited_function(*args, **kargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = minInterval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.time()
            return ret
        return rate_limited_function
    return decorate


class ESI(object):
    BASE_URL = 'https://esi.tech.ccp.is'

    def __init__(self, credentials=None):
        if credentials:
            self._token_store = TokenStore(credentials)
        else:
            self._token_store = None

    @rate_limited(20)
    @backoff.on_exception(
        backoff.expo,
        requests.exceptions.HTTPError
    )
    def get(self, endpoint, version='latest', page=None):
        headers = {
            'User-Agent': USER_AGENT_STRING
        }

        if self._token_store:
            headers['Authorization'] = 'Bearer {}'.format(self._token_store.get_token())

        resp = requests.get(
            '{}/{}/{}?{}'.format(
                self.BASE_URL,
                version,
                endpoint,
                'page={}'.format(page) if page else ''
            ),
            headers=headers
        )
        resp.raise_for_status()
        return resp.json()
