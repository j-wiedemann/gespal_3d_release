__title__ = "FreeCAD Profile"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"

## @package ArchProfile
#  \ingroup ARCH
#  \brief Profile tools for ArchStructure
#
#  This module provides tools to build base profiles
#  for Arch Structure elements


import FreeCAD
import Draft
import os
from FreeCAD import Vector

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt
    # \endcond


# Compteur, Nom, Famille, Longueur, Largeur, Epaisseur, Forme
# def makeProfile(profile=[0, 'REC', 'REC100x100', 'R', 100, 100]):
def makeProfile(profile=[0, 'REC100x100', 1, 100, 100, 100, 'R']):
    '''makeProfile(profile): returns a shape with the face defined by the \
    profile data'''

    if not FreeCAD.ActiveDocument:
        FreeCAD.Console.PrintError("No active document. Aborting\n")
        return
    name = profile[1]
    name = "Profile"
    obj = FreeCAD.ActiveDocument.addObject(
        "Part::Part2DObjectPython", name)
    obj.Label = profile[1]
    if profile[6] == "C":
        _ProfileC(obj, profile)
    elif profile[6] == "H":
        _ProfileH(obj, profile)
    elif profile[6] == "R":
        _ProfileR(obj, profile)
    elif profile[6] == "RH":
        _ProfileRH(obj, profile)
    elif profile[6] == "U":
        _ProfileU(obj, profile)
    else:
        print("Profile not supported")
    if FreeCAD.GuiUp:
        ViewProviderProfile(obj.ViewObject)
    return obj


class _Profile(Draft._DraftObject):

    '''Superclass for Profile classes'''

    def __init__(self, obj, profile):
        self.Profile = profile
        Draft._DraftObject.__init__(self, obj, "Profile")


class _ProfileC(_Profile):

    '''A parametric circular tubeprofile.
    Profile data: [Outside diameter, Inside diameter]'''

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyLength",
            "Diameter",
            "Draft",
            QT_TRANSLATE_NOOP("App::Property", "Outside Diameter")
            ).Diameter = profile[4]

        """obj.addProperty(
            "App::PropertyLength",
            "Thickness",
            "Draft",
            QT_TRANSLATE_NOOP("App::Property", "Wall thickness")
            ).Thickness = profile[5]"""
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        import Part
        pl = obj.Placement
        c = Part.Circle(
            FreeCAD.Vector(0.0, 0.0, 0.0),
            FreeCAD.Vector(0.0, 0.0, 1.0),
            obj.Diameter.Value/2)
        obj.Shape = c.toShape()
        obj.Placement = pl


class _ProfileH(_Profile):

    '''A parametric H or I beam profile. Profile data: [width, height, web thickness, flange thickness] (see http://en.wikipedia.org/wiki/I-beam for reference)'''

    def __init__(self,obj, profile):
        obj.addProperty("App::PropertyLength","Width","Draft",QT_TRANSLATE_NOOP("App::Property","Width of the beam")).Width = profile[5]
        obj.addProperty("App::PropertyLength","Height","Draft",QT_TRANSLATE_NOOP("App::Property","Height of the beam")).Height = profile[5]
        obj.addProperty("App::PropertyLength","WebThickness","Draft",QT_TRANSLATE_NOOP("App::Property","Thickness of the web")).WebThickness = profile[6]
        obj.addProperty("App::PropertyLength","FlangeThickness","Draft",QT_TRANSLATE_NOOP("App::Property","Thickness of the flanges")).FlangeThickness = profile[7]
        _Profile.__init__(self,obj,profile)

    def execute(self,obj):
        import Part
        pl = obj.Placement
        p1 = Vector(-obj.Width.Value/2,-obj.Height.Value/2,0)
        p2 = Vector(obj.Width.Value/2,-obj.Height.Value/2,0)
        p3 = Vector(obj.Width.Value/2,(-obj.Height.Value/2)+obj.FlangeThickness.Value,0)
        p4 = Vector(obj.WebThickness.Value/2,(-obj.Height.Value/2)+obj.FlangeThickness.Value,0)
        p5 = Vector(obj.WebThickness.Value/2,obj.Height.Value/2-obj.FlangeThickness.Value,0)
        p6 = Vector(obj.Width.Value/2,obj.Height.Value/2-obj.FlangeThickness.Value,0)
        p7 = Vector(obj.Width.Value/2,obj.Height.Value/2,0)
        p8 = Vector(-obj.Width.Value/2,obj.Height.Value/2,0)
        p9 = Vector(-obj.Width.Value/2,obj.Height.Value/2-obj.FlangeThickness.Value,0)
        p10 = Vector(-obj.WebThickness.Value/2,obj.Height.Value/2-obj.FlangeThickness.Value,0)
        p11 = Vector(-obj.WebThickness.Value/2,(-obj.Height.Value/2)+obj.FlangeThickness.Value,0)
        p12 = Vector(-obj.Width.Value/2,(-obj.Height.Value/2)+obj.FlangeThickness.Value,0)
        p = Part.makePolygon([p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p1])
        p = Part.Face(p)
        #p.reverse()
        obj.Shape = p
        obj.Placement = pl


