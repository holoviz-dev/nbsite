#!/usr/bin/env python

import os
import sys

from nbsite.cmd import generate_rst

# if only someone had made a way to handle parameters
org = sys.argv[1]
project = sys.argv[2]
examples_path = os.path.abspath(sys.argv[3])
doc_path = os.path.abspath(sys.argv[4])
offset = 0
overwrite = bool(1)
if len(sys.argv) > 5:
    offset = int(sys.argv[5])
if len(sys.argv) > 6:
    overwrite = int(sys.argv[6])

generate_rst(
    project,
    examples=examples_path,
    doc=doc_path,
    org = org,
    repo=project,
    offset=offset,
    overwrite=bool(overwrite))
