from setuptools import setup, find_packages
import re

VERSIONFILE = "src/esi/_version.py"
verstr = "unknown"
try:
    verstrline = open(VERSIONFILE, "rt").read()
    VSRE = r"^VERSION = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
except EnvironmentError:
    print "unable to find version in %s" % (VERSIONFILE,)
    raise RuntimeError("if %s exists, it is required to be well-formed" % (VERSIONFILE,))

setup(
    name='esi-market-trawler',
    version=verstr,
    description='EVE Online ESI market trawler',
    author='James Muscat',
    author_email='jamesremuscat@gmail.com',
    url='https://github.com/jamesremuscat/esi-market-trawler',
    packages=find_packages('src', exclude=["*.tests"]),
    package_dir={'': 'src'},
    long_description="""\
        A market trawler for EVE Online using the ESI API and dumping into a Postgres database.
      """,
    setup_requires=[],
    tests_require=[],
    install_requires=["backoff", "python-dateutil", "psycopg2", "requests", "ujson"],
    entry_points={
        'console_scripts': [
            'esi-market-trawler = esi.market.trawler:main',
        ],
    }
)
