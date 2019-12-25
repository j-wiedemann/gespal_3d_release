import FreeCAD
import DraftVecUtils
from freecad.workbench_gespal3d import tracker
from freecad.workbench_gespal3d import connect_db

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


def typecheck(args_and_types, name="?"):
    """typecheck([arg1,type),(arg2,type),...]): checks arguments types"""
    for v, t in args_and_types:
        if not isinstance(v, t):
            w = "typecheck[" + str(name) + "]: "
            w += str(v) + " is not " + str(t) + "\n"
            FreeCAD.Console.PrintWarning(w)
            raise TypeError("Draft." + str(name))


class _CommandPanel:

    "the Gespal3D Panel command definition"

    def __init__(self):
        pass

    def GetResources(self):

        return {'Pixmap': 'Arch_Panel',
                'MenuText': QT_TRANSLATE_NOOP("Gespal3D", "Panneaux"),
                'Accel': "P, N",
                'ToolTip': QT_TRANSLATE_NOOP(
                    "Paneaux",
                    "Créer un panneau en cliquant sur deux points.")}

    def IsActive(self):
        active = False
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

    def Activated(self):
        # parameters
        path = "User parameter:BaseApp/Preferences/Mod/Gespal3D"
        self.p = FreeCAD.ParamGet(str(path))

        self.continueCmd = self.p.GetBool("PanelContinue", False)

        # fetch data from sqlite database
        # self.panelDB = connect_db.getPanelDB()

        self.wp = FreeCAD.DraftWorkingPlane
        self.basepoint = None
        self.tracker = tracker.rectangleTracker()
        self.tracker.setPlane(self.wp.axis)
        title = translate("Gespal3D", "Premier coin du panneau ") + ":"
        FreeCADGui.Snapper.getPoint(
            callback=self.getpoint,
            movecallback=self.update,
            extradlg=[self.taskbox()],
            title=title)

    def getpoint(self, point=None, obj=None):
        "this function is called by the snapper when it has a 3D point"
        # no point
        if point is None:
            print("no point : finalize panel tracker")
            self.tracker.finalize()
            return
        # first clic : pick rectangle origin
        if self.basepoint is None:
            print("first point : set origin panel tracker")
            self.setWorkingPlane(point=point)
            self.tracker.setorigin(point)
            self.basepoint = point
            FreeCADGui.Snapper.getPoint(
                last=point,
                callback=self.getpoint,
                movecallback=self.update,
                extradlg=[self.taskbox()],
                title=translate("Arch", "Next point")+":",
                mode="rectangle")
            return
        # second clic : make panel
        print("second point : finalize panel tracker")
        self.tracker.finalize()
        print("second point : make panel transaction")
        self.makeTransaction(point)

    def update(self, point, info):
        "this function is called by the Snapper when the mouse is moved"
        if FreeCADGui.Control.activeDialog():
            if self.basepoint:
                self.tracker.update(point)

    def taskbox(self):
        "sets up a taskbox widget"

        taskwidget = QtGui.QWidget()
        # ui = FreeCADGui.UiLoader()
        taskwidget.setWindowTitle(translate("Gespal3D", "Ajout d'un panneau"))
        grid = QtGui.QGridLayout(taskwidget)

        # categories
        """categories_label = QtGui.QLabel(translate("Gespal3D", "Famille"))
        self.categories_cb = QtGui.QComboBox()
        self.categories_cb.addItems(
            [str(cat[1]) for cat in self.panelDB["categories"]])
        grid.addWidget(categories_label, 0, 0, 1, 1)
        grid.addWidget(self.categories_cb, 0, 1, 1, 1)"""
        # presets box
        presets_label = QtGui.QLabel(translate("Gespal3D", "Plan"))
        self.wp_cb = QtGui.QComboBox()
        self.wp_cb.addItems(["+XY", "+XZ", "+YZ", "-XY", "-XZ", "-YZ"])
        grid.addWidget(presets_label, 0, 0, 1, 1)
        grid.addWidget(self.wp_cb, 0, 1, 1, 1)

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
            self.wp_cb,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.setWorkingPlane)

        QtCore.QObject.connect(
            continue_cb,
            QtCore.SIGNAL("stateChanged(int)"),
            self.setContinue)

        self.restoreParams()

        return taskwidget

    def restoreParams(self):
        # wp
        wp = self.p.GetInt("PanelWP", 0)
        if wp:
            self.wp_cb.setCurrentIndex(wp)
        self.setWorkingPlane()

    def setWorkingPlane(self, idx=None, point=None):
        if idx is None:
            idx = self.wp_cb.currentIndex()
        else:
            self.p.SetInt("PanelWP", idx)
        axis_list = [
            FreeCAD.Vector(0.0, 0.0, 1.0),
            FreeCAD.Vector(0.0, 1.0, 0.0),
            FreeCAD.Vector(1.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, -1.0),
            FreeCAD.Vector(0.0, -1.0, 0.0),
            FreeCAD.Vector(-1.0, 0.0, 0.0), ]

        upvec_list = [
            FreeCAD.Vector(0.0, 1.0, 0.0),
            FreeCAD.Vector(1.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, 1.0),
            FreeCAD.Vector(0.0, -1.0, 0.0),
            FreeCAD.Vector(-1.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, -1.0), ]

        if point is None:
            self.wp.setup(
                direction=axis_list[idx],
                point=FreeCAD.Vector(0.0, 0.0, 0.0),
                upvec=upvec_list[idx],
                force=True)
        else:
            self.wp.setup(
                direction=axis_list[idx],
                point=point,
                upvec=upvec_list[idx],
                force=True)

        FreeCADGui.Snapper.setGrid()
        self.tracker.setPlane(axis_list[idx])

    def setContinue(self, i):
        self.continueCmd = bool(i)
        if hasattr(FreeCADGui, "draftToolBar"):
            FreeCADGui.draftToolBar.continueMode = bool(i)
        self.p.SetBool("PanelContinue", bool(i))

    def makeTransaction(self, point=None):
        if point is not None:
            p1 = self.basepoint
            p3 = point
            diagonal = p3.sub(p1)
            p2 = p1.add(
                DraftVecUtils.project(diagonal, self.wp.v))
            p4 = p1.add(
                DraftVecUtils.project(diagonal, self.wp.u))
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
            qr = '(' + str(qr[0]) + ',' + str(qr[1]) + ',' \
                + str(qr[2]) + ',' + str(qr[3]) + ')'

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

            FreeCAD.ActiveDocument.openTransaction(
                translate("Gespal3D", "Ajouter un panneau"))
            FreeCADGui.addModule("Arch")

            # Create panel wit Arch Tool
            FreeCADGui.doCommand(
                'p = Arch.makePanel('
                + 'length=' + str(length) + ','
                + 'width=' + str(height) + ','
                + 'thickness=' + str(12.0)
                + ')')

            FreeCADGui.doCommand('pl = FreeCAD.Placement()')
            FreeCADGui.doCommand('pl.Rotation.Q = ' + qr)
            FreeCADGui.doCommand('pl.Base = ' + DraftVecUtils.toString(base))
            FreeCADGui.doCommand('p.Placement = pl')

            FreeCAD.ActiveDocument.commitTransaction()
            FreeCAD.ActiveDocument.recompute()
            if self.continueCmd:
                self.Activated()


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('PanelCreator', _CommandPanel())
