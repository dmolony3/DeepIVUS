from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsLineItem
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QPainter, QPainterPath, QColor, QPolygonF
import numpy as np
from scipy.interpolate import splprep, splev

class Marker(QGraphicsLineItem):
    """Class that describes a line in the longitudinal view"""
    def __init__(self, pos, display_height, display_length, color=[173, 216, 230], dashed=False):
        super(Marker, self).__init__()
        self.setZValue(3)
        self.display_height = display_height
        self.display_length = display_length

        self.defaultColor = QPen(QColor(color[0], color[1], color[2]), 2)

        if dashed:
            self.defaultColor.setDashPattern([10,10,10])
        self.setLine(pos, 0, pos, self.display_height) 
        self.setPen(self.defaultColor)
        self.pos = self.display_length
        
    def update(self, pos):
        """Updates the Point position"""
        self.pos = pos
        # point must be constrained to bottom and top of scene 
        if pos < 0:
            pos = 0
        elif pos > self.display_length:
            pos = self.display_length
        self.setLine(pos, 0, pos, self.display_height)
        return pos
        
class Arrowhead(QGraphicsPathItem):
    def __init__(self, source: QPointF = None, direction: str = "left"):
        super(Arrowhead, self).__init__()

        self._sourcePoint = source
        self.defaultColor = QPen(QColor(255, 255, 255), 2)
        self.setPen(self.defaultColor)
        self.direction = direction
        #self.setZValue(3)

    def directPath(self):
        p1 = QPointF(self._sourcePoint.x(), self._sourcePoint.y() + 5.0)
        p2 = QPointF(self._sourcePoint.x(), self._sourcePoint.y() - 5.0)
        if self.direction == "right":
            p3 = QPointF(self._sourcePoint.x() + 5.0, self._sourcePoint.y())
        else:
            p3 = QPointF(self._sourcePoint.x() - 5.0, self._sourcePoint.y())
        
        path = QPainterPath(p1)
        path.lineTo(p2)
        path.lineTo(p3)
        path.closeSubpath()
        return path
        
    def draw(self):
        path = self.directPath()
        self.setPath(path)
        
class Arrowbody(QGraphicsPathItem):
    def __init__(self, source: QPointF = None, destination: QPointF = None, *args, **kwargs):
        super(Arrowbody, self).__init__(*args, **kwargs)

        self._sourcePoint = source
        self._destinationPoint = destination
        self.defaultColor = QPen(QColor(255, 255, 255), 2)
        self.setPen(self.defaultColor)
        #self.setZValue(3)

        self._arrow_height = 5
        self._arrow_width = 4

    def setSource(self, point: QPointF):
        self._sourcePoint = point

    def setDestination(self, point: QPointF):
        self._destinationPoint = point

    def directPath(self):
        path = QPainterPath(self._sourcePoint)
        path.lineTo(self._destinationPoint)
        return path

    def arrowCalc(self, start_point=None, end_point=None):  # calculates the point where the arrow should be drawn

        try:
            startPoint, endPoint = start_point, end_point

            if start_point is None:
                startPoint = self._sourcePoint

            if endPoint is None:
                endPoint = self._destinationPoint

            dx, dy = startPoint.x() - endPoint.x(), startPoint.y() - endPoint.y()

            leng = math.sqrt(dx ** 2 + dy ** 2)
            normX, normY = dx / leng, dy / leng  # normalize

            # perpendicular vector
            perpX = -normY
            perpY = normX

            leftX = endPoint.x() + self._arrow_height * normX + self._arrow_width * perpX
            leftY = endPoint.y() + self._arrow_height * normY + self._arrow_width * perpY

            rightX = endPoint.x() + self._arrow_height * normX - self._arrow_width * perpX
            rightY = endPoint.y() + self._arrow_height * normY - self._arrow_width * perpY

            point2 = QPointF(leftX, leftY)
            point3 = QPointF(rightX, rightY)

            return QPolygonF([point2, endPoint, point3])

        except (ZeroDivisionError, Exception):
            return None
            
    def draw(self):
    
        path = self.directPath()
        self.setPath(path)

    #def paint(self, painter: QPainter, option, widget=None) -> None:

    #    painter.setRenderHint(painter.Antialiasing)

    #    painter.pen().setWidth(2)
    #    painter.setBrush(Qt.NoBrush)

    #    path = self.directPath()
    #    painter.drawPath(path)
    #    self.setPath(path)

    #    triangle_source = self.arrowCalc(path.pointAtPercent(0.1), self._sourcePoint)  # change path.PointAtPercent() value to move arrow on the line

    #    if triangle_source is not None:
    #        painter.drawPolyline(triangle_source)
            
class Line(QGraphicsLineItem):
    """Class that describes a line in the cross-section view"""
    def __init__(self, pos, display_size):
        super(Line, self).__init__()
        self.setZValue(3)
        self.display_size = display_size
        image_radius = display_size//2

        self.defaultColor = QPen(QColor(173, 216, 230), 5)
        self.setLine(pos[0], pos[1], pos[2], pos[3]) 
        self.setPen(self.defaultColor)
        theta = np.linspace(0, 2*np.pi, 180)
        self.points = [[image_radius*np.cos(val) + image_radius, image_radius*np.sin(val) + image_radius] for val in theta]

    def update(self, pos):
        """Updates the Point position"""
        
        dist = [np.sqrt((pt[0] - pos.x())**2 + (pt[1] - pos.y())**2) for pt in self.points]
        idx = [i for i, val in enumerate(dist) if val == min(dist)]
        # point must be constrained to circular path
        new_x = self.points[idx[0]][0]
        new_y = self.points[idx[0]][1]
        if new_x > self.display_size//2:
            new_x1 = self.display_size - new_x
        else:
            new_x1 = self.display_size - new_x
        
        if new_y > self.display_size//2:
            new_y1 = self.display_size - new_y
        else:
            new_y1 = self.display_size - new_y
            
        self.setLine(new_x1, new_y1, new_x, new_y)
        return [new_x1, new_y1, new_x, new_y]

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
