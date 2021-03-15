# coding: utf-8

import os

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    from freecad.workbench_gespal3d import __version__ as wb_version
    from freecad.workbench_gespal3d import ICONPATH
    from freecad.workbench_gespal3d import print_debug


__title__ = "Gespal 3D Help"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class _ShowHelp:
    """Export plan de fabrication"""

    def GetResources(self):

        return {
            "Pixmap": os.path.join(ICONPATH, "help-browser.svg"),
            "Accel": "H,F",
            "MenuText": "Gespal 3D Aide",
            "ToolTip": "<html><head/><body><p><b>Affiche la version de Gespal 3D</b> \
                </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        msg = (
            "<html><head/><body><p><b>Gespal 3D</b> \
        </p><p>Version : %s</p></body></html>"
            % (str(wb_version))
        )
        reply = QtGui.QMessageBox.information(None, "", msg)
        return


if App.GuiUp:
    Gui.addCommand("G3D_Help", _ShowHelp())
