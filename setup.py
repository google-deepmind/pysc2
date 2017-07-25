# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module setuptools script."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from setuptools import setup


def read(fname):
  with open(os.path.join(os.path.dirname(__file__), fname)) as f:
    return f.read()


setup(
    name='PySC2',
    version='1.0',
    description='Starcraft II environment and library for training agents.',
    long_description=read('README.md'),
    author='DeepMind',
    author_email='pysc2@deepmind.com',
    license='Apache License, Version 2.0',
    keywords='StarCraft AI',
    url='https://github.com/deepmind/pysc2',
    packages=[
        'pysc2',
        'pysc2.agents',
        'pysc2.bin',
        'pysc2.env',
        'pysc2.lib',
        'pysc2.maps',
        'pysc2.run_configs',
        'pysc2.tests',
    ],
    install_requires=[
        'enum34',
        'future',
        'futures',
        'google-apputils',
        'mock',
        'numpy>=1.10',
        'portpicker',
        'protobuf>=2.6',
        'python-gflags>=3.1.1',
        'pygame',
        # 's2clientprotocol',
        'six',
        'websocket-client',
    ],
    entry_points={
        'console_scripts': [
            'pysc2_agent = pysc2.bin.agent:main',
            'pysc2_play = pysc2.bin.play:main',
            'pysc2_replay_info = pysc2.bin.replay_info:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
