########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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


import sys
import StringIO

import argh
import argh.utils

from docl import commands
from docl import logs


def main():
    logs.setup_logging()
    parser = argh.ArghParser()
    subparsers_action = argh.utils.get_subparsers(parser, create=True)
    subparsers_action.metavar = ''
    parser.add_commands(commands.app.commands)
    errors = StringIO.StringIO()
    parser.dispatch(errors_file=errors)
    errors_value = errors.getvalue()
    if errors_value:
        errors_value = errors_value.replace('CommandError', 'error').strip()
        sys.exit(errors_value)


if __name__ == '__main__':
    main()
