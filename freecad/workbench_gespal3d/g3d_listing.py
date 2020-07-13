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

    def translate(ctxt, txt):
        return txt


# waiting for Gespal3D_rc and eventual FreeCAD integration
__dir__ = os.path.dirname(__file__)

__title__ = "Gespal 3D List"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class gespal3d_exports:
    def __init__(self):
        doc = FreeCAD.ActiveDocument
        path_doc = doc.FileName
        if len(path_doc) > 0:
            id = doc.Name.split("_")[1]
            path_project = os.path.split(path_doc)
            name_image = "3D_" + id + ".png"
            name_csv = "CP_" + id + ".csv"
            pc_pdf = "PC_" + id + ".pdf"
            pf_pdf = "PF_" + id + ".pdf"
            self.path_image = os.path.join(path_project[0], name_image)
            self.path_csv = os.path.join(path_project[0], name_csv)
            self.path_pc = os.path.join(path_project[0], pc_pdf)
            self.path_pf = os.path.join(path_project[0], pf_pdf)
            self.p = FreeCAD.ParamGet(str(PARAMPATH))
            self.path_template = self.p.GetString("PathTemplate", "")

            objs = doc.Objects
            self.objlist = []
            self.projgroup_list = []
            objother = []
            self.objproduct = None
            self.boundbox = None
            self.grp_dimension = []
            self.mySheet = None
            if DEBUG:
                msg = "There is %s object in document.\n" % len(objs)
                FreeCAD.Console.PrintMessage(msg)
            for obj in objs:
                if DEBUG:
                    msg = "Current object is %s \n" % obj.Name
                    FreeCAD.Console.PrintMessage(msg)
                if hasattr(obj, "Tag"):
                    if obj.Tag == "Gespal":
                        if hasattr(obj, "Description"):
                            if obj.Description is not None:
                                self.objlist.append(obj)
                                self.projgroup_list.append(obj)
                                if DEBUG:
                                    msg = "%s is added to the objlist.\n" % obj.Name
                                    FreeCAD.Console.PrintMessage(msg)
                elif obj.TypeId == "Part::Mirroring":
                    src = self.getSource(obj)
                    if src.Tag == "Gespal":
                        if hasattr(src, "Description"):
                            if src.Description is not None:
                                self.objlist.append(src)
                                if DEBUG:
                                    msg = "%s is added to the objlist.\n" % src.Name
                                    FreeCAD.Console.PrintMessage(msg)
                    self.projgroup_list.append(obj)
                elif obj.Name == "Gespal3DListe":
                    self.mySheet = obj
                elif obj.Name == "Product":
                    self.objproduct = obj
                    # For project created before v0.5.0
                    if obj.TypeId == "Part::Box":
                        self.boundbox = obj
                elif obj.Name == "Box":
                    self.boundbox = obj
                elif "Dimension" in obj.Name:
                    self.grp_dimension.append(obj)
                else:
                    objother.append(obj)
            if len(self.objlist) < 0:
                FreeCAD.Console.PrintMessage(
                    "La liste des composants Gespal est vide.\n"
                )
            else:
                if DEBUG:
                    msg = "There is %s object objlist.\n" % len(self.objlist)
                    FreeCAD.Console.PrintMessage(msg)
                    msg = [obj.Name for obj in self.objlist]
                    FreeCAD.Console.PrintMessage(msg)

        else:
            FreeCAD.Console.PrintMessage("Sauvegardez d'abord votre document.\n")

    def getSource(self, obj):
        if DEBUG:
            msg = "Looking for source of %s \n" % obj.Name
            FreeCAD.Console.PrintWarning(msg)
        src = obj.Source
        if DEBUG:
            msg = "Current source is %s \n" % src.Name
            FreeCAD.Console.PrintWarning(msg)
        while src.TypeId == "Part::Mirroring":
            if DEBUG:
                msg = "Source is a Part::Mirror object \n"
                FreeCAD.Console.PrintWarning(msg)
            src = src.Source
        if DEBUG:
            msg = "Source is : %s \n" % src.Name
            FreeCAD.Console.PrintWarning(msg)
        return src

    def getArea(self, face):
        return face.Area

    def getFacesMax(self, faces):
        faces = sorted(faces, key=self.getArea, reverse=True)
        facesMax = faces[0:4]
        return facesMax

    def getCoupleFacesEquerre(self, faces):
        listeCouple = []
        lenfaces = len(faces)
        faces.append(faces[0])
        for n in range(lenfaces):
            norm2 = faces[n + 1].normalAt(0, 0)
            norm1 = faces[n].normalAt(0, 0)
            norm0 = faces[n - 1].normalAt(0, 0)
            if abs(round(math.degrees(DraftVecUtils.angle(norm1, norm0)))) == 90.0:
                listeCouple.append([faces[n], faces[n - 1]])
            if abs(round(math.degrees(DraftVecUtils.angle(norm1, norm2)))) == 90.0:
                listeCouple.append([faces[n], faces[n + 1]])
        return listeCouple

    def shapeAnalyse(self, shape):
        ## Create a new object with the shape of the current arch object
        ## His placment is set to 0,0,0
        obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "shapeAnalyse")
        obj.Shape = shape
        obj.Placement.Base = FreeCAD.Vector(0.0, 0.0, 0.0)
        obj.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0.0, 0.0, 1.0), 0.0)
        FreeCAD.ActiveDocument.recompute()
        ## Get the face to align with XY plane
        faces = obj.Shape.Faces
        facesMax = self.getFacesMax(faces)
        coupleEquerre = self.getCoupleFacesEquerre(facesMax)
        ## Get the normal of this face
        nv1 = coupleEquerre[0][0].normalAt(0, 0)
        ## Get the goal normal vector
        zv = Vector(0, 0, 1)
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
        maxLength = 0.0
        for e in coupleEquerre[0][0].Edges:
            if e.Length > maxLength:
                maxLength = e.Length
                edgeMax = e
        ## Get the angle between edge and X axis and rotate object
        vec = DraftGeomUtils.vec(edgeMax)
        vecZ = FreeCAD.Vector(vec[0], vec[1], 0.0)
        pos2 = obj.Placement.Base
        rotZ = math.degrees(
            DraftVecUtils.angle(vecZ, FreeCAD.Vector(1.0, 0.0, 0.0), zv)
        )
        Draft.rotate([obj], rotZ, pos2, axis=zv, copy=False)
        bb = obj.Shape.BoundBox
        movex = bb.XMin * -1
        movey = bb.YMin * -1
        movez = bb.ZMin * -1
        Draft.move([obj], FreeCAD.Vector(movex, movey, movez))
        FreeCAD.ActiveDocument.recompute()
        ## Get the boundbox
        analyse = [
            obj.Shape.BoundBox.YLength,
            obj.Shape.BoundBox.ZLength,
            obj.Shape.BoundBox.XLength,
        ]
        # if not "Shape" in self.export :
        FreeCAD.ActiveDocument.removeObject(obj.Name)
        return analyse

    def makeSpreadsheet(self):
        if DEBUG:
            msg = "Start making Spreadsheet...\n"
            FreeCAD.Console.PrintMessage(msg)
        if self.mySheet:
            self.mySheet.clearAll()
            FreeCAD.ActiveDocument.recompute()
        else:
            FreeCAD.ActiveDocument.addObject("Spreadsheet::Sheet", "Gespal3DListe")
            self.mySheet = FreeCAD.ActiveDocument.getObject("Gespal3DListe")
            FreeCAD.ActiveDocument.recompute()
        mySheet = self.mySheet
        mySheet.set("A1", "ID")
        mySheet.set("B1", "Largeur")
        mySheet.set("C1", "Hauteur")
        mySheet.set("D1", "Longueur")
        mySheet.set("E1", "Usinage")
        n = 1
        for obj in self.objlist:
            shape = obj.Shape
            analyse = self.shapeAnalyse(shape)
            if DEBUG:
                msg = "row %s : object %s.\n" % (n, obj.Name)
                FreeCAD.Console.PrintMessage(msg)
                msg = analyse
                FreeCAD.Console.PrintMessage(msg)
                FreeCAD.Console.PrintMessage("\n")
            if hasattr(obj, "Height"):
                width = obj.Width
                height = obj.Height
                length = str(analyse[2]) + " mm"
            elif hasattr(obj, "Thickness"):
                width = obj.Thickness
                m = 0
                for dim in analyse:
                    if dim == width:
                        analyse.pop(m)
                    m += 1
                height = str(min(analyse)) + " mm"
                length = str(max(analyse)) + " mm"
            else:
                width = str(analyse[0]) + " mm"
                height = str(analyse[1]) + " mm"
                length = str(analyse[2]) + " mm"
            if len(obj.Subtractions) > 0:
                usinage = "C"
            else:
                usinage = None
            desc = "'" + str(obj.Description)
            mySheet.set("A" + str(n + 1), str(desc))
            mySheet.set("B" + str(n + 1), str(width))
            mySheet.set("C" + str(n + 1), str(height))
            # mySheet.set('D'+str(n+1), str(obj.Length))
            mySheet.set("D" + str(n + 1), str(length))
            if usinage is not None:
                mySheet.set("E" + str(n + 1), str(usinage))
            n += 1
        FreeCAD.ActiveDocument.recompute()
        mySheet.exportFile(self.path_csv)
        if DEBUG:
            msg = "End making Spreadsheet...\n"
            FreeCAD.Console.PrintMessage(msg)
        return

    def makeImage(self):
        av = FreeCADGui.activeDocument().activeView()
        av.setAxisCross(False)
        self.objproduct.ViewObject.Visibility = False
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = False
        if hasattr(FreeCADGui, "Snapper"):
            FreeCADGui.Snapper.setTrackers()
            if FreeCADGui.Snapper.grid:
                if FreeCADGui.Snapper.grid.Visible:
                    FreeCADGui.Snapper.grid.off()
                    FreeCADGui.Snapper.forceGridOff = True
        FreeCADGui.activeDocument().activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        av.setCameraType("Orthographic")
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        # av.setCameraType("Perspective")
        av.saveImage(self.path_image, 2560, 1600, "White")
        self.objproduct.ViewObject.Visibility = True
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = True
        av.setCameraType("Orthographic")
        # FreeCADGui.ActiveDocument.ActiveView.setAxisCross(True)
        return

    def makePlan(self, name):
        doc = FreeCAD.activeDocument()
        projgrp_name = "ProjGroup" + str(name)
        isoview_name = "View" + str(name)
        # check if page exist
        page = doc.getObject(name)
        if doc.getObject(name):
            if doc.getObject(projgrp_name):
                doc.getObject(projgrp_name).Source = self.projgroup_list
            if doc.getObject(isoview_name):
                doc.getObject(isoview_name).Source = self.projgroup_list
            return

        # Page
        page = doc.addObject("TechDraw::DrawPage", name)
        # Template
        template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")

        # Portrait or Landscape
        max_length = max(
            self.boundbox.Length.Value,
            self.boundbox.Width.Value,
            self.boundbox.Height.Value,
        )
        if max_length == self.boundbox.Height.Value:
            orientation = "A4P"
        else:
            orientation = "A4L"
        # Templae path
        path = FreeCAD.ParamGet(str(PARAMPATH)).GetString("PathTemplate", "")
        if orientation == "A4P":
            path = os.path.join(path, "A4P.svg")
        else:
            path = os.path.join(path, "A4L.svg")
        template.Template = path
        page.Template = template

        r = template.Width.Value / self.boundbox.Length.Value
        r = template.Height.Value / max_length
        r = r / 3
        scale = round(r, 2)
        template.setEditFieldContent("NOM", doc.Comment)
        template.setEditFieldContent("FC-SH", doc.Name)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        template.setEditFieldContent("FC-DATE", dt_string)
        template.setEditFieldContent("FC-SC", str(scale))
        # ProjGroup
        projgroup = doc.addObject("TechDraw::DrawProjGroup", projgrp_name)
        page.addView(projgroup)
        projgroup.Source = self.projgroup_list
        projgroup.ScaleType = u"Custom"
        projgroup.Scale = scale
        projgroup.addProjection("Front")
        if orientation == "A4L":
            projgroup.Anchor.Direction = FreeCAD.Vector(0.000, 0.000, 1.000)
            projgroup.Anchor.RotationVector = FreeCAD.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = FreeCAD.Vector(1.000, 0.000, 0.000)
            y = (self.boundbox.Width.Value * projgroup.Scale) / 2 + 40.0
        else:
            projgroup.Anchor.Direction = FreeCAD.Vector(0.000, -1.000, 0.000)
            projgroup.Anchor.RotationVector = FreeCAD.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = FreeCAD.Vector(1.000, 0.000, 0.000)
            y = 297 - 20 - ((self.boundbox.Height.Value * projgroup.Scale) / 2)
        projgroup.Anchor.recompute()
        if orientation == "A4L":
            projgroup.addProjection("Bottom")
            projgroup.addProjection("Left")
        else:
            projgroup.addProjection("Top")
            projgroup.addProjection("Left")
        for view in projgroup.Views:
            view.Perspective = True
            view.Focus = "100 m"
        x = 20 + (self.boundbox.Length.Value * projgroup.Scale) / 2
        projgroup.X = x
        projgroup.Y = y
        projgroup.AutoDistribute = False
        # Iso View
        iso_view = doc.addObject("TechDraw::DrawViewPart", isoview_name)
        page.addView(iso_view)
        iso_view.Source = self.projgroup_list
        iso_view.Direction = FreeCAD.Vector(0.577, -0.577, 0.577)
        iso_view.XDirection = FreeCAD.Vector(0.707, 0.707, -0.000)
        iso_view.Scale = scale / 2
        if orientation == "A4L":
            iso_view.X = 240.0
            iso_view.Y = 170.0
        else:
            iso_view.X = 3 * 210.0 / 4
            iso_view.Y = 100.0

        iso_view.recompute()
        # Recompute
        page.recompute(True)
        page.ViewObject.show()
        return

    def exportPlanCommercial(self):
        doc = FreeCAD.ActiveDocument
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        page = doc.getObject("plan_commercial")
        TechDrawGui.exportPageAsPdf(page, self.path_pc)
        return

    def exportPlanFabrication(self):
        doc = FreeCAD.ActiveDocument
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.clearPreselection()
        page = doc.getObject("plan_fabrication")
        TechDrawGui.exportPageAsPdf(page, self.path_pf)
        return