class _ProfileR(_Profile):

    '''A parametric rectangular beam profile based on [Width, Height]'''

    def __init__(self, obj, profile):
        obj.addProperty(
            "App::PropertyLength",
            "Width",
            "Draft",
            QT_TRANSLATE_NOOP("App::Property", "Width of the beam")
            ).Width = profile[5]
        obj.addProperty(
            "App::PropertyLength",
            "Height",
            "Draft",
            QT_TRANSLATE_NOOP("App::Property", "Height of the beam")
            ).Height = profile[4]
        _Profile.__init__(self, obj, profile)

    def execute(self, obj):
        import Part
        pl = obj.Placement
        p1 = Vector(-obj.Height.Value/2, -obj.Width.Value/2, 0)
        p2 = Vector(-obj.Height.Value/2, obj.Width.Value/2, 0)
        p3 = Vector(obj.Height.Value/2, obj.Width.Value/2, 0)
        p4 = Vector(obj.Height.Value/2, -obj.Width.Value/2, 0)
        p = Part.makePolygon([p1, p2, p3, p4, p1])
        p = Part.Face(p)
        p.reverse()
        obj.Shape = p
        obj.Placement = pl


class _ProfileRH(_Profile):

    '''A parametric Rectangular hollow beam profile. Profile data: [width, height, thickness]'''

    def __init__(self,obj, profile):
        obj.addProperty("App::PropertyLength","Width","Draft",QT_TRANSLATE_NOOP("App::Property","Width of the beam")).Width = profile[5]
        obj.addProperty("App::PropertyLength","Height","Draft",QT_TRANSLATE_NOOP("App::Property","Height of the beam")).Height = profile[5]
        obj.addProperty("App::PropertyLength","Thickness","Draft",QT_TRANSLATE_NOOP("App::Property","Thickness of the sides")).Thickness = profile[6]
        _Profile.__init__(self,obj,profile)

    def execute(self,obj):
        import Part
        pl = obj.Placement
        p1 = Vector(-obj.Width.Value/2,-obj.Height.Value/2,0)
        p2 = Vector(obj.Width.Value/2,-obj.Height.Value/2,0)
        p3 = Vector(obj.Width.Value/2,obj.Height.Value/2,0)
        p4 = Vector(-obj.Width.Value/2,obj.Height.Value/2,0)
        q1 = Vector(-obj.Width.Value/2+obj.Thickness.Value,-obj.Height.Value/2+obj.Thickness.Value,0)
        q2 = Vector(obj.Width.Value/2-obj.Thickness.Value,-obj.Height.Value/2+obj.Thickness.Value,0)
        q3 = Vector(obj.Width.Value/2-obj.Thickness.Value,obj.Height.Value/2-obj.Thickness.Value,0)
        q4 = Vector(-obj.Width.Value/2+obj.Thickness.Value,obj.Height.Value/2-obj.Thickness.Value,0)
        p = Part.makePolygon([p1,p2,p3,p4,p1])
        q = Part.makePolygon([q1,q2,q3,q4,q1])
        #r = Part.Face([p,q])
        #r.reverse()
        p = Part.Face(p)
        q = Part.Face(q)
        r = p.cut(q)
        obj.Shape = r
        obj.Placement = pl


class _ProfileU(_Profile):

    '''A parametric H or I beam profile. Profile data: [width, height, web thickness, flange thickness] (see  http://en.wikipedia.org/wiki/I-beam forreference)'''

    def __init__(self,obj, profile):
        obj.addProperty("App::PropertyLength","Width","Draft",QT_TRANSLATE_NOOP("App::Property","Width of the beam")).Width = profile[5]
        obj.addProperty("App::PropertyLength","Height","Draft",QT_TRANSLATE_NOOP("App::Property","Height of the beam")).Height = profile[5]
        obj.addProperty("App::PropertyLength","WebThickness","Draft",QT_TRANSLATE_NOOP("App::Property","Thickness of the webs")).WebThickness = profile[6]
        obj.addProperty("App::PropertyLength","FlangeThickness","Draft",QT_TRANSLATE_NOOP("App::Property","Thickness of the flange")).FlangeThickness = profile[7]
        _Profile.__init__(self,obj,profile)

    def execute(self,obj):
        import Part
        pl = obj.Placement
        p1 = Vector(-obj.Width.Value/2,-obj.Height.Value/2,0)
        p2 = Vector(obj.Width.Value/2,-obj.Height.Value/2,0)
        p3 = Vector(obj.Width.Value/2,obj.Height.Value/2,0)
        p4 = Vector(obj.Width.Value/2-obj.FlangeThickness.Value,obj.Height.Value/2,0)
        p5 = Vector(obj.Width.Value/2-obj.FlangeThickness.Value,obj.WebThickness.Value-obj.Height.Value/2,0)
        p6 = Vector(-obj.Width.Value/2+obj.FlangeThickness.Value,obj.WebThickness.Value-obj.Height.Value/2,0)
        p7 = Vector(-obj.Width.Value/2+obj.FlangeThickness.Value,obj.Height.Value/2,0)
        p8 = Vector(-obj.Width.Value/2,obj.Height.Value/2,0)
        p = Part.makePolygon([p1,p2,p3,p4,p5,p6,p7,p8,p1])
        p = Part.Face(p)
        #p.reverse()
        obj.Shape = p
        obj.Placement = pl


