import FreeCAD
if FreeCAD.GuiUp:
    import FreeCADGui
    import Arch, Draft, Part
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from FreeCAD import Base, Console, Vector, Rotation
    import TechDraw, TechDrawGui
    import math, DraftGeomUtils, DraftVecUtils
    import os
    from datetime import datetime
    from freecad.workbench_gespal3d import __version__ as wb_version
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


class gespal3d_exports():

    def __init__(self):
        doc = FreeCAD.ActiveDocument
        path_doc = doc.FileName
        if len(path_doc) > 0:
            id = doc.Name.split("_")[1]
            path_project = os.path.split(path_doc)
            name_image = '3D_' + id + '.png'
            name_csv = 'CP_' + id + '.csv'
            pc_pdf = 'PC_' + id + '.pdf'
            pf_pdf = 'PF_' + id + '.pdf'
            self.path_image = os.path.join(path_project[0], name_image)
            self.path_csv = os.path.join(path_project[0], name_csv)
            self.path_pc = os.path.join(path_project[0], pc_pdf)
            self.path_pf = os.path.join(path_project[0], pf_pdf)
            self.p = FreeCAD.ParamGet(str(PARAMPATH))
            self.path_template = self.p.GetString('PathTemplate', '')

            objs = doc.Objects
            self.objlist = []
            objother = []
            self.objproduct = None
            self.grp_dimension = []
            self.mySheet = None
            for obj in objs:
                if hasattr(obj, "Tag"):
                    if obj.Tag == "Gespal":
                        if hasattr(obj, "Description"):
                            if obj.Description is not None:
                                self.objlist.append(obj)
                elif obj.Name == 'Gespal3DListe':
                    self.mySheet = obj
                elif obj.Name == 'Product':
                    self.objproduct = obj
                elif "Dimension" in obj.Name:
                    self.grp_dimension.append(obj)
                else:
                    objother.append(obj)
            if len(self.objlist) < 0:
                FreeCAD.Console.PrintWarning("La liste des composants Gespal est vide.")

        else:
            FreeCAD.Console.PrintWarning(
                "Sauvegardez d'abord votre document.")

    def getArea(self, face):
        return face.Area

    def getFacesMax(self, faces):
        faces = sorted(faces,key=self.getArea, reverse = True)
        facesMax = faces[0:4]
        return facesMax

    def getCoupleFacesEquerre(self, faces):
        listeCouple = []
        lenfaces = len(faces)
        faces.append(faces[0])
        for n in range(lenfaces):
            norm2 = faces[n+1].normalAt(0,0)
            norm1 = faces[n].normalAt(0,0)
            norm0 = faces[n-1].normalAt(0,0)
            if abs(round(math.degrees(DraftVecUtils.angle(norm1,norm0)))) == 90.:
                listeCouple.append([faces[n],faces[n-1]])
            if abs(round(math.degrees(DraftVecUtils.angle(norm1,norm2)))) == 90.:
                listeCouple.append([faces[n],faces[n+1]])
        return listeCouple

    def shapeAnalyse(self, shape):
        ## Create a new object with the shape of the current arch object
        ## His placment is set to 0,0,0
        obj = FreeCAD.ActiveDocument.addObject('Part::Feature','shapeAnalyse')
        obj.Shape=shape
        obj.Placement.Base = FreeCAD.Vector(0.0,0.0,0.0)
        obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0.0,0.0,1.0),0.0)
        FreeCAD.ActiveDocument.recompute()
        ## Get the face to align with XY plane
        faces = obj.Shape.Faces
        facesMax = self.getFacesMax(faces)
        coupleEquerre = self.getCoupleFacesEquerre(facesMax)
        ## Get the normal of this face
        nv1 = coupleEquerre[0][0].normalAt(0,0)
        ## Get the goal normal vector
        zv = Vector(0,0,1)
        ## Find and apply a rotation to the object to align face
        pla = obj.Placement
        rot = pla.Rotation
        rot1 = Rotation(nv1, zv)
        newrot = rot.multiply(rot1)
        pla.Rotation = newrot
        ## Get the face to align with XY plane
        faces = obj.Shape.Faces
        facesMax = self.getFacesMax(faces)
        coupleEquerre = self.getCoupleFacesEquerre(facesMax)
        ## Get the longest edge from aligned face
        maxLength = 0.
        for e in coupleEquerre[0][0].Edges:
            if e.Length > maxLength:
                maxLength = e.Length
                edgeMax = e
        ## Get the angle between edge and X axis and rotate object
        vec = DraftGeomUtils.vec(edgeMax)
        vecZ = FreeCAD.Vector(vec[0],vec[1],0.0)
        pos2 = obj.Placement.Base
        rotZ = math.degrees(DraftVecUtils.angle(vecZ,FreeCAD.Vector(1.0,0.0,0.0),zv))
        Draft.rotate([obj],rotZ,pos2,axis=zv,copy=False)
        bb = obj.Shape.BoundBox
        movex = bb.XMin*-1
        movey = bb.YMin*-1
        movez = bb.ZMin*-1
        Draft.move([obj], FreeCAD.Vector(movex, movey, movez))
        FreeCAD.ActiveDocument.recompute()
        ## Get the boundbox
        analyse = [obj.Shape.BoundBox.YLength, obj.Shape.BoundBox.ZLength, obj.Shape.BoundBox.XLength]
        #if not "Shape" in self.export :
        FreeCAD.ActiveDocument.removeObject(obj.Name)
        return analyse

    def makeSpreadsheet(self):
        if self.mySheet:
            self.mySheet.clearAll()
            FreeCAD.ActiveDocument.recompute()
        else:
            FreeCAD.ActiveDocument.addObject('Spreadsheet::Sheet','Gespal3DListe')
            self.mySheet = FreeCAD.ActiveDocument.getObject('Gespal3DListe')
            FreeCAD.ActiveDocument.recompute()
        mySheet = self.mySheet
        mySheet.set('A1', 'ID')
        mySheet.set('B1', 'Largeur')
        mySheet.set('C1', 'Hauteur')
        mySheet.set('D1', 'Longueur')
        mySheet.set('E1', 'Usinage')
        n=1
        for obj in self.objlist:
            shape = obj.Shape
            analyse = self.shapeAnalyse(shape)
            if hasattr(obj, 'Height'):
                height = obj.Height
            elif hasattr(obj, 'Thickness'):
                height = obj.Thickness
            else:
                height = 0.0
            if len(obj.Subtractions) > 0:
                usinage = 'C'
            else:
                usinage = None
            desc = "'" + str(obj.Description)
            mySheet.set('A'+str(n+1), str(desc))
            mySheet.set('B'+str(n+1), str(obj.Width))
            mySheet.set('C'+str(n+1), str(height))
            #mySheet.set('D'+str(n+1), str(obj.Length))
            mySheet.set('D'+str(n+1), str(analyse[2]))
            if usinage is not None:
                mySheet.set('E'+str(n+1), str(usinage))
            n += 1
        FreeCAD.ActiveDocument.recompute()
        mySheet.exportFile(self.path_csv)
        return

    def makeImage(self):
        av = FreeCADGui.activeDocument().activeView()
        av.setAxisCross(False)
        self.objproduct.ViewObject.Visibility = False
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = False
        if hasattr(FreeCADGui,"Snapper"):
            FreeCADGui.Snapper.setTrackers()
            if FreeCADGui.Snapper.grid:
                if FreeCADGui.Snapper.grid.Visible:
                    FreeCADGui.Snapper.grid.off()
                    FreeCADGui.Snapper.forceGridOff=True
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        av.setCameraType("Orthographic")
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        #av.setCameraType("Perspective")
        av.saveImage(
            self.path_image,
            2560,
            1600,
            'White')
        self.objproduct.ViewObject.Visibility = True
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = True
        av.setCameraType("Orthographic")
        # FreeCADGui.ActiveDocument.ActiveView.setAxisCross(True)
        return

    def makePlan(self, name):
        doc = FreeCAD.activeDocument()
        projgrp_name = 'ProjGroup' + str(name)
        isoview_name = 'View' + str(name)
        # check if page exist
        page = doc.getObject(name)
        if doc.getObject(name):
            if doc.getObject(projgrp_name):
                doc.getObject(projgrp_name).Source = self.objlist
            if doc.getObject(isoview_name):
                doc.getObject(isoview_name).Source = self.objlist
            return

        # Page
        page = doc.addObject('TechDraw::DrawPage',name)
        # Template
        path = FreeCAD.ParamGet(str(PARAMPATH)).GetString('PathTemplate', '')
        template = doc.addObject('TechDraw::DrawSVGTemplate','Template')
        template.Template = path
        page.Template = template
        r = template.Width.Value / self.objproduct.Length.Value
        max_length = max(
            self.objproduct.Length.Value,
            self.objproduct.Width.Value,
            self.objproduct.Height.Value,
            )
        r = template.Height.Value / max_length
        r = r / 3
        scale = round(r, 2)
        template.setEditFieldContent("NOM", doc.Comment)
        template.setEditFieldContent("FC-SH", doc.Name)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        template.setEditFieldContent("FC-DATE", dt_string)
        # template.setEditFieldContent("FC-SC", str(scale))
        # ProjGroup
        projgroup = doc.addObject('TechDraw::DrawProjGroup', projgrp_name)
        page.addView(projgroup)
        projgroup.Source = self.objlist
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
        projgroup.AutoDistribute = False
        # Iso View
        iso_view = doc.addObject('TechDraw::DrawViewPart', isoview_name)
        page.addView(iso_view)
        iso_view.Source = self.objlist
        iso_view.Direction = FreeCAD.Vector(0.577,-0.577,0.577)
        iso_view.XDirection = FreeCAD.Vector(0.707,0.707,-0.000)
        iso_view.Scale = scale / 2
        iso_view.X = 240.0
        iso_view.Y = 170.0
        iso_view.recompute()
        # Recompute
        page.recompute(True)
        page.ViewObject.show()
        return

    def exportPlanCommercial(self):
        doc = FreeCAD.ActiveDocument
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        page = doc.getObject('plan_commercial')
        TechDrawGui.exportPageAsPdf(page, self.path_pc)
        return

    def exportPlanFabrication(self):
        doc = FreeCAD.ActiveDocument
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        page = doc.getObject('plan_fabrication')
        TechDrawGui.exportPageAsPdf(page, self.path_pf)
        return


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
        # Spreadsheet
        gespal3d_exports().makeSpreadsheet()

        # Image
        gespal3d_exports().makeImage()

        # Plan
        gespal3d_exports().makePlan(name='plan_commercial')
        gespal3d_exports().makePlan(name='plan_fabrication')

        return


