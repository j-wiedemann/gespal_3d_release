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


def makeArray(p1, p2, qte, w):
    points_list = []
    length = DraftVecUtils.dist(p1, p2)
    interval_init = (length - qte * w) / (qte + 1)
    interval_ext = interval_init + (w / 2)
    interval = interval_init + w
    points_list.append(interval_ext)
    if qte > 1:
        for x in range(qte-1):
            points_list.append(interval)
    points_list.append(interval_ext)
    return points_list


class _CommandComposant:

    "the Arch Structure command definition"

    def __init__(self):
        # input mode are:
        #       "point"
        #       "line"
        #       "array"
        self.mode = "point"

    def GetResources(self):

        return {'Pixmap': 'Arch_Structure',
                'MenuText': QT_TRANSLATE_NOOP("Gespal3D", "Composant"),
                'Accel': "C, O",
                'ToolTip': QT_TRANSLATE_NOOP(
                    "Arch_Structure",
                    "Creates a structure object from scratch or from a \
                    selected object (sketch, wire, face or solid)")}

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

        path = "User parameter:BaseApp/Preferences/Mod/Gespal3D"
        self.p = FreeCAD.ParamGet(str(path))

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
        self.continueCmd = self.p.GetBool("BeamContinue", False)
        self.bpoint = None

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
            title = translate("Arch", "Base point of the beam") + ":"
        else:
            title = translate("Arch", "First point of the beam") + ":"
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
                title=translate("Arch", "Next point")+":",
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
                title=translate("Arch", "Next point")+":",
                mode="line")
            return
        # premier clic en mode 1 ou second en mode 2
        self.tracker.finalize()
        self.makeTransaction(point)

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"
        if DEBUG:
            print("_CommandComposant update")

        if FreeCADGui.Control.activeDialog():
            if self.mode == "point":
                self.tracker.setPosition(point)
                self.tracker.on()
            else:
                self.tracker.off()
            """else:
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
                    self.tracker.off()"""

    def taskbox(self):
        "sets up a taskbox widget"

        taskwidget = QtGui.QWidget()
        ui = FreeCADGui.UiLoader()
        taskwidget.setWindowTitle(translate("Gespal3D", "Options de l'éléments"))
        grid = QtGui.QGridLayout(taskwidget)

        # categories box
        categories_items = [x[1] for x in self.categories]
        categories_label = QtGui.QLabel(translate("Arch", "Category"))
        self.categories_cb = QtGui.QComboBox()
        self.categories_cb.addItems(categories_items)
        grid.addWidget(categories_label, 2, 0, 1, 1)
        grid.addWidget(self.categories_cb, 2, 1, 1, 1)

        # presets box
        presets_label = QtGui.QLabel(translate("Arch", "Preset"))
        self.composant_cb = QtGui.QComboBox()
        grid.addWidget(presets_label, 3, 0, 1, 1)
        grid.addWidget(self.composant_cb, 3, 1, 1, 1)

        # direction
        direction_label = QtGui.QLabel(translate("Arch", "Direction"))
        self.direction_cb = QtGui.QComboBox()
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
        length_label = QtGui.QLabel(translate("Arch", "Length"))
        self.length_input = ui.createWidget("Gui::InputField")
        self.length_input.setText(
                FreeCAD.Units.Quantity(
                    self.Length, FreeCAD.Units.Length).UserString)
        grid.addWidget(length_label, 5, 0, 1, 1)
        # grid.addWidget(self.mode_lg, 4, 1, 1, 1)
        grid.addWidget(self.length_input, 5, 1, 1, 1)

        # insert point box
        insert_label = QtGui.QLabel(translate("Gespal3D", "Insertion"))
        self.insert_group = QtGui.QButtonGroup()
        buttons_grid = QtGui.QGridLayout()

        insert = QtGui.QRadioButton("7")
        if self.InsertPoint == 7:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 7)
        buttons_grid.addWidget(insert, 0, 0, 1, 1)

        insert = QtGui.QRadioButton("8")
        if self.InsertPoint == 8:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 8)
        buttons_grid.addWidget(insert, 0, 1, 1, 1)

        insert = QtGui.QRadioButton("9")
        if self.InsertPoint == 9:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 9)
        buttons_grid.addWidget(insert, 0, 2, 1, 1)

        insert = QtGui.QRadioButton("4")
        if self.InsertPoint == 4:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 4)
        buttons_grid.addWidget(insert, 1, 0, 1, 1)

        insert = QtGui.QRadioButton("5")
        if self.InsertPoint == 5:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 5)
        buttons_grid.addWidget(insert, 1, 1, 1, 1)

        insert = QtGui.QRadioButton("6")
        if self.InsertPoint == 6:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 6)
        buttons_grid.addWidget(insert, 1, 2, 1, 1)

        insert = QtGui.QRadioButton("1")
        if self.InsertPoint == 1:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 1)
        buttons_grid.addWidget(insert, 2, 0, 1, 1)

        insert = QtGui.QRadioButton("2")
        if self.InsertPoint == 2:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 2)
        buttons_grid.addWidget(insert, 2, 1, 1, 1)

        insert = QtGui.QRadioButton("3")
        if self.InsertPoint == 3:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 3)
        buttons_grid.addWidget(insert, 2, 2, 1, 1)

        grid.addWidget(insert_label, 7, 0, 1, 1)
        grid.addLayout(buttons_grid, 7, 1, 1, 1)

        # deversement
        deversement_label = QtGui.QLabel(translate("Gespal3D", "Déversement"))
        self.deversement_input = QtGui.QComboBox()
        self.deversement_input.addItems(["À plat", "Sur chant"])
        """self.deversement_input = ui.createWidget("Gui::InputField")
        self.deversement_input.setText(
            FreeCAD.Units.Quantity(
                self.Deversement,
                FreeCAD.Units.Angle).UserString)"""
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

        # repartition
        self.repartition_cb = QtGui.QCheckBox("Répartition")
        self.repartition_input = QtGui.QSpinBox()
        self.repartition_input.setRange(1, 99)
        # self.rep_start = QtGui.QCheckBox("Élément au début")
        # self.rep_end = QtGui.QCheckBox("Élément à la fin")
        grid.addWidget(self.repartition_cb, 14, 0, 1, 1)
        grid.addWidget(self.repartition_input, 14, 1, 1, 1)
        # grid.addWidget(self.rep_start, 15, 1, 1, 1)
        # grid.addWidget(self.rep_end, 16, 1, 1, 1)

        # continue button
        continue_label = QtGui.QLabel(translate("Arch", "Con&tinue"))
        continue_cb = QtGui.QCheckBox()
        continue_cb.setObjectName("ContinueCmd")
        continue_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        continue_label.setBuddy(continue_cb)
        if hasattr(FreeCADGui, "draftToolBar"):
            continue_cb.setChecked(FreeCADGui.draftToolBar.continueMode)
            self.continueCmd = FreeCADGui.draftToolBar.continueMode
        grid.addWidget(continue_label, 17, 0, 1, 1)
        grid.addWidget(continue_cb, 17, 1, 1, 1)

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
            self.setMode)
        QtCore.QObject.connect(
            continue_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setContinue)

        # restore preset
        self.restoreOptions()

        return taskwidget

    def restoreOptions(self):
        if DEBUG:
            print("restoreOptions")
        stored_composant = self.p.GetInt("BeamPreset", 1)
        stored_direction = self.p.GetInt("BeamDirection", 0)
        stored_deversement = self.p.GetFloat("BeamDev", 0)

        if stored_composant:
            if DEBUG:
                print("restore composant")
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
                print("restore direction")
            self.direction_cb.setCurrentIndex(int(stored_direction))
            self.setDirection()

        if stored_deversement:
            if DEBUG:
                print("restore deversement")
            if stored_deversement == 0.0:
                self.deversement_input.setCurrentIndex(0)
            else:
                self.deversement_input.setCurrentIndex(1)

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
            print(idx)
        self.p.SetInt("BeamDirection", idx)
        self.setWorkingPlane(idx)
        self.setMode()
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)
        # self.update()

    def setWorkingPlane(self, idx):
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

    def setMode(self):
        idx = self.direction_cb.currentIndex()
        if idx > 2:
            idx -= 3
        array = self.repartition_cb.isChecked()
        if idx == 3:
            self.mode = "line"
            self.repartition_cb.setChecked(False)
            self.repartition_cb.setDisabled(True)
            self.repartition_input.setDisabled(True)
            # self.rep_start.setDisabled(True)
            # self.rep_end.setDisabled(True)
        else:
            if array is True:
                self.mode = "array"
            else:
                self.mode = "point"
                self.repartition_cb.setDisabled(False)
                self.repartition_input.setDisabled(False)
                # self.rep_start.setDisabled(False)
                # self.rep_end.setDisabled(False)
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

    def setTrackerPlacement(self):
        self.tracker.setPlacement(
            snap_bp=None,
            bp_idx=self.InsertPoint,
            dev=self.Deversement)

    def setContinue(self, i):

        self.continueCmd = bool(i)
        if hasattr(FreeCADGui, "draftToolBar"):
            FreeCADGui.draftToolBar.continueMode = bool(i)
        self.p.SetBool("BeamContinue", bool(i))

    def makeTransaction(self, point=None):
        FreeCAD.ActiveDocument.openTransaction(
            translate("Gespal3D", "Create Beam"))
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

        # calculate rotation
        if self.mode == "line" and self.bpoint is not None:
            FreeCADGui.doCommand(
                's.Placement = Arch.placeAlongEdge('
                + DraftVecUtils.toString(self.bpoint)
                + ","
                + DraftVecUtils.toString(point)
                + ")"
            )
        elif self.mode == "array" and self.bpoint is not None:
            pass
        else:
            axis = FreeCAD.DraftWorkingPlane.axis
            if axis.x != 0.0:
                if axis.x == -1.0:
                    point = point.add(FreeCAD.Vector(-self.Length, 0.0, 0.0))
                    self.setWorkingPlane(0)
            elif axis.y != 0.0:
                if axis.y == -1.0:
                    point = point.add(FreeCAD.Vector(0.0, -self.Length, 0.0))
                    self.setWorkingPlane(1)
            elif axis.z != 0.0:
                if axis.z == -1.0:
                    point = point.add(FreeCAD.Vector(0.0, 0.0, -self.Length))
                    self.setWorkingPlane(2)

            FreeCADGui.doCommand(
                's.Placement.Base = '
                + DraftVecUtils.toString(point)
            )
            FreeCADGui.doCommand(
                's.Placement.Rotation = s.Placement.Rotation.multiply( \
                    FreeCAD.DraftWorkingPlane.getRotation().Rotation)'
            )

        FreeCADGui.addModule("Draft")
        FreeCADGui.doCommand("Draft.autogroup(s)")
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        if self.continueCmd:
            self.Activated()


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('BeamCreator', _CommandComposant())
