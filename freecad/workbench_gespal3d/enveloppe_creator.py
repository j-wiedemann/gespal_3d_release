import FreeCAD
import Draft
import Part
if FreeCAD.GuiUp:
    import FreeCADGui
    # from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt


def makeEnveloppe(id=None, length=1000, width=1000, height=1000):
    box = FreeCAD.ActiveDocument.addObject("Part::Box", "Product")
    if not id :
        id = "Product"
    box.Label = id
    box.Length = length
    box.Height = height
    box.Width = width
    box.ViewObject.DisplayMode = u"Wireframe"
    box.ViewObject.DrawStyle = u"Dashed"
    dimensions = []
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(length, 0.0, 0.0),
        FreeCAD.Vector(0.0, -200, 0.0))
    dimensions.append(dim)
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, width, 0.0),
        FreeCAD.Vector(-200.0, 0.0, 0.0))
    dimensions.append(dim)
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, height),
        FreeCAD.Vector(-200.0, -200.0, 0.0))
    dimensions.append(dim)
    for dim in dimensions:
        dim.ViewObject.DisplayMode = u"3D"
        dim.ViewObject.ExtLines = '-50 mm'
        dim.ViewObject.ArrowType = u"Tick-2"
        dim.ViewObject.ArrowSize = '10 mm'
        dim.ViewObject.DimOvershoot = '15 mm'
        dim.ViewObject.Decimals = 0


class _CommandEnveloppe:

    "the Arch Structure command definition"

    def __init__(self):
        self.beammode = True

    def GetResources(self):
        return {'Pixmap': 'Arch_Space',
                'MenuText': QT_TRANSLATE_NOOP("Gespal3D", "Produit"),
                'Accel': "P, R",
                'ToolTip': QT_TRANSLATE_NOOP(
                    "Arch_Structure",
                    "Creates a structure object from scratch or from a \
selected object (sketch, wire, face or solid)")}

    def IsActive(self):
        active = True
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = False
        else:
            active = False

        return active

    def Activated(self):
        makeEnveloppe(1200.0, 900.0, 560.0)
        # Set view
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('EnveloppeCreator', _CommandEnveloppe())
