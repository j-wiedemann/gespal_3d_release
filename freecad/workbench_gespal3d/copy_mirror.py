###########################################################################
#                                                                         *
#   Copyright (c) 2019                                                    *
#   Jonathan Wiedemann <contact@freecad-france.com>                       *
#                                                                         *
#   This program is free software; you can redistribute it and/or modify  *
#   it under the terms of the GNU Lesser General Public License (LGPL)    *
#   as published by the Free Software Foundation; either version 2 of     *
#   the License, or (at your option) any later version.                   *
#   for detail see the LICENCE text file.                                 *
#                                                                         *
#   This program is distributed in the hope that it will be useful,       *
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#   GNU Library General Public License for more details.                  *
#                                                                         *
#   You should have received a copy of the GNU Library General Public     *
#   License along with this program; if not, write to the Free Software   *
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#   USA                                                                   *
###########################################################################


import FreeCAD
import DraftVecUtils
from FreeCAD import Vector

# from freecad.workbench_gespal3d import profiles_parser
from freecad.workbench_gespal3d import tracker
from freecad.workbench_gespal3d import connect_db
from freecad.workbench_gespal3d import DEBUG
from freecad.workbench_gespal3d import PARAMPATH
import math

if FreeCAD.GuiUp:
    import FreeCADGui
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


__title__ = "Copy Mirror Gespal3D"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def makeCopyMirror(objs, plane):
    support = plane.Support[0][0].Name

    if support == "XY_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = FreeCAD.Vector(0.0, 0.0, offset,)
        normal = FreeCAD.Vector(0.0, 0.0, 1.0,)
        expression1 = ".Base.z"
        expression2 = u"DPSymXY.AttachmentOffset.Base.z"

    elif support == "XZ_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = FreeCAD.Vector(0.0, offset, 0.0,)
        normal = FreeCAD.Vector(0.0, 1.0, 0.0,)
        expression1 = ".Base.y"
        expression2 = u"DPSymXZ.AttachmentOffset.Base.z"

    elif support == "YZ_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = FreeCAD.Vector(offset, 0.0, 0.0,)
        normal = FreeCAD.Vector(1.0, 0.0, 0.0,)
        expression1 = ".Base.x"
        expression2 = u"DPSymYZ.AttachmentOffset.Base.z"
    else:
        pass

    doc = FreeCAD.ActiveDocument

    for obj in objs:
        mirror = doc.addObject("Part::Mirroring")
        mirror.Source = obj
        label = obj.Label + u" Mirroir"
        mirror.Label = label
        mirror.Normal = normal
        mirror.Base = base
        mirror.setExpression(expression1, expression2)
        mirror.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
    doc.recompute()
    return


class _CopyMirrorTaskPanel:
    def __init__(self):
        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.indication_label = QtGui.QLabel(self.form)
        self.grid.addWidget(self.indication_label)
        self.retranslateUi(self.form)
        self.PlaneVisibility(True)

    def PlaneVisibility(self, show=True):
        doc = FreeCAD.ActiveDocument
        if show == True:
            doc.DPSymXY.ViewObject.Visibility = True
            doc.DPSymXZ.ViewObject.Visibility = True
            doc.DPSymYZ.ViewObject.Visibility = True
        else:
            doc.DPSymXY.ViewObject.Visibility = False
            doc.DPSymXZ.ViewObject.Visibility = False
            doc.DPSymYZ.ViewObject.Visibility = False

    def accept(self):

        sel = FreeCADGui.Selection.getSelection()
        if len(sel) > 1:
            plane = sel[-1]
            objs = sel[:-1]
            if plane.TypeId == "PartDesign::Plane":
                # makeCopyMirror(objs, plane)
                FreeCAD.ActiveDocument.openTransaction(
                    translate("Gespal3D", "Create Mirror")
                )
                FreeCADGui.addModule("freecad.workbench_gespal3d.copy_mirror")
                FreeCADGui.doCommand("sel = FreeCADGui.Selection.getSelection()")
                FreeCADGui.doCommand("plane = sel[-1]")
                FreeCADGui.doCommand("objs = sel[:-1]")
                FreeCADGui.doCommand(
                    "freecad.workbench_gespal3d.copy_mirror.makeCopyMirror(objs, plane)"
                )
                FreeCAD.ActiveDocument.commitTransaction()
            else:
                print("La sélection ne contient pas de plan de référence")
        else:
            print("La sélection n'est pas bonne.")
        self.PlaneVisibility(False)
        return True

    def reject(self):
        self.PlaneVisibility(False)
        FreeCAD.Console.PrintMessage("Annulation de la copie par symétrie.\n")
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle("Plan de symétrie")
        self.indication_label.setText(
            "Sélectionner les objets à copier et le plan de symétrie puis cliquer sur Ok."
        )


class _CommandCopyMirror:
    "commande pour faire une copie en mirroir d'un ou plusieurs obj selon un plan"

    def __init__(self):
        pass

    def GetResources(self):
        return {
            "Pixmap": "Draft_Mirror",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Mirroir"),
            "Accel": "P, R",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Gespal3D",
                "Créer une copie mirroir d'un ou plusieur composant selon le plan sélectionné.",
            ),
        }

    def IsActive(self):
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True
        else:
            active = False
        return active

    def Activated(self):
        panel = _CopyMirrorTaskPanel()
        # self.PlaneVisibility(True)
        FreeCADGui.Control.showDialog(panel)
        # self.PlaneVisibility(False)

    def PlaneVisibility(self, show=True):
        doc = FreeCAD.ActiveDocument
        if show == True:
            doc.DPSymXY.ViewObject.Visibility = True
            doc.DPSymXZ.ViewObject.Visibility = True
            doc.DPSymYZ.ViewObject.Visibility = True
        else:
            doc.DPSymXY.ViewObject.Visibility = False
            doc.DPSymXZ.ViewObject.Visibility = False
            doc.DPSymYZ.ViewObject.Visibility = False


if FreeCAD.GuiUp:
    FreeCADGui.addCommand("CopyMirror", _CommandCopyMirror())
