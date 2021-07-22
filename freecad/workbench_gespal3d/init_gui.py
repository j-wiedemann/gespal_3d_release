# coding: utf-8

import os
import FreeCADGui as Gui
import FreeCAD as App
from freecad.workbench_gespal3d import ICONPATH
from freecad.workbench_gespal3d import PARAMPATH
from freecad.workbench_gespal3d import g3d_connect_db
from freecad.workbench_gespal3d import g3d_product
from freecad.workbench_gespal3d import g3d_beam
from freecad.workbench_gespal3d import g3d_panel
from freecad.workbench_gespal3d import g3d_accessory
from freecad.workbench_gespal3d import g3d_machining
from freecad.workbench_gespal3d import g3d_listing
from freecad.workbench_gespal3d import g3d_mirror_copy
from freecad.workbench_gespal3d import g3d_delete
from freecad.workbench_gespal3d import g3d_component_manager
from freecad.workbench_gespal3d import g3d_help
from freecad.workbench_gespal3d import __version__ as wb_version

__title__ = "Gespal 3D InitGui"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class gespal3d_workbench(Gui.Workbench):
    """
    class which gets initiated at startup of the gui
    """

    MenuText = "Gespal 3D"
    ToolTip = "Fabrication de palettes"
    Icon = os.path.join(ICONPATH, "gespal3d_wb.svg")
    toolbox_gespal3d = [
        "G3D_Product",
        "G3D_BeamComposant",
        "G3D_PanelComposant",
        "G3D_AccesoryComposant",
        "G3D_Machining",
        "Separator",
        "G3D_Listing",
        "G3D_CommercialDrawing",
        "G3D_FabricationDrawing",
        "Separator",
        "G3D_Help",
        "G3D_ComponentsManager",
    ]
    toolbox_mod = [
        "Draft_Move",
        "Draft_Rotate",
        "G3D_MirrorCopy",
        "Draft_Offset",
        "Draft_Trimex",
        "Arch_CutPlane",
        "Arch_CutLine",
        "Draft_Upgrade",
        "Arch_Remove",
        "G3D_Delete",
    ]
    toolbox_create = [
        "Draft_Line",
        "Draft_ArcTools",
        "Draft_Circle",
        "Draft_Rectangle",
        "Draft_Wire",
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
        c.SetBool("DuplicateLabels", True)
        d = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
        d.SetBool("grid", False)


        self.appendToolbar(u"G3D Ajouter", self.toolbox_gespal3d)
        self.appendMenu(u"G3D Ajouter", self.toolbox_gespal3d)

        self.appendToolbar(u"G3D Modifier", self.toolbox_mod)
        self.appendMenu(u"G3D Modifier", self.toolbox_mod)

        self.appendToolbar(u"G3D Dessiner", self.toolbox_create)
        self.appendMenu(u"G3D Dessiner", self.toolbox_create)

    def Activated(self):
        """
        code which should be computed when a user switch to this workbench
        """

        App.Console.PrintMessage("Bienvenue sur l'atelier Gespal 3D \n")
        msg = "Version : " + str(wb_version) + "\n"
        App.Console.PrintMessage(msg)

        g3d_connect_db.sql_connection()

        if hasattr(Gui, "draftToolBar"):
            Gui.draftToolBar.Activated()

    def Deactivated(self):
        """
        code which should be computed when this workbench is deactivated
        """
        pass


Gui.addWorkbench(gespal3d_workbench())