class _PlanCommercial():
    """Export plan commercial"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH
        return {'Pixmap'  :  os.path.join(ICONPATH, "document-print.svg"),
                'Accel' : "P,C",
                'MenuText': "Gespal 3D Export",
                'ToolTip' : "<html><head/><body><p><b>Exporte le plan commercial.</b> \
                </p></body></html>"}

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active


    def Activated(self):
        gespal3d_exports().exportPlanCommercial()
        return


class _PlanFabrication():
    """Export plan de fabrication"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH
        return {'Pixmap'  :  os.path.join(ICONPATH, "document-print.svg"),
                'Accel' : "P,F",
                'MenuText': "Gespal 3D Export",
                'ToolTip' : "<html><head/><body><p><b>Exporte le plan de fabrication</b> \
                </p></body></html>"}

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        gespal3d_exports().exportPlanFabrication()
        return


class _ShowHelp():
    """Export plan de fabrication"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH
        return {'Pixmap'  :  os.path.join(ICONPATH, "help-browser.svg"),
                'Accel' : "H,F",
                'MenuText': "Gespal 3D Aide",
                'ToolTip' : "<html><head/><body><p><b>Affiche la version de Gespal 3D</b> \
                </p></body></html>"}

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        msg = "<html><head/><body><p><b>Gespal 3D</b> \
        </p><p>Version : %s</p></body></html>" % (str(wb_version))
        reply = QtGui.QMessageBox.information(None,"",msg)
        return


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('ListCreator', _ListCreator())
    FreeCADGui.addCommand('PlanCommercial', _PlanCommercial())
    FreeCADGui.addCommand('PlanFabrication', _PlanFabrication())
    FreeCADGui.addCommand('Help', _ShowHelp())
