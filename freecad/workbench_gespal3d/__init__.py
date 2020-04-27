import os
from .version import __version__

print("Gespal3D version", __version__)

RESOURCESPATH = os.path.join(os.path.dirname(__file__), "resources")
ICONPATH = os.path.join(RESOURCESPATH, "icons")
PARAMPATH = "User parameter:BaseApp/Preferences/Mod/Gespal3D"

DEBUG = False  # general
DEBUG_T = False  # tracker
