# coding: utf-8

import os
from .version import __version__
import FreeCAD


__title__ = "Gespal 3D init"
__author__ = "Jonathan Wiedemann"
__license__ = "LGPLv2.1"
__url__ = "https://freecad-france.com"


print("Gespal3D v{} loaded".format(__version__))

RESOURCESPATH = os.path.join(os.path.dirname(__file__), "resources")
ICONPATH = os.path.join(RESOURCESPATH, "icons")
UIPATH = os.path.join(RESOURCESPATH, "ui")
PARAMPATH = "User parameter:BaseApp/Preferences/Mod/Gespal3D"

DEBUG = False  # general
DEBUG_U = False  # beam update
DEBUG_T = False  # tracker
DEBUG_DB = False  # database connect


def print_debug(messages):
    if DEBUG:
        if type(messages) is list:
            for msg in messages:
                msg = str(msg) + "\n"
                FreeCAD.Console.PrintMessage(msg)
        else:
            messages = messages + "\n"
            FreeCAD.Console.PrintMessage(messages)
