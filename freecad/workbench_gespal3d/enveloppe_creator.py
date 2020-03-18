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


def makeEnveloppe(id=None, name=None, length=1000, width=1000, height=1000):
    doc = FreeCAD.ActiveDocument
    if not id:
        id = "Produit"
    if name:
        doc.Comment = str(name)
    # Part Box variante
    """box = doc.addObject("Part::Box", "Product")
    box.Label = id
    box.Length = length
    box.Height = height
    box.Width = width
    box.ViewObject.DisplayMode = u"Wireframe"
    box.ViewObject.DrawStyle = u"Dashed"
    """
    # Body variante
    body = doc.addObject("PartDesign::Body", "Product")
    box = doc.addObject("PartDesign::AdditiveBox", "Box")
    body.addObject(box)
    box.Support = doc.getObject("XY_Plane")
    box.MapMode = "FlatFace"
    box.Length = length
    box.Width = width
    box.Height = height
    body.Label = id
    body.ViewObject.DisplayMode = u"Wireframe"
    body.ViewObject.DrawStyle = u"Dashed"
    box.recompute()
    body.recompute()
    dp_names = ["DPSymXY", "DPSymXZ", "DPSymYZ"]
    dp_planes = ["XY_Plane", "XZ_Plane", "YZ_Plane"]
    dp_offset = [height / 2, width / 2, length / 2]
    dp_expressions = [u"Box.Height / 2 ", u"Box.Width / 2", u"Box.Length / 2"]
    c = 0
    for name in dp_names:
        dp = body.newObject("PartDesign::Plane", name)
        dp.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0000000000, 0.0000000000, dp_offset[c]),
            FreeCAD.Rotation(0.0000000000, 0.0000000000, 0.0000000000),
        )
        if c != 1:
            dp.MapReversed = False
        else:
            dp.MapReversed = True
        dp.Support = doc.getObject(dp_planes[c])
        dp.MapMode = "FlatFace"
        dp.setExpression(".AttachmentOffset.Base.z", dp_expressions[c])
        dp.ViewObject.Visibility = False
        dp.recompute()
        c += 1
    box.recompute()
    body.recompute()
    doc.recompute(None, True, True)

    # Dimensions
    dimensions = []
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(length, 0.0, 0.0),
        FreeCAD.Vector(0.0, -200, 0.0),
    )
    dim.setExpression(".End.x", u"Box.Length")
    dimensions.append(dim)
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, width, 0.0),
        FreeCAD.Vector(-200.0, 0.0, 0.0),
    )
    dim.setExpression(".End.y", u"Box.Width")
    dimensions.append(dim)
    dim = Draft.makeDimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, height),
        FreeCAD.Vector(-200.0, -200.0, 0.0),
    )
    dim.setExpression(".End.z", u"Box.Height")
    dimensions.append(dim)
    for dim in dimensions:
        dim.ViewObject.DisplayMode = u"3D"
        dim.ViewObject.ExtLines = "-50 mm"
        dim.ViewObject.ArrowType = u"Tick-2"
        dim.ViewObject.ArrowSize = "10 mm"
        dim.ViewObject.DimOvershoot = "15 mm"
        dim.ViewObject.Decimals = 0

    FreeCADGui.Selection.clearSelection()


class _CommandEnveloppe:

    "the Arch Structure command definition"

    def __init__(self):
        self.beammode = True

    def GetResources(self):
        return {
            "Pixmap": "Arch_Space",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Produit"),
            "Accel": "P, R",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Gespal3D", "Créer un composant de type bois ou dès."
            ),
        }

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
        makeEnveloppe(None, "Test", 1200.0, 900.0, 560.0)
        # Set view
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")


if FreeCAD.GuiUp:
    FreeCADGui.addCommand("EnveloppeCreator", _CommandEnveloppe())