class ViewProviderProfile(Draft._ViewProviderDraft):

    '''General view provider for Profile classes'''

    def __init__(self, vobj):

        Draft._ViewProviderDraft.__init__(self, vobj)

    def getIcon(self):

        import Arch_rc
        return ":/icons/Arch_Profile.svg"

    def setEdit(self, vobj, mode):

        taskd = ProfileTaskPanel(vobj.Object)
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):

        FreeCADGui.Control.closeDialog()
        FreeCAD.ActiveDocument.recompute()
        return


class ProfileTaskPanel:

    '''The editmode TaskPanel for Profile objects'''

    def __init__(self, obj):

        self.obj = obj
        self.profile = None
        if isinstance(self.obj.Proxy, _ProfileC):
            self.type = "C"
        elif isinstance(self.obj.Proxy, _ProfileH):
            self.type = "H"
        elif isinstance(self.obj.Proxy, _ProfileR):
            self.type = "R"
        elif isinstance(self.obj.Proxy, _ProfileRH):
            self.type = "RH"
        elif isinstance(self.obj.Proxy, _ProfileU):
            self.type = "U"
        else:
            self.type = "Undefined"
        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)
        self.comboCategory = QtGui.QComboBox(self.form)
        layout.addWidget(self.comboCategory)
        self.comboProfile = QtGui.QComboBox(self.form)
        layout.addWidget(self.comboProfile)
        QtCore.QObject.connect(
            self.comboCategory,
            QtCore.SIGNAL("currentIndexChanged(QString)"),
            self.changeCategory)
        QtCore.QObject.connect(
            self.comboProfile,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.changeProfile)
        # Read preset profiles and add relevant ones
        self.categories = []
        self.presets = readPresets()
        for pre in self.presets:
            if pre[3] == self.type:
                if pre[1] not in self.categories:
                    self.categories.append(pre[1])
        self.comboCategory.addItem(" ")
        if self.categories:
            self.comboCategory.addItems(self.categories)
        # Find current profile by label
        for pre in self.presets:
            if self.obj.Label in pre[2]:
                self.profile = pre
                break
        if not self.profile:
            # try to find by size
            if hasattr(self.obj, "Width") and hasattr(self.obj, "Height"):
                for pre in self.presets:
                    if abs(self.obj.Width - self.profile[5]) < 0.1 and \
                       abs(self.obj.Height - self.Profile[5]) < 0.1:
                        self.profile = pre
                        break
        if self.profile:
            # the operation below will change self.profile
            origprofile = list(self.profile)
            self.comboCategory.setCurrentIndex(
                1 + self.categories.index(origprofile[1]))
            self.changeCategory(origprofile[1])
            self.comboProfile.setCurrentIndex(
                self.currentpresets.index(origprofile))
        self.retranslateUi(self.form)

    def changeCategory(self, text):

        self.comboProfile.clear()
        self.currentpresets = []
        for pre in self.presets:
            if pre[1] == text:
                self.currentpresets.append(pre)
                f = FreeCAD.Units.Quantity(
                    pre[4], FreeCAD.Units.Length).getUserPreferred()
                d = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Units")
                d = d.GetInt("Decimals", 2)
                s1 = str(round(pre[4]/f[1], d))
                s2 = str(round(pre[5]/f[1], d))
                s3 = str(f[2])
                self.comboProfile.addItem(pre[2]+" ("+s1+"x"+s2+s3+")")

    def changeProfile(self, idx):

        self.profile = self.currentpresets[idx]

    def accept(self):

        if self.profile:
            self.obj.Label = self.profile[1]
            if self.type in ["H", "R", "RH", "U"]:
                self.obj.Width = self.profile[5]
                self.obj.Height = self.profile[5]
                if self.type in ["H", "U"]:
                    self.obj.WebThickness = self.profile[6]
                    self.obj.FlangeThickness = self.profile[7]
                elif self.type == "RH":
                    self.obj.Thickness = self.profile[6]
            elif self.type == "C":
                self.obj.OutDiameter = self.profile[5]
                self.obj.Thickness = self.profile[5]
            FreeCAD.ActiveDocument.recompute()
            FreeCADGui.ActiveDocument.resetEdit()
        return True

    def retranslateUi(self, TaskPanel):

        self.form.setWindowTitle(
            self.type+" "+QtGui.QApplication.translate("Arch", "Profile", None))
