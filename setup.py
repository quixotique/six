#!/usr/local/stackless-2.65/bin/python2.6
# vim: sw=4 sts=4 et fileencoding=latin1 nomod

from distutils.core import setup

setup(name='six',
      version='0.1',
      description='Network database of personal contacts',
      author='Andrew Bettison',
      author_email='andrewb@zip.com.au',
      packages=['six', 'six/reports'],
      scripts=['scripts/six']
     )
