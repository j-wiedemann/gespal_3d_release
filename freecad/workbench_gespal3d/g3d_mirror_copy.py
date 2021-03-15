# coding: utf-8

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    import DraftVecUtils
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
    from freecad.workbench_gespal3d import DEBUG
    from freecad.workbench_gespal3d import PARAMPATH
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


__title__ = "Copy Mirror Gespal3D"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def makeCopyMirror(objs, plane):
    support = plane.Support[0][0].Name

    if support == "XY_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = App.Vector(0.0, 0.0, offset,)
        normal = App.Vector(0.0, 0.0, 1.0,)
        expression1 = ".Base.z"
        expression2 = u"DPSymXY.AttachmentOffset.Base.z"

    elif support == "XZ_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = App.Vector(0.0, offset, 0.0,)
        normal = App.Vector(0.0, 1.0, 0.0,)
        expression1 = ".Base.y"
        expression2 = u"DPSymXZ.AttachmentOffset.Base.z"

    elif support == "YZ_Plane":
        offset = plane.AttachmentOffset.Base.z
        base = App.Vector(offset, 0.0, 0.0,)
        normal = App.Vector(1.0, 0.0, 0.0,)
        expression1 = ".Base.x"
        expression2 = u"DPSymYZ.AttachmentOffset.Base.z"
    else:
        pass

    doc = App.ActiveDocument

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
        doc = App.ActiveDocument
        if show == True:
            doc.DPSymXY.ViewObject.Visibility = True
            doc.DPSymXZ.ViewObject.Visibility = True
            doc.DPSymYZ.ViewObject.Visibility = True
        else:
            doc.DPSymXY.ViewObject.Visibility = False
            doc.DPSymXZ.ViewObject.Visibility = False
            doc.DPSymYZ.ViewObject.Visibility = False

    def accept(self):

        sel = Gui.Selection.getSelection()
        if len(sel) > 1:
            plane = sel[-1]
            objs = sel[:-1]
            if plane.TypeId == "PartDesign::Plane":
                # makeCopyMirror(objs, plane)
                App.ActiveDocument.openTransaction(
                    translate("Gespal3D", "Create Mirror")
                )
                Gui.addModule("freecad.workbench_gespal3d.g3d_mirror_copy")
                Gui.doCommand("sel = Gui.Selection.getSelection()")
                Gui.doCommand("plane = sel[-1]")
                Gui.doCommand("objs = sel[:-1]")
                Gui.doCommand(
                    "freecad.workbench_gespal3d.g3d_mirror_copy.makeCopyMirror(objs, plane)"
                )
                App.ActiveDocument.commitTransaction()
            else:
                print("La sélection ne contient pas de plan de référence")
        else:
            print("La sélection n'est pas bonne.")
        self.PlaneVisibility(False)
        return True

    def reject(self):
        self.PlaneVisibility(False)
        App.Console.PrintMessage("Annulation de la copie par symétrie.\n")
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
        if App.ActiveDocument:
            for obj in App.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True
        else:
            active = False
        return active

    def Activated(self):
        panel = _CopyMirrorTaskPanel()
        # self.PlaneVisibility(True)
        Gui.Control.showDialog(panel)
        # self.PlaneVisibility(False)

    def PlaneVisibility(self, show=True):
        doc = App.ActiveDocument
        if show == True:
            doc.DPSymXY.ViewObject.Visibility = True
            doc.DPSymXZ.ViewObject.Visibility = True
            doc.DPSymYZ.ViewObject.Visibility = True
        else:
            doc.DPSymXY.ViewObject.Visibility = False
            doc.DPSymXZ.ViewObject.Visibility = False
            doc.DPSymYZ.ViewObject.Visibility = False


if App.GuiUp:
    Gui.addCommand("G3D_MirrorCopy", _CommandCopyMirror())
