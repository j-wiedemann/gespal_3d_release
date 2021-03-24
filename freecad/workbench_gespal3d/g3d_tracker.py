# coding: utf-8

import FreeCAD as App
from FreeCAD import Vector
import DraftVecUtils
from draftguitools.gui_trackers import Tracker
from pivy import coin
from freecad.workbench_gespal3d import DEBUG
from freecad.workbench_gespal3d import DEBUG_T

if (DEBUG == True) and (DEBUG_T == True):
    DEBUG_T = True


__title__ = "Gespal 3D Trackers"
__license__ = "LGPLv2.1"
__author__ = "Jonathan Wiedemann"
__url__ = "https://freecad-france.com"


class beamTracker(Tracker):
    '''A box tracker, can be based on a line object.'''

    def __init__(self, line=None, width=0.1, height=1, shaded=False):
        self.trans = coin.SoTransform()
        m = coin.SoMaterial()
        m.transparency.setValue(0.8)
        m.diffuseColor.setValue([0.4, 0.4, 0.6])
        w = coin.SoDrawStyle()
        w.style = coin.SoDrawStyle.LINES
        self.cube = coin.SoCube()
        self.cube.height.setValue(width)
        self.cube.depth.setValue(height)
        self.baseline = None
        if line:
            self.baseline = line
            self.update()
        if shaded:
            Tracker.__init__(
                self, children=[self.trans, m, self.cube], name="beamTracker"
            )
        else:
            Tracker.__init__(
                self, children=[self.trans, w, self.cube], name="beamTracker"
            )

    def update(
        self,
        inclination=0.0,
        anchor_idx=0,
        base_snap_vertex=None,
        final_snap_vertex=None,
    ):
        '''Update the tracker.'''

        import DraftGeomUtils

        if base_snap_vertex == None:
            base_snap_vertex = Vector(0.0, 0.0, 0.0)
        if final_snap_vertex == None:
            final_snap_vertex = Vector(1.0, 0.0, 0.0)
        
        bp = base_snap_vertex
        lvec = final_snap_vertex.sub(bp)

        self.cube.width.setValue(lvec.Length)

        inclination = inclination * -1

        p = App.Placement()  # objet Placement
        p.Base = bp  # base est coordonnée bp
        if lvec.x == 0 and lvec.y == 0:  # orientation verticale
            up = Vector(0, -1, 0)
            yaxis = up.cross(lvec)
            xaxis = lvec.cross(yaxis)
            if round(lvec.Length, 3) > 0:
                p.Rotation = App.Rotation(lvec, yaxis, xaxis, "ZXY")
                p.Rotation = App.Rotation(
                    p.Rotation.multVec(Vector(1, 0, 0)), inclination
                ).multiply(p.Rotation)
        else:
            up = Vector(0, 0, 1)  # vector up = Z
            yaxis = up.cross(lvec)  # yaxis = produit vectoriel entre Z et lvec
            xaxis = lvec.cross(yaxis)  # xaxis = produit vectoriel entre lvec et yaxis
            if round(lvec.Length, 3) > 0:
                #p.Rotation = App.Rotation(lvec, xaxis, yaxis, "ZXY")
                p.Rotation = App.Rotation(lvec, yaxis, xaxis, "ZXY")
                p.Rotation = App.Rotation(
                    p.Rotation.multVec(Vector(1, 0, 0)), inclination
                ).multiply(p.Rotation)

        self.setRotation(p.Rotation)
        delta = self.getDelta(anchor_idx)
        delta = p.Rotation.multVec(delta)
        delta = delta.add(lvec.multiply(0.5))
        bp = bp.add(delta)
        self.pos(bp)

    def getDelta(self, anchor):
        h = self.cube.height.getValue() / 2.0
        d = self.cube.depth.getValue() / 2.0
        o = 0.0
        deltas = [
            Vector(o, -h, d),
            Vector(o, o, d),
            Vector(o, h, d),
            Vector(o, -h, o),
            Vector(o, o, o),
            Vector(o, h, o),
            Vector(o, -h, -d),
            Vector(o, o, -d),
            Vector(o, h, -d),
        ]
        return deltas[anchor]

    def setRotation(self, rot):
        '''Set the rotation.'''
        self.trans.rotation.setValue(rot.Q)

    def pos(self, p):
        '''Set the translation.'''
        self.trans.translation.setValue(DraftVecUtils.tup(p))

    def width(self, w=None):
        '''Set the width.'''
        if w:
            self.cube.height.setValue(w)
        else:
            return self.cube.height.getValue()

    def length(self, l=None):
        '''Set the length.'''
        if l:
            self.cube.width.setValue(l)
        else:
            return self.cube.width.getValue()

    def height(self, h=None):
        '''Set the height.'''
        if h:
            self.cube.depth.setValue(h)
            self.update()
        else:
            return self.cube.depth.getValue()


