# -*- coding: utf-8 -*-

import os
from setuptools import setup
from setuptools import find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

# import version number
version = {}
with open("./sr700api/version.py") as fp:
    exec(fp.read(), version)
# later on we use: version['__version__']

# get deploy key from https://help.github.com/articles/git-automation-with-oauth-tokens/
# github_token = os.environ['GITHUB_TOKEN']

setup(
    name='sr700api',
    version=version['__version__'],
    description='A Python module to control a FreshRoast SR700 coffee roaster'
        ' with Artisan software, requiring a temperature probe connected '
        'to a v3.6 Bus Pirate.',
    long_description=long_description,
    url='https://none',
    author='int3ll3ct',
    author_email='int3ll3ct.ly@gmail.com',
    maintainer='int3ll3ct',
    maintainer_email='int3ll3ct.ly@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'flask-restful>=0.3.6',
        'requests',
        'freshroastsr700>=0.2.4'
        # 'pyBusPirateLite'
    ],
    scripts=['bin/sr700api']
    # This requires git OAuth tokens to run,
    # and requires pip install with --process-dependency-links option
    # dependency_links=[
    #     'git+https://{github_token}@github.com/juhasch/{package}.git/@{version}#egg={package}-0'
    #     .format(github_token=github_token, package=pyBusPirateLite, version=master)
    # ]
)
