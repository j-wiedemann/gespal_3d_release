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
import Arch
import DraftVecUtils
from FreeCAD import Vector

# from freecad.workbench_gespal3d import g3d_profiles_parser
from freecad.workbench_gespal3d import g3d_tracker
from freecad.workbench_gespal3d import g3d_connect_db
from freecad.workbench_gespal3d import DEBUG
from freecad.workbench_gespal3d import DEBUG_U
from freecad.workbench_gespal3d import print_debug
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


def makeG3DBeam(pname, length, profile, color, description):
    p = FreeCAD.ActiveDocument.getObject(pname)
    s = Arch.makeStructure(p, length=length)
    s.Profile = profile
    # Set color
    color = color.split(",")
    r = float(color[0]) / 255.0
    g = float(color[1]) / 255.0
    b = float(color[2]) / 255.0
    s.ViewObject.ShapeColor = (r, g, b)

    s.Label = profile
    s.IfcType = u"Transport Element"
    s.PredefinedType = u"NOTDEFINED"
    s.Tag = u"Gespal"
    s.Description = description
    s.MoveBase = True
    return s


class _CommandComposant:

    "Gespal 3D - Beam Creator tool"

    def __init__(self):
        # possible input mode are:
        #       "point"
        #       "array"
        #       "fill"
        self.mode = "point"

    def GetResources(self):

        return {
            "Pixmap": "Arch_Structure",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Composant"),
            "Accel": "C, O",
            "ToolTip": "<html><head/><body><p><b>Ajouter un composant</b> \
                    (hors panneaux). \
                    <br><br> \
                    Possibilité d'ajouter le composant par répartition ou \
                    par remplissage. \
                    </p></body></html>",
        }

    def IsActive(self):
        active = False
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

    def Activated(self):

        if DEBUG:
            print_debug(["Beam Creator Activated"])

        # Reads preset profiles and categorizes them
        self.categories = g3d_connect_db.getCategories(include=["BO"])

        self.p = FreeCAD.ParamGet(str(PARAMPATH))

        product = FreeCAD.ActiveDocument.getObject("Product")
        if hasattr(product, "Length"):
            self.product = [
                product.Length.Value,
                product.Width.Value,
                product.Height.Value,
            ]
        else:
            product = FreeCAD.ActiveDocument.getObject("Box")
            self.product = [
                product.Length.Value,
                product.Width.Value,
                product.Height.Value,
            ]

        self.Width = self.p.GetFloat("BeamWidth", 100)
        self.Height = self.p.GetFloat("BeamHeight", 22)
        self.Length = self.p.GetFloat("BeamLength", 1200)
        self.Profile = None
        self.anchor_idx = self.p.GetInt("BeamInsertPoint", 1)
        self.inclination = self.p.GetFloat("BeamDev", 0.0)
        self.continueCmd = self.p.GetBool("BeamContinue", True)
        self.p.GetString("BeamMode", self.mode)
        self.fill_space = self.p.GetFloat("BeamFillSpace", 0.0)
        self.base_snap_vertex = None
        self.array_qty = self.p.GetInt("BeamArrayQty", 1)

        if DEBUG:
            messages = ["Params :"]
            messages.append("Mode = {}".format(self.mode))
            messages.append("Profile = {}".format(self.Profile))
            messages.append("Width = {}".format(self.Width))
            messages.append("Height = {}".format(self.Height))
            messages.append("Length = {}".format(self.Length))
            messages.append("Anchor index = {}".format(self.anchor_idx))
            messages.append("Inclination = {}".format(self.inclination))
            messages.append("FillSpace = {}".format(self.fill_space))
            messages.append("array_qty = {}".format(self.array_qty))
            messages.append("continueCmd = {}".format(self.continueCmd))
            print_debug(messages)

        # interactive mode
        self.initTracker()

    def initTracker(self):
        self.points = []
        self.tracker = g3d_tracker.boxTracker(
            width=self.Height, height=self.Width, length=self.Length
        )
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
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
            title=title,
        )

    def getPoint(self, point=None, obj=None):
        "this function is called by the snapper when it has a 3D point"

        # pas de point
        if point is None:
            self.tracker.finalize()
            return
        # mode array
        if (self.mode == "array") and (self.base_snap_vertex is None):
            self.base_snap_vertex = FreeCAD.Vector(
                round(point.x, 2), round(point.y, 2), round(point.z, 2)
            )
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getPoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Gespal3D", "Point suivant") + ":",
                mode="point",
            )
            return
        # mode array
        if (self.mode == "fill") and (self.base_snap_vertex is None):
            self.base_snap_vertex = FreeCAD.Vector(
                round(point.x, 2), round(point.y, 2), round(point.z, 2)
            )
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getPoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Gespal3D", "Point suivant") + ":",
                mode="point",
            )
            return
        # premier clic en mode 1 ou second en mode 2
        self.tracker.finalize()
        self.makeTransaction(point)

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"
        if DEBUG and DEBUG_U:
            msg = "_CommandComposant update"
            print_debug(msg)

        if FreeCADGui.Control.activeDialog():
            if DEBUG and DEBUG_U:
                msg = "Current Mode is : %s \n" % self.mode
                print_debug(msg)
            if self.mode == "point":
                self.tracker.update(
                    anchor_idx=self.anchor_idx,
                    inclination=self.inclination,
                    base_snap_vertex=point,
                )
                self.tracker.on()
            elif self.mode == "array":
                self.tracker.update(
                    anchor_idx=self.anchor_idx,
                    inclination=self.inclination,
                    base_snap_vertex=point,
                )
                self.tracker.on()
            elif self.mode == "fill":
                self.tracker.update(
                    anchor_idx=self.anchor_idx,
                    inclination=self.inclination,
                    base_snap_vertex=point,
                )
                self.tracker.on()
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
        self.direction_cb.addItems(
            [
                "Direction X",
                "Direction Y",
                "Direction Z",
                "Direction -X",
                "Direction -Y",
                "Direction -Z",
                # "Libre",
            ]
        )
        grid.addWidget(direction_label, 4, 0, 1, 1)
        grid.addWidget(self.direction_cb, 4, 1, 1, 1)

        # length
        length_label = QtGui.QLabel(translate("Gespal3D", "Longueur"))
        self.length_input = ui.createWidget("Gui::InputField")
        grid.addWidget(length_label, 5, 0, 1, 1)

        vlay = QtGui.QHBoxLayout()
        self.fixlength_checkbox = QtGui.QCheckBox("Fixer")
        vlay.addWidget(self.length_input)
        vlay.addWidget(self.fixlength_checkbox)

        grid.addLayout(vlay, 5, 1, 1, 1)

        # insert point box
        insert_label = QtGui.QLabel(translate("Gespal3D", "Insertion"))
        self.insert_group = QtGui.QButtonGroup()
        buttons_grid = QtGui.QGridLayout()

        insert = QtGui.QRadioButton("&7")
        if self.anchor_idx == 7:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 7)
        buttons_grid.addWidget(insert, 0, 0, 1, 1)

        insert = QtGui.QRadioButton("&8")
        if self.anchor_idx == 8:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 8)
        buttons_grid.addWidget(insert, 0, 1, 1, 1)

        insert = QtGui.QRadioButton("&9")
        if self.anchor_idx == 9:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 9)
        buttons_grid.addWidget(insert, 0, 2, 1, 1)

        insert = QtGui.QRadioButton("&4")
        if self.anchor_idx == 4:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 4)
        buttons_grid.addWidget(insert, 1, 0, 1, 1)

        insert = QtGui.QRadioButton("&5")
        if self.anchor_idx == 5:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 5)
        buttons_grid.addWidget(insert, 1, 1, 1, 1)

        insert = QtGui.QRadioButton("&6")
        if self.anchor_idx == 6:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 6)
        buttons_grid.addWidget(insert, 1, 2, 1, 1)

        insert = QtGui.QRadioButton("&1")
        if self.anchor_idx == 1:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 1)
        buttons_grid.addWidget(insert, 2, 0, 1, 1)

        insert = QtGui.QRadioButton("&2")
        if self.anchor_idx == 2:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 2)
        buttons_grid.addWidget(insert, 2, 1, 1, 1)

        insert = QtGui.QRadioButton("&3")
        if self.anchor_idx == 3:
            insert.setChecked(True)
        self.insert_group.addButton(insert, 3)
        buttons_grid.addWidget(insert, 2, 2, 1, 1)

        # horizontal layout for insert point box
        horizontal_layout = QtGui.QHBoxLayout()
        spacerItemLeft = QtGui.QSpacerItem(
            20, 40, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        horizontal_layout.addSpacerItem(spacerItemLeft)

        horizontal_layout.addLayout(buttons_grid)

        spacerItemRight = QtGui.QSpacerItem(
            20, 40, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        horizontal_layout.addSpacerItem(spacerItemRight)

        grid.addWidget(insert_label, 7, 0, 1, 1)
        grid.addLayout(horizontal_layout, 7, 1, 1, 1)

        # deversement
        deversement_label = QtGui.QLabel(translate("Gespal3D", "Déversement"))
        self.deversement_input = QtGui.QComboBox()
        self.deversement_input.addItems(["À plat 0.0°", "Sur chant 90.0°"])
        """
        # with angle
        self.deversement_input = ui.createWidget("Gui::InputField")
        self.deversement_input.setText(
            FreeCAD.Units.Quantity(
                self.inclination,
                FreeCAD.Units.Angle).UserString)
        """
        grid.addWidget(deversement_label, 8, 0, 1, 1)
        grid.addWidget(self.deversement_input, 8, 1, 1, 1)

        # width
        width_label = QtGui.QLabel(translate("Arch", "Width"))
        self.width_input = ui.createWidget("Gui::InputField")
        self.width_input.setText(
            FreeCAD.Units.Quantity(self.Width, FreeCAD.Units.Length).UserString
        )
        grid.addWidget(width_label, 12, 0, 1, 1)
        grid.addWidget(self.width_input, 12, 1, 1, 1)

        # height
        height_label = QtGui.QLabel(translate("Arch", "Height"))
        self.height_input = ui.createWidget("Gui::InputField")
        self.height_input.setText(
            FreeCAD.Units.Quantity(self.Height, FreeCAD.Units.Length).UserString
        )
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
            FreeCAD.Units.Quantity(0.0, FreeCAD.Units.Length).UserString
        )
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
            self.setCategory,
        )
        QtCore.QObject.connect(
            self.composant_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setComposant,
        )
        QtCore.QObject.connect(
            self.direction_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setDirection,
        )
        QtCore.QObject.connect(
            self.length_input, QtCore.SIGNAL("valueChanged(double)"), self.setLength
        )
        QtCore.QObject.connect(
            self.deversement_input,
            # QtCore.SIGNAL("valueChanged(double)"),
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setInclination,
        )
        QtCore.QObject.connect(
            self.insert_group, QtCore.SIGNAL("buttonClicked(int)"), self.setInsertPoint
        )
        QtCore.QObject.connect(
            self.width_input, QtCore.SIGNAL("valueChanged(double)"), self.setWidth
        )
        QtCore.QObject.connect(
            self.height_input, QtCore.SIGNAL("valueChanged(double)"), self.setHeight
        )
        QtCore.QObject.connect(
            self.repartition_cb, QtCore.SIGNAL("stateChanged(int)"), self.setArrayMode
        )
        QtCore.QObject.connect(
            self.continue_cb, QtCore.SIGNAL("stateChanged(int)"), self.setContinue
        )
        QtCore.QObject.connect(
            self.remplissage_cb, QtCore.SIGNAL("stateChanged(int)"), self.setFillMode
        )
        QtCore.QObject.connect(
            self.remplissage_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setFillSpace,
        )
        QtCore.QObject.connect(
            self.repartition_input, QtCore.SIGNAL("valueChanged(int)"), self.setArrayQty
        )
        QtCore.QObject.connect(
            self.fixlength_checkbox,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setFixedLength,
        )

        # restore preset
        self.restoreParams()

        return taskwidget

    def restoreParams(self):
        if DEBUG:
            print_debug("restoreParams")
        stored_composant = self.p.GetInt("BeamPreset", 1)
        stored_direction = self.p.GetInt("BeamDirection", 0)
        stored_deversement = self.p.GetFloat("BeamDev", 0)
        stored_continue = self.p.GetBool("BeamDev", 0)
        stored_mode = self.p.GetString("BeamMode", self.mode)
        stored_fillspace = self.p.GetFloat("BeamFillSpace", 0.0)
        stored_array_qty = self.p.GetInt("BeamArrayQty", 1)
        stored_fixlength = self.p.GetBool("BeamFixLength", 0)
        # print(stored_fixlength)

        if stored_composant:
            if DEBUG:
                print_debug("restore composant")
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

        if stored_direction:
            if DEBUG:
                print_debug("restore direction")
            self.direction_cb.setCurrentIndex(int(stored_direction))
            self.setDirection()

        if stored_deversement:
            if DEBUG:
                print_debug("restore deversement")
            if stored_deversement == 0.0:
                self.deversement_input.setCurrentIndex(0)
            else:
                self.deversement_input.setCurrentIndex(1)

        if stored_mode:
            if DEBUG:
                print_debug("restore mode")
            if self.base_snap_vertex:
                if stored_mode == "fill":
                    self.remplissage_cb.setChecked(True)
                elif stored_mode == "array":
                    self.repartition_cb.setChecked(True)

        if stored_fillspace:
            if DEBUG:
                print_debug("restore fillspace")
            self.remplissage_input.setText(
                FreeCAD.Units.Quantity(
                    stored_fillspace, FreeCAD.Units.Length
                ).UserString
            )

        if stored_array_qty:
            if DEBUG:
                print_debug("restore array_qty")
            self.repartition_input.setValue(stored_array_qty)

        if stored_fixlength:
            if DEBUG:
                print_debug("restore fixlength")
            self.fixlength_checkbox.setChecked(bool(stored_fixlength))

        self.continue_cb.setChecked(self.continueCmd)

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
                self.width_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[5]), FreeCAD.Units.Length
                    ).UserString
                )
                self.width_input.setDisabled(True)
            else:
                self.width_input.setDisabled(False)

            # height
            if float(comp[4]) > 0.0:
                self.height_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[4]), FreeCAD.Units.Length
                    ).UserString
                )
                self.height_input.setDisabled(True)
            else:
                self.height_input.setDisabled(False)

            # length
            if float(comp[3]) > 0.0:
                self.length_input.setText(
                    FreeCAD.Units.Quantity(
                        float(comp[3]), FreeCAD.Units.Length
                    ).UserString
                )
                self.length_input.setDisabled(True)
            else:
                self.setDirection()
                self.length_input.setDisabled(False)

            self.p.SetInt("BeamPreset", comp[0])

    def setDirection(self):
        idx = self.direction_cb.currentIndex()
        if DEBUG:
            print_debug("idx setDirection : {}".format(idx))
        self.p.SetInt("BeamDirection", idx)
        self.setWorkingPlane(idx)
        self.setMode()
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)

    def setWorkingPlane(self, idx):
        if idx == 6:
            idx = 0
        axis_list = [
            FreeCAD.Vector(1, 0, 0),
            FreeCAD.Vector(0, 1, 0),
            FreeCAD.Vector(0, 0, 1),
            FreeCAD.Vector(-1, 0, 0),
            FreeCAD.Vector(0, -1, 0),
            FreeCAD.Vector(0, 0, -1),
        ]

        upvec_list = [
            FreeCAD.Vector(0.0, 1.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, 1.0),
            FreeCAD.Vector(1.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, -1.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, -1.0),
            FreeCAD.Vector(-1.0, 0.0, 0.0),
        ]

        if hasattr(FreeCAD, "DraftWorkingPlane"):
            FreeCAD.DraftWorkingPlane.alignToPointAndAxis(
                point=FreeCAD.Vector(0.0, 0.0, 0.0),
                axis=axis_list[idx],
                upvec=upvec_list[idx],
            )

        FreeCADGui.Snapper.toggleGrid()
        FreeCADGui.Snapper.toggleGrid()

    def setFillMode(self, state):
        if state == 2:
            self.remplissage_input.setDisabled(False)
            self.repartition_input.setDisabled(True)
            self.rep_start.setDisabled(True)
            self.rep_end.setDisabled(True)
            self.repartition_cb.setChecked(False)
        else:
            self.remplissage_input.setDisabled(True)

        self.setMode()

    def setArrayMode(self, state):
        if state == 2:
            self.remplissage_input.setDisabled(True)
            self.remplissage_cb.setChecked(False)
            self.repartition_input.setDisabled(False)
            self.rep_start.setDisabled(False)
            self.rep_end.setDisabled(False)
        else:
            self.repartition_input.setDisabled(True)
            self.rep_start.setDisabled(True)
            self.rep_end.setDisabled(True)

        self.setMode()

    def setArrayQty(self):
        self.array_qty = self.repartition_input.value()
        self.p.SetInt("BeamArrayQty", self.array_qty)

    def setMode(self):
        if DEBUG:
            messages = ["Set Mode :"]
            messages.append("Current Mode is : {}".format(self.mode))
            print_debug(messages)
        idx = self.direction_cb.currentIndex()
        if idx > 2:
            idx -= 3

        self.repartition_cb.setDisabled(False)
        self.remplissage_cb.setDisabled(False)
        if self.remplissage_cb.isChecked():
            self.mode = "fill"
        elif self.repartition_cb.isChecked():
            self.mode = "array"
        else:
            self.mode = "point"

        self.p.SetString("BeamMode", self.mode)

        if float(self.Profile[3]) > 0.0:
            self.setLength(self.Profile[3])
            self.length_input.setText(
                FreeCAD.Units.Quantity(self.Length, FreeCAD.Units.Length).UserString
            )
        elif (self.mode == "array") or (self.mode == "fill"):
            self.length_input.setText(
                FreeCAD.Units.Quantity(self.Length, FreeCAD.Units.Length).UserString
            )
        elif self.p.GetBool("BeamFixLength", 0) is False:
            self.setLength(self.product[idx])
            self.length_input.setText(
                FreeCAD.Units.Quantity(self.Length, FreeCAD.Units.Length).UserString
            )
        else:
            self.length_input.setText(
                FreeCAD.Units.Quantity(self.Length, FreeCAD.Units.Length).UserString
            )

        if DEBUG:
            print_debug("New Mode is : {}".format(self.mode))

        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)

    def setInsertPoint(self):
        id = self.insert_group.checkedId()
        self.anchor_idx = id
        self.p.SetInt("BeamInsertPoint", id)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)

    def setInclination(self, idx):
        if idx == 0:
            self.inclination = 0.0
            self.p.SetFloat("BeamDev", 0.0)
        elif idx == 1:
            self.inclination = 90.0
            self.p.SetFloat("BeamDev", 90.0)
        else:
            self.inclination = 0.0
            self.p.SetFloat("BeamDev", 0.0)

        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)

    def setFixedLength(self, i):
        self.p.SetBool("BeamFixLength", bool(i))

    def setLength(self, d):
        self.Length = d
        self.tracker.length(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.p.SetFloat("BeamLength", d)

    def setWidth(self, d):
        self.Width = d
        self.tracker.height(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.p.SetFloat("BeamWidth", d)

    def setHeight(self, d):
        self.Height = d
        self.tracker.width(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.p.SetFloat("BeamHeight", d)

    def setFillSpace(self, d):
        self.fill_space = d
        self.p.SetFloat("BeamFillSpace", d)

    def setContinue(self, i):
        self.continueCmd = bool(i)
        self.p.SetBool("BeamContinue", bool(i))

    def makeTransaction(self, point=None):
        """g3d beam makeTransaction"""
        # Round precision of point
        x = round(point.x, 2)
        y = round(point.y, 2)
        z = round(point.z, 2)
        point = FreeCAD.Vector(x, y, z)
        if DEBUG:
            messages = ["G3D_BeamComposant.makeTransaction :"]
            messages.append("Current Mode is : {}".format(self.mode))
            messages.append("self.base_snap_vertex = {}".format(self.base_snap_vertex))
            messages.append("point = {}".format(point))
            print_debug(messages)

        if self.mode == "point":
            base_vertex = point
            transaction_name = "Create G3DBeam"
        elif self.mode == "fill":
            base_vertex = self.base_snap_vertex
            transaction_name = "Create G3DBeam filling"
        elif self.mode == "array":
            base_vertex = self.base_snap_vertex
            transaction_name = "Create G3DBeam array"
        else:
            FreeCAD.Console.PrintWarning("This mode is not implemented")
            return

        # Open transaction
        FreeCAD.ActiveDocument.openTransaction(translate("Gespal3D", transaction_name))

        FreeCADGui.addModule("Draft")
        FreeCADGui.addModule("Arch")
        FreeCADGui.addModule("freecad.workbench_gespal3d.g3d_profiles_parser")
        FreeCADGui.addModule("freecad.workbench_gespal3d.g3d_beam")

        # Create profil with g3d_profiles_parser tools
        FreeCADGui.doCommand(
            "p = freecad.workbench_gespal3d.g3d_profiles_parser.makeProfile("
            + str(self.Profile)
            + ")"
        )

        # setDelta
        if self.anchor_idx in [1, 4, 7]:
            x = self.Height / 2.0
        elif self.anchor_idx in [3, 6, 9]:
            x = -self.Height / 2.0
        else:
            x = 0.0

        if self.anchor_idx in [1, 2, 3]:
            y = -self.Width / 2.0
        elif self.anchor_idx in [7, 8, 9]:
            y = self.Width / 2.0
        else:
            y = 0.0

        # Move profile to anchor point
        FreeCADGui.doCommand(
            "Draft.move(p, "
            + "FreeCAD.Vector("
            + str(x)
            + ", "
            + str(y)
            + ", "
            + str(0.0)
            + "))"
        )

        # Rotate profil around Z axis by inclination value
        FreeCADGui.doCommand(
            "Draft.rotate(p, "
            + str(self.inclination)
            + ","
            + "FreeCAD.Vector(0.0, 0.0, 0.0), FreeCAD.Vector(0.0, 0.0, 1.0)"
            + ")"
        )

        normalWP = FreeCAD.DraftWorkingPlane.getNormal()
        vec_0 = FreeCAD.Vector(0.0, 0.0, 0.0)
        vec_z = FreeCAD.Vector(0.0, 0.0, 1.0)
        vec_y = FreeCAD.Vector(0.0, 1.0, 0.0)
        vec_x = FreeCAD.Vector(1.0, 0.0, 0.0)
        if normalWP == vec_x:
            params = [-90.0, vec_0, vec_x, -90.0, vec_0, vec_z]  # check : todo
        elif normalWP == vec_y:
            params = [-90.0, vec_0, vec_x, 0.0, vec_0, vec_z]  # check : good
        elif normalWP == vec_z:
            params = [0.0, vec_0, vec_z, 0.0, vec_0, vec_z]  # check : good
        elif normalWP == vec_x.negative():
            params = [-90.0, vec_0, vec_x, 90.0, vec_0, vec_z]  # check : good
        elif normalWP == vec_y.negative():
            params = [180.0, vec_0, vec_z, 90.0, vec_0, vec_x]  # check : good
        elif normalWP == vec_z.negative():
            params = [180.0, vec_0, vec_y, 0.0, vec_0, vec_z]  # check : good
        else:
            params = [0.0, vec_0, vec_z, 0.0, vec_0, vec_z]  # check : good

        # We need zero, one or two rotations to get the good orientation
        # rotation param are given just behind
        # Let's make the first rotation
        FreeCADGui.doCommand(
            "Draft.rotate(p, "
            + str(params[0])
            + ", "
            + DraftVecUtils.toString(params[1])
            + ", "
            + DraftVecUtils.toString(params[2])
            + ")"
        )
        # Then the second rotation
        FreeCADGui.doCommand(
            "Draft.rotate(p, "
            + str(params[3])
            + ", "
            + DraftVecUtils.toString(params[4])
            + ", "
            + DraftVecUtils.toString(params[5])
            + ")"
        )

        # Move profil to base_snap_vertex
        FreeCADGui.doCommand(
            "Draft.move(p, " + DraftVecUtils.toString(base_vertex) + ")"
        )

        # Make the G3D Beam component
        # Get the name of the profile object
        FreeCADGui.doCommand(
            "s = freecad.workbench_gespal3d.g3d_beam.makeG3DBeam("
            + "p.Name, '"
            + str(self.Length)
            + "', '"
            + str(self.Profile[1])
            + "', '"
            + str(self.Profile[-1])
            + "', '"
            + str(self.Profile[0])
            + "')"
        )

        if self.mode != "point":
            if self.base_snap_vertex is not None and point is not None:
                tracker_vec = point.sub(self.base_snap_vertex)
                if self.mode == "array" or self.mode == "fill":
                    original_point = point

            if DEBUG:
                print_debug(["tracker_vec = {}".format(tracker_vec)])
            axis = FreeCAD.DraftWorkingPlane.getNormal()

            if axis.x != 0.0:
                if tracker_vec.y > 0.0:
                    vec_transaction = "FreeCAD.Vector({1}, {0}, {2})"
                    situation = 1
                    reverse = False
                else:
                    vec_transaction = "FreeCAD.Vector({1}, {0}, {2})"
                    situation = 2
                    reverse = True
                if axis.x == -1.0:
                    pass

            elif axis.y != 0.0:
                if tracker_vec.x > 0.0:
                    vec_transaction = "FreeCAD.Vector({0}, {1}, {2})"
                    situation = 3
                else:
                    vec_transaction = "FreeCAD.Vector({0}, {1}, {2})"
                    situation = 4
                    reverse = True
                if axis.y == -1.0:
                    pass

            elif axis.z != 0.0:
                if (tracker_vec.x < 0.0) or (tracker_vec.y < 0.0):
                    if tracker_vec.x > tracker_vec.y:
                        vec_transaction = "FreeCAD.Vector({2}, {0}, {1})"
                        situation = 7
                    else:
                        vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                        situation = 8
                    reverse = True
                elif (tracker_vec.x > 0.0) or (tracker_vec.y > 0.0):
                    if tracker_vec.x > tracker_vec.y:
                        vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                        situation = 5
                    else:
                        vec_transaction = "FreeCAD.Vector({2}, {0}, {1})"
                        situation = 6
                    reverse = False
                else:
                    vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                    situation = 9
                    reverse = False
                    if DEBUG:
                        print_debug(["Unexpected situation !"])

                if axis.z == -1.0:
                    if (tracker_vec.x < 0.0) or (tracker_vec.y < 0.0):
                        if tracker_vec.x > tracker_vec.y:
                            vec_transaction = "FreeCAD.Vector({2}, {0}, {1})"
                            situation = 12
                        else:
                            vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                            situation = 13
                        reverse = True
                    elif (tracker_vec.x > 0.0) or (tracker_vec.y > 0.0):
                        if tracker_vec.x > tracker_vec.y:
                            vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                            situation = 10
                        else:
                            vec_transaction = "FreeCAD.Vector({2}, {0}, {1})"
                            situation = 11
                        reverse = False
                    else:
                        vec_transaction = "FreeCAD.Vector({0}, {2}, {1})"
                        situation = 14
                        reverse = False
                        if DEBUG:
                            print_debug(["Unexpected situation !"])

            if DEBUG:
                msg = ["vec_transaction = {}".format(vec_transaction)]
                msg.append("Situation " + str(situation))
                print_debug(msg)

            if self.mode == "fill" and self.base_snap_vertex is not None:
                # length between two picked points
                length = DraftVecUtils.dist(self.base_snap_vertex, original_point)
                # get space between g3d_beam
                space = self.fill_space
                # set delta from inclination
                if self.inclination == 90.0:
                    if situation in [1, 2, 3, 4, 5, 8, 10, 13]:
                        delta = self.Width
                    else:
                        delta = self.Height
                else:
                    if situation in [1, 2, 3, 4, 5, 8, 10, 13]:
                        delta = self.Height
                    else:
                        delta = self.Width
                # add space tp delta
                delta += space
                # get length division
                div = length / delta
                qte = math.ceil(div) - 1
                leftspace = length - qte * delta
                if leftspace >= delta:
                    qte += 1

                if reverse == True:
                    delta = delta * -1

                for x in range(qte - 1):
                    FreeCADGui.doCommand(
                        "p2 = Draft.move(p, "
                        + vec_transaction.format(str(delta * (x + 1)), 0.0, 0.0)
                        + ", copy=True)"
                    )
                    # Make the G3D Beam component
                    # Get the name of the profile object
                    FreeCADGui.doCommand(
                        "s = freecad.workbench_gespal3d.g3d_beam.makeG3DBeam("
                        + "p2.Name, '"
                        + str(self.Length)
                        + "', '"
                        + str(self.Profile[1])
                        + "', '"
                        + str(self.Profile[-1])
                        + "', '"
                        + str(self.Profile[0])
                        + "')"
                    )
                if DEBUG:
                    messages = ["Filling :"]
                    messages.append("length : {}".format(length))
                    messages.append("div : {}".format(div))
                    messages.append("qte : {}".format(qte))
                    messages.append("space : {}".format(space))
                    messages.append("delta : {}".format(delta))
                    messages.append("leftspace : {}".format(leftspace))
                    print_debug(messages)

            elif self.mode == "array" and self.base_snap_vertex is not None:
                length = DraftVecUtils.dist(self.base_snap_vertex, original_point)
                space = length / (self.array_qty + 1)
                spaces_list = []
                for qty in range(self.array_qty):
                    spaces_list.append(space * (qty + 1))

                if reverse == True:
                    spaces_list = [x * -1 for x in spaces_list]
                    space = space * -1

                if DEBUG:
                    messages = ["Array :"]
                    messages.append("length : {}".format(length))
                    messages.append("qte : {}".format(self.array_qty))
                    messages.append("space : {}".format(space))
                    messages.append("spaces_list : {}".format(spaces_list))
                    print_debug(messages)

                FreeCADGui.doCommand(
                    "Draft.move(p, "
                    + vec_transaction.format(spaces_list[0], 0.0, 0.0)
                    + ")"
                )

                for x in spaces_list[1:]:
                    FreeCADGui.doCommand(
                        "p2 = Draft.move(p,"
                        + vec_transaction.format(str(x - space), 0.0, 0.0)
                        + ", copy=True)"
                    )

                    # Make the G3D Beam component
                    # Get the name of the profile object
                    FreeCADGui.doCommand(
                        "s = freecad.workbench_gespal3d.g3d_beam.makeG3DBeam("
                        + "p2.Name, '"
                        + str(self.Length)
                        + "', '"
                        + str(self.Profile[1])
                        + "', '"
                        + str(self.Profile[-1])
                        + "', '"
                        + str(self.Profile[0])
                        + "')"
                    )
            else:
                pass

        FreeCADGui.doCommand("Draft.autogroup(s)")
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        if self.continueCmd:
            self.Activated()


if FreeCAD.GuiUp:
    FreeCADGui.addCommand("G3D_BeamComposant", _CommandComposant())
