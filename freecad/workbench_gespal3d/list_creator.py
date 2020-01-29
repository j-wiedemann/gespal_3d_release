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
                'ToolTip' : "<html><head/><body><p><b>Exporte le projet dans Gespal</b> \
                (liste, image et plan). \
                <br><br> \
                Pour que <b>l'outil soit disponible</b> vous devez: \
                <ul><li>enregistrer votre document</li> \
                <li>avoir un objet Produit dans le document</li> \
                <li>être sur la vue 3D</li> \
                </p></body></html>"}


    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = False
        if FreeCAD.ActiveDocument:
            doc = FreeCAD.ActiveDocument
            if len(doc.FileName) > 0:
                if hasattr(FreeCADGui.activeDocument().activeView(), 'zoomIn'):
                    for obj in doc.Objects:
                        if obj.Name == "Product":
                            active = True
        return active


    def Activated(self):
        doc = FreeCAD.ActiveDocument
        path_doc = doc.FileName
        if len(path_doc) > 0:
            id = doc.Name.split("_")[1]
            path_project = os.path.split(path_doc)
            name_image = '3D_' + id + '.png'
            name_csv = 'CP_' + id + '.csv'
            plan_pdf = 'PF_' + id + '.pdf'
            path_image = os.path.join(path_project[0], name_image)
            path_csv = os.path.join(path_project[0], name_csv)
            path_plan = os.path.join(path_project[0], plan_pdf)

            # makeListing()
            objs = doc.Objects
            objlist = []
            objother = []
            objproduct = None
            mySheet = False
            for obj in objs:
                if hasattr(obj, "Tag"):
                    if obj.Tag == "Gespal":
                        if hasattr(obj, "Description"):
                            if obj.Description is not None:
                                objlist.append(obj)
                elif obj.Name == 'Gespal3DListe':
                    mySheet = obj
                    obj.clearAll()
                    FreeCAD.ActiveDocument.recompute()
                elif obj.Name == 'Product':
                    objproduct = obj
                else:
                    objother.append(obj)
            if len(objlist) < 0:
                FreeCAD.Console.PrintWarning("La liste des composants Gespal est vide.")
            if not mySheet:
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
            objproduct.ViewObject.Visibility = False
            for obj in objother:
                obj.ViewObject.Visibility = False
            FreeCADGui.activeDocument().activeView().viewIsometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")
            FreeCADGui.activeDocument().activeView().saveImage(
                path_image,
                2560,
                1600,
                'White')
            objproduct.ViewObject.Visibility = True
            for obj in objother:
                obj.ViewObject.Visibility = True

            # makePlan()
            if doc.getObject("Page"):
                doc.removeObject('Page')
                #doc.recompute()
            page = doc.addObject('TechDraw::DrawPage','Page')
            template = doc.addObject('TechDraw::DrawSVGTemplate','Template')
            template.Template = "/home/jo/Documents/FreeCAD/FreeCADFrance/Clients/Pascal BERTRAND/Dev/A4_Landscape_JanesTimber.svg"
            page.Template = template
            projgroup = doc.addObject('TechDraw::DrawProjGroup','ProjGroup')
            page.addView(projgroup)
            projgroup.Source = objlist
            #projgroup.ScaleType = u"Automatic"
            projgroup.ScaleType = u"Custom"
            projgroup.Scale = 0.10
            projgroup.addProjection('Front')
            projgroup.Anchor.Direction = FreeCAD.Vector(0.000,0.000,1.000)
            projgroup.Anchor.RotationVector = FreeCAD.Vector(1.000,0.000,0.000)
            projgroup.Anchor.XDirection = FreeCAD.Vector(1.000,0.000,0.000)
            projgroup.Anchor.recompute()
            projgroup.addProjection('Bottom')
            projgroup.addProjection('Left')
            x = (objproduct.Length.Value * projgroup.Scale) / 2 + 20.0
            y = (objproduct.Width.Value * projgroup.Scale) / 2 + 40.0
            projgroup.X = x
            projgroup.Y = y

            iso_view = doc.addObject('TechDraw::DrawViewPart','View')
            page.addView(iso_view)
            iso_view.Source = objlist
            iso_view.Direction = FreeCAD.Vector(0.577,-0.577,0.577)
            iso_view.XDirection = FreeCAD.Vector(0.707,0.707,-0.000)
            iso_view.Scale = 0.05
            iso_view.X = 240.0
            iso_view.Y = 170.0
            iso_view.recompute()

            template.setEditFieldContent("NOM", doc.Comment)
            template.setEditFieldContent("FC-SH", doc.Name)
            template.setEditFieldContent("FC-DATE", "01/01/2020")
            template.setEditFieldContent("FC-SC", "1/10")


            page.recompute(True)
        else:
            FreeCAD.Console.PrintWarning(
                "Sauvegardez d'abord votre document.")

        # makePlan()

        return


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('ListCreator', _ListCreator())
