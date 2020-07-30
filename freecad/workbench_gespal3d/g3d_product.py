import FreeCAD
import Draft
import Part

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
    dim = Draft.make_linear_dimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(length, 0.0, 0.0),
        FreeCAD.Vector(0.0, -200, 0.0),
    )
    dim.setExpression(".End.x", u"Box.Length")
    dimensions.append(dim)
    dim = Draft.make_linear_dimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, width, 0.0),
        FreeCAD.Vector(-200.0, 0.0, 0.0),
    )
    dim.setExpression(".End.y", u"Box.Width")
    dimensions.append(dim)
    dim = Draft.make_linear_dimension(
        FreeCAD.Vector(0.0, 0.0, 0.0),
        FreeCAD.Vector(0.0, 0.0, height),
        FreeCAD.Vector(-200.0, -200.0, 0.0),
    )
    dim.setExpression(".End.z", u"Box.Height")
    dimensions.append(dim)
    for dim in dimensions:
        dim.ViewObject.DisplayMode = u"3D"
        dim.ViewObject.FontSize = "2.5 mm"
        dim.ViewObject.ExtLines = "-50 mm"
        dim.ViewObject.ArrowType = u"Tick-2"
        dim.ViewObject.ArrowSize = "10 mm"
        dim.ViewObject.DimOvershoot = "15 mm"
        dim.ViewObject.Decimals = 0

    FreeCADGui.Selection.clearSelection()


class _CommandEnveloppe:

    "the G3D Product command definition"

    def __init__(self):
        pass

    def GetResources(self):
        return {
            "Pixmap": "Arch_Space",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Produit"),
            "Accel": "P, R",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Gespal3D",
                "<html><head/><body><p><b>Créer un produit.</b> \
                        <br><br> \
                        Un produit est une enveloppe de la palette ou la caisse \
                        à réaliser.</p></body></html>",
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
        panel = _EnveloppeTaskPanel()
        FreeCADGui.Control.showDialog(panel)


class _EnveloppeTaskPanel:

    "the G3D Product taskpanel class"

    def __init__(self):
        # form widget
        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        # freecad specific input field
        ui = FreeCADGui.UiLoader()
        # grid layout
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        # ID row
        self.id = QtGui.QLabel(self.form)
        self.grid.addWidget(
            self.id, 0, 0,
        )
        self.id_input = QtGui.QLineEdit(self.form)
        self.grid.addWidget(
            self.id_input, 0, 1,
        )
        # Name row
        self.name = QtGui.QLabel(self.form)
        self.grid.addWidget(
            self.name, 1, 0,
        )
        self.name_input = QtGui.QLineEdit(self.form)
        self.grid.addWidget(
            self.name_input, 1, 1,
        )
        # Length row
        self.length_label = QtGui.QLabel(self.form)
        self.grid.addWidget(
            self.length_label, 2, 0,
        )
        self.length_input = ui.createWidget("Gui::InputField")
        self.length_input.setText(
            FreeCAD.Units.Quantity(1200.00, FreeCAD.Units.Length).UserString
        )
        self.grid.addWidget(
            self.length_input, 2, 1,
        )
        # Width row
        self.width_label = QtGui.QLabel(self.form)
        self.grid.addWidget(
            self.width_label, 3, 0,
        )
        self.width_input = ui.createWidget("Gui::InputField")
        self.width_input.setText(
            FreeCAD.Units.Quantity(900.00, FreeCAD.Units.Length).UserString
        )
        self.grid.addWidget(
            self.width_input, 3, 1,
        )
        # Height row
        self.height_label = QtGui.QLabel(self.form)
        self.grid.addWidget(
            self.height_label, 4, 0,
        )
        self.height_input = ui.createWidget("Gui::InputField")
        self.height_input.setText(
            FreeCAD.Units.Quantity(560.00, FreeCAD.Units.Length).UserString
        )
        self.grid.addWidget(
            self.height_input, 4, 1,
        )
        self.retranslateUi(self.form)

    def accept(self):
        id = self.id_input.text()
        if id == "":
            id = "None"
        name = self.name_input.text()
        if name == "":
            name = "None"
        length = self.length_input.property("rawValue")
        width = self.width_input.property("rawValue")
        height = self.height_input.property("rawValue")
        FreeCAD.ActiveDocument.openTransaction(translate("Gespal3D", "Create Product"))
        FreeCADGui.addModule("freecad.workbench_gespal3d.g3d_product")
        FreeCADGui.doCommand(
            "freecad.workbench_gespal3d.g3d_product.makeEnveloppe("
            + "'"
            + str(id)
            + "'"
            + ","
            + "'"
            + str(name)
            + "'"
            + ","
            + str(length)
            + ","
            + str(width)
            + ","
            + str(height)
            + ")"
        )
        FreeCAD.ActiveDocument.commitTransaction()
        # Set view
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        return True

    def reject(self):
        FreeCAD.Console.PrintMessage("Création de produit annulée.\n")
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle("Création de produit")
        self.id.setText("ID")
        self.name.setText("Nom")
        self.length_label.setText("Longueur (X)")
        self.width_label.setText("Largeur (Y)")
        self.height_label.setText("Hauteur (Z)")


if FreeCAD.GuiUp:
    FreeCADGui.addCommand("G3D_Product", _CommandEnveloppe())
