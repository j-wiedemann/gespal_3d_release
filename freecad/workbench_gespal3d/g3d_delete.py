import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond

from freecad.workbench_gespal3d import DEBUG
from freecad.workbench_gespal3d import ICONPATH
import math
import os


__title__ = "Gespal 3D Delete tool"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def delete_G3Dcomposant(obj):
    App.ActiveDocument.removeObject(obj.Name)


class _Command_Delete:

    "Gespal 3D - Delete tool"

    def __init__(self):
        pass

    def GetResources(self):

        return {
            "Pixmap": os.path.join(ICONPATH, "delete.svg"),
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Supprimer le(s) composant(s)"),
            "Accel": "C, O",
            "ToolTip": "<html><head/><body><p><b>Supprimer le(s) composant(s) sélectionné(s).</b> \
                    <br><br> \
                    Sélectionner un ou plusieurs composants pour les supprimer. \
                    </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = False
        if len(Gui.Selection.getSelection()) > 0:
            active = True
        return active

    def Activated(self):
        delete_list = []
        selection = Gui.Selection.getSelection()
        for sel in selection:
            if hasattr(sel, "Tag"):
                if sel.Tag == "Gespal":
                    if len(sel.OutList) > 0:
                        if sel.Base:
                            delete = True
                            for obj in sel.Base.InList:
                                if not obj in selection:
                                    delete = False
                            if delete == True:
                                delete_list.append(sel.Base)
                        if len(sel.Subtractions) > 0:
                            for obj in sel.Subtractions:
                                delete_list.append(obj)
                        if len(sel.Additions) > 0:
                            for obj in sel.Additions:
                                delete_list.append(obj)
                        delete_list.append(sel)
                    elif len(sel.OutList) == 0:
                        delete_list.append(sel)
            if "Part__Mirroring" in sel.Name:
                delete_list.append(sel)
        if len(delete_list) > 0:
            App.ActiveDocument.openTransaction(
                translate("Gespal3D", "Delete composants")
            )
            for obj in delete_list:
                Gui.doCommand(
                    "App.ActiveDocument.removeObject('%s')" % obj.Name
                )
            App.ActiveDocument.commitTransaction()


if App.GuiUp:
    Gui.addCommand("G3D_Delete", _Command_Delete())
