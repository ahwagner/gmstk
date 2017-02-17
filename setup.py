#!/usr/bin/env python

from distutils.core import setup

setup(name='gmstk',
      version='0.1',
      description='GMS tooklit',
      author='Alex Wagner',
      author_email='awagner24@wustl.edu',
      packages=['gmstk'],
      requires=['paramiko', 'pandas'],
      provides=['gmstk']
      )
