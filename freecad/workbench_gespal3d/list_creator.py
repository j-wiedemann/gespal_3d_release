import FreeCAD
if FreeCAD.GuiUp:
    import FreeCADGui
    import Arch, Draft, Part
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from FreeCAD import Base, Console, Vector, Rotation
    import math, DraftGeomUtils, DraftVecUtils
    import os
    from datetime import datetime
    from freecad.workbench_gespal3d import PARAMPATH
    from freecad.workbench_gespal3d import DEBUG
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
            pc_pdf = 'PC_' + id + '.pdf'
            pf_pdf = 'PF_' + id + '.pdf'
            path_image = os.path.join(path_project[0], name_image)
            path_csv = os.path.join(path_project[0], name_csv)
            path_pc = os.path.join(path_project[0], pc_pdf)
            path_pf = os.path.join(path_project[0], pf_pdf)
            self.p = FreeCAD.ParamGet(str(PARAMPATH))
            path_template = self.p.GetString('PathTemplate', '')

            # makeListing()
            objs = doc.Objects
            objlist = []
            objother = []
            self.objproduct = None
            self.grp_dimension = []
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
                    self.objproduct = obj
                elif "Dimension" in obj.Name:
                    self.grp_dimension.append(obj)
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

            # Image
            self.makeImage(path_image)

            # Plan
            if doc.getObject("Page"):
                doc.getObject("Page").recompute(True)
            else:
                paths = [path_pc, path_pf]
                self.makePlan(objlist, paths)
        else:
            FreeCAD.Console.PrintWarning(
                "Sauvegardez d'abord votre document.")

        return

    def makeImage(self, path):
        self.objproduct.ViewObject.Visibility = False
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = False
        if hasattr(FreeCADGui,"Snapper"):
            FreeCADGui.Snapper.setTrackers()
            if FreeCADGui.Snapper.grid:
                if FreeCADGui.Snapper.grid.Visible:
                    FreeCADGui.Snapper.grid.off()
                    FreeCADGui.Snapper.forceGridOff=True
        FreeCADGui.activeDocument().activeView().setCameraType("Perspective")
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        FreeCADGui.activeDocument().activeView().saveImage(
            path,
            2560,
            1600,
            'White')
        self.objproduct.ViewObject.Visibility = True
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = True
        FreeCADGui.activeDocument().activeView().setCameraType("Orthographic")

    def makePlan(self, objlist, paths):
        doc = FreeCAD.activeDocument()
        # Page
        page = doc.addObject('TechDraw::DrawPage','Page')
        # Template
        path = FreeCAD.ParamGet(str(PARAMPATH)).GetString('PathTemplate', '')
        template = doc.addObject('TechDraw::DrawSVGTemplate','Template')
        template.Template = path
        page.Template = template
        r = template.Width.Value / self.objproduct.Length.Value
        r = r / 2.5
        scale = round(r, 2)
        template.setEditFieldContent("NOM", doc.Comment)
        template.setEditFieldContent("FC-SH", doc.Name)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        template.setEditFieldContent("FC-DATE", dt_string)
        template.setEditFieldContent("FC-SC", str(scale))
        # ProjGroup
        projgroup = doc.addObject('TechDraw::DrawProjGroup','ProjGroup')
        page.addView(projgroup)
        projgroup.Source = objlist
        projgroup.ScaleType = u"Custom"
        projgroup.Scale = scale
        projgroup.addProjection('Front')
        projgroup.Anchor.Direction = FreeCAD.Vector(0.000,0.000,1.000)
        projgroup.Anchor.RotationVector = FreeCAD.Vector(1.000,0.000,0.000)
        projgroup.Anchor.XDirection = FreeCAD.Vector(1.000,0.000,0.000)
        projgroup.Anchor.recompute()
        projgroup.addProjection('Bottom')
        projgroup.addProjection('Left')
        x = (self.objproduct.Length.Value * projgroup.Scale) / 2 + 20.0
        y = (self.objproduct.Width.Value * projgroup.Scale) / 2 + 40.0
        projgroup.X = x
        projgroup.Y = y
        # Iso View
        iso_view = doc.addObject('TechDraw::DrawViewPart','View')
        page.addView(iso_view)
        iso_view.Source = objlist
        iso_view.Direction = FreeCAD.Vector(0.577,-0.577,0.577)
        iso_view.XDirection = FreeCAD.Vector(0.707,0.707,-0.000)
        iso_view.Scale = scale / 2
        iso_view.X = 240.0
        iso_view.Y = 170.0
        iso_view.recompute()
        # Recompute
        page.recompute(True)
        page.ViewObject.show()
        # Export
        __objs__=[]
        __objs__.append(page)
        #FreeCADGui.export(__objs__, paths[0])
        #FreeCADGui.export(__objs__, paths[1])
        del __objs__
        return

if FreeCAD.GuiUp:
    FreeCADGui.addCommand('ListCreator', _ListCreator())
