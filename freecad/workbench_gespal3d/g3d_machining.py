# coding: utf-8

import FreeCAD as App
import os

if App.GuiUp:
    import FreeCADGui as Gui
    import Arch
    from pivy import coin
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
    from freecad.workbench_gespal3d import ICONPATH
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt

    # \endcond


__title__ = "Gespal 3D Machining tool"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class _CommandMachining:

    """Gespal 3D - Machinings tool

    This command allow user to create a free machining on a composant.
    The command will guide the user through a sequence of command and operation to achieve the machining.
    The sequences are :
        Select a face of an existing composant.
        Let the user choose a drafting command between Circle, Rectangle and Polyligne.
        Let him drafting his profile.
        Then directly allow him to extrude the profile.
        At the end the command make the soustraction from the Arch component."""

    def __init__(self):
        pass

    def GetResources(self):

        return {
            "Pixmap": os.path.join(ICONPATH, "PartDesign_Pocket.svg"),
            "MenuText": QT_TRANSLATE_NOOP("Gespal3D", "Usinage"),
            "Accel": "U, S",
            "ToolTip": "<html><head/><body><p><b>Créer un usinage.</b> \
                    <br><br> \
                    Sélectionner la face de l'objet ou faire l'usinage, \
                    choisir un outil draft (rectangle ou cercle) pour dessiner l'usinage, \
                    puis choisir la profondeur de l'usinage (avec la souris ou en rentrant la valeur. \
                    </p></body></html>",
        }

    def IsActive(self):
        """Always active...

        TODO: Active only if there is at least 1 composant or 1 panel"""
        active = True
        return active

    def Activated(self):
        self.states = [
            'selecting_face',
            'choosing_drafting_tools',
            'drawing',
            'extruding',
            'finalizing']
        self.state = self.states[0]

        # Coin Separator for text helping user during the command

        textSep = coin.SoSeparator()
        cam = coin.SoOrthographicCamera()
        cam.aspectRatio = 1
        cam.viewportMapping = coin.SoCamera.LEAVE_ALONE

        trans = coin.SoTranslation()
        trans.translation = (-0.98, 0.85, 0)

        myFont = coin.SoFont()
        myFont.name = "Arial"
        size = 50
        myFont.size.setValue(size)
        self.SoText2 = coin.SoText2()
        self.SoText2.string.setValues(0,2,["Sélectionner une face d'un composant",""])
        color = coin.SoBaseColor()
        color.rgb = (0, 0, 0)

        textSep.addChild(cam)
        textSep.addChild(trans)
        textSep.addChild(color)
        textSep.addChild(myFont)
        textSep.addChild(self.SoText2)

        activeDoc = Gui.ActiveDocument
        view = activeDoc.ActiveView
        self.sg = view.getSceneGraph()
        viewer = view.getViewer()
        self.render = viewer.getSoRenderManager()
        self.sup = self.render.addSuperimposition(textSep)
        self.sg.touch()

        # Timer to check what the user is doing
        self.machining_timer = QtCore.QTimer()
        self.machining_timer.setInterval(200)
        self.machining_timer.timeout.connect(self.check)
        self.start()

    def start(self):
        """Start the Machining command"""
        self.machining_timer.start()
        #print('timer started')

    def pause(self):
        """Pause the Machining command"""
        self.machining_timer.stop()
        #print('timer paused')
        self.render.removeSuperimposition(self.sup)

    def stop(self):
        """Stop the Machining command"""
        self.machining_timer.stop()
        #print('timer stopped')
        self.state = self.states[0]
        self.parent_obj = None
        self.profil = None
        self.render.removeSuperimposition(self.sup)

    def check(self):
        """Check the state of the command :
        State could be :
        'selecting_face',
        'choosing_drafting_tools',
        'drawing',
        'extruding',
        'finalizing'
        """
        self.sg.touch()
        if self.state == 'selecting_face':
            #print('state : selecting_face')
            self.get_face()
        elif self.state == 'choosing_drafting_tools':
            self.SoText2.string.setValues(0,2,["Choisissez un outil de dessin","Rectangle, Cercle ou Polyligne"])
            #print('state : choosing_drafting_tools')
            self.wait_drafting_tool()
        elif self.state == 'drawing':
            self.SoText2.string.setValues(0,2,["Dessiner le contour",""])
            #print('state : drawing')
            self.wait_drafting()
        elif self.state == 'extruding':
            self.SoText2.string.setValues(0,2,["Profondeur de l'extrusion",""])
            #print('state : extruding')
            self.wait_trimex()
        elif self.state == 'finalizing':
            #print('state : finalizing')
            self.stop()
        else:
            #print("state : Unknown !")
            self.stop()

    def get_face(self):
        """Get the selected face to start the command"""
        sel = Gui.Selection.getSelection()
        if len(sel)>0:
            self.state = self.states[1]
            #print("face is selected")
            workplane = App.DraftWorkingPlane
            workplane.alignToSelection()
            Gui.Snapper.toggleGrid()
            Gui.Snapper.toggleGrid()
            self.parent_obj = sel[0]
        #else:
            #print('select face from solid')

    def wait_drafting_tool(self):
        #if not Gui.Control.activeDialog():
        if Gui.Control.activeDialog():
            #print('user is choosing a draft command')
        #else:
            self.state = self.states[2]
            #print('draft command started')
            #self.parent_obj.ViewObject.Selectable = False
            self.parent_obj.ViewObject.DisplayMode = u"Wireframe"
            Gui.Snapper.toggle_snap('WorkingPlane',True)

    def wait_drafting(self):
        #if Gui.Control.activeDialog():
        if not Gui.Control.activeDialog():
            #print("draft command in use")
        #else :
            #print("draft command is over")
            self.profil = Gui.Selection.getSelection()[0]
            #print("trimex command started")
            self.state = self.states[3]
            Gui.runCommand('Draft_Trimex',0)
            self.parent_obj.ViewObject.DisplayMode = u"Flat Lines"
            self.parent_obj.ViewObject.Transparency = 90
            #self.parent_obj.ViewObject.Selectable = True
            Gui.Snapper.toggle_snap('WorkingPlane',False)

    def wait_trimex(self):
        #if Gui.Control.activeDialog():
        if not Gui.Control.activeDialog():
            #print("trimex command in use")
        #else :
            self.state = self.states[4]
            #print("trimex command in OVER!!!")
            self.parent_obj.ViewObject.Transparency = 0
            machining = Arch.makeStructure(self.profil.InList[0])
            machining.MoveWithHost = True
            Arch.removeComponents([machining],self.parent_obj)
            App.ActiveDocument.recompute()

if App.GuiUp:
    Gui.addCommand("G3D_Machining", _CommandMachining())
