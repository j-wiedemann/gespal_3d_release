# coding: utf-8

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    import Arch
    import DraftVecUtils

    import math

    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP

    from freecad.workbench_gespal3d import g3d_tracker
    from freecad.workbench_gespal3d import g3d_connect_db
    from freecad.workbench_gespal3d import g3d_profiles_parser
    from freecad.workbench_gespal3d import DEBUG
    from freecad.workbench_gespal3d import print_debug
    from freecad.workbench_gespal3d import PARAMPATH
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


__title__ = "Gespal 3D Beam"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


def makeG3DBeam(
    g3d_profile = None,
    p1 = [0.0, 0.0, 0.0],
    p2 = [1000.0, 0.0, 0.0],
    anchor = 4,
    inclination = 0.0,
    ):
    """
    Create a G3D Beam (Arch Structure) from a given profile, with sprecified length, color and description.
    :param g3d_profile: list
    :param p1: list[float]
    :param p2: list[float]
    :param anchor: int
    :param inclination: float
    :param description: str
    :return: object
    """

    print_debug(
        [
            "",
            "makeG3DBeam called with :",
            "g3d_profile : {}, type : {}".format(g3d_profile, type(g3d_profile)),
            "p1 : {}, type : {}".format(p1, type(p1)),
            "p2 : {}, type : {}".format(p2, type(p2)),
            "anchor : {}, type : {}".format(anchor, type(anchor)),
            "inclination : {}, type : {}".format(inclination, type(inclination)),
            "",
        ]
    )

    p1 = App.Vector(p1[0], p1[1], p1[2])
    p2 = App.Vector(p2[0], p2[1], p2[2])
    
    if g3d_profile is None:
        section = g3d_profiles_parser.makeProfile() 
    else:
        section = g3d_profiles_parser.makeProfile(
            profile = g3d_profile
        ) 
    
    if g3d_profile[6] == 'R':
        height = section.Height
        width = section.Width
    elif g3d_profile[6] == 'C':
        height = width = section.Diameter

    length = DraftVecUtils.dist(p1, p2)
    
    delta_list = [
                App.Vector(height/2,  -width/2, 0),
                App.Vector(0,         -width/2, 0),
                App.Vector(-height/2, -width/2, 0),

                App.Vector(height/2,  0,        0),
                App.Vector(0,         0,        0),
                App.Vector(-height/2, 0,        0),

                App.Vector(height/2,  width/2,  0),
                App.Vector(0,         width/2,  0),
                App.Vector(-height/2, width/2,  0),
            ]
    delta = delta_list[anchor]  

    pl = App.Placement()  # objet Placement
    pl.Base = p1  # base est coordonnée p1
    zaxis = p2.sub(p1)  # zaxis = soustraction de p2 - p1
    inclination = inclination * -1
    if zaxis.x == 0 and zaxis.y == 0: # orientation verticale
        up = App.Vector(0, -1, 0)
        yaxis = up.cross(zaxis)  # yaxis = produit vectoriel entre Z et zaxis 
        xaxis = zaxis.cross(yaxis)  # xaxis = produit vectoriel entre zaxis et yaxis
        pl.Rotation = App.Rotation(xaxis,yaxis,zaxis,"ZXY")
        #inclination = inclination + 180.0
        inclination = inclination + 90.0
        pl.Rotation = App.Rotation(pl.Rotation.multVec(App.Vector(0,0,1)), inclination).multiply(pl.Rotation)
    else:
        up = App.Vector(0, 0, 1)  # vector up = Z
        yaxis = up.cross(zaxis)  # yaxis = produit vectoriel entre Z et zaxis 
        xaxis = zaxis.cross(yaxis)  # xaxis = produit vectoriel entre zaxis et yaxis
        pl.Rotation = App.Rotation(xaxis,yaxis,zaxis,"ZXY")
        inclination = inclination + 90.0
        pl.Rotation = App.Rotation(pl.Rotation.multVec(App.Vector(0,0,1)), inclination).multiply(pl.Rotation)
    
    delta = pl.Rotation.multVec(delta)
    pl.Base = p1.add(delta)

    section.Placement = pl

    beam = Arch.makeStructure(section, length=length)

    beam.Profile = g3d_profile[1]
    # Set color
    color = g3d_profile[7].split(",")
    r = float(color[0]) / 255.0
    g = float(color[1]) / 255.0
    b = float(color[2]) / 255.0
    beam.ViewObject.ShapeColor = (r, g, b)

    beam.Label = g3d_profile[1]
    beam.IfcType = u"Transport Element"
    beam.PredefinedType = u"NOTDEFINED"
    beam.Tag = u"Gespal"
    beam.Description = str(g3d_profile[0])
    beam.MoveBase = True
    App.activeDocument().recompute(None, True, True)
    return beam


