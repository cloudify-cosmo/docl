########
# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

from setuptools import setup


setup(
    name='docl',
    version='0.54',
    author='Cloudify',
    author_email='cosmo-admin@cloudify.co',
    packages=[
        'docl',
        'docl.resources',
    ],
    description='Cloudify Docker dev tools',
    license='Apache License, Version 2.0',
    zip_safe=False,
    install_requires=[
        'argh==0.26.2',
        'sh==1.11',
        'path.py==8.1.2',
        'watchdog==0.8.3',
        'pyyaml==4.2b4',
        'FileServer==0.3'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'docl = docl.main:main',
        ],
    }
)
