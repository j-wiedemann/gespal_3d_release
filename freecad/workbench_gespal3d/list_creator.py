import FreeCAD
if FreeCAD.GuiUp:
    import FreeCADGui
    import Arch, Draft, Part
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from FreeCAD import Base, Console, Vector, Rotation
    import math, DraftGeomUtils, DraftVecUtils
    import os

else:
    def translate(ctxt,txt):
        return txt

# waiting for Gespal3D_rc and eventual FreeCAD integration
__dir__ = os.path.dirname(__file__)

__title__="Gespal 3D List"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class _ListCreator():
    """Gespal3DList"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH
        return {'Pixmap'  :  os.path.join(ICONPATH, "Gespal3D_Listing.svg"),
                'Accel' : "E,L",
                'MenuText': "Gespal 3D Export",
                'ToolTip' : "Exporte le projet dans Gespal (liste, image et plan)"}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        path_doc = doc.FileName
        if len(path_doc) > 0:
            path_project = os.path.split(path_doc)
            name_image = doc.Name + '.png'
            name_csv = doc.Name + '.csv'
            path_image = os.path.join(path_project[0], name_image)
            path_csv = os.path.join(path_project[0], name_csv)


            # makeListing()
            objs = doc.Objects
            objlist = []
            for obj in objs:
                if hasattr(obj, "Tag"):
                    if obj.Tag == "Gespal":
                        if hasattr(obj, "Description"):
                            if obj.Description is not None:
                                objlist.append(obj)
            if len(objlist) < 0:
                FreeCAD.Console.PrintWarning("La liste des composants Gespal est vide.")
            mySheet = FreeCAD.ActiveDocument.addObject('Spreadsheet::Sheet','Gespal3DListe')
            FreeCAD.ActiveDocument.recompute()
            mySheet.set('A1','ID')
            mySheet.set('B1','Largeur')
            mySheet.set('C1','Hauteur')
            mySheet.set('D1','Longueur')
            mySheet.set('E1','Usinage')
            n=1
            for obj in objlist:
                desc = "'" + str(obj.Description)
                mySheet.set('A'+str(n+1), str(desc))
                mySheet.set('B'+str(n+1), str(obj.Width))
                mySheet.set('C'+str(n+1), str(obj.Height))
                mySheet.set('D'+str(n+1), str(obj.Length))
                n += 1
            FreeCAD.ActiveDocument.recompute()
            mySheet.exportFile(path_csv)

            # makeImage()
            FreeCADGui.activeDocument().activeView().viewIsometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")
            FreeCADGui.activeDocument().activeView().saveImage(
                path_image,
                2560,
                1600,
                'White')
        else:
            FreeCAD.Console.PrintWarning(
                "Sauvegardez d'abord votre document.")

        # makePlan()

        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = False
        if FreeCAD.ActiveDocument:
            for obj in FreeCAD.ActiveDocument.Objects:
                if obj.Name == "Product":
                    active = True

        return active

if FreeCAD.GuiUp:
    FreeCADGui.addCommand('ListCreator', _ListCreator())
