import os
from .version import __version__
import FreeCAD


print("Gespal3D version", __version__)

RESOURCESPATH = os.path.join(os.path.dirname(__file__), "resources")
ICONPATH = os.path.join(RESOURCESPATH, "icons")
PARAMPATH = "User parameter:BaseApp/Preferences/Mod/Gespal3D"

DEBUG = False  # general
DEBUG_U = False  # beam update
DEBUG_T = False  # tracker
DEBUG_DB = False  # database connect


def print_debug(messages):
    if DEBUG:
        if type(messages) is list:
            for msg in messages:
                FreeCAD.Console.PrintMessage("\n")
                FreeCAD.Console.PrintMessage(msg)
        else:
            FreeCAD.Console.PrintMessage("\n")
            FreeCAD.Console.PrintMessage(messages)
