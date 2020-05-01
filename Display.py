from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from Geometry import Point, Spline
import math

class Display(QGraphicsView):
    def __init__(self):
        super(Display, self).__init__()
        print("View Height: {}, View Width: {}".format(self.width(), self.height()))
        scene = QGraphicsScene(self)
        self.scene = scene
        self.pointIdx = None
        self.frame = 0
        self.lumen = ([], [])
        self.plaque = ([], [])
        self.hide = True
        self.enable_drag = True
        self.activePoint = None
        self.innerPoint = []
        self.outerPoint = []

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.image = QGraphicsPixmapItem(QPixmap(500, 500))
        self.scene.addItem(self.image)
        self.setScene(self.scene)

    def findItem(self, item, eventPos):
        min_dist = 10
        pos = item.mapFromScene(self.mapToScene(eventPos))
        dist = item.select_point(pos)
        if dist < min_dist:
            item.updateColor()
            self.enable_drag = True
            self.activePoint = item
        else:
            self.activePoint = None
            print("No active point")

    def mousePressEvent(self, event):
        super(Display, self).mousePressEvent(event)

        # identify which point has been clicked
        items = self.items(event.pos())
        for item in items:
            if item in self.innerPoint:
                # Convert mouse position to item position https://stackoverflow.com/questions/53627056/how-to-get-cursor-click-position-in-qgraphicsitem-coordinate-system
                self.pointIdx = [i for i, checkItem in enumerate(self.innerPoint) if item == checkItem][0]
                #print(self.pointIdx, 'Item found')
                self.activeContour = 1
                self.findItem(item, event.pos())
            elif item in self.outerPoint:
                self.pointIdx = [i for i, checkItem in enumerate(self.outerPoint) if item == checkItem][0]
                self.activeContour = 2
                self.findItem(item, event.pos())

    def mouseReleaseEvent(self, event):
        if self.pointIdx is not None:
            item = self.activePoint
            item.resetColor()
				
    def mouseMoveEvent(self, event):
        #self.setMouseTracking(True) # if this is disabled mouse tracking only occurs when a button is pressed
        if self.pointIdx is not None:
            item = self.activePoint
            pos = item.mapFromScene(self.mapToScene(event.pos()))
            newPos = item.update(pos)
            # update the spline
            if self.activeContour == 1:
                self.innerSpline.update(newPos, self.pointIdx)
            elif self.activeContour == 2:
                self.outerSpline.update(newPos, self.pointIdx)
            #self.disable_drag = False

    def setData(self, lumen, plaque, images):
        self.numberOfFrames = images.shape[0]
        #lumen, plaque = self.resizeContours(lumen, plaque, scale)
        self.lumen, self.plaque = self.downsample(lumen, plaque)
        self.images = images
        self.imsize = self.images.shape
        self.displayImage()
		
    def resizeContours(self, lumen, plaque, scale):
        """If image is not 500x500 resize the contours for appropriate display"""
        print('Scaling images by {} for display'.format(scale))
        lumen = self.resize(lumen, scale)
        plaque = self.resize(plaque, scale)
        return lumen, plaque

    def resize(self, contours, scale):
        for idx in range(len(contours[0])):
            if contours[0][idx]:
                contours[0][idx] = [int(val*scale) for val in contours[0][idx]]
        for idx in range(len(contours[1])):
            if contours[0][idx]:
                contours[1][idx] = [int(val*scale) for val in contours[1][idx]]
        return (contours[0], contours[1])

    def getData(self):
        """Returns the interpolated image contours"""
        lumenContour = [[], []]
        plaqueContour = [[], []]
        for frame in range(self.numberOfFrames):
            if self.lumen[0][frame]:
                lumen = Spline([self.lumen[0][frame], self.lumen[1][frame]], 'r')
                plaque = Spline([self.plaque[0][frame], self.plaque[1][frame]], 'y')
                lumenContour[0].append(list(lumen.points[0]))
                lumenContour[1].append(list(lumen.points[1]))
                plaqueContour[0].append(list(plaque.points[0]))
                plaqueContour[1].append(list(plaque.points[1]))
            else:
                lumenContour[0].append([])
                lumenContour[1].append([])
                plaqueContour[0].append([])
                plaqueContour[1].append([])                
        return lumenContour, plaqueContour

    def downsample(self, lumen, plaque, num_points=20):
        """Downsamples input contour data by selecting n points from original contour"""
        numberOfFrames = len(lumen[0])
        lumenDownsampled = [[] for idx in range(numberOfFrames)], [[] for idx in range(numberOfFrames)]
        plaqueDownsampled = [[] for idx in range(numberOfFrames)], [[] for idx in range(numberOfFrames)]
        for i in range(len(lumen[0])):
            if lumen[0][i]:
                idx = len(lumen[0][i])//num_points
                lumenDownsampled[0][i] = [pnt for j, pnt in enumerate(lumen[0][i]) if j % idx == 0]
                lumenDownsampled[1][i] = [pnt for j, pnt in enumerate(lumen[1][i]) if j % idx == 0]
            if plaque[0][i]:
                idx = len(plaque[0][i])//num_points
                plaqueDownsampled[0][i] = [pnt for j, pnt in enumerate(plaque[0][i]) if j % idx == 0]
                plaqueDownsampled[1][i] = [pnt for j, pnt in enumerate(plaque[1][i]) if j % idx == 0]
        return lumenDownsampled, plaqueDownsampled

    def cart2pol(self, lumen):
        """Converts points from cartesian to polar"""
        center = [sum(lumen[0])/len(lumen[0]), sum(lumen[1])/len(lumen[1])]
        lumen = [[pnt - center[0] for pnt in lumen[0]], [pnt - center[1] for pnt in lumen[1]]]
        #r = [math.sqrt(lumen[0][i]**2 + lumen[1][i]**2) for i in range(len(lumen[0]))]
        theta = [math.atan2(lumen[1][i], lumen[0][i]) + math.pi for i in range(len(lumen[0]))]
        return theta

    def displayImage(self):
        self.scene.clear()
        self.viewport().update()
        [self.removeItem(item) for item in self.scene.items()]
        self.activePoint = None
        self.pointIdx = None
        if len(self.images.shape) == 3:
            self.image=QImage(self.images[self.frame, : ,:], self.imsize[1], self.imsize[2], QImage.Format_Grayscale8)
        else:
            bytesPerLine = 3*self.imsize[2]
            current_image = self.images[self.frame, : ,:, :].astype(np.uint8, order='C', casting='unsafe')
            self.image=QImage(current_image.data, self.imsize[1], self.imsize[2], bytesPerLine, QImage.Format_RGB888) 
        image = QPixmap.fromImage(self.image)
        self.image = QGraphicsPixmapItem(image)
        self.scene.addItem(self.image)
        if self.hide == False:
            if self.lumen[0]:
                if self.lumen[0][self.frame]:
                    self.addInteractiveSplines(self.lumen, self.plaque)
        self.setScene(self.scene)
        
    def addInteractiveSplines(self, lumen, plaque):
        self.innerSpline = Spline([lumen[0][self.frame], lumen[1][self.frame]], 'r')
        self.outerSpline = Spline([plaque[0][self.frame], plaque[1][self.frame]], 'y')
        self.innerPoint = [Point((self.innerSpline.knotPoints[0][idx], self.innerSpline.knotPoints[1][idx]), 'r') for idx in range(len(self.innerSpline.knotPoints[0])-1)]
        self.outerPoint = [Point((self.outerSpline.knotPoints[0][idx], self.outerSpline.knotPoints[1][idx]), 'y') for idx in range(len(self.outerSpline.knotPoints[0])-1)] # IMPORTANT TO NOT INCLUDE LAST COPIED KNOT POINT DUE TO PERIODICITY
        [self.scene.addItem(point) for point in self.innerPoint]        
        [self.scene.addItem(point) for point in self.outerPoint]        
        self.scene.addItem(self.innerSpline)
        self.scene.addItem(self.outerSpline)

    def run(self): 
        self.displayImage()
		
    def setFrame(self, value):
        self.frame = value

    def setDisplay(self, hide):
        self.hide = hide
