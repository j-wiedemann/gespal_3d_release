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


__title__ = "Beam Gespal3D"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class _CommandComposant:

    "Gespal 3D - Beam Creator tool"

    def __init__(self):
        # input mode are:
        #       "point"
        #       "line"
        #       "array"
        #       "fill"
        self.mode = "point"

    def GetResources(self):

        return {'Pixmap': 'Arch_Structure',
                'MenuText': QT_TRANSLATE_NOOP("Gespal3D", "Composant"),
                'Accel': "C, O",
                'ToolTip': "<html><head/><body><p><b>Ajouter un composant</b> \
                    (hors panneaux) . \
                    <br><br> \
                    Possibilité d'ajouter le composant par répartition ou \
                    par remplissage. \
                    </p></body></html>"}

    def IsActive(self):
        active = False
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

    def Activated(self):

        # Reads preset profiles and categorizes them
        self.categories = connect_db.getCategories(exclude=["Panneaux"])

        self.p = FreeCAD.ParamGet(str(PARAMPATH))

        product = FreeCAD.ActiveDocument.getObject("Product")
        self.product = [
            product.Length.Value,
            product.Width.Value,
            product.Height.Value]

        self.Width = self.p.GetFloat("BeamWidth", 100)
        self.Height = self.p.GetFloat("BeamHeight", 22)
        self.Length = self.p.GetFloat("BeamLength", 1200)
        self.Profile = None
        self.InsertPoint = self.p.GetInt("BeamInsertPoint", 1)
        self.Deversement = self.p.GetFloat("BeamDev", 0.0)
        self.continueCmd = self.p.GetBool("BeamContinue", True)
        self.p.GetString("BeamMode", self.mode)
        self.FillSpace = self.p.GetFloat("BeamFillSpace", 0.0)
        self.bpoint = None
        self.array_qty = self.p.GetInt("BeamArrayQty", 1)

        if DEBUG:
            msg = "TODO: Debug Beam Creator Activated"
            FreeCAD.Console.PrintMessage(msg)
            # TODO
            #msg = 'Beam Creator Activated : '
            #+ 'Params : '
            #+ 'width = %s, height = %s, length = %s, profile = %s,'
            #+ 'insert_point = %s, deversement = %s, continue = %s '
            #+ '\n' % (self.Width, self.Height, self.Length, self.Profile,
            #self.InsertPoint, self.Deversement, self.continueCmd)
            #FreeCAD.Console.PrintMessage(msg)


        # interactive mode
        self.initTracker()

    def initTracker(self):
        """if hasattr(FreeCAD,"DraftWorkingPlane"):
            FreeCAD.DraftWorkingPlane.setup()"""
        self.points = []
        self.tracker = tracker.boxTracker(
            width=self.Width,
            height=self.Height,
            length=self.Length,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)
        self.tracker.setPlacement(
            snap_bp=None, bp_idx=self.InsertPoint, dev=self.Deversement
        )
        self.tracker.on()

        # init Snapper
        if self.mode == "point":
            title = translate("Gespal3D", "Point d'insertion du composant") + ":"
        elif self.mode == "array":
            title = translate("Gespal3D", "Point de départ de la répartition") + ":"
        elif self.mode == "fill":
            title = translate("Gespal3D", "Point de départ du remplissage") + ":"
        else:
            title = translate("Gespal3D", "Point de départ du composant") + ":"
        FreeCADGui.Snapper.getPoint(
            callback=self.getPoint,
            movecallback=self.update,
            extradlg=[self.taskbox()],
            title=title)

    def getPoint(self, point=None, obj=None):
        "this function is called by the snapper when it has a 3D point"

        # pas de point
        if point is None:
            self.tracker.finalize()
            return
        # mode line et pas de 1er clic
        if (self.mode == "line") and (self.bpoint is None):
            self.bpoint = point
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getPoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Gespal3D", "Point suivant")+":",
                mode="line")
            return
        # mode array
        if (self.mode == "array") and (self.bpoint is None):
            self.bpoint = point
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getPoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Gespal3D", "Point suivant")+":",
                mode="point")
            return
        # mode array
        if (self.mode == "fill") and (self.bpoint is None):
            self.bpoint = point
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getPoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Gespal3D", "Point suivant")+":",
                mode="point")
            return
        # premier clic en mode 1 ou second en mode 2
        self.tracker.finalize()
        self.makeTransaction(point)

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"
        if DEBUG:
            FreeCAD.Console.PrintMessage("_CommandComposant update \n")

        if FreeCADGui.Control.activeDialog():
            if DEBUG:
                msg = "Current Mode is : %s \n" % self.mode
                FreeCAD.Console.PrintMessage(msg)
            if self.mode == "point":
                self.tracker.setPosition(point)
                self.tracker.on()
            elif self.mode == "array":
                self.tracker.setPosition(point)
                self.tracker.on()
            elif self.mode == "fill":
                self.tracker.setPosition(point)
                self.tracker.on()
            elif self.mode == "line":
                if self.bpoint:
                    self.tracker.update(
                        [self.bpoint.add(delta), point.add(delta)])
                    self.tracker.on()
                    tracker_length = (point.sub(self.bpoint)).Length
                    self.length_input.setText(
                        FreeCAD.Units.Quantity(
                            tracker_length,
                            FreeCAD.Units.Length
                        ).UserString)
                else:
                    self.tracker.off()
            else:
                self.tracker.off()
        else:
            FreeCADGui.Snapper.toggleGrid()

    def taskbox(self):
        "sets up a taskbox widget"

        taskwidget = QtGui.QWidget()
        ui = FreeCADGui.UiLoader()
        taskwidget.setWindowTitle(translate("Gespal3D", "Options de l'éléments"))
        layout_widget = QtGui.QVBoxLayout(taskwidget)
        grid = QtGui.QGridLayout()
        layout_widget.addLayout(grid)

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

        # direction
        direction_label = QtGui.QLabel(translate("Gespal3D", "D&irection"))
        self.direction_cb = QtGui.QComboBox()
        direction_label.setBuddy(self.direction_cb)
        self.direction_cb.addItems([
            "Direction X",
            "Direction Y",
            "Direction Z",
            "Direction -X",
            "Direction -Y",
            "Direction -Z",
            "Libre"])
        grid.addWidget(direction_label, 4, 0, 1, 1)
        grid.addWidget(self.direction_cb, 4, 1, 1, 1)

        # length
        length_label = QtGui.QLabel(translate("Gespal3D", "Longueur"))
        self.length_input = ui.createWidget("Gui::InputField")
        self.length_input.setText(
                FreeCAD.Units.Quantity(
                    self.Length, FreeCAD.Units.Length).UserString)
        grid.addWidget(length_label, 5, 0, 1, 1)
        grid.addWidget(self.length_input, 5, 1, 1, 1)

        # insert point box
        insert_label = QtGui.QLabel(translate("Gespal3D", "Insertion"))
        self.insert_group = QtGui.QButtonGroup()
        buttons_grid = QtGui.QGridLayout()

        insert = QtGui.QRadioButton("&7")
        if self.InsertPoint == 7:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 7)
        buttons_grid.addWidget(insert, 0, 0, 1, 1)

        insert = QtGui.QRadioButton("&8")
        if self.InsertPoint == 8:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 8)
        buttons_grid.addWidget(insert, 0, 1, 1, 1)

        insert = QtGui.QRadioButton("&9")
        if self.InsertPoint == 9:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 9)
        buttons_grid.addWidget(insert, 0, 2, 1, 1)

        insert = QtGui.QRadioButton("&4")
        if self.InsertPoint == 4:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 4)
        buttons_grid.addWidget(insert, 1, 0, 1, 1)

        insert = QtGui.QRadioButton("&5")
        if self.InsertPoint == 5:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 5)
        buttons_grid.addWidget(insert, 1, 1, 1, 1)

        insert = QtGui.QRadioButton("&6")
        if self.InsertPoint == 6:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 6)
        buttons_grid.addWidget(insert, 1, 2, 1, 1)

        insert = QtGui.QRadioButton("&1")
        if self.InsertPoint == 1:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 1)
        buttons_grid.addWidget(insert, 2, 0, 1, 1)

        insert = QtGui.QRadioButton("&2")
        if self.InsertPoint == 2:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 2)
        buttons_grid.addWidget(insert, 2, 1, 1, 1)

        insert = QtGui.QRadioButton("&3")
        if self.InsertPoint == 3:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 3)
        buttons_grid.addWidget(insert, 2, 2, 1, 1)

        # horizontal layout for insert point box
        horizontal_layout = QtGui.QHBoxLayout()
        spacerItemLeft = QtGui.QSpacerItem(
            20, 40,
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Minimum)
        horizontal_layout.addSpacerItem(spacerItemLeft)

        horizontal_layout.addLayout(buttons_grid)

        spacerItemRight = QtGui.QSpacerItem(
            20, 40,
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Minimum)
        horizontal_layout.addSpacerItem(spacerItemRight)

        grid.addWidget(insert_label, 7, 0, 1, 1)
        grid.addLayout(horizontal_layout, 7, 1, 1, 1)

        # deversement
        deversement_label = QtGui.QLabel(translate("Gespal3D", "Déversement"))
        self.deversement_input = QtGui.QComboBox()
        self.deversement_input.addItems(["À plat", "Sur chant"])
        """
        # with angle
        self.deversement_input = ui.createWidget("Gui::InputField")
        self.deversement_input.setText(
            FreeCAD.Units.Quantity(
                self.Deversement,
                FreeCAD.Units.Angle).UserString)
        """
        grid.addWidget(deversement_label, 8, 0, 1, 1)
        grid.addWidget(self.deversement_input, 8, 1, 1, 1)

        # width
        width_label = QtGui.QLabel(translate("Arch", "Width"))
        self.width_input = ui.createWidget("Gui::InputField")
        self.width_input.setText(
            FreeCAD.Units.Quantity(
                self.Width, FreeCAD.Units.Length).UserString)
        grid.addWidget(width_label, 12, 0, 1, 1)
        grid.addWidget(self.width_input, 12, 1, 1, 1)

        # height
        height_label = QtGui.QLabel(translate("Arch", "Height"))
        self.height_input = ui.createWidget("Gui::InputField")
        self.height_input.setText(
            FreeCAD.Units.Quantity(
                self.Height, FreeCAD.Units.Length).UserString)
        grid.addWidget(height_label, 13, 0, 1, 1)
        grid.addWidget(self.height_input, 13, 1, 1, 1)

        layout_h = QtGui.QHBoxLayout()
        layout_widget.addLayout(layout_h)

        layout_repartition = QtGui.QGridLayout()
        layout_h.addLayout(layout_repartition)

        line_vertical = QtGui.QFrame()
        line_vertical.setFrameStyle(QtGui.QFrame.VLine)
        layout_h.addWidget(line_vertical)

        layout_remplissage = QtGui.QGridLayout()
        layout_h.addLayout(layout_remplissage)

        # repartition
        self.repartition_cb = QtGui.QCheckBox(translate("Gespal3D", "&Répartition"))
        repartition_label = QtGui.QLabel(translate("Gespal3D", "Quantité"))
        self.repartition_input = QtGui.QSpinBox()
        self.repartition_input.setRange(1, 9999)
        self.repartition_input.setDisabled(True)
        self.rep_start = QtGui.QCheckBox("Début")
        self.rep_start.setDisabled(True)
        self.rep_end = QtGui.QCheckBox("Fin")
        self.rep_end.setDisabled(True)
        layout_repartition.addWidget(self.repartition_cb, 0, 0, 1, 1)
        layout_repartition.addWidget(repartition_label, 1, 0, 1, 1)
        layout_repartition.addWidget(self.repartition_input, 1, 1, 1, 1)
        layout_repartition.addWidget(self.rep_start, 2, 0, 1, 1)
        layout_repartition.addWidget(self.rep_end, 2, 1, 1, 1)
        layout_repartition.setColumnStretch(1, 1)

        # remplissage
        self.remplissage_cb = QtGui.QCheckBox(translate("Gespal3D", "Rem&plissage"))
        remplissage_label = QtGui.QLabel(translate("Gespal3D", "Claire voie"))
        self.remplissage_input = ui.createWidget("Gui::InputField")
        self.remplissage_input.setDisabled(True)
        self.remplissage_input.setText(
            FreeCAD.Units.Quantity(
                0.0,
                FreeCAD.Units.Length).UserString)
        layout_remplissage.addWidget(self.remplissage_cb, 0, 0, 1, 1)
        layout_remplissage.addWidget(remplissage_label, 1, 0, 1, 1)
        layout_remplissage.addWidget(self.remplissage_input, 1, 1, 1, 1)

        # continue button
        continue_label = QtGui.QLabel(translate("Gespal3D", "&Continuer"))
        self.continue_cb = QtGui.QCheckBox()
        self.continue_cb.setObjectName("ContinueCmd")
        self.continue_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        continue_label.setBuddy(self.continue_cb)
        grid.addWidget(continue_label, 17, 0, 1, 1)
        grid.addWidget(self.continue_cb, 17, 1, 1, 1)

        grid.setColumnStretch(1, 1)

        # connect slots
        QtCore.QObject.connect(
            self.categories_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setCategory)
        QtCore.QObject.connect(
            self.composant_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setComposant)
        QtCore.QObject.connect(
            self.direction_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setDirection)
        QtCore.QObject.connect(
            self.length_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setLength)
        QtCore.QObject.connect(
            self.deversement_input,
            # QtCore.SIGNAL("valueChanged(double)"),
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setDeversement)
        QtCore.QObject.connect(
            self.insert_group,
            QtCore.SIGNAL("buttonClicked(int)"),
            self.setInsertPoint)
        QtCore.QObject.connect(
            self.width_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setWidth)
        QtCore.QObject.connect(
            self.height_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setHeight)
        QtCore.QObject.connect(
            self.repartition_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setArrayMode)
        QtCore.QObject.connect(
            self.continue_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setContinue)
        QtCore.QObject.connect(
            self.remplissage_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setFillMode)
        QtCore.QObject.connect(
            self.remplissage_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setFillSpace)
        QtCore.QObject.connect(
            self.repartition_input,
            QtCore.SIGNAL("valueChanged(int)"),
            self.setArrayQty)

        # restore preset
        self.restoreOptions()

        return taskwidget

    def restoreOptions(self):
        if DEBUG:
            FreeCAD.Console.PrintMessage("restoreOptions \n")
        stored_composant = self.p.GetInt("BeamPreset", 1)
        stored_direction = self.p.GetInt("BeamDirection", 0)
        stored_deversement = self.p.GetFloat("BeamDev", 0)
        stored_continue = self.p.GetBool("BeamDev", 0)
        stored_mode = self.p.GetString("BeamMode", self.mode)
        stored_fillspace = self.p.GetFloat("BeamFillSpace", 0.0)
        stored_array_qty = self.p.GetInt("BeamArrayQty", 1)

        if stored_composant:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore composant \n")
            comp = connect_db.getComposant(id=stored_composant)
            cat = comp[2]
            n = 0
            for x in self.categories:
                if x[0] == cat:
                    self.categories_cb.setCurrentIndex(n)
                n += 1
            self.composant_items = connect_db.getComposants(categorie=cat)
            self.composant_cb.clear()
            self.composant_cb.addItems([x[1] for x in self.composant_items])
            n = 0
            for x in self.composant_items:
                if x[0] == stored_composant:
                    self.composant_cb.setCurrentIndex(n)
                n += 1

        if stored_direction:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore direction \n")
            self.direction_cb.setCurrentIndex(int(stored_direction))
            self.setDirection()

        if stored_deversement:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore deversement \n")
            if stored_deversement == 0.0:
                self.deversement_input.setCurrentIndex(0)
            else:
                self.deversement_input.setCurrentIndex(1)

        if stored_mode:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore mode \n")
            if self.bpoint:
                if stored_mode == "fill":
                    self.remplissage_cb.setChecked(True)
                elif stored_mode == "array":
                    self.repartition_cb.setChecked(True)

        if stored_fillspace:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore fillspace \n")
            self.remplissage_input.setText(
                FreeCAD.Units.Quantity(
                    stored_fillspace,
                    FreeCAD.Units.Length).UserString)

        if stored_array_qty:
            if DEBUG:
                FreeCAD.Console.PrintMessage("restore array_qty \n")
            self.repartition_input.setValue(stored_array_qty)

        self.continue_cb.setChecked(self.continueCmd)

    def setCategory(self, i):
        self.composant_cb.clear()
        fc_compteur = self.categories[i][0]
        self.composant_items = connect_db.getComposants(categorie=fc_compteur)
        self.composant_cb.addItems([x[1] for x in self.composant_items])

    def setComposant(self, i):
        self.Profile = None
        id = self.composant_items[i][0]
        comp = connect_db.getComposant(id=id)

        if comp:
            self.Profile = comp
            # width
            if float(comp[5]) > 0.0:
                self.width_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[5]),
                        FreeCAD.Units.Length).UserString)
                self.width_input.setDisabled(True)
            else:
                self.width_input.setDisabled(False)

            # height
            if float(comp[4]) > 0.0:
                self.height_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[4]),
                        FreeCAD.Units.Length).UserString)
                self.height_input.setDisabled(True)
            else:
                self.height_input.setDisabled(False)

            # length
            if float(comp[3]) > 0.0:
                self.length_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[3]),
                        FreeCAD.Units.Length).UserString)
                self.length_input.setDisabled(True)
            else:
                self.setDirection()
                self.length_input.setDisabled(False)

            self.p.SetInt("BeamPreset", comp[0])

    def setDirection(self):
        idx = self.direction_cb.currentIndex()
        if DEBUG:
            msg = 'idx setDirection : %s \n' % idx
            FreeCAD.Console.PrintMessage(msg)
        self.p.SetInt("BeamDirection", idx)
        self.setWorkingPlane(idx)
        self.setMode()
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)
        # self.update()

    def setWorkingPlane(self, idx):
        if idx == 6:
            idx = 0
        axis_list = [
            FreeCAD.Vector(1, 0, 0),
            FreeCAD.Vector(0, 1, 0),
            FreeCAD.Vector(0, 0, 1),
            FreeCAD.Vector(-1, 0, 0),
            FreeCAD.Vector(0, -1, 0),
            FreeCAD.Vector(0, 0, -1), ]

        upvec_list = [
            FreeCAD.Vector(0.0, 1.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, 1.0),
            FreeCAD.Vector(1.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, -1.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, -1.0),
            FreeCAD.Vector(-1.0, 0.0, 0.0), ]

        if hasattr(FreeCAD, "DraftWorkingPlane"):
            FreeCAD.DraftWorkingPlane.setup(
                direction=axis_list[idx],
                point=FreeCAD.Vector(0.0, 0.0, 0.0),
                upvec=upvec_list[idx],
                force=True)

        FreeCADGui.Snapper.setGrid()

    def setFillMode(self, state):
        if state == 2:
            # Change mode to "fill"
            #self.mode = "fill"
            #self.p.SetString("BeamMode", self.mode)
            # Unlock remplissage_input
            self.remplissage_input.setDisabled(False)
            # Lock other parameters
            self.repartition_input.setDisabled(True)
            self.rep_start.setDisabled(True)
            self.rep_end.setDisabled(True)
            self.repartition_cb.setChecked(False)
        else:
            # Lock remplissage_input
            #self.mode = "point"
            #self.p.SetString("BeamMode", self.mode)
            self.remplissage_input.setDisabled(True)

        self.setMode()

    def setArrayMode(self, state):
        if state == 2:
            # Change mode to "array"
            #self.mode = "array"
            #self.p.SetString("BeamMode", self.mode)
            # Lock other parameters
            self.remplissage_input.setDisabled(True)
            self.remplissage_cb.setChecked(False)
            # Unlock remplissage_input
            self.repartition_input.setDisabled(False)
            self.rep_start.setDisabled(False)
            self.rep_end.setDisabled(False)
        else:
            # Lock array parameters
            #self.mode = "point"
            #self.p.SetString("BeamMode", self.mode)
            self.repartition_input.setDisabled(True)
            self.rep_start.setDisabled(True)
            self.rep_end.setDisabled(True)

        self.setMode()

    def setArrayQty(self):
        self.array_qty = self.repartition_input.value()
        self.p.SetInt("BeamArrayQty", self.array_qty)

    def setMode(self):
        if DEBUG:
            msg = "Set Mode \n"
            FreeCAD.Console.PrintMessage(msg)
            msg = "Current Mode is : %s \n" % self.mode
            FreeCAD.Console.PrintMessage(msg)
        idx = self.direction_cb.currentIndex()
        if idx > 2:
            idx -= 3
        if idx == 3:
            self.mode = "line"
            self.p.SetString("BeamMode", self.mode)
            self.repartition_cb.setChecked(False)
            self.remplissage_cb.setChecked(False)
            self.repartition_cb.setDisabled(True)
            self.remplissage_cb.setDisabled(True)
        else:
            self.repartition_cb.setDisabled(False)
            self.remplissage_cb.setDisabled(False)
            if self.remplissage_cb.isChecked():
                self.mode = 'fill'
            elif self.repartition_cb.isChecked():
                self.mode = 'array'
            else:
                self.mode = 'point'
            self.p.SetString("BeamMode", self.mode)
            if float(self.Profile[3]) > 0.0:
                self.setLength(self.Profile[3])
                self.length_input.setText(
                    FreeCAD.Units.Quantity(
                        self.Length, FreeCAD.Units.Length).UserString)
            else:
                self.setLength(self.product[idx])
                self.length_input.setText(
                    FreeCAD.Units.Quantity(
                        self.Length, FreeCAD.Units.Length).UserString)


        if DEBUG:
            msg = "New Mode is : %s \n" % self.mode
            FreeCAD.Console.PrintMessage(msg)

        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)

    def setDelta(self):
        delta_list = [[
            Vector(self.Height/2, self.Width/2, 0.0),
            Vector(0.0, self.Width/2, 0.0),
            Vector(-self.Height/2, self.Width/2, 0.0),
            Vector(self.Height/2, 0.0, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(-self.Height/2, 0.0, 0.0),
            Vector(self.Height/2, -self.Width/2, 0.0),
            Vector(0.0, -self.Width/2, 0.0),
            Vector(-self.Height/2, -self.Width/2, 0.0)
            ], [
            Vector(self.Width/2, self.Height/2, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(-self.Width/2, self.Height/2, 0.0),
            Vector(self.Width/2, 0.0, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(-self.Width/2, 0.0, 0.0),
            Vector(self.Width/2, -self.Height/2, 0.0),
            Vector(0.0, -self.Height/2, 0.0),
            Vector(-self.Width/2, -self.Height/2, 0.0)
            ], [
            Vector(-self.Height/2, self.Width/2, 0.0),
            Vector(0.0, self.Width/2, 0.0),
            Vector(self.Height/2, self.Width/2, 0.0),
            Vector(-self.Height/2, 0.0, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(self.Height/2, 0.0, 0.0),
            Vector(-self.Height/2, -self.Width/2, 0.0),
            Vector(0.0, -self.Width/2, 0.0),
            Vector(self.Height/2, -self.Width/2, 0.0)
            ], [
            Vector(-self.Width/2, self.Height/2, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(self.Width/2, self.Height/2, 0.0),
            Vector(-self.Width/2, 0.0, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(self.Width/2, 0.0, 0.0),
            Vector(-self.Width/2, -self.Height/2, 0.0),
            Vector(0.0, -self.Height/2, 0.0),
            Vector(self.Width/2, -self.Height/2, 0.0)
            ], [
            Vector(-self.Height/2, self.Width/2, 0.0),
            Vector(-self.Height/2, 0.0, 0.0),
            Vector(-self.Height/2, -self.Width/2, 0.0),
            Vector(0.0, self.Width/2, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(0.0, -self.Width/2, 0.0),
            Vector(self.Height/2, self.Width/2, 0.0),
            Vector(self.Height/2, 0.0, 0.0),
            Vector(self.Height/2, -self.Width/2, 0.0)
            ], [
            Vector(-self.Width/2, self.Height/2, 0.0),
            Vector(-self.Height/2, 0.0, 0.0),
            Vector(-self.Width/2, -self.Height/2, 0.0),
            Vector(0.0, self.Height/2, 0.0),
            Vector(0.0, 0.0, 0.0),
            Vector(0.0, -self.Height/2, 0.0),
            Vector(self.Width/2, self.Height/2, 0.0),
            Vector(self.Height/2, 0.0, 0.0),
            Vector(self.Width/2, -self.Height/2, 0.0)
            ]]
        point_idx = self.InsertPoint - 1
        axis = FreeCAD.DraftWorkingPlane.axis
        if axis.x != 0.0:
            if self.Deversement == 0.0:
                self.delta = delta_list[0][point_idx]
            else:
                self.delta = delta_list[1][point_idx]
        elif axis.y != 0.0:
            if self.Deversement == 0.0:
                self.delta = delta_list[2][point_idx]
            else:
                self.delta = delta_list[3][point_idx]
        elif axis.z != 0.0:
            if self.Deversement == 0.0:
                self.delta = delta_list[4][point_idx]
            else:
                self.delta = delta_list[5][point_idx]

        return self.delta

    def setInsertPoint(self):
        id = self.insert_group.checkedId()
        self.InsertPoint = id
        # self.setDelta()
        self.p.SetInt("BeamInsertPoint", id)
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)

    def setDeversement(self, idx):
        if idx == 0:
            self.Deversement = 0.0
            self.p.SetFloat("BeamDev", 0.0)
            # self.tracker.height(self.Height)
            # self.tracker.width(self.Width)
        else:
            self.Deversement = 90.0
            self.p.SetFloat("BeamDev", 90.0)
            # self.tracker.width(self.Height)
            # self.tracker.height(self.Width)
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)

    def setLength(self, d):

        self.Length = d
        self.tracker.length(d)
        self.p.SetFloat("BeamLength", d)

    def setWidth(self, d):

        self.Width = d
        self.tracker.width(d)
        self.p.SetFloat("BeamWidth", d)

    def setHeight(self, d):

        self.Height = d
        self.tracker.height(d)
        self.p.SetFloat("BeamHeight", d)

    def setFillSpace(self, d):

        self.FillSpace = d
        #self.tracker.height(d)
        self.p.SetFloat("BeamFillSpace", d)

    def setTrackerPlacement(self):
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)

    def setContinue(self, i):
        self.continueCmd = bool(i)
        self.p.SetBool("BeamContinue", bool(i))

    def makeTransaction(self, point=None):
        FreeCAD.ActiveDocument.openTransaction(
            translate("Gespal3D", "Create Beam"))
        if DEBUG:
            FreeCAD.Console.PrintMessage('BeamCreator.makeTransaction : \n')
            msg = "Current Mode is : %s \n" % self.mode
            FreeCAD.Console.PrintMessage(msg)
            msg = 'self.bpoint = %s \n' % self.bpoint
            FreeCAD.Console.PrintMessage(msg)
            msg = 'point = %s \n' % point
            FreeCAD.Console.PrintMessage(msg)
        FreeCADGui.addModule("Draft")
        FreeCADGui.addModule("Arch")
        FreeCADGui.addModule("freecad.workbench_gespal3d.profiles_parser")

        if self.Profile is not None:
            delta = self.setDelta()

            # Create profil with profiles_parser tools
            FreeCADGui.doCommand(
                'p = freecad.workbench_gespal3d.profiles_parser.makeProfile('
                # 'p = Arch.makeProfile('
                + str(self.Profile)
                + ')'
                )

            # Then rotate it for deversement
            v1 = 'FreeCAD.Vector(0.0, 0.0, 0.0)'
            v2 = 'FreeCAD.Vector(0.0, 0.0, 1.0)'
            angle = self.Deversement
            FreeCADGui.doCommand(
                'p.Placement.rotate('
                + str(v1)
                + ','
                + str(v2)
                + ','
                + str(angle)
                + ')'
                )

            # Move it according BPoint
            FreeCADGui.doCommand(
                'p.Placement.move('
                + 'FreeCAD.'
                + str(delta)
                + ')'
                )

            FreeCADGui.doCommand(
                's = Arch.makeStructure(p, length='
                + str(self.Length)
                + ')'
                )

            FreeCADGui.doCommand(
                's.Profile = "'
                + self.Profile[1]
                + '"'
                )
        else:
            FreeCADGui.doCommand(
                's = Arch.makeStructure(length='
                + str(self.Length)
                + ',width='
                + str(self.Width)
                + ',height='
                + str(self.Height)
                + ')')

        FreeCADGui.doCommand(
            's.Label = "'
            + self.Profile[1]
            + '"'
            )
        FreeCADGui.doCommand('s.IfcType = u"Transport Element"')
        FreeCADGui.doCommand('s.PredefinedType = u"NOTDEFINED"')
        FreeCADGui.doCommand('s.Tag = u"Gespal"')
        FreeCADGui.doCommand(
            's.Description = "'
            + str(self.Profile[0])
            +'"'
        )

        # calculate rotation
        if self.mode == "line" and self.bpoint is not None:
            FreeCADGui.doCommand(
                's.Placement = Arch.placeAlongEdge('
                + DraftVecUtils.toString(self.bpoint)
                + ","
                + DraftVecUtils.toString(point)
                + ")"
            )

        else:
            if self.bpoint is not None:
                tracker_vec = point.sub(self.bpoint)
            else:
                tracker_vec = FreeCAD.Vector(0.0,0.0,0.0)
            if DEBUG:
                msg = 'tracker_vec = %s \n' % tracker_vec
                FreeCAD.Console.PrintWarning(msg)
            axis = FreeCAD.DraftWorkingPlane.axis
            if axis.x != 0.0:
                if tracker_vec.y > 0.0:
                    vec_transaction = 'FreeCAD.Vector(0.0, %s, 0.0)'
                else:
                    vec_transaction = 'FreeCAD.Vector(0.0, -%s, 0.0)'
                if axis.x == -1.0:
                    point = point.add(FreeCAD.Vector(-self.Length, 0.0, 0.0))
                    self.setWorkingPlane(0)
            elif axis.y != 0.0:
                if tracker_vec.x > 0.0:
                    vec_transaction = 'FreeCAD.Vector(%s, 0.0, 0.0)'
                else:
                    vec_transaction = 'FreeCAD.Vector(-%s, 0.0, 0.0)'
                if axis.y == -1.0:
                    point = point.add(FreeCAD.Vector(0.0, -self.Length, 0.0))
                    self.setWorkingPlane(1)
            elif axis.z != 0.0:
                if (tracker_vec.x > 0.0) or (tracker_vec.y > 0.0):
                    if tracker_vec.x > tracker_vec.y:
                        vec_transaction = 'FreeCAD.Vector(%s, 0.0, 0.0)'
                    else:
                        vec_transaction = 'FreeCAD.Vector(0.0, %s, 0.0)'
                elif (tracker_vec.x < 0.0) or (tracker_vec.y < 0.0):
                    if tracker_vec.x > tracker_vec.y:
                        vec_transaction = 'FreeCAD.Vector(0.0, -%s, 0.0)'
                    else:
                        vec_transaction = 'FreeCAD.Vector(-%s, 0.0, 0.0)'
                else:
                    vec_transaction = 'FreeCAD.Vector(%s, 0.0, 0.0)'
                    if DEBUG:
                        FreeCAD.Console.PrintWarning("Unexpected situation !\n")
                if axis.z == -1.0:
                    point = point.add(FreeCAD.Vector(0.0, 0.0, -self.Length))
                    self.setWorkingPlane(2)
                    if tracker_vec.x < tracker_vec.y:
                        vec_transaction = 'FreeCAD.Vector(%s, 0.0, 0.0)'
                    else:
                        vec_transaction = 'FreeCAD.Vector(0.0, %s, 0.0)'
            if DEBUG:
                msg = 'vec_transaction = %s \n' % vec_transaction
                FreeCAD.Console.PrintWarning(msg)

            if self.mode == "fill" and self.bpoint is not None:
                FreeCADGui.doCommand(
                    's.Placement.Base = '
                    + DraftVecUtils.toString(self.bpoint)
                )
                FreeCADGui.doCommand(
                    's.Placement.Rotation = s.Placement.Rotation.multiply( \
                        FreeCAD.DraftWorkingPlane.getRotation().Rotation)'
                )
                length = DraftVecUtils.dist(self.bpoint, point)
                space = self.FillSpace
                delta = self.Height + space
                div = length / delta
                qte = math.ceil(div) - 1
                for x in range(qte):
                    FreeCADGui.doCommand(
                        'Draft.move(s,'
                        + vec_transaction % str(delta * (x+1))
                        + ', copy=True)'
                    )

            elif self.mode == "array" and self.bpoint is not None:
                length = DraftVecUtils.dist(self.bpoint, point)
                space = length / (self.array_qty + 1)
                spaces_list = []
                for x in range(self.array_qty):
                    spaces_list.append(space * (x+1))
                vec_str = vec_transaction % str(spaces_list[0])
                d = vec_str.split('(')[1].split(')')[0].split(',')
                d_vec = FreeCAD.Vector(float(d[0]), float(d[1]), float(d[2]))
                first_vec = self.bpoint.add(d_vec)

                if DEBUG:
                    FreeCAD.Console.PrintMessage('Array : \n')
                    msg = "length : %s \n" % length
                    FreeCAD.Console.PrintMessage(msg)
                    msg = "qte : %s \n" % self.array_qty
                    FreeCAD.Console.PrintMessage(msg)
                    msg = "space : %s \n" % space
                    FreeCAD.Console.PrintMessage(msg)
                    msg = "spaces_list : %s \n" % spaces_list
                    FreeCAD.Console.PrintMessage(msg)
                    msg = "d_vec : %s \n" % d_vec
                    FreeCAD.Console.PrintMessage(msg)
                    msg = "first_vec : %s \n" % first_vec
                    FreeCAD.Console.PrintMessage(msg)

                FreeCADGui.doCommand(
                    's.Placement.Base = '
                    + DraftVecUtils.toString(first_vec)
                )
                FreeCADGui.doCommand(
                    's.Placement.Rotation = s.Placement.Rotation.multiply( \
                        FreeCAD.DraftWorkingPlane.getRotation().Rotation)'
                )

                for x in spaces_list[1:]:
                    FreeCADGui.doCommand(
                        'Draft.move(s,'
                        + vec_transaction % str(x-space)
                        + ', copy=True)'
                    )
            else:
                FreeCADGui.doCommand(
                    's.Placement.Base = '
                    + DraftVecUtils.toString(point)
                )
                FreeCADGui.doCommand(
                    's.Placement.Rotation = s.Placement.Rotation.multiply( \
                        FreeCAD.DraftWorkingPlane.getRotation().Rotation)'
                )


        FreeCADGui.doCommand("Draft.autogroup(s)")
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCADGui.Snapper.toggleGrid()
        FreeCAD.ActiveDocument.recompute()
        if self.continueCmd:
            self.Activated()


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('BeamCreator', _CommandComposant())
