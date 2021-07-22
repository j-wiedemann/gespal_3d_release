# coding: utf-8

import os
import FreeCAD as App
import Draft

if App.GuiUp:
    import FreeCADGui as Gui
    from DraftTools import translate
    from freecad.workbench_gespal3d import g3d_connect_db
    from freecad.workbench_gespal3d import g3d_component_manager
    from freecad.workbench_gespal3d import PARAMPATH
    from freecad.workbench_gespal3d import ICONPATH
    from freecad.workbench_gespal3d import DEBUG
    from freecad.workbench_gespal3d import print_debug
    from PySide import QtCore, QtGui
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


__title__ = "Gespal3D Accessory tool"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"

def add_accesory(g3d_profile):
    p = App.ParamGet(str(PARAMPATH))
    cao_path = p.GetString("PathCAO", "no_path_cao")
    project_doc = App.ActiveDocument

    path = os.path.join(cao_path, g3d_profile[9])
    import Part
    print(path)
    Part.open(path)
    accessory_doc = App.ActiveDocument
    for obj in accessory_doc.Objects:
        if len(obj.Shape.Shells) == 0:
            if obj.Shape.isClosed() == False:
                try:
                    _ = Part.Shell([]+ obj.Shape.Faces)
                    if _.isNull(): raise RuntimeError('Failed to create shell')
                    accessory_doc.addObject('Part::Feature','Shell').Shape = _.removeSplitter()
                    del _
                    accessory_doc.removeObject(obj.Name)
                except:
                    pass

    for obj in accessory_doc.Objects:
        if len(obj.Shape.Solids) == 0:
            try:
                shell = obj.Shape
                if shell.ShapeType != 'Shell': raise RuntimeError('Part object is not a shell')
                _=Part.Solid(shell)
                if _.isNull(): raise RuntimeError('Failed to create solid')
                accessory_doc.addObject('Part::Feature','Solid').Shape=_.removeSplitter()
                del _
                accessory_doc.removeObject(obj.Name)
            except:
                pass
    links = accessory_doc.Objects
    if len(links) > 1:
        obj = accessory_doc.addObject("Part::Compound","Compound")
        obj.Links = links
        accessory_doc.recompute()
        Draft.move(
            obj.OutList,
            App.Vector(
                -obj.Shape.BoundBox.XMin,
                -obj.Shape.BoundBox.YMin,
                -obj.Shape.BoundBox.ZMin
                )
            )
        accessory_doc.recompute()
    else:
        obj = App.ActiveDocument.Objects[0]
    App.ActiveDocument.recompute()
    if obj.Shape.isValid():
        import Arch
        obj = Arch.makeEquipment(obj)
    else:
        obj.addProperty("App::PropertyString", "Description")
        obj.addProperty("App::PropertyString", "Tag")
        obj.addProperty("App::PropertyString", "IfcType")
        obj.addProperty("App::PropertyString", "PredefinedType")
        obj.addProperty("App::PropertyString", "EquipmentPower")
    # Set color
    color = g3d_profile[7].split(",")
    r = float(color[0]) / 255.0
    g = float(color[1]) / 255.0
    b = float(color[2]) / 255.0
    obj.ViewObject.ShapeColor = (r, g, b)
    obj.Label = g3d_profile[1]
    obj.IfcType = u"Transport Element"
    obj.PredefinedType = u"NOTDEFINED"
    obj.Tag = u"Gespal"
    obj.Description = str(g3d_profile[0])
    App.ActiveDocument.recompute()
    obj = project_doc.copyObject(obj, True)
    App.closeDocument(accessory_doc.Name)
    Gui.Selection.addSelection(project_doc.Name, obj.Name)
    Gui.runCommand('Draft_Move',0)


class _AccessoryTaskPanel:
    def __init__(self):
        print_debug("G3D ACCESSORY ACTIVATED")
        # parameters
        self.p = App.ParamGet(str(PARAMPATH))
        self.continueCmd = self.p.GetBool("AccessoryContinue", False)

        # fetch data from sqlite database
        self.categories = g3d_connect_db.getCategories(include=["QU"])
        print_debug("self.categories = ")
        print_debug([cat for cat in self.categories])

        # form
        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        grid = QtGui.QGridLayout(self.form)
        self.indication_label = QtGui.QLabel(self.form)
        grid.addWidget(self.indication_label, 0, 0, 1, 2)


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
        self.retranslateUi(self.form)

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
            continue_cb, QtCore.SIGNAL("stateChanged(int)"), self.setContinue
        )
        
        self.restoreParams()

    def restoreParams(self):
        print_debug("Accessory restoreParams")
        stored_composant = self.p.GetInt("AccessoryPreset", 0)

        if stored_composant != 0:
            if DEBUG:
                App.Console.PrintMessage("restore composant \n")
            comp = g3d_connect_db.getComposant(id=stored_composant)
            cat = comp[2]
            get_category = False
            n = 0
            for x in self.categories:
                if x[0] == cat:
                    self.categories_cb.setCurrentIndex(n)
                    get_category = True
                n += 1
            if get_category == False:
                self.setCategory(i=0)
                return
            self.composant_items = g3d_connect_db.getComposants(categorie=cat)
            self.composant_cb.clear()
            self.composant_cb.addItems([x[1] for x in self.composant_items])
            n = 0
            for x in self.composant_items:
                if x[0] == stored_composant:
                    self.composant_cb.setCurrentIndex(n)
                n += 1
        else:
            self.setCategory(i=0)

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
            self.p.SetInt("AccessoryPreset", comp[0])

    def setContinue(self, i):
        self.continueCmd = bool(i)
        if hasattr(Gui, "draftToolBar"):
            Gui.draftToolBar.continueMode = bool(i)
        self.p.SetBool("PanelContinue", bool(i))

    def accept(self):
        add_accesory(self.Profile)
    
    def reject(self):
        App.Console.PrintMessage("Annulation de l'ajout d'un accessoire.\n")
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle("Ajouter un acccessoire")
        self.indication_label.setText(
            "Choisir un accessoire dans la liste puis cliquer sur Ok.\nUne fois importé, l'objet peut être déplacé."
        )


class _CommandAccessory:

    "the Gespal3D Accessory command definition"

    def __init__(self):
        pass
        
    def GetResources(self):

        return {
            "Pixmap": "Arch_Equipment",
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Accessoire"),
            "Accel": "A, C",
            "ToolTip": QT_TRANSLATE_NOOP(
                "Paneaux",
                "<html><head/><body><p><b>Ajouter un accessoire.</b> \
                        </p></body></html>",
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
        warning = False
        categories = g3d_connect_db.getCategories(include=["QU"])
        if len(categories) == 0:
            warning = True
        else:
            composant_items = []
            c = 0
            for x in categories:
                composant_items.append(g3d_connect_db.getComposants(categorie=categories[c][0]))
                c += 1
            warning = True
            for x in composant_items:
                if len(x) > 0 :
                    warning = False
        if warning == False:
            panel = _AccessoryTaskPanel()
            Gui.Control.showDialog(panel)
        else:
            msg = QtGui.QMessageBox.information(
                None,
                "Pas d'accessoires !",
                "Il n'y a pas d'accessoire dans la base de données. Cliquer sur OK pour ouvrir le gestionnaire de composants.",
                QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Ok)
            #print(msg)
            if msg == QtGui.QMessageBox.Ok:
                Gui.runCommand('G3D_ComponentsManager',0)
                #form = g3d_component_manager.ComponentManager()


if App.GuiUp:
    Gui.addCommand("G3D_AccesoryComposant", _CommandAccessory())
