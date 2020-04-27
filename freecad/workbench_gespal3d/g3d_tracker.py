__title__ = "FreeCAD Draft Trackers"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"


import FreeCAD
from draftguitools.gui_trackers import Tracker
import DraftVecUtils

# import DraftGeomUtils
# import WorkingPlane
from pivy import coin
from freecad.workbench_gespal3d import DEBUG
from freecad.workbench_gespal3d import DEBUG_T


if (DEBUG == True) and (DEBUG_T == True):
    DEBUG_T = True


class boxTracker(Tracker):
    """A box tracker, can be based on a line object"""

    def __init__(self, width=0.1, height=0.2, length=1.0, bp_idx=5, dev=0.0):
        self.trans = coin.SoTransform()
        w = coin.SoDrawStyle()
        w.style = coin.SoDrawStyle.LINES

        self.cube = coin.SoCube()
        self.cube.height.setValue(height)
        self.cube.width.setValue(width)
        self.cube.depth.setValue(length)
        self.bp_idx = bp_idx
        self.deversement = dev
        self.snap_bp = FreeCAD.Vector(0.0, 0.0, 0.0)

        Tracker.__init__(self, children=[self.trans, w, self.cube], name="boxTracker")

    def setRotation(self, rot):
        if DEBUG_T:
            msg = "tracker setRotation : %s \n" % rot
            FreeCAD.Console.PrintMessage(msg)
        self.trans.rotation.setValue(rot.Q)

    def setPosition(self, p):
        if DEBUG_T:
            msg = "tracker setPosition : %s \n" % p
            FreeCAD.Console.PrintMessage(msg)
        p = p.add(self.delta)
        self.trans.translation.setValue(DraftVecUtils.tup(p))

    def setPlacement(self, snap_bp, bp_idx, dev):
        if DEBUG_T:
            FreeCAD.Console.PrintMessage("tracker setPlacement \n")
            msg = "snap_bp : %s \n" % snap_bp
            FreeCAD.Console.PrintMessage(msg)
            msg = "bp_idx : %s \n" % bp_idx
            FreeCAD.Console.PrintMessage(msg)
            msg = "dev : %s \n" % dev
            FreeCAD.Console.PrintMessage(msg)
        w = self.width()
        h = self.height()
        d = self.length()
        if dev == 0.0:
            dev = 0
        else:
            dev = 1
        if snap_bp is None:
            snap_bp = self.snap_bp

        axis = FreeCAD.DraftWorkingPlane.axis

        # base point
        delta_list = [
            [
                FreeCAD.Vector(d / 2, h / 2, w / 2),
                FreeCAD.Vector(d / 2, 0, w / 2),
                FreeCAD.Vector(d / 2, -h / 2, w / 2),
                FreeCAD.Vector(d / 2, h / 2, 0),
                FreeCAD.Vector(d / 2, 0, 0),
                FreeCAD.Vector(d / 2, -h / 2, 0),
                FreeCAD.Vector(d / 2, h / 2, -w / 2),
                FreeCAD.Vector(d / 2, 0, -w / 2),
                FreeCAD.Vector(d / 2, -h / 2, -w / 2),
            ],
            [
                FreeCAD.Vector(d / 2, w / 2, h / 2),
                FreeCAD.Vector(d / 2, 0, h / 2),
                FreeCAD.Vector(d / 2, -w / 2, h / 2),
                FreeCAD.Vector(d / 2, w / 2, 0),
                FreeCAD.Vector(d / 2, 0, 0),
                FreeCAD.Vector(d / 2, -w / 2, 0),
                FreeCAD.Vector(d / 2, w / 2, -h / 2),
                FreeCAD.Vector(d / 2, 0, -h / 2),
                FreeCAD.Vector(d / 2, -w / 2, -h / 2),
            ],
            [
                FreeCAD.Vector(h / 2, d / 2, w / 2),
                FreeCAD.Vector(0, d / 2, w / 2),
                FreeCAD.Vector(-h / 2, d / 2, w / 2),
                FreeCAD.Vector(h / 2, d / 2, 0),
                FreeCAD.Vector(0, d / 2, 0),
                FreeCAD.Vector(-h / 2, d / 2, 0),
                FreeCAD.Vector(h / 2, d / 2, -w / 2),
                FreeCAD.Vector(0, d / 2, -w / 2),
                FreeCAD.Vector(-h / 2, d / 2, -w / 2),
            ],
            [
                FreeCAD.Vector(w / 2, d / 2, h / 2),
                FreeCAD.Vector(0, d / 2, h / 2),
                FreeCAD.Vector(-w / 2, d / 2, h / 2),
                FreeCAD.Vector(w / 2, d / 2, 0),
                FreeCAD.Vector(0, d / 2, 0),
                FreeCAD.Vector(-w / 2, d / 2, 0),
                FreeCAD.Vector(w / 2, d / 2, -h / 2),
                FreeCAD.Vector(0, d / 2, -h / 2),
                FreeCAD.Vector(-w / 2, d / 2, -h / 2),
            ],
            [
                FreeCAD.Vector(w / 2, h / 2, d / 2),
                FreeCAD.Vector(0, h / 2, d / 2),
                FreeCAD.Vector(-w / 2, h / 2, d / 2),
                FreeCAD.Vector(w / 2, 0, d / 2),
                FreeCAD.Vector(0, 0, d / 2),
                FreeCAD.Vector(-w / 2, 0, d / 2),
                FreeCAD.Vector(w / 2, -h / 2, d / 2),
                FreeCAD.Vector(0, -h / 2, d / 2),
                FreeCAD.Vector(-w / 2, -h / 2, d / 2),
            ],
            [
                FreeCAD.Vector(h / 2, w / 2, d / 2),
                FreeCAD.Vector(0, w / 2, d / 2),
                FreeCAD.Vector(-h / 2, w / 2, d / 2),
                FreeCAD.Vector(h / 2, 0, d / 2),
                FreeCAD.Vector(0, 0, d / 2),
                FreeCAD.Vector(-h / 2, 0, d / 2),
                FreeCAD.Vector(h / 2, -w / 2, d / 2),
                FreeCAD.Vector(0, -w / 2, d / 2),
                FreeCAD.Vector(-h / 2, -w / 2, d / 2),
            ],
        ]

        # manage direction
        if axis.x != 0.0:
            if dev == 0:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 90)
                self.setRotation(rot.Rotation)
                p = delta_list[0][bp_idx - 1]
                if axis.x == -1.0:
                    p.x = p.x * -1
                p = p.add(snap_bp)
            if dev == 1:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 90)
                self.setRotation(rot.Rotation)
                p = delta_list[1][bp_idx - 1]
                if axis.x == -1.0:
                    p.x = p.x * -1
                p = p.add(snap_bp)

        elif axis.y != 0:
            if dev == 0:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 90)
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 90)
                self.setRotation(rot.Rotation)
                p = delta_list[2][bp_idx - 1]
                if axis.y == -1.0:
                    p.y = p.y * -1
                p = p.add(snap_bp)
            if dev == 1:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
                self.setRotation(rot.Rotation)
                p = delta_list[3][bp_idx - 1]
                if axis.y == -1.0:
                    p.y = p.y * -1
                p = p.add(snap_bp)

        elif axis.z != 0:
            if dev == 0:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 0)
                self.setRotation(rot.Rotation)
                p = delta_list[4][bp_idx - 1]
                if axis.z == -1.0:
                    p.z = p.z * -1
                p = p.add(snap_bp)
            if dev == 1:
                rot = FreeCAD.Placement()
                rot.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 90)
                self.setRotation(rot.Rotation)
                p = delta_list[5][bp_idx - 1]
                if axis.z == -1.0:
                    p.z = p.z * -1
                p = p.add(snap_bp)

        self.delta = p
        self.snap_bp = snap_bp
        self.bp_idx = bp_idx
        self.deversement = dev
        self.setPosition(p)

    def width(self, w=None):
        if w:
            self.cube.width.setValue(w)
            self.setPlacement(
                snap_bp=self.snap_bp, bp_idx=self.bp_idx, dev=self.deversement
            )
        else:
            return self.cube.width.getValue()

    def length(self, vlength=None):
        if vlength:
            self.cube.depth.setValue(vlength)
            self.setPlacement(
                snap_bp=self.snap_bp, bp_idx=self.bp_idx, dev=self.deversement
            )
        else:
            return self.cube.depth.getValue()

    def height(self, h=None):
        if h:
            self.cube.height.setValue(h)
            self.setPlacement(
                snap_bp=self.snap_bp, bp_idx=self.bp_idx, dev=self.deversement
            )
        else:
            return self.cube.height.getValue()


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
            FreeCAD.Console.PrintMessage("rectangle tracker : __init__ \n")
        self.origin = FreeCAD.Vector(0.0, 0.0, 0.0)
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
        self.u = FreeCAD.DraftWorkingPlane.u
        self.v = FreeCAD.DraftWorkingPlane.v

    def setorigin(self, point):
        """sets the base point of the rectangle"""
        if DEBUG_T:
            FreeCAD.Console.PrintMessage("rectangle tracker : set origin \n")
        self.coords.point.set1Value(0, point.x, point.y, point.z)
        self.coords.point.set1Value(4, point.x, point.y, point.z)
        self.origin = point

    def update(self, point):
        """sets the opposite (diagonal) point of the rectangle"""
        if DEBUG_T:
            FreeCAD.Console.PrintMessage("rectangle tracker : update \n")
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
            FreeCAD.Console.PrintMessage("rectangle tracker : set plane \n")
        self.u = u
        if v:
            self.v = v
        else:
            norm = FreeCAD.DraftWorkingPlane.u.cross(FreeCAD.DraftWorkingPlane.v)
            self.v = self.u.cross(norm)

    def p1(self, point=None):
        """sets or gets the base point of the rectangle"""
        if point:
            self.setorigin(point)
        else:
            return FreeCAD.Vector(self.coords.point.getValues()[0].getValue())

    def p2(self):
        """gets the second point (on u axis) of the rectangle"""
        return FreeCAD.Vector(self.coords.point.getValues()[3].getValue())

    def p3(self, point=None):
        """sets or gets the opposite (diagonal) point of the rectangle"""
        if point:
            self.update(point)
        else:
            return FreeCAD.Vector(self.coords.point.getValues()[2].getValue())

    def p4(self):
        """gets the fourth point (on v axis) of the rectangle"""
        return FreeCAD.Vector(self.coords.point.getValues()[1].getValue())

    def getSize(self):
        """returns (length,width) of the rectangle"""
        p1 = FreeCAD.Vector(self.coords.point.getValues()[0].getValue())
        p2 = FreeCAD.Vector(self.coords.point.getValues()[2].getValue())
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
