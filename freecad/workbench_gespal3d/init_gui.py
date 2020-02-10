import os
import FreeCADGui as Gui
import FreeCAD as App
from freecad.workbench_gespal3d import ICONPATH
from freecad.workbench_gespal3d import PARAMPATH
from freecad.workbench_gespal3d import enveloppe_creator
from freecad.workbench_gespal3d import beam_creator
from freecad.workbench_gespal3d import panel_creator
from freecad.workbench_gespal3d import list_creator

__title__="Gespal 3D InitGui"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class gespal3d_workbench(Gui.Workbench):
    """
    class which gets initiated at starup of the gui
    """

    MenuText = "Gespal 3D"
    ToolTip = "Fabrication de palettes"
    Icon = os.path.join(ICONPATH, "template_resource.svg")
    toolbox_gespal3d = [
        "EnveloppeCreator",
        "BeamCreator",
        "PanelCreator",
        "ListCreator",
        # "Plan",
        # "Rendu"
        ]
    toolbox_mod = [
        "Draft_Move",
        "Draft_Rotate",
        "Arch_CutPlane"
        ]
    toolbox_create = [
        "Draft_Line",
        "Draft_Circle",
        "Draft_Rectangle",
        "Draft_Dimension",
        ]

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        """
        This function is called at the first activation of the workbench.
        here is the place to import all the commands
        """
        App.Console.PrintMessage("Initialisation de l'atelier Gespal3D \n")

        p = App.ParamGet(str(PARAMPATH))
        c = App.ParamGet("User parameter:BaseApp/Preferences/Document")
        c.SetBool('DuplicateLabels', True)

        self.appendToolbar("Gespal3D", self.toolbox_gespal3d)
        self.appendMenu("Gespal3D", self.toolbox_gespal3d)

        self.appendToolbar("Modification", self.toolbox_mod)
        self.appendMenu("Modification", self.toolbox_mod)

        self.appendToolbar(u"Creation", self.toolbox_create)
        self.appendMenu(u"Creation", self.toolbox_create)

    def Activated(self):
        '''
        code which should be computed when a user switch to this workbench
        '''
        App.Console.PrintMessage("Bienvenue sur l'atelier Gespal 3D \n")

        if hasattr(Gui, "draftToolBar"):
            Gui.draftToolBar.Activated()
        if hasattr(Gui, "Snapper"):
            Gui.Snapper.show()

    def Deactivated(self):
        '''
        code which should be computed when this workbench is deactivated
        '''
        pass


Gui.addWorkbench(gespal3d_workbench())
