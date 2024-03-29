#!/usr/bin/env python3
# vim: sw=4 sts=4 et fileencoding=utf-8 nomod

from distutils.core import setup

setup(name='sixx',
      version='0.1',
      description='Network database of personal contacts',
      author='Andrew Bettison',
      author_email='andrew@iverin.com.au',
      packages=['sixx', 'sixx/reports'],
      scripts=['scripts/six']
     )