class _ListCreator:
    """Gespal3DList"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH

        return {
            "Pixmap": os.path.join(ICONPATH, "Gespal3D_Listing.svg"),
            "Accel": "E,L",
            "MenuText": "Gespal 3D Export",
            "ToolTip": "<html><head/><body><p><b>Exporte le projet dans Gespal</b> \
                (liste, image et plan). \
                <br><br> \
                Pour que <b>l'outil soit disponible</b> vous devez: \
                <ul><li>enregistrer votre document</li> \
                <li>avoir un objet Produit dans le document</li> \
                <li>être sur la vue 3D</li> \
                </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = False
        if FreeCAD.ActiveDocument:
            doc = FreeCAD.ActiveDocument
            if len(doc.FileName) > 0:
                if hasattr(FreeCADGui.activeDocument().activeView(), "zoomIn"):
                    for obj in doc.Objects:
                        if obj.Name == "Product":
                            active = True
        return active

    def Activated(self):
        # Spreadsheet
        export = gespal3d_exports()
        export.makeSpreadsheet()

        # Image
        export.makeImage()

        # Plan
        export.makePlan(name="plan_commercial")
        export.makePlan(name="plan_fabrication")

        return


class _PlanCommercial:
    """Export plan commercial"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH

        return {
            "Pixmap": os.path.join(ICONPATH, "document-print.svg"),
            "Accel": "P,C",
            "MenuText": "Gespal 3D Export",
            "ToolTip": "<html><head/><body><p><b>Exporte le plan commercial.</b> \
                </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        gespal3d_exports().exportPlanCommercial()
        return


class _PlanFabrication:
    """Export plan de fabrication"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH

        return {
            "Pixmap": os.path.join(ICONPATH, "document-print.svg"),
            "Accel": "P,F",
            "MenuText": "Gespal 3D Export",
            "ToolTip": "<html><head/><body><p><b>Exporte le plan de fabrication</b> \
                </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        gespal3d_exports().exportPlanFabrication()
        return


class _ShowHelp:
    """Export plan de fabrication"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH

        return {
            "Pixmap": os.path.join(ICONPATH, "help-browser.svg"),
            "Accel": "H,F",
            "MenuText": "Gespal 3D Aide",
            "ToolTip": "<html><head/><body><p><b>Affiche la version de Gespal 3D</b> \
                </p></body></html>",
        }

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""

        active = True

        return active

    def Activated(self):
        msg = (
            "<html><head/><body><p><b>Gespal 3D</b> \
        </p><p>Version : %s</p></body></html>"
            % (str(wb_version))
        )
        reply = QtGui.QMessageBox.information(None, "", msg)
        return


if FreeCAD.GuiUp:
    FreeCADGui.addCommand("G3D_Listing", _ListCreator())
    FreeCADGui.addCommand("G3D_CommercialDrawing", _PlanCommercial())
    FreeCADGui.addCommand("G3D_FabricationDrawing", _PlanFabrication())
    FreeCADGui.addCommand("G3D_Help", _ShowHelp())
