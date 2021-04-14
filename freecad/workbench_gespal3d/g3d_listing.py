# coding: utf-8

import os
import string
import math
from datetime import datetime
from fractions import Fraction

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui
    import Draft, Part
    import TechDraw, TechDrawGui
    import DraftGeomUtils, DraftVecUtils
    from PySide import QtCore, QtGui
    from freecad.workbench_gespal3d import __version__ as wb_version
    from freecad.workbench_gespal3d import PARAMPATH
    from freecad.workbench_gespal3d import print_debug
    from freecad.workbench_gespal3d import RESOURCESPATH


__title__ = "Gespal 3D Listing"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class gespal3d_exports:
    def __init__(self):
        doc = App.ActiveDocument
        path_doc = doc.FileName
        if len(doc.Name.split("PL_")) > 1:
            id = doc.Name.split("PL_")[1]
        else:
            id = doc.Name
        path_project = os.path.split(path_doc)
        name_image = "3D_" + id + ".png"
        name_csv = "CP_" + id + ".csv"
        pc_pdf = "PC_" + id + ".pdf"
        pf_pdf = "PF_" + id + ".pdf"
        self.path_image = os.path.join(path_project[0], name_image)
        self.path_csv = os.path.join(path_project[0], name_csv)
        self.path_pc = os.path.join(path_project[0], pc_pdf)
        self.path_pf = os.path.join(path_project[0], pf_pdf)
        self.p = App.ParamGet(str(PARAMPATH))
        self.path_template = self.p.GetString(
            "PathTemplate",
            os.path.join(RESOURCESPATH, "templates"))
        print_debug(["PathTemplates :", self.path_template])

        objs = doc.Objects
        self.objlist = []
        self.projgroup_list = []
        objother = []
        self.objproduct = None
        self.boundbox = None
        self.grp_dimension = []
        self.mySheet = None
        print_debug("There is %s object in document." % len(objs))
        for obj in objs:
            print_debug("Checking object : %s." % obj.Name)
            if hasattr(obj, "Tag"):
                if obj.Tag == "Gespal":
                    if hasattr(obj, "Description"):
                        if obj.Description is not None:
                            self.objlist.append(obj)
                            self.projgroup_list.append(obj)
                            print_debug("%s added to the objlist." % obj.Name)
            elif obj.TypeId == "Part::Mirroring":
                src = self.getSource(obj)
                if src.Tag == "Gespal":
                    if hasattr(src, "Description"):
                        if src.Description is not None:
                            self.objlist.append(src)
                            print_debug("%s is added to the objlist." % src.Name)
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
            App.Console.PrintMessage("La liste des composants Gespal est vide.\n")
        else:
            print_debug("There is %s object in objlist :" % len(self.objlist))
            print_debug([obj.Name for obj in self.objlist])

    def getSource(self, obj):
        print_debug("Looking for source of %s." % obj.Name)
        src = obj.Source
        print_debug("Current source is %s." % src.Name)
        while src.TypeId == "Part::Mirroring":
            print_debug("Source is a Part::Mirror object.")
            src = src.Source
        print_debug("Source is : %s." % src.Name)
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
        obj = App.ActiveDocument.addObject("Part::Feature", "shapeAnalyse")
        obj.Shape = shape
        obj.Placement.Base = App.Vector(0.0, 0.0, 0.0)
        obj.Placement.Rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), 0.0)
        App.ActiveDocument.recompute()
        ## Get the face to align with XY plane
        faces = obj.Shape.Faces
        facesMax = self.getFacesMax(faces)
        coupleEquerre = self.getCoupleFacesEquerre(facesMax)
        ## Get the normal of this face
        nv1 = coupleEquerre[0][0].normalAt(0, 0)
        ## Get the goal normal vector
        zv = App.Vector(0, 0, 1)
        ## Find and apply a rotation to the object to align face
        pla = obj.Placement
        rot = pla.Rotation
        rot1 = App.Rotation(nv1, zv)
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
        vecZ = App.Vector(vec[0], vec[1], 0.0)
        pos2 = obj.Placement.Base
        rotZ = math.degrees(
            DraftVecUtils.angle(vecZ, App.Vector(1.0, 0.0, 0.0), zv)
        )
        Draft.rotate([obj], rotZ, pos2, axis=zv, copy=False)
        bb = obj.Shape.BoundBox
        movex = bb.XMin * -1
        movey = bb.YMin * -1
        movez = bb.ZMin * -1
        Draft.move([obj], App.Vector(movex, movey, movez))
        App.ActiveDocument.recompute()
        ## Get the boundbox
        analyse = [
            obj.Shape.BoundBox.YLength,
            obj.Shape.BoundBox.ZLength,
            obj.Shape.BoundBox.XLength,
        ]
        # if not "Shape" in self.export :
        App.ActiveDocument.removeObject(obj.Name)
        return analyse

    def makeSpreadsheet(self):
        print_debug("Start making Spreadsheet...")
        if self.mySheet:
            self.mySheet.clearAll()
            App.ActiveDocument.recompute()
        else:
            App.ActiveDocument.addObject("Spreadsheet::Sheet", "Gespal3DListe")
            self.mySheet = App.ActiveDocument.getObject("Gespal3DListe")
            App.ActiveDocument.recompute()
        mySheet = self.mySheet
        headers = [
            "ID",
            "Désignation",
            "Largeur",
            "Hauteur",
            "Longueur",
            "Usinage",
        ]
        columns = list(string.ascii_uppercase)
        count = 0
        for header in headers:
            index = str(columns[count]) + "1"
            mySheet.set(index, headers[count])
            count += 1
        n = 1
        for obj in self.objlist:
            shape = obj.Shape
            label = obj.Label
            analyse = self.shapeAnalyse(shape)
            print_debug("row %s : object's name is %s." % (n, obj.Name))
            print_debug(analyse)
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
            mySheet.set("B" + str(n + 1), str(label))
            mySheet.set("C" + str(n + 1), str(width))
            mySheet.set("D" + str(n + 1), str(height))
            mySheet.set("E" + str(n + 1), str(length))
            if usinage is not None:
                mySheet.set("F" + str(n + 1), str(usinage))
            n += 1
        App.ActiveDocument.recompute()
        mySheet.exportFile(self.path_csv)
        print_debug("End making Spreadsheet...")
        return

    def makeImage(self):
        av = Gui.activeDocument().activeView()
        av.setAxisCross(False)
        self.objproduct.ViewObject.Visibility = False
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = False
        if hasattr(Gui, "Snapper"):
            Gui.Snapper.setTrackers()
            if Gui.Snapper.grid:
                if Gui.Snapper.grid.Visible:
                    Gui.Snapper.grid.off()
                    Gui.Snapper.forceGridOff = True
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        av.setCameraType("Orthographic")
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
        # av.setCameraType("Perspective")
        av.saveImage(self.path_image, 2560, 1600, "White")
        self.objproduct.ViewObject.Visibility = True
        for obj in self.grp_dimension:
            obj.ViewObject.Visibility = True
        av.setCameraType("Orthographic")
        # Gui.ActiveDocument.ActiveView.setAxisCross(True)
        return

    def makePlan(self, name):
        doc = App.activeDocument()
        projgrp_name = "ProjGroup_" + str(name)
        isoview_name = "View_" + str(name)
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
        if orientation == "A4P":
            path = os.path.join(self.path_template, "A4P.svg")
        else:
            path = os.path.join(self.path_template, "A4L.svg")
        template.Template = path
        page.Template = template

        r = template.Width.Value / self.boundbox.Length.Value
        r = template.Height.Value / max_length
        r = r / 3
        scale = round(r, 2)
        template.setEditFieldContent("NOM", doc.Comment)
        template.setEditFieldContent("FC-SH", self.objproduct.Label)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        template.setEditFieldContent("FC-DATE", dt_string)
        template.setEditFieldContent("FC-SC", str(Fraction(str(scale))))
        # ProjGroup
        projgroup = doc.addObject("TechDraw::DrawProjGroup", projgrp_name)
        page.addView(projgroup)
        projgroup.Source = self.projgroup_list
        projgroup.ScaleType = u"Custom"
        projgroup.Scale = scale
        projgroup.addProjection("Front")
        if orientation == "A4L":
            projgroup.Anchor.Direction = App.Vector(0.000, 0.000, 1.000)
            projgroup.Anchor.RotationVector = App.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = App.Vector(1.000, 0.000, 0.000)
            y = (self.boundbox.Width.Value * projgroup.Scale) / 2 + 40.0
        else:
            projgroup.Anchor.Direction = App.Vector(0.000, -1.000, 0.000)
            projgroup.Anchor.RotationVector = App.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = App.Vector(1.000, 0.000, 0.000)
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
        iso_view.Direction = App.Vector(0.577, -0.577, 0.577)
        iso_view.XDirection = App.Vector(0.707, 0.707, -0.000)
        iso_view.ScaleType = u"Custom"
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
        doc = App.ActiveDocument
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
        page = doc.getObject("plan_commercial")
        TechDrawGui.exportPageAsPdf(page, self.path_pc)
        return

    def exportPlanFabrication(self):
        doc = App.ActiveDocument
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
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
        if App.ActiveDocument:
            doc = App.ActiveDocument
            if len(doc.FileName) > 0:
                if hasattr(Gui.activeDocument().activeView(), "zoomIn"):
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
        App.ActiveDocument.recompute(None,True,True)
        return


class _PlanCommercial:
    """Export plan commercial"""

    def GetResources(self):
        from freecad.workbench_gespal3d import ICONPATH

        return {
            "Pixmap": os.path.join(ICONPATH, "plan-commercial-pdf.svg"),
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
            "Pixmap": os.path.join(ICONPATH, "plan-fabrication-pdf.svg"),
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



if App.GuiUp:
    Gui.addCommand("G3D_Listing", _ListCreator())
    Gui.addCommand("G3D_CommercialDrawing", _PlanCommercial())
    Gui.addCommand("G3D_FabricationDrawing", _PlanFabrication())
