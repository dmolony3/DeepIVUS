from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath
import numpy as np
from scipy.interpolate import splprep, splev

class Point(QGraphicsEllipseItem):
    """Class that describes a spline point"""

    def __init__(self, pos, color):
        super(Point, self).__init__()
        self.setZValue(3)

        if color =='y':
            self.defaultColor = QPen(Qt.yellow, 5)
        elif color =='r':
            self.defaultColor = QPen(Qt.red, 5)
        else:
            self.defaultColor = QPen(Qt.blue, 5)

        self.setPen(self.defaultColor)
        self.setRect(pos[0], pos[1], 3, 3)
		
    def select_point(self, pos):
        """Identifies what point has been selected with the mouse"""

        dist = np.sqrt((self.rect().x() - pos.x())**2 + (self.rect().y() - pos.y())**2)

        return dist

    def getPoint(self):
        return self.rect().x(), self.rect().y()
		
    def updateColor(self): 
        self.setPen(QPen(Qt.blue, 2))
        
    def resetColor(self):
        self.setPen(self.defaultColor)

    def update(self, pos):
        """Updates the Point position"""

        self.setRect(pos.x(), pos.y(), 3, 3)

        return self.rect()
		
class Spline(QGraphicsPathItem):
    """Class that describes a spline"""
    def __init__(self, points, color):
        self.setKnotPoints(points)
        self.setZValue(3)

        if color =='y':
            self.setPen(QPen(Qt.yellow, 2))
        elif color == "r":
            self.setPen(QPen(Qt.red, 2))
        else:
            self.setPen(QPen(Qt.blue, 2))
			
    def setKnotPoints(self, knotPoints):
        """KnotPoints is a list of points"""

        p1 = QPointF(knotPoints[0][0], knotPoints[1][0])
        self.path = QPainterPath(p1)
        super(Spline, self).__init__(self.path)

        self.points = self.interpolate(knotPoints)
        for i in range(0, len(self.points[0])):
            self.path.lineTo(self.points[0][i], self.points[1][i])

        self.setPath(self.path)
        self.path.closeSubpath()
        self.knotPoints = knotPoints

    def interpolate(self, pts):
        """Interpolates the spline points at 500 points along spline"""
        pts = np.array(pts)
        tck, u = splprep(pts, u=None, s=0.0, per=1)
        u_new = np.linspace(u.min(), u.max(), 500)
        x_new, y_new = splev(u_new, tck, der=0)

        return (x_new, y_new)
        
    def update(self, pos, idx):
        """Updates the stored spline everytime it is moved
        Args:
            pos: new points coordinates
            idx: index on spline of updated point
        """
        
        if idx == len(self.knotPoints[0]) + 1:
            self.knotPoints[0].append(pos.x())
            self.knotPoints[1].append(pos.y())
        else:
            self.knotPoints[0][idx] = pos.x()
            self.knotPoints[1][idx] = pos.y()
        self.points = self.interpolate(self.knotPoints)
        for i in range(0, len(self.points[0])):
            self.path.setElementPositionAt(i, self.points[0][i], self.points[1][i])
        self.setPath(self.path)