class arrayBoxTracker(Tracker):
    """A tracker to show multiple box distributed along a line"""

    def __init__(self):
        self.trans = coin.SoTransform()
        w = coin.SoDrawStyle()
        w.style = coin.SoDrawStyle.LINES
        cube = coin.SoCube()
        self.array = coin.SoArray()
        self.array.addChild(cube)
        Tracker.__init__(
            self, children=[self.trans, w, self.array], name="arrayBoxTracker"
        )

    def update(self, qte=1, line=None, start=False, end=False):
        if qte == 1:
            # mettre la barre au milieu des 2 points
            pass
        if qte > 1:
            for i in range(qte):
                cube = coin.SoCube()
                self.array.addChild(cube)


class rectangleTracker(Tracker):
    """A Rectangle tracker, used by the rectangle tool"""

    def __init__(self, dotted=False, scolor=None, swidth=None, face=False):
        if DEBUG_T:
            App.Console.PrintMessage("rectangle tracker : __init__ \n")
        self.origin = Vector(0.0, 0.0, 0.0)
        line = coin.SoLineSet()
        line.numVertices.setValue(5)
        self.coords = coin.SoCoordinate3()  # this is the coordinate
        self.coords.point.setValues(
            0, 50, [[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0], [0, 0, 0]]
        )
        if face:
            m1 = coin.SoMaterial()
            m1.transparency.setValue(0.5)
            m1.diffuseColor.setValue([0.5, 0.5, 1.0])
            f = coin.SoIndexedFaceSet()
            f.coordIndex.setValues([0, 1, 2, 3])
            Tracker.__init__(
                self,
                dotted,
                scolor,
                swidth,
                [self.coords, line, m1, f],
                name="rectangleTracker",
            )
        else:
            Tracker.__init__(
                self,
                dotted,
                scolor,
                swidth,
                [self.coords, line],
                name="rectangleTracker",
            )
        self.u = App.DraftWorkingPlane.u
        self.v = App.DraftWorkingPlane.v

    def setorigin(self, point):
        """sets the base point of the rectangle"""
        if DEBUG_T:
            App.Console.PrintMessage("rectangle tracker : set origin \n")
        self.coords.point.set1Value(0, point.x, point.y, point.z)
        self.coords.point.set1Value(4, point.x, point.y, point.z)
        self.origin = point

    def update(self, point):
        """sets the opposite (diagonal) point of the rectangle"""
        if DEBUG_T:
            App.Console.PrintMessage("rectangle tracker : update \n")
        diagonal = point.sub(self.origin)
        inpoint1 = self.origin.add(DraftVecUtils.project(diagonal, self.v))
        inpoint2 = self.origin.add(DraftVecUtils.project(diagonal, self.u))
        self.coords.point.set1Value(1, inpoint1.x, inpoint1.y, inpoint1.z)
        self.coords.point.set1Value(2, point.x, point.y, point.z)
        self.coords.point.set1Value(3, inpoint2.x, inpoint2.y, inpoint2.z)

    def setPlane(self, u, v=None):
        """sets given (u,v) vectors as working plane. You can give only u
        and v will be deduced automatically given current workplane"""
        if DEBUG_T:
            App.Console.PrintMessage("rectangle tracker : set plane \n")
        self.u = u
        if v:
            self.v = v
        else:
            norm = App.DraftWorkingPlane.u.cross(App.DraftWorkingPlane.v)
            self.v = self.u.cross(norm)

    def p1(self, point=None):
        """sets or gets the base point of the rectangle"""
        if point:
            self.setorigin(point)
        else:
            return Vector(self.coords.point.getValues()[0].getValue())

    def p2(self):
        """gets the second point (on u axis) of the rectangle"""
        return Vector(self.coords.point.getValues()[3].getValue())

    def p3(self, point=None):
        """sets or gets the opposite (diagonal) point of the rectangle"""
        if point:
            self.update(point)
        else:
            return Vector(self.coords.point.getValues()[2].getValue())

    def p4(self):
        """gets the fourth point (on v axis) of the rectangle"""
        return Vector(self.coords.point.getValues()[1].getValue())

    def getSize(self):
        """returns (length,width) of the rectangle"""
        p1 = Vector(self.coords.point.getValues()[0].getValue())
        p2 = Vector(self.coords.point.getValues()[2].getValue())
        diag = p2.sub(p1)
        return (
            (DraftVecUtils.project(diag, self.u)).Length,
            (DraftVecUtils.project(diag, self.v)).Length,
        )

    def getNormal(self):
        """returns the normal of the rectangle"""
        return (self.u.cross(self.v)).normalize()

    def isInside(self, point):
        """returns True if the given point is inside the rectangle"""
        vp = point.sub(self.p1())
        uv = self.p2().sub(self.p1())
        vv = self.p4().sub(self.p1())
        uvp = DraftVecUtils.project(vp, uv)
        vvp = DraftVecUtils.project(vp, vv)
        if uvp.getAngle(uv) < 1:
            if vvp.getAngle(vv) < 1:
                if uvp.Length <= uv.Length:
                    if vvp.Length <= vv.Length:
                        return True
        return False
