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
        self.doc = App.ActiveDocument
        
        if len(self.doc.Label.split("PL_")) > 1:
            self.project_id = self.doc.Label.split("PL_")[1]
        else:
            self.project_id = self.doc.Label
        self.path_project = os.path.split(self.doc.FileName)[0]

        self.p = App.ParamGet(str(PARAMPATH))

        #self.GespalObjetcs = []
        self.GespalListing = []
        self.GespalBOM = []
        self.GespalObjectsToDrawings = []

        self.gespal_ProjectProduct = None
        self.gespal_ProductBBox = None
        self.gespal_DimensionsFolder = []
        self.InventoryList_Sheet = None
        self.CuttingList_Sheet = None
  
        self.makeListing()
        self.makeCondensedListing()

    def makeListing(self):
        # get all objects in the current document
        objs = self.doc.Objects
        print_debug("There is %s object in document." % len(objs))

        _gespal_objects = []
        _objother = []
        # sorting out gespal objects
        for obj in objs:
            print_debug("Checking object : {} ({}).".format(obj.Name, obj.Label, obj.TypeId))
            if self.is_gespal_object(obj):
                _gespal_objects.append(obj)
            elif obj.TypeId == "Part::Mirroring":
                src = self.getSource(obj)
                if self.is_gespal_object(src):
                    _gespal_objects.append(obj)
            elif obj.Name == "Product":
                self.gespal_ProjectProduct = obj
            elif obj.Name == "Box":
                self.gespal_ProductBBox = obj
            elif "Dimension" in obj.Name:
                self.gespal_DimensionsFolder.append(obj)
            elif obj.Name == "Gespal3DListe":
                self.InventoryList_Sheet = obj
            elif obj.Name == "Gespal3DDebit":
                self.CuttingList_Sheet = obj
            else:
                _objother.append(obj)

        if len(_gespal_objects) < 0:
            App.Console.PrintMessage("La liste des composants Gespal est vide.\n")
        else:
            print_debug("There is %s object in GespalObjetcs :" % len(_gespal_objects))

        # special folder for accessory
        accessoryBB_group = self.doc.getObject('AccessoiresBB')
        if accessoryBB_group is None:
            accessoryBB_group = self.doc.addObject('App::DocumentObjectGroup','AccessoiresBB')
        else:
            accessoryBB_group.removeObjectsFromDocument()
        self.doc.recompute()

        _gespal_listing = []
        for obj in _gespal_objects:
            if obj.TypeId == "Part::Mirroring":
                src = self.getSource(obj)
                _gespal_listing.append(src)
                if hasattr(src, "EquipmentPower"):
                    bb = self.makeEquipmentBBox(obj)
                    accessoryBB_group.addObject(bb)
                    self.GespalObjectsToDrawings.append(bb)
                else:
                    self.GespalObjectsToDrawings.append(obj)
            else:
                _gespal_listing.append(obj)
                if hasattr(obj, "EquipmentPower"):
                    bb = self.makeEquipmentBBox(obj)
                    accessoryBB_group.addObject(bb)
                    self.GespalObjectsToDrawings.append(bb)
                else:
                    self.GespalObjectsToDrawings.append(obj)

        accessoryBB_group.ViewObject.Visibility = False
        print_debug("There is %s object in GespalObjectsToDrawings :" % len(self.GespalObjectsToDrawings))

        for obj in _gespal_listing:

            component = {"ID":int,
                    "Label":str,
                    "Type":str,
                    "Width":float,
                    "Height":float,
                    "Length":float,
                    "Machining":bool,}

            component["ID"] = int(obj.Description)
            component["Label"] = str(obj.Label)
            component["Machining"] = False

            if not hasattr(obj, "EquipmentPower"):
                boundbox = self.getAlignedBoundBox(obj.Shape)
                #print_debug("row %s : object's name is %s." % (n, obj.Name))
                #print_debug(boundbox)
                boundbox = [round(float(boundbox[0]), 2),
                            round(float(boundbox[1]), 2),
                            round(float(boundbox[2]), 2)]

                boundbox0 = boundbox[0]
                boundbox1 = boundbox[1]
                boundbox2 = boundbox[2]

                if hasattr(obj, "Height"):
                    component["Type"] = "Barre"
                    width = boundbox1
                    height = boundbox0
                    length = boundbox2
                elif hasattr(obj, "Thickness"):
                    component["Type"] = "Panneaux"
                    width = obj.Thickness.Value
                    m = 0
                    for dim in boundbox:
                        print_debug([dim, width])
                        if round(dim,2) == width:
                            boundbox.pop(m)
                        m += 1
                    height = float(min(boundbox))
                    length = float(max(boundbox))
                else:
                    component["Type"] = "Barre"
                    width = boundbox0
                    height = boundbox1
                    length = boundbox2
                if hasattr(obj, "Subtractions"):
                    if len(obj.Subtractions) > 0:
                        component["Machining"] = True
            else:
                component["Type"] = "Quincaillerie"
                width = 0.00
                height = 0.00
                length = 0.00
            
            component["Width"] = width
            component["Height"] = height
            component["Length"] = length
            
            self.GespalListing.append(component)

    def makeCondensedListing(self):
        for obj in self.GespalListing:
            if len(self.GespalBOM) > 0:
                listed = False
                for comp in self.GespalBOM:
                    if obj["ID"] == comp["ID"]:
                        if obj["Length"] == comp["Length"]:
                            if obj["Width"] == comp["Width"] and obj["Height"] == comp["Height"] :
                                comp["Quantity"] += 1
                                listed = True
                                print_debug("{} is already listed, let's add +1 to qty.".format(obj))
                        
                if listed == False:
                    print_debug("{} is not listed yet, creating a new component.".format(obj))
                    component = self.createComponent(obj)
                    component["Reference"] = reference_count
                    reference_count += 1
                    self.GespalBOM.append(component)
            else:
                print_debug("{} is not listed yet, creating a new component.".format(obj))
                component = self.createComponent(obj)
                reference_count = 1
                component["Reference"] = reference_count
                reference_count += 1
                self.GespalBOM.append(component)

    def createComponent(self, obj):
        component = {"ID":int,
                "Label":str,
                "Type":str,
                "Width":float,
                "Height":float,
                "Length":float,
                "Machining":bool,
                "Quantity":int,
                "Reference":int}
        component["Quantity"] = 1
        component["ID"] = obj["ID"]
        component["Label"] = obj["Label"]
        component["Type"] = obj["Type"]
        component["Width"] = obj["Width"]
        component["Height"] = obj["Height"]
        component["Length"] = obj["Length"]
        component["Machining"] = obj["Machining"]
        component["Reference"] = 0
        return component


    def is_gespal_object(self, obj):
        if hasattr(obj, "Tag"):
            if obj.Tag == "Gespal":
                if hasattr(obj, "Description"):
                    if obj.Description is not None:
                        return True
        return False

    def makeEquipmentBBox(self, obj):
        bb = self.doc.addObject("Part::Box","BBox")
        bb.Label = obj.Label
        bb.Length = obj.Shape.BoundBox.XLength
        bb.Width = obj.Shape.BoundBox.YLength
        bb.Height = obj.Shape.BoundBox.ZLength
        bb.Placement.Base = [obj.Shape.BoundBox.XMin,obj.Shape.BoundBox.YMin,obj.Shape.BoundBox.ZMin]
        return bb

    def getSource(self, obj):
        print_debug("Looking for source of %s." % obj.Name)
        src = obj.Source
        while src.TypeId == "Part::Mirroring":
            print_debug("Source is {}. It's a Part::Mirror object.".format(src.Name))
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

    def getAlignedBoundBox(self, shape):
        ## Create a new object with the shape of the current arch object
        ## His placment is set to 0,0,0
        obj = App.ActiveDocument.addObject("Part::Feature", "AlignedBoundBox")
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


    def makeInventory_Sheet(self):
        print_debug("Start making Spreadsheet...")
        if self.InventoryList_Sheet:
            self.InventoryList_Sheet.clearAll()
        else:
            App.ActiveDocument.addObject("Spreadsheet::Sheet", "Gespal3DListe")
            self.InventoryList_Sheet = App.ActiveDocument.getObject("Gespal3DListe")
        App.ActiveDocument.recompute()

        spreadsheet = self.InventoryList_Sheet
        debitSheet = self.CuttingList_Sheet
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
            spreadsheet.set(index, headers[count])
            count += 1
        n = 2
        for component in self.GespalListing:
            id_format = "'" + str(component["ID"])
            spreadsheet.set("A" + str(n), id_format)
            label_format = "'" + str(component["Label"])
            spreadsheet.set("B" + str(n), label_format)
            spreadsheet.set("C" + str(n), str(component["Width"]))
            spreadsheet.setDisplayUnit("C" + str(n), 'mm')
            spreadsheet.set("D" + str(n), str(component["Height"]))
            spreadsheet.setDisplayUnit("D" + str(n), 'mm')
            spreadsheet.set("E" + str(n), str(component["Length"]))
            spreadsheet.setDisplayUnit("E" + str(n), 'mm')
            if component["Machining"] is True:
                spreadsheet.set("F" + str(n), "C")
            n += 1

        App.ActiveDocument.recompute()
        name_csv = "CP_" + self.project_id + ".csv"
        path_csv = os.path.join(self.path_project, name_csv)
        spreadsheet.exportFile(path_csv)

        print_debug("End making Iventory Spreadsheet...")
        return


    def makeCuttingList_Sheet(self):
        print_debug("Start making Cutting list Spreadsheet...")
        if self.CuttingList_Sheet:
            self.CuttingList_Sheet.clearAll()
        else:
            App.ActiveDocument.addObject("Spreadsheet::Sheet", "Gespal3DDebit")
            self.CuttingList_Sheet = App.ActiveDocument.getObject("Gespal3DDebit")
        App.ActiveDocument.recompute()

        spreadsheet = self.CuttingList_Sheet
        headers = [
            "ID",
            "Désignation",
            "Quantité",
            "Largeur",
            "Hauteur",
            "Longueur",
            "Référence plan"
            #"Volume",
        ]
        columns = list(string.ascii_uppercase)
        count = 0
        for header in headers:
            index = str(columns[count]) + "1"
            spreadsheet.set(index, headers[count])
            count += 1
        n = 2
        for component in self.GespalBOM:
            id_format = "'" + str(component["ID"])
            spreadsheet.set("A" + str(n), id_format)

            label_format = "'" + str(component["Label"])
            if component["Machining"] is True:
                label_format += " (Usinage)"
            spreadsheet.set("B" + str(n), label_format)

            spreadsheet.set("D" + str(n), str(component["Width"]))
            #spreadsheet.setDisplayUnit("D" + str(n), 'mm')

            spreadsheet.set("E" + str(n), str(component["Height"]))
            #spreadsheet.setDisplayUnit("E" + str(n), 'mm')

            spreadsheet.set("F" + str(n), str(component["Length"]))
            #spreadsheet.setDisplayUnit("F" + str(n), 'mm')
            
            qty_format = "'" + str(component["Quantity"])
            spreadsheet.set("C" + str(n), qty_format)
            spreadsheet.setAlignment("C" + str(n), 'center', 'keep')

            ref_format = "'" + str(component["Reference"])
            spreadsheet.set("G" + str(n), ref_format)
            spreadsheet.setStyle("G" + str(n), 'bold', 'add')
            spreadsheet.setAlignment("G" + str(n), 'center', 'keep')

            n += 1

        App.ActiveDocument.recompute()
        name_csv = "BOM_" + self.project_id + ".csv"
        path_csv = os.path.join(self.path_project, name_csv)
        spreadsheet.exportFile(path_csv)

        print_debug("End making Cutting list Spreadsheet...")
        return


    def makeImage(self):
        av = Gui.activeDocument().activeView()
        av.setAxisCross(False)
        self.gespal_ProjectProduct.ViewObject.Visibility = False
        for obj in self.gespal_DimensionsFolder:
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
        name_image = "3D_" + self.project_id + ".png"
        path_image = os.path.join(self.path_project, name_image)
        av.saveImage(path_image, 2560, 1600, "White")
        self.gespal_ProjectProduct.ViewObject.Visibility = True
        for obj in self.gespal_DimensionsFolder:
            obj.ViewObject.Visibility = True
        av.setCameraType("Orthographic")
        # Gui.ActiveDocument.ActiveView.setAxisCross(True)
        return

    def makePlan(self, name):
        self.doc = App.activeDocument()
        projgrp_name = "ProjGroup_" + str(name)
        isoview_name = "View_" + str(name)
        # check if page exist
        page = self.doc.getObject(name)
        if self.doc.getObject(name):
            if self.doc.getObject(projgrp_name):
                self.doc.getObject(projgrp_name).Source = self.GespalObjectsToDrawings
            if self.doc.getObject(isoview_name):
                self.doc.getObject(isoview_name).Source = self.GespalObjectsToDrawings
            return

        # Page
        page = self.doc.addObject("TechDraw::DrawPage", name)
        # Template
        template = self.doc.addObject("TechDraw::DrawSVGTemplate", "Template")

        # Portrait or Landscape
        max_length = max(
            self.gespal_ProductBBox.Length.Value,
            self.gespal_ProductBBox.Width.Value,
            self.gespal_ProductBBox.Height.Value,
        )
        if max_length == self.gespal_ProductBBox.Height.Value:
            orientation = "A4P"
        else:
            orientation = "A4L"
        
        # Template path
        path_template = self.p.GetString(
            "PathTemplate",
            os.path.join(RESOURCESPATH, "templates"))

        print_debug(["PathTemplates :", path_template])

        if orientation == "A4P":
            path = os.path.join(path_template, "A4P.svg")
        else:
            path = os.path.join(path_template, "A4L.svg")
        template.Template = path
        page.Template = template


        r = template.Width.Value / self.gespal_ProductBBox.Length.Value
        r = template.Height.Value / max_length
        r = r / 2
        scale = round(r, 2)
        template.setEditFieldContent("NOM", self.doc.Comment)
        template.setEditFieldContent("FC-SH", self.gespal_ProjectProduct.Label)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        template.setEditFieldContent("FC-DATE", dt_string)
        template.setEditFieldContent("FC-SC", str(Fraction(str(scale))))
        # ProjGroup
        projgroup = self.doc.addObject("TechDraw::DrawProjGroup", projgrp_name)
        page.addView(projgroup)
        projgroup.Source = self.GespalObjectsToDrawings
        projgroup.ScaleType = u"Custom"
        projgroup.Scale = scale
        projgroup.addProjection("Front")
        if orientation == "A4L":
            projgroup.Anchor.Direction = App.Vector(0.000, -1.000, 0.000)
            projgroup.Anchor.RotationVector = App.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = App.Vector(1.000, 0.000, 0.000)
            y = 297/2 + self.gespal_ProductBBox.Height.Value * projgroup.Scale * 2.5
        else:
            projgroup.Anchor.Direction = App.Vector(0.000, -1.000, 0.000)
            projgroup.Anchor.RotationVector = App.Vector(1.000, 0.000, 0.000)
            projgroup.Anchor.XDirection = App.Vector(1.000, 0.000, 0.000)
            y = 297 - 20 - ((self.gespal_ProductBBox.Height.Value * projgroup.Scale) / 2)
        projgroup.Anchor.recompute()
        if orientation == "A4L":
            projgroup.addProjection("Top")
            projgroup.addProjection("Left")
        else:
            projgroup.addProjection("Top")
            projgroup.addProjection("Left")
        for view in projgroup.Views:
            view.Perspective = False
            view.Focus = "100 m"
        x = 20 + (self.gespal_ProductBBox.Length.Value * projgroup.Scale) / 2
        projgroup.X = x
        projgroup.Y = y
        projgroup.AutoDistribute = True
        projgroup.spacingY = 0
        # Iso View
        iso_view = self.doc.addObject("TechDraw::DrawViewPart", isoview_name)
        page.addView(iso_view)
        iso_view.Source = self.GespalObjectsToDrawings
        iso_view.Direction = App.Vector(0.577, -0.577, 0.577)
        iso_view.XDirection = App.Vector(0.707, 0.707, -0.000)
        iso_view.ScaleType = u"Custom"
        iso_view.Scale = scale / 2
        if orientation == "A4L":
            iso_view.X = 240.0
            iso_view.Y = 70.0
        else:
            iso_view.X = 3 * 210.0 / 4
            iso_view.Y = 100.0

        iso_view.recompute()
        # Recompute
        page.recompute(True)
        #page.ViewObject.show()
        page.KeepUpdated = False
        return

    def exportPlanCommercial(self):
        self.doc = App.ActiveDocument
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
        page = self.doc.getObject("plan_commercial")
        pc_pdf = "PC_" + self.project_id + ".pdf"
        pc_svg = "PC_" + self.project_id + ".svg"
        path_pc_pdf = os.path.join(self.path_project, pc_pdf)
        path_pc_svg = os.path.join(self.path_project, pc_svg)
        TechDrawGui.exportPageAsPdf(page, path_pc_pdf)
        TechDrawGui.exportPageAsSvg(page, path_pc_svg)
        return

    def exportPlanFabrication(self):
        self.doc = App.ActiveDocument
        Gui.Selection.clearSelection()
        Gui.Selection.clearPreselection()
        page = self.doc.getObject("plan_fabrication")
        pf_pdf = "PF_" + self.project_id + ".pdf"
        pf_svg = "PF_" + self.project_id + ".svg"
        path_pf_pdf = os.path.join(self.path_project, pf_pdf)
        path_pf_svg = os.path.join(self.path_project, pf_svg)
        TechDrawGui.exportPageAsPdf(page, path_pf_pdf)
        TechDrawGui.exportPageAsSvg(page, path_pf_svg)
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
            self.doc = App.ActiveDocument
            if len(self.doc.FileName) > 0:
                if hasattr(Gui.activeDocument().activeView(), "zoomIn"):
                    for obj in self.doc.Objects:
                        if obj.Name == "Product":
                            active = True
        return active

    def Activated(self):
        pb = Gui.getMainWindow().statusBar().findChild(QtGui.QProgressBar)
        pb.setMaximum(100)
        pb.setValue(0)
        pb.show()
        Gui.updateGui()
        
        # Spreadsheet
        export = gespal3d_exports()
        
        pb.setValue(20)
        pb.show()
        Gui.updateGui()
        
        export.makeInventory_Sheet()
        #print(export.GespalBOM)
        export.makeCuttingList_Sheet()
        
        pb.setValue(40)
        pb.show()
        Gui.updateGui()

        # Image
        export.makeImage()
        
        pb.setValue(60)
        pb.show()
        Gui.updateGui()

        # Plan
        export.makePlan(name="plan_commercial")
        
        pb.setValue(80)
        pb.show()
        Gui.updateGui()
        
        export.makePlan(name="plan_fabrication")
        pb.setValue(100)
        pb.show()
        Gui.updateGui()
        
        App.ActiveDocument.recompute(None,True,True)
        pb.hide()
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
