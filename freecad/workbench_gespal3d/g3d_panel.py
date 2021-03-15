# coding: utf-8

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    from DraftTools import translate
    import DraftVecUtils
    from freecad.workbench_gespal3d import g3d_tracker
    from freecad.workbench_gespal3d import g3d_connect_db
    from freecad.workbench_gespal3d import PARAMPATH
    from freecad.workbench_gespal3d import DEBUG
    from PySide import QtCore, QtGui
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


__title__ = "Gespal3D Panel tool"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def typecheck(args_and_types, name="?"):
    """typecheck([arg1,type),(arg2,type),...]): checks arguments types"""
    for v, t in args_and_types:
        if not isinstance(v, t):
            w = "typecheck[" + str(name) + "]: "
            w += str(v) + " is not " + str(t) + "\n"
            App.Console.PrintWarning(w)
            raise TypeError("Draft." + str(name))


class _CommandPanel:

    "the Gespal3D Panel command definition"

    def __init__(self):
        self.thickness = 10.00
        pass

    def GetResources(self):

        return {
            "Pixmap": "Arch_Panel",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Panneaux"),
            "Accel": "P, N",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Paneaux",
                "<html><head/><body><p><b>Ajouter un panneau.</b> \
                        <br><br> \
                        ajouter un panneau en cliquant sur 2 point définissant \
                        la diagonale de l'élément.</p></body></html>",
            ),
        }

    def IsActive(self):
        active = False
        if App.ActiveDocument:
            for obj in App.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

    def Activated(self):
        # parameters
        self.p = App.ParamGet(str(PARAMPATH))

        self.continueCmd = self.p.GetBool("PanelContinue", False)

        # fetch data from sqlite database
        self.categories = g3d_connect_db.getCategories(include=["PX"])

        self.wp = App.DraftWorkingPlane
        self.basepoint = None
        self.TrackerRect = g3d_tracker.rectangleTracker()
        self.TrackerRect.setPlane(self.wp.axis)
        title = translate("Gespal3D", "Premier coin du panneau ") + ":"
        Gui.Snapper.getPoint(
            callback=self.getpoint,
            movecallback=self.update,
            extradlg=[self.taskbox()],
            title=title,
        )

    def getpoint(self, point=None, obj=None):
        "this function is called by the snapper when it has a 3D point"
        # no point
        if point is None:
            print("no point : finalize panel tracker")
            self.TrackerRect.finalize()
            return
        # first clic : pick rectangle origin
        if self.basepoint is None:
            print("first point : set origin panel tracker")
            self.setWorkingPlane(point=point)
            self.TrackerRect.setorigin(point)
            self.basepoint = point
            Gui.Snapper.getPoint(
                last=point,
                callback=self.getpoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Arch", "Next point") + ":",
                mode="rectangle",
            )
            return
        # second clic : make panel
        print("second point : finalize panel tracker")
        self.TrackerRect.finalize()
        print("second point : make panel transaction")
        self.makeTransaction(point)

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"
        if Gui.Control.activeDialog():
            if self.basepoint:
                self.TrackerRect.update(point)

    def taskbox(self):
        "sets up a taskbox widget"

        taskwidget = QtGui.QWidget()
        ui = Gui.UiLoader()
        taskwidget.setWindowTitle(translate("Gespal3D", "Ajout d'un panneau"))
        grid = QtGui.QGridLayout(taskwidget)

        # categories box
        categories_items = [x[1] for x in self.categories]
        categories_label = QtGui.QLabel(translate("Gespal3D", "C&atégorie"))
        self.categories_cb = QtGui.QComboBox()
        categories_label.setBuddy(self.categories_cb)
        self.categories_cb.addItems(categories_items)
        grid.addWidget(categories_label, 2, 0, 1, 1)
        grid.addWidget(self.categories_cb, 2, 1, 1, 1)

        # presets box
        presets_label = QtGui.QLabel(translate("Gespal3D", "&Type"))
        self.composant_cb = QtGui.QComboBox()
        presets_label.setBuddy(self.composant_cb)
        grid.addWidget(presets_label, 3, 0, 1, 1)
        grid.addWidget(self.composant_cb, 3, 1, 1, 1)

        # presets box
        presets_label = QtGui.QLabel(translate("Gespal3D", "Plan"))
        self.wp_cb = QtGui.QComboBox()
        self.wp_cb.addItems(["+XY", "+XZ", "+YZ", "-XY", "-XZ", "-YZ"])
        grid.addWidget(presets_label, 4, 0, 1, 1)
        grid.addWidget(self.wp_cb, 4, 1, 1, 1)

        # length
        thickness_label = QtGui.QLabel(translate("Gespal3D", "Épaisseur"))
        self.thickness_input = ui.createWidget("Gui::InputField")
        self.thickness_input.setText(
            App.Units.Quantity(10.0, App.Units.Length).UserString
        )
        grid.addWidget(thickness_label, 6, 0, 1, 1)
        grid.addWidget(self.thickness_input, 6, 1, 1, 1)

        # continue button
        continue_label = QtGui.QLabel(translate("Arch", "Con&tinue"))
        continue_cb = QtGui.QCheckBox()
        continue_cb.setObjectName("ContinueCmd")
        continue_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        continue_label.setBuddy(continue_cb)
        if hasattr(Gui, "draftToolBar"):
            continue_cb.setChecked(Gui.draftToolBar.continueMode)
            self.continueCmd = Gui.draftToolBar.continueMode
        grid.addWidget(continue_label, 17, 0, 1, 1)
        grid.addWidget(continue_cb, 17, 1, 1, 1)

        # connect slots
        QtCore.QObject.connect(
            self.categories_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setCategory,
        )
        QtCore.QObject.connect(
            self.composant_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setComposant,
        )

        QtCore.QObject.connect(
            self.wp_cb, QtCore.SIGNAL("currentIndexChanged(int)"), self.setWorkingPlane
        )

        QtCore.QObject.connect(
            continue_cb, QtCore.SIGNAL("stateChanged(int)"), self.setContinue
        )

        QtCore.QObject.connect(
            self.thickness_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setThickness,
        )

        self.restoreParams()

        return taskwidget

    def restoreParams(self):
        if DEBUG:
            App.Console.PrintMessage("Panel restoreParams \n")
        stored_composant = self.p.GetInt("PanelPreset", 5)
        stored_wp = wp = self.p.GetInt("PanelWP", 0)

        if stored_composant:
            if DEBUG:
                App.Console.PrintMessage("restore composant \n")
            comp = g3d_connect_db.getComposant(id=stored_composant)
            cat = comp[2]
            n = 0
            for x in self.categories:
                if x[0] == cat:
                    self.categories_cb.setCurrentIndex(n)
                n += 1
            self.composant_items = g3d_connect_db.getComposants(categorie=cat)
            self.composant_cb.clear()
            self.composant_cb.addItems([x[1] for x in self.composant_items])
            n = 0
            for x in self.composant_items:
                if x[0] == stored_composant:
                    self.composant_cb.setCurrentIndex(n)
                n += 1

        if stored_wp:
            self.wp_cb.setCurrentIndex(wp)
        self.setWorkingPlane()

    def setCategory(self, i):
        self.composant_cb.clear()
        fc_compteur = self.categories[i][0]
        self.composant_items = g3d_connect_db.getComposants(categorie=fc_compteur)
        self.composant_cb.addItems([x[1] for x in self.composant_items])

    def setComposant(self, i):
        self.Profile = None
        id = self.composant_items[i][0]
        comp = g3d_connect_db.getComposant(id=id)

        if comp:
            self.Profile = comp
            # width
            if float(comp[5]) > 0.0:
                self.thickness_input.setText(
                    App.Units.Quantity(
                        float(comp[5]), App.Units.Length
                    ).UserString
                )
                self.thickness_input.setDisabled(True)
            else:
                self.thickness_input.setDisabled(False)

            """# height
            if float(comp[4]) > 0.0:
                self.height_input.setText(
                    App.Units.Quantity(
                        float(comp[4]),
                        App.Units.Length).UserString)
                self.height_input.setDisabled(True)
            else:
                self.height_input.setDisabled(False)

            # length
            if float(comp[3]) > 0.0:
                self.length_input.setText(
                    App.Units.Quantity(
                        float(comp[3]),
                        App.Units.Length).UserString)
                self.length_input.setDisabled(True)
            else:
                self.setDirection()
                self.length_input.setDisabled(False)"""

            self.p.SetInt("PanelPreset", comp[0])

    def setWorkingPlane(self, idx=None, point=None):
        if idx is None:
            idx = self.wp_cb.currentIndex()
        else:
            self.p.SetInt("PanelWP", idx)
        axis_list = [
            App.Vector(0.0, 0.0, 1.0),
            App.Vector(0.0, 1.0, 0.0),
            App.Vector(1.0, 0.0, 0.0),
            App.Vector(0.0, 0.0, -1.0),
            App.Vector(0.0, -1.0, 0.0),
            App.Vector(-1.0, 0.0, 0.0),
        ]

        upvec_list = [
            App.Vector(0.0, 1.0, 0.0),
            App.Vector(1.0, 0.0, 0.0),
            App.Vector(0.0, 0.0, 1.0),
            App.Vector(0.0, -1.0, 0.0),
            App.Vector(-1.0, 0.0, 0.0),
            App.Vector(0.0, 0.0, -1.0),
        ]

        if point is None:
            self.wp.alignToPointAndAxis(
                point=App.Vector(0.0, 0.0, 0.0),
                axis=axis_list[idx],
                upvec=upvec_list[idx],
            )
        else:
            self.wp.alignToPointAndAxis(
                point=point,
                axis=axis_list[idx],
                upvec=upvec_list[idx],
            )

        Gui.Snapper.toggleGrid()
        Gui.Snapper.toggleGrid()
        self.TrackerRect.setPlane(axis_list[idx])

    def setThickness(self, d):
        self.thickness = d

    def setContinue(self, i):
        self.continueCmd = bool(i)
        if hasattr(Gui, "draftToolBar"):
            Gui.draftToolBar.continueMode = bool(i)
        self.p.SetBool("PanelContinue", bool(i))

    def makeTransaction(self, point=None):
        if point is not None:
            p1 = self.basepoint
            p3 = point
            diagonal = p3.sub(p1)
            p2 = p1.add(DraftVecUtils.project(diagonal, self.wp.v))
            p4 = p1.add(DraftVecUtils.project(diagonal, self.wp.u))
            length = p4.sub(p1).Length
            a = abs(DraftVecUtils.angle(p4.sub(p1), self.wp.u, self.wp.axis))
            if a > 1:
                length = -length
            height = p2.sub(p1).Length
            a = abs(DraftVecUtils.angle(p2.sub(p1), self.wp.v, self.wp.axis))
            if a > 1:
                height = -height
            base = p1
            p = self.wp.getRotation()
            qr = p.Rotation.Q
            qr = (
                "("
                + str(qr[0])
                + ","
                + str(qr[1])
                + ","
                + str(qr[2])
                + ","
                + str(qr[3])
                + ")"
            )

            if (length > 0) and (height > 0):
                print("length > 0) and (height > 0)")
                base = base.add(diagonal.scale(0.5, 0.5, 0.5))
            elif (length == 0) or (height == 0):
                print("(length == 0) or (height == 0)")
                print("Abort")
                return
            elif (length < 0) and (height < 0):
                print("(length < 0) and (height < 0)")
                length = -length
                height = -height
                base = base.add(diagonal.scale(0.5, 0.5, 0.5))
            elif length < 0:
                print("length < 0")
                length = -length
                base = base.add(diagonal.scale(0.5, 0.5, 0.5))
            elif height < 0:
                print("height < 0")
                height = -height
                base = base.add(diagonal.scale(0.5, 0.5, 0.5))
            else:
                print("Situation inconnue. Veuillez contacter le support.")
                print("Abort")
                return

            App.ActiveDocument.openTransaction(
                translate("Gespal3D", "Ajouter un panneau")
            )
            Gui.addModule("Arch")

            # Create panel wit Arch Tool
            Gui.doCommand(
                "p = Arch.makePanel("
                + "length="
                + str(length)
                + ","
                + "width="
                + str(height)
                + ","
                + "thickness="
                + str(self.thickness)
                + ")"
            )

            Gui.doCommand("pl = App.Placement()")
            Gui.doCommand("pl.Rotation.Q = " + qr)
            Gui.doCommand("pl.Base = " + DraftVecUtils.toString(base))
            Gui.doCommand("p.Placement = pl")

            # Info Gespal
            Gui.doCommand('p.Label = "' + self.Profile[1] + '"')
            Gui.doCommand('p.IfcType = u"Transport Element"')
            Gui.doCommand('p.PredefinedType = u"NOTDEFINED"')
            Gui.doCommand('p.Tag = u"Gespal"')
            Gui.doCommand('p.Description = "' + str(self.Profile[0]) + '"')

            color = self.Profile[-2].split(",")
            r = str(int(color[0]) / 255)
            g = str(int(color[1]) / 255)
            b = str(int(color[2]) / 255)
            Gui.doCommand(
                "p.ViewObject.ShapeColor = (" + r + "," + g + "," + b + ")"
            )

            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            if self.continueCmd:
                self.Activated()


if App.GuiUp:
    Gui.addCommand("G3D_PanelComposant", _CommandPanel())