class _CommandComposant:

    "Gespal 3D - Beam Creator tool"

    def __init__(self):
        pass

    def GetResources(self):

        "Tool resources"

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

        "Conditions to the tool to be active"

        active = False
        if App.ActiveDocument:
            for obj in App.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

    def Activated(self):

        "When the tool is clicked"

        print_debug(["","---------","Beam Creator Activated"])

        # Reads preset profiles and categorizes them
        self.categories = g3d_connect_db.getCategories(include=["BO"])

        self.params = App.ParamGet(str(PARAMPATH))

        product = App.ActiveDocument.getObject("Product")
        if hasattr(product, "Length"):
            self.product = [
                product.Length.Value,
                product.Width.Value,
                product.Height.Value,
            ]
        else:
            product = App.ActiveDocument.getObject("Box")
            self.product = [
                product.Length.Value,
                product.Width.Value,
                product.Height.Value,
            ]


        self.clicked_points = []

        self.tracker = g3d_tracker.beamTracker(shaded=False)
                
        title = translate("Gespal3D", "Point de départ du composant") + ":"
        
        Gui.Snapper.getPoint(
            callback=self.getPoint,
            movecallback=self.update,
            extradlg=[self.taskbox()],
            title=title,
        )

    def taskbox(self):
        "sets up a taskbox widget"

        taskwidget = QtGui.QWidget()
        ui = Gui.UiLoader()
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
                "Libre",
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

        insert = QtGui.QRadioButton("&1")
        #if self.anchor_idx == 0:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 0)
        buttons_grid.addWidget(insert, 2, 0, 1, 1)

        insert = QtGui.QRadioButton("&2")
        #if self.anchor_idx == 1:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 1)
        buttons_grid.addWidget(insert, 2, 1, 1, 1)

        insert = QtGui.QRadioButton("&3")
        #if self.anchor_idx == 2:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 2)
        buttons_grid.addWidget(insert, 2, 2, 1, 1)

        insert = QtGui.QRadioButton("&4")
        #if self.anchor_idx == 3:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 3)
        buttons_grid.addWidget(insert, 1, 0, 1, 1)

        insert = QtGui.QRadioButton("&5")
        #if self.anchor_idx == 4:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 4)
        buttons_grid.addWidget(insert, 1, 1, 1, 1)

        insert = QtGui.QRadioButton("&6")
        #if self.anchor_idx == 5:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 5)
        buttons_grid.addWidget(insert, 1, 2, 1, 1)

        insert = QtGui.QRadioButton("&7")
        #if self.anchor_idx == 6:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 6)
        buttons_grid.addWidget(insert, 0, 0, 1, 1)

        insert = QtGui.QRadioButton("&8")
        #if self.anchor_idx == 7:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 7)
        buttons_grid.addWidget(insert, 0, 1, 1, 1)

        insert = QtGui.QRadioButton("&9")
        #if self.anchor_idx == 8:
        #    insert.setChecked(True)
        self.insert_group.addButton(insert, 8)
        buttons_grid.addWidget(insert, 0, 2, 1, 1)

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

        # inclination
        inclination_label = QtGui.QLabel(translate("Gespal3D", "Déversement"))
        self.inclination_input = ui.createWidget("Gui::InputField")        
        grid.addWidget(inclination_label, 8, 0, 1, 1)
        grid.addWidget(self.inclination_input, 8, 1, 1, 1)

        # width
        width_label = QtGui.QLabel(translate("Arch", "Width"))
        self.width_input = ui.createWidget("Gui::InputField")
        
        grid.addWidget(width_label, 12, 0, 1, 1)
        grid.addWidget(self.width_input, 12, 1, 1, 1)

        # height
        height_label = QtGui.QLabel(translate("Arch", "Height"))
        self.height_input = ui.createWidget("Gui::InputField")
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
        self.distribution_cb = QtGui.QCheckBox(translate("Gespal3D", "&Répartition"))
        repartition_label = QtGui.QLabel(translate("Gespal3D", "Quantité"))
        self.distribution_input = QtGui.QSpinBox()
        self.distribution_input.setRange(1, 9999)
        self.distribution_input.setDisabled(True)
        self.distribution_start = QtGui.QCheckBox("Début")
        #self.distribution_start.setDisabled(True)
        self.distribution_end = QtGui.QCheckBox("Fin")
        #self.distribution_end.setDisabled(True)
        layout_repartition.addWidget(self.distribution_cb, 0, 0, 1, 1)
        layout_repartition.addWidget(repartition_label, 1, 0, 1, 1)
        layout_repartition.addWidget(self.distribution_input, 1, 1, 1, 1)
        layout_repartition.addWidget(self.distribution_start, 2, 0, 1, 1)
        layout_repartition.addWidget(self.distribution_end, 2, 1, 1, 1)
        layout_repartition.setColumnStretch(1, 1)

        # remplissage
        self.filling_cb = QtGui.QCheckBox(translate("Gespal3D", "Rem&plissage"))
        self.filling_cb.setDisabled(True)
        remplissage_label = QtGui.QLabel(translate("Gespal3D", "Claire voie"))
        self.filling_input = ui.createWidget("Gui::InputField")
        self.filling_input.setDisabled(True)
        self.filling_input.setText(
            App.Units.Quantity(0.0, App.Units.Length).UserString
        )
        layout_remplissage.addWidget(self.filling_cb, 0, 0, 1, 1)
        layout_remplissage.addWidget(remplissage_label, 1, 0, 1, 1)
        layout_remplissage.addWidget(self.filling_input, 1, 1, 1, 1)

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
            self.length_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setLength
        )
        QtCore.QObject.connect(
            self.fixlength_checkbox,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setFixedLength,
        )
        QtCore.QObject.connect(
            self.inclination_input,
            QtCore.SIGNAL("valueChanged(double)"),
            # QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setInclination,
        )
        QtCore.QObject.connect(
            self.insert_group,
            QtCore.SIGNAL("buttonClicked(int)"),
            self.setAnchor
        )
        QtCore.QObject.connect(
            self.width_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setWidth
        )
        QtCore.QObject.connect(
            self.height_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setHeight
        )
        QtCore.QObject.connect(
            self.distribution_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setDistributionMode
        )
        QtCore.QObject.connect(
            self.continue_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setContinue
        )
        QtCore.QObject.connect(
            self.distribution_input,
            QtCore.SIGNAL("valueChanged(int)"),
            self.setDistributionQty
        )
        QtCore.QObject.connect(
            self.distribution_start,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setDistributionStart
        )
        QtCore.QObject.connect(
            self.distribution_end,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setDistributionEnd
        )
        QtCore.QObject.connect(
            self.filling_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setFillingMode
        )
        QtCore.QObject.connect(
            self.filling_input,
            QtCore.SIGNAL("valueChanged(double)"),
            self.setFillingSpace,
        )
        
        # restore preset
        self.restoreParams()

        return taskwidget

    def restoreParams(self):
        print_debug(["", "Start restoreParams"])

        self.composant = self.params.GetInt("BeamPreset", 1)
        self.Width = self.params.GetFloat("BeamWidth", 100)
        self.Height = self.params.GetFloat("BeamHeight", 22)
        self.Length = self.params.GetFloat("BeamLength", 1200)
        self.Profile = None
        self.anchor_idx = self.params.GetInt("BeamAnchor", 0)
        self.inclination = self.params.GetFloat("BeamDev", 0.0)
        self.continueCmd = self.params.GetBool("BeamContinue", True)
        self.fill_space = self.params.GetFloat("BeamFillingSpace", 0.0)
        self.distribution_qty = self.params.GetInt("BeamDistributionQty", 1)
        self.direction = self.params.GetString("BeamDirection", '+x')  # direction could be line, +x, -x, +y, -y, +z, -z
        self.pattern = self.params.GetString("BeamPattern", 'none')  # pattern could be 'none', 'distribution', 'filling'
        self.fixed_length = self.params.GetBool("BeamFixLength", 0)

        if self.Width is not None:
            print_debug("restore beam width")
            self.width_input.setText(
                App.Units.Quantity(self.Width, App.Units.Length).UserString
            )

        if self.Height is not None:
            print_debug("restore beam height")
            self.height_input.setText(
                App.Units.Quantity(self.Height, App.Units.Length).UserString
            )

        if self.Length is not None:
            print_debug("restore beam length")
            self.length_input.setText(
                App.Units.Quantity(self.Length, App.Units.Length).UserString
            )

        if self.composant is not None:
            print_debug("restore composant")
            comp = g3d_connect_db.getComposant(id=self.composant)
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
                if x[0] == self.composant:
                    self.composant_cb.setCurrentIndex(n)
                n += 1

        if self.direction is not None:
            print_debug("restore direction")
            directions = ['+x', '+y', '+z', '-x', '-y', '-z', 'line']
            idx = directions.index(self.direction)
            self.direction_cb.setCurrentIndex(idx)

        if self.inclination is not None:
            print_debug("restore inclination")
            self.inclination_input.setText(
                App.Units.Quantity(
                    self.inclination,
                    App.Units.Angle).UserString)
        
        if self.anchor_idx is not None:
            print_debug("restore anchor")
            anchor_button = self.insert_group.buttons()[self.anchor_idx]
            anchor_button.setChecked(True)
        
        if self.pattern is not None:
            print_debug("restore pattern")
            if len(self.clicked_points) > 0:
                #print_debug("len clicked point > 0")
                if self.pattern == 'distribution':
                    self.distribution_cb.setChecked(True)
                    if self.params.GetBool("BeamDistributionStart", False):
                        self.distribution_start.setChecked(True)
                    if self.params.GetBool("BeamDistributionEnd", False):
                        self.distribution_end.setChecked(True)
                elif self.pattern == 'filling':
                    self.filling_cb.setChecked(True)
            else:
                #print_debug("len clicked point <= 0")
                self.filling_cb.setChecked(False)
                self.distribution_cb.setChecked(False)
                self.params.SetBool("BeamDistributionStart", False)
                self.params.SetBool("BeamDistributionEnd", False)
                self.pattern = 'none'
                self.params.SetString("BeamPattern", 'none')
            print_debug(self.pattern)

        if self.distribution_qty is not None:
            print_debug("restore array_qty")
            self.distribution_input.setValue(self.distribution_qty)

        if self.fill_space is not None:
            print_debug("restore fillspace")
            self.filling_input.setText(
                App.Units.Quantity(self.fill_space, App.Units.Length).UserString
            )

        if self.fixed_length is not None:
            print_debug("restore fixlength")
            self.fixlength_checkbox.setChecked(bool(self.fixed_length))

        if self.continueCmd is not None:
            print_debug("restore continue mode")
            self.continue_cb.setChecked(self.continueCmd)

        if self.direction != 'line':
            if len(self.clicked_points) == 0:
                self.tracker.on()

        if DEBUG:
            messages = ["", "End of restore params :"]
            messages.append("détails de la liste des points cliqués :")
            messages.append("longueur = {}".format(len(self.clicked_points)))
            for p in self.clicked_points:
                messages.append(str(p))
            messages.append("Profile = {}".format(self.Profile))
            messages.append("Width = {}".format(self.Width))
            messages.append("Height = {}".format(self.Height))
            messages.append("Length = {}".format(self.Length))
            messages.append("Anchor index = {}".format(self.anchor_idx))
            messages.append("direction = {}".format(self.direction))
            messages.append("Inclination = {}".format(self.inclination))
            messages.append("Pattern = {}".format(self.pattern))
            messages.append("FillSpace = {}".format(self.fill_space))
            messages.append("array_qty = {}".format(self.distribution_qty))
            messages.append("continueCmd = {}".format(self.continueCmd))
            messages.append("fixed = {}".format(str(self.fixed_length)))
            messages.append("")
            print_debug(messages)

    def getPoint(self, point=None, obj=None):
        "this function is called by the snapper when it has a 3D point"

        # pas de point
        if point is None:
            self.tracker.finalize()
            return
        else:
            self.clicked_points.append(
                App.Vector(
                    round(point.x, 2), round(point.y, 2), round(point.z, 2)
                )
            )

        if self.pattern == 'none':
            if self.direction != 'line':
                self.clicked_points.append(
                    self.clicked_points[0].add(
                        self.get_final_point(
                            self.direction
                        )
                    )
                )
                self.tracker.finalize()
                self.makeTransaction()
                return
            elif self.direction == 'line':
                if len(self.clicked_points) == 1:
                    self.tracker.on()
                    snapper_last = self.clicked_points[0]
                    snapper_title = "Point suivant"
                elif len(self.clicked_points) == 2:
                    self.tracker.finalize()
                    self.makeTransaction()
                    return
                else:
                    pass
            else:
                return
        elif (self.pattern == 'distribution') or (self.pattern == 'filling'):
            if self.direction != 'line':
                if len(self.clicked_points) == 1:
                    self.clicked_points.append(
                        self.clicked_points[0].add(
                            self.get_final_point(
                                self.direction
                            )
                        )
                    )
                    self.tracker.finalize()
                    snapper_last = self.clicked_points[0]
                    snapper_title = "Point suivant"
                elif len(self.clicked_points) == 3:
                    #self.tracker.finalize()
                    self.makeTransaction()
                    return
                else:
                    return
            elif self.direction == 'line':
                if len(self.clicked_points) == 1:
                    snapper_last = self.clicked_points[0]
                    snapper_title = "Point d'arrivé du composant"
                elif len(self.clicked_points) == 2:
                    self.tracker.finalize()
                    snapper_last = self.clicked_points[0]
                    snapper_title = "Point d'arrivé de la répartition"
                elif len(self.clicked_points) == 3:
                    self.makeTransaction()
                    return
                else:
                    return
        else:
            return

        Gui.Snapper.getPoint(
            last=snapper_last,
            callback=self.getPoint,
            movecallback=self.update,
            extradlg=[self.taskbox()],
            title=translate("Gespal3D", snapper_title) + ":",
            mode="line",
        )

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"

        if Gui.Control.activeDialog():

            if self.direction != "line":
                if len(self.clicked_points) == 0:
                    final_point = point.add(self.get_final_point(self.direction))
                    self.tracker.update(
                        anchor_idx=self.anchor_idx,
                        inclination=self.inclination,
                        base_snap_vertex=point,
                        final_snap_vertex=final_point,
                    )
                    self.tracker.on()

            elif self.direction == "line":
                if len(self.clicked_points) == 1:
                    length = DraftVecUtils.dist(self.clicked_points[0],point)
                    self.length_input.setText(
                        App.Units.Quantity(length, App.Units.Length).UserString
                    )
                    self.tracker.update(
                        inclination=self.inclination,
                        anchor_idx=self.anchor_idx,
                        base_snap_vertex=self.clicked_points[0],
                        final_snap_vertex=point,
                    )
                    self.tracker.on()

            else:
                self.tracker.off()

        else:
            Gui.Snapper.toggleGrid()

    def setCategory(self, idx):
        self.composant_cb.clear()
        fc_compteur = self.categories[idx][0]
        self.composant_items = g3d_connect_db.getComposants(categorie=fc_compteur)
        self.composant_cb.addItems([x[1] for x in self.composant_items])

    def setComposant(self, i=0):
        print_debug(["", "Start setComposant :"])
        self.Profile = None
        idx = self.composant_items[i][0]
        comp = g3d_connect_db.getComposant(id=idx)

        if comp:
            print_debug("composant : w = {} ; h = {} ; l = {}".format(float(comp[5]), float(comp[4]), float(comp[3])))
            self.Profile = comp
            # width
            if float(comp[5]) > 0.0:
                self.width_input.setText(
                    App.Units.Quantity(float(comp[5]), App.Units.Length).UserString
                )
                self.width_input.setDisabled(True)
            else:
                self.width_input.setDisabled(False)

            # height
            if float(comp[4]) > 0.0:
                self.height_input.setText(
                    App.Units.Quantity(float(comp[4]), App.Units.Length).UserString
                )
                self.height_input.setDisabled(True)
            else:
                self.height_input.setDisabled(False)

            # length
            if float(comp[3]) > 0.0:
                self.length_input.setText(
                    App.Units.Quantity(float(comp[3]), App.Units.Length).UserString
                )
                self.length_input.setDisabled(True)
                self.fixlength_checkbox.setDisabled(True)
                self.fixlength_checkbox.setChecked(True)
            else:
                self.length_input.setDisabled(False)
                self.fixlength_checkbox.setDisabled(False)
                self.fixlength_checkbox.setChecked(False)
                self.length_input.setText(
                    App.Units.Quantity(self.Length, App.Units.Length).UserString
                )
                
            self.params.SetInt("BeamPreset", comp[0])
        else:
            print_debug("no composant")
        print_debug(["End setComposant", ""])

    def get_final_point(self, dir='+x'):
        l = self.Length
        final_point = {
            '+x' : App.Vector( l,  0,  0),
            '-x' : App.Vector(-l,  0,  0),
            '+y' : App.Vector( 0,  l,  0),
            '-y' : App.Vector( 0, -l,  0),
            '+z' : App.Vector( 0,  0,  l),
            '-z' : App.Vector( 0,  0, -l),
        }

        return final_point[dir]

    def setDirection(self):
        print_debug(["", "Start setDirection :"])
        directions = ['+x', '+y', '+z', '-x', '-y', '-z', 'line']
        idx = self.direction_cb.currentIndex()
            print_debug("setDirection : idx={}, str={}".format(idx, directions[idx]))
        self.params.SetString("BeamDirection", directions[idx])
        self.direction = directions[idx]
        if self.fixed_length == False:
            print_debug("self.fixed_length is False")
            if 'x' in self.direction:
                self.Length = self.product[0]
                self.length_input.setText(
                    App.Units.Quantity(self.Length, App.Units.Length).UserString
                )
            elif 'y' in self.direction:
                self.Length = self.product[1]
                self.length_input.setText(
                    App.Units.Quantity(self.Length, App.Units.Length).UserString
                )
            elif 'z' in self.direction:
                self.Length = self.product[2]
                self.length_input.setText(
                    App.Units.Quantity(self.Length, App.Units.Length).UserString
                )
        else:
            print_debug("self.fixed_length is True")
        print_debug(["End setDirection", ""])

    def setAnchor(self):
        self.anchor_idx = self.insert_group.checkedId()
        self.params.SetInt("BeamAnchor", self.anchor_idx)

    def setInclination(self, idx):
        self.inclination = idx
        self.params.SetFloat("BeamDev", idx)

    def setFixedLength(self, i):
        self.params.SetBool("BeamFixLength", bool(i))

    def setLength(self, d):
        self.Length = d
        self.tracker.length(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.params.SetFloat("BeamLength", d)

    def setWidth(self, d):
        self.Width = d
        self.tracker.height(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.params.SetFloat("BeamWidth", d)

    def setHeight(self, d):
        self.Height = d
        self.tracker.width(d)
        self.tracker.update(anchor_idx=self.anchor_idx, inclination=self.inclination)
        self.params.SetFloat("BeamHeight", d)

    def setContinue(self, i):
        self.continueCmd = bool(i)
        self.params.SetBool("BeamContinue", bool(i))

    def setDistributionMode(self, state):
        print_debug(['distribution cb state: {}'.format(state)])
        if state == 2:
            self.pattern = "distribution"
            self.filling_input.setDisabled(True)
            self.filling_cb.setChecked(False)
            self.distribution_input.setDisabled(False)
            self.distribution_start.setDisabled(False)
            self.distribution_end.setDisabled(False)
        else:
            self.distribution_input.setDisabled(True)
            self.distribution_start.setDisabled(True)
            self.distribution_end.setDisabled(True)
            if not self.filling_cb.isChecked():
                self.pattern = 'none'
        self.params.SetString("BeamPattern", str(self.pattern))

    def setDistributionQty(self):
        self.distribution_qty = self.distribution_input.value()
        self.params.SetInt("BeamDistributionQty", self.distribution_qty)

    def setDistributionStart(self):
        if self.distribution_start.isChecked():
            self.params.SetBool("BeamDistributionStart", True)
        else:
            self.params.SetBool("BeamDistributionStart", False)

    def setDistributionEnd(self):
        if self.distribution_end.isChecked():
            self.params.SetBool("BeamDistributionEnd", True)
        else:
            self.params.SetBool("BeamDistributionEnd", False)

    def setFillingMode(self, state):
        print_debug(['filling cb state: {}'.format(state)])
        if state == 2:
            self.pattern = "filling"
            self.filling_input.setDisabled(False)
            self.distribution_input.setDisabled(True)
            self.distribution_start.setDisabled(True)
            self.distribution_end.setDisabled(True)
            self.distribution_cb.setChecked(False)
        else:
            self.filling_input.setDisabled(True)
            if not self.distribution_cb.isChecked():
                self.pattern = 'none'
        self.params.SetString("BeamPattern", str(self.pattern))

    def setFillingSpace(self, d):
        self.fill_space = d
        self.params.SetFloat("BeamFillingSpace", d)

    def makeTransaction(self, point=None):
        """g3d beam makeTransaction"""
        msg = ["", "----------", "makeTransaction"]
        msg.append("la direction est : {}".format(str(self.direction)))
        msg.append("le mode de pattern est : {}".format(str(self.pattern)))
        msg.append("Détails de la liste des points cliqués :")
        msg.append("longueur = {}".format(len(self.clicked_points)))
        for p in self.clicked_points:
            msg.append(str(p))
        print_debug(msg)

        commands = []
        if self.pattern == 'none':
            transaction_name = "Create G3DBeam from 1 points"
            command = "freecad.workbench_gespal3d.g3d_beam.makeG3DBeam(" \
            + "g3d_profile={}, ".format(str(self.Profile)) \
            + "p1={}, ".format(str(DraftVecUtils.tup(self.clicked_points[0],True))) \
            + "p2={}, ".format(str(DraftVecUtils.tup(self.clicked_points[1],True))) \
            + "anchor={}, ".format(self.anchor_idx) \
            + "inclination={}, ".format(self.inclination) \
            + ")"
            commands.append(command)

        elif self.pattern == 'distribution':
            transaction_name = "Création d'une répartition de composants."
            length = DraftVecUtils.dist(self.clicked_points[0], self.clicked_points[2])
            space = length / (self.distribution_qty + 1)
            vec = self.clicked_points[2].sub(self.clicked_points[0])
            vec_norm = vec.normalize()
            vec_axe = vec_norm.multiply(space)
            p1 = self.clicked_points[0]
            p2 = self.clicked_points[1]
            qty = self.distribution_qty
            if self.distribution_start.isChecked():
                p1 = p1.sub(vec_axe)
                p2 = p2.sub(vec_axe)
                qty += 1
            if self.distribution_end.isChecked():
                qty += 1
            for distri in range(qty):
                #if not self.distribution_start.isChecked():    
                p1 = p1.add(vec_axe)
                p2 = p2.add(vec_axe)
                command = "freecad.workbench_gespal3d.g3d_beam.makeG3DBeam(" \
                + "g3d_profile={}, ".format(str(self.Profile)) \
                + "p1={}, ".format(str(DraftVecUtils.tup(p1, True))) \
                + "p2={}, ".format(str(DraftVecUtils.tup(p2, True))) \
                + "anchor={}, ".format(self.anchor_idx) \
                + "inclination={}, ".format(self.inclination) \
                + ")"
                commands.append(command)

        elif self.pattern == 'filling':
            transaction_name = "Création d'un remplissage de composants."
            length = DraftVecUtils.dist(self.clicked_points[0], self.clicked_points[2])
            space = length / (self.distribution_qty + 1)
            vec = self.clicked_points[2].sub(self.clicked_points[0])
            vec_norm = vec.normalize()
            vec_axe = vec_norm.multiply(space)
            p1 = self.clicked_points[0]
            p2 = self.clicked_points[1]
            for qty in range(self.distribution_qty):
                p1 = p1.add(vec_axe)
                p2 = p2.add(vec_axe)
                command = "freecad.workbench_gespal3d.g3d_beam.makeG3DBeam(" \
                + "g3d_profile={}, ".format(str(self.Profile)) \
                + "p1={}, ".format(str(DraftVecUtils.tup(p1, True))) \
                + "p2={}, ".format(str(DraftVecUtils.tup(p2, True))) \
                + "anchor={}, ".format(self.anchor_idx) \
                + "inclination={}, ".format(self.inclination) \
                + ")"
                commands.append(command)



        else:
            App.Console.PrintWarning("This mode is not implemented")
            return
        
        App.ActiveDocument.openTransaction(translate("Gespal3D", transaction_name))
        Gui.addModule("freecad.workbench_gespal3d.g3d_beam")
        for command in commands:
            Gui.doCommand(command)
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()

        if self.continueCmd:
            self.Activated()
            return
        else:
            return

if App.GuiUp:
    Gui.addCommand("G3D_BeamComposant", _CommandComposant())

App.Console.PrintLog("Loading G3D Beam... done\n")
