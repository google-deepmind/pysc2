"""TODO(tewalds): DO NOT SUBMIT without one-line documentation for __init__.

TODO(tewalds): DO NOT SUBMIT without a detailed description of __init__.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from google.apputils import app
import gflags as flags

FLAGS = flags.FLAGS


def main(argv):
  del argv  # Unused.


if __name__ == '__main__':
  app.run(main)
