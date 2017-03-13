#!/usr/bin/env python

from distutils.core import setup

setup(name='gmstk',
      version='0.2.3',
      description='GMS tooklit',
      author='Alex Wagner',
      author_email='awagner24@wustl.edu',
      url='https://github.com/ahwagner/gmstk',
      license='MIT',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
      ],
      keywords='gms toolkit',
      packages=['gmstk'],
      install_requires=['paramiko', 'pandas']
      )
