import os
from .version import __version__

print("Gespal3D version", __version__)

ICONPATH = os.path.join(os.path.dirname(__file__), "resources")

DEBUG = False
