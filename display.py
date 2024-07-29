from geometry import Point, Spline, Line, Marker, Arrowbody, Arrowhead
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsLineItem, QHBoxLayout, QWidget, QFrame
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QPoint, QLineF
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor, QFont, QPainter, QPainterPath
import math
import numpy as np
from PIL import ImageDraw, Image

class LesionView(QGraphicsView):
    """Displays graphical lesion analysis in the longitudinal view.

    """
    updateFrameFromLesionViewSignal = pyqtSignal(int)
    def __init__(self):
        super(LesionView, self).__init__()
        print("View Height: {}, View Width: {}".format(self.width(), self.height()))
        self.lview_length = 1600
        self.lview_height = 200
        self.numberOfFrames = 0
        self.setFrameStyle(QFrame.NoFrame)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalScrollBar().hide()
        
        self.pos = self.lview_length
        self.marker = None
        self.mla_maker = None
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(Qt.black)

        self.setScene(self.scene)
        
    def createPolygon(self, lview_lumenY, lview_plaqueY, lview_lumen, lview_plaque):
        """Updates the lview"""
        print('poly', len(lview_lumenY), len(lview_lumen))
        lview_lumen1, lview_lumen2 = [], []
        lview_plaque1, lview_plaque2 = [], []
        lview_lumenY1, lview_plaqueY1 = [], []
        for i in range(len(lview_lumen)):
            if lview_lumen[i] is not None:
                lview_lumen1.append(self.lview_height//2 - lview_lumen[i]*(self.lview_height//2))
                lview_lumen2.append(self.lview_height//2 + lview_lumen[i]*(self.lview_height//2))
                lview_lumenY1.append(lview_lumenY[i])
                
        for i in range(len(lview_plaque)):
            if lview_plaque[i] is not None:
                lview_plaque1.append(self.lview_height//2 - lview_plaque[i]*(self.lview_height//2))
                lview_plaque2.append(self.lview_height//2 + lview_plaque[i]*(self.lview_height//2))
                lview_plaqueY1.append(lview_plaqueY[i])

        lumen_polygon = []
        plaque_polygon = []
        for i in range(len(lview_lumen1)):
            lumen_polygon.append((int(lview_lumen1[i]), int(lview_lumenY1[i])))
            
        for i in reversed(range(len(lview_lumen2))):
            lumen_polygon.append((int(lview_lumen2[i]), int(lview_lumenY1[i])))
            
        for i in range(len(lview_plaque1)):
            plaque_polygon.append((int(lview_plaque1[i]), int(lview_plaqueY1[i])))
            
        for i in reversed(range(len(lview_plaque2))):
            plaque_polygon.append((int(lview_plaque2[i]), int(lview_plaqueY1[i])))
            
        self.lview_lumenY = lview_lumenY
        self.lview_plaqueY = lview_plaqueY
        return lumen_polygon, plaque_polygon
        
    
    def createImage(self, lview_lumenY, lview_plaqueY, lview_lumen, lview_plaque):
        """creates a cartoon image of lumen area"""
        lumen_polygon, plaque_polygon = self.createPolygon(lview_lumenY, lview_plaqueY, lview_lumen, lview_plaque)
        print(lumen_polygon)
        print(plaque_polygon)
        
        # L is grayscale
        image = Image.new('RGB', (self.lview_height, self.lview_length), (128, 128, 128)) #gray

        ImageDraw.Draw(image).polygon(plaque_polygon, outline=1, fill=255)
        ImageDraw.Draw(image).polygon(lumen_polygon, outline=1, fill=1)
        image = np.transpose(np.array(image), [1, 0, 2]).copy()

        return image
        
    def createLesion(self, lesion_info):
        """creates an overlay image that colors lesions"""
        num_lesions = len(lesion_info)
        opacity = 25
        
        lesion = np.zeros((self.imsize[0], self.imsize[1], 4), dtype=np.uint8)
        for i in range(num_lesions):
            idx = [frame / self.numberOfFrames * self.lview_length for frame in lesion_info[i]['idx']]
            lesion[:, int(round(idx[0])):int(round(idx[-1]))] = [255, 0, 0, opacity]

        bytesPerLine = 4*self.imsize[1]
        
        image = QImage(lesion.data, lesion.shape[1], lesion.shape[0], bytesPerLine, QImage.Format_RGBA8888).scaled(self.lview_length, self.lview_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 
        pixmap = QPixmap.fromImage(image)
        self.pixmap = self.scene.addPixmap(pixmap)           
       
    def createArrow(self, lesion_start, lesion_end, lesion_mid, direction="left"):
        
        if direction == "left":
            source = QPointF(lesion_start + 5, self.lview_height//2)
            destination = QPointF(lesion_mid - 50, self.lview_height//2)
            head = Arrowhead(source, direction)
        elif direction == "right":
            source = QPointF(lesion_mid + 50, self.lview_height//2)
            destination = QPointF(lesion_end - 5, self.lview_height//2)
            head = Arrowhead(destination, direction)

        head.draw()
        self.scene.addItem(head)
        
        self.body = Arrowbody(source, destination)
        self.body.draw()
        self.scene.addItem(self.body)
            
    def createScene(self, lview_lumenY, lview_plaqueY, lview_lumen, lview_plaque, lesion_info, lview_length):
        # create marker for display current cross section in lview mode
        num_frames = len(lview_lumenY)
        self.lview_length = lview_length
        fill = (0, 0, 0)
        self.scene.clear()
        [self.removeItem(item) for item in self.scene.items()]
        
        image = self.createImage(lview_lumenY, lview_plaqueY, lview_lumen, lview_plaque)
        self.imsize = image.shape
        
        bytesPerLine = 3*self.imsize[1]

        image = QImage(image.data, image.shape[1], image.shape[0], bytesPerLine, QImage.Format_RGB888).scaled(self.lview_length, self.lview_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 
        pixmap = QPixmap.fromImage(image)
        self.pixmap = self.scene.addPixmap(pixmap)        

        self.marker = Marker(self.pos, self.lview_height, self.lview_length)
        self.scene.addItem(self.marker)

        num_lesions = len(lesion_info)

        for i in range(num_lesions):
            lesion_mla = lesion_info[i]['MLA idx']/self.numberOfFrames * self.lview_length
            lesion_mpb = lesion_info[i]['MPB idx']/self.numberOfFrames * self.lview_length
            lesion_start = lesion_info[i]['idx'][0]/self.numberOfFrames * self.lview_length
            lesion_end = lesion_info[i]['idx'][-1]/self.numberOfFrames * self.lview_length
            lesion_mid = lesion_start + (lesion_end - lesion_start)/2

            if lesion_mla < 40:
                lesion_mla = lesion_mla + 40
            elif lesion_mla > self.lview_length - 90:
                lesion_mla = lesion_mla - 90
            
            if lesion_mpb < 40:
                lesion_mpb = lesion_mpb + 40
            elif lesion_mpb > self.lview_length - 90:
                lesion_mpb = lesion_mpb - 90
                
            self.mla_marker = Marker(lesion_mla, self.lview_height, self.lview_length, [255,255,0], dashed=True)
            self.scene.addItem(self.mla_marker)

            #textArea = self.scene.addText(f"{lesion_info[i]['MLA']:.2f}mm\u00b2")
            textArea = self.scene.addText('MLA')
            textArea.setPos(lesion_mla, self.lview_height//2)
            textArea.setDefaultTextColor(QColor(255, 255, 0))
            textArea.setFont(QFont('Roboto'))
  
            self.mpb_marker = Marker(lesion_mpb, self.lview_height, self.lview_length, [255,255,0], dashed=True)
            self.scene.addItem(self.mpb_marker)

            textArea = self.scene.addText("MPB")
            textArea.setPos(lesion_mpb, self.lview_height//2)
            textArea.setDefaultTextColor(QColor(255, 255, 0))
            textArea.setFont(QFont('Roboto'))
            
            self.createArrow(lesion_start, lesion_end, lesion_mid, direction="left")
            self.createArrow(lesion_start, lesion_end, lesion_mid, direction="right")
            
            textLength = self.scene.addText(f"{lesion_info[i]['length']:.1f}mm")
            if lesion_info[i]['length'] < 10:
                textLength.setPos(lesion_mid - 45, self.lview_height//2 + 20)
            else:    
                textLength.setPos(lesion_mid - 45, self.lview_height//2 - 20)
            textLength.setDefaultTextColor(QColor(255, 255, 255))
            font = QFont('Roboto')
            font.setBold(True)
            textLength.setFont(font)
            
        self.createLesion(lesion_info)

    def setNumberOfFrames(self, numberOfFrames):
        self.numberOfFrames = numberOfFrames
                
    def updateMarker(self, pos):
        if self.marker is None:
            return
        self.pos = pos/self.numberOfFrames*self.lview_length
        self.marker.update(self.pos)
        
    def mousePressEvent(self, event):
        super(LesionView, self).mousePressEvent(event)
        pos = self.mapToScene(event.pos())
        
        if self.marker is None:
            return
        
        mla_dist = pos.x() - self.mla_marker.line().x1()
        mpd_dist = pos.x() - self.mpb_marker.line().x1()
        if abs(mla_dist) < 5:
            frame = round(self.mla_marker.line().x1()/self.lview_length * self.numberOfFrames)
            self.updateFrameFromLesionViewSignal.emit(frame)
        elif abs(mpd_dist) < 5:
            frame = round(self.mpb_marker.line().x1()/self.lview_length * self.numberOfFrames)
            self.updateFrameFromLesionViewSignal.emit(frame)        

class LView(QGraphicsView):
    """Displays images and contours in the longitudinal view.

    Displays images and contours as well as allowing user to 
    interact and manipulate contours. 

    Attributes:
        scene: QGraphicsScene, all items
    """
    markerChangedSignal = pyqtSignal(float)
    markerChangedKeySignal = pyqtSignal(object)
    def __init__(self, displayTopSize):
        super(LView, self).__init__()
        print("View Height: {}, View Width: {}".format(self.width(), self.height()))

        self.lview_length = 1600
        self.lview_height = 400
        self.displayTopSize = displayTopSize
        
        self.setFrameStyle(QFrame.NoFrame)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.marker = None
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(Qt.black)

        self.setScene(self.scene)
        
    def createScene(self, lview_array):
        # create marker for display current cross section in lview mode
        self.scene.clear()
        
        bytesPerLine = lview_array.shape[1]*1
        image = QImage(lview_array.data, lview_array.shape[1], lview_array.shape[0], bytesPerLine, QImage.Format_Grayscale8).scaled(self.lview_length, self.lview_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 
        pixmap = QPixmap.fromImage(image)
        lview_image = QGraphicsPixmapItem(pixmap)
        self.pixmap = self.scene.addPixmap(pixmap) 

        self.marker = Marker(self.lview_length, self.lview_height, self.lview_length)
        self.scene.addItem(self.marker)

        
    def keyPressEvent(self, event):
        """Key events."""
        self.markerChangedKeySignal.emit(event)

    def mousePressEvent(self, event):
        super(LView, self).mousePressEvent(event)

        if not self.marker:
            return
            
        pos = self.mapToScene(event.pos())
        
        dist = pos.x() - self.marker.line().x1()

        #dist = np.sqrt((pos.x() - self.marker.line().x1())**2 + (pos.y() - self.marker.line().y1())**2)
        if abs(dist) < 15:
            self.enable_drag = True
        else:
            self.enable_drag = False
  
    def mouseMoveEvent(self, event):
        if self.enable_drag:
            pos = self.marker.mapFromScene(self.mapToScene(event.pos()))
            
            newPos = self.marker.update(pos.x())
            self.markerChangedSignal.emit(newPos/self.lview_length)
 
    def createLViewContours(self, lview_lumenY, lview_plaqueY, lview_lumen1, lview_lumen2, lview_plaque1, lview_plaque2):
        """Updates the lview"""
        self.lview_lumenY = lview_lumenY
        self.lview_plaqueY = lview_plaqueY
        
        self.lview_lumen1 = lview_lumen1
        self.lview_lumen2 = lview_lumen2
        self.lview_plaque1 = lview_plaque1
        self.lview_plaque2 = lview_plaque2

        self.pathLumenItem1 = QGraphicsPathItem()
        self.pathLumenItem1.setPen(QPen(Qt.red, 2))
        self.pathLumenItem2 = QGraphicsPathItem()
        self.pathLumenItem2.setPen(QPen(Qt.red, 2))

        if self.lview_lumen1:
            first_idx = min([i for i in range(len(self.lview_lumen1)) if self.lview_lumen1[i] is not None])            
            l1 = QPointF(self.lview_lumenY[first_idx], self.lview_lumen1[first_idx])
            l2 = QPointF(self.lview_lumenY[first_idx], self.lview_lumen2[first_idx])
            pathLumen1 = QPainterPath(l1)
            pathLumen2 = QPainterPath(l2)
            for i in range(first_idx, len(self.lview_lumen1)):
                #path1.lineTo(self.lviewX1[i], self.lviewY[i])
                if self.lview_lumen1[i] is None:
                    continue
                pathLumen1.lineTo(self.lview_lumenY[i], self.lview_lumen1[i])
                pathLumen2.lineTo(self.lview_lumenY[i], self.lview_lumen2[i])
                print("LLL", pathLumen1.currentPosition().x(), pathLumen1.currentPosition().y())
            self.pathLumenItem1.setPath(pathLumen1)
            self.pathLumenItem2.setPath(pathLumen2)
        self.scene.addItem(self.pathLumenItem1)
        self.scene.addItem(self.pathLumenItem2)

        # create path for vessel
        self.pathVesselItem1 = QGraphicsPathItem()
        self.pathVesselItem1.setPen(QPen(Qt.yellow, 2))
        self.pathVesselItem2 = QGraphicsPathItem()
        self.pathVesselItem2.setPen(QPen(Qt.yellow, 2))

        if self.lview_plaque1:
            first_idx = min([i for i in range(len(self.lview_plaque1)) if self.lview_plaque1[i] is not None])
            v1 = QPointF(self.lview_plaqueY[first_idx], self.lview_plaque1[first_idx])
            v2 = QPointF(self.lview_plaqueY[first_idx], self.lview_plaque2[first_idx])
            pathVessel1 = QPainterPath(v1)
            pathVessel2 = QPainterPath(v2)
            print('fffff', len(self.lview_plaqueY), self.lview_plaqueY[0], len(self.lview_plaque1))
            for i in range(first_idx, len(self.lview_plaque1)):
                    #path1.lineTo(self.lviewX1[i], self.lviewY[i])
                if self.lview_plaque1[i] is None:
                    continue
                pathVessel1.lineTo(self.lview_plaqueY[i], self.lview_plaque1[i])
                pathVessel2.lineTo(self.lview_plaqueY[i], self.lview_plaque2[i])
            self.pathVesselItem1.setPath(pathVessel1)
            self.pathVesselItem2.setPath(pathVessel2)
            self.scene.addItem(self.pathVesselItem1)
            self.scene.addItem(self.pathVesselItem2)               
            
    def updateImage(self, lview_array):
        bytesPerLine = lview_array.shape[1]*1
        image = QImage(lview_array.data, lview_array.shape[1], lview_array.shape[0], bytesPerLine, QImage.Format_Grayscale8).scaled(self.lview_length, self.lview_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 
        pixmap = QPixmap.fromImage(image)
        self.pixmap.setPixmap(pixmap)
        
    def updateMarker(self, pos):
        self.marker.setLine(pos, 0, pos, self.lview_height)
        
    def updateLViewContours(self, lview_lumenY, lview_plaqueY, lview_lumen1, lview_lumen2, lview_plaque1, lview_plaque2):

        self.lview_lumenY = lview_lumenY
        self.lview_plaqueY = lview_plaqueY

        self.lview_lumen1 = lview_lumen1
        self.lview_lumen2 = lview_lumen2
        self.lview_plaque1 = lview_plaque1
        self.lview_plaque2 = lview_plaque2

        #pathLumen1 = self.scene.pathLumenItem1.path()
        #pathLumen2 = self.pathLumenItem2.path()
        pathLumen1 = self.pathLumenItem1.path()
        pathLumen2 = self.pathLumenItem2.path()
        
        pathVessel1 = self.pathVesselItem1.path()
        pathVessel2 = self.pathVesselItem2.path()

        idx = 0
        print(len(self.lview_lumenY), len(self.lview_lumen1), pathLumen1.elementCount())
        for i in range(len(self.lview_lumen1)):
            if self.lview_lumen1[i] is None:
                continue
            print(i, idx, 'l', pathLumen1.elementAt(idx).x, 'l',pathLumen1.elementAt(idx).y)
            pathLumen1.setElementPositionAt(idx, self.lview_lumenY[i], self.lview_lumen1[i])
            pathLumen2.setElementPositionAt(idx, self.lview_lumenY[i], self.lview_lumen2[i])
            print(i, idx, 'l', lview_lumenY[i], pathLumen1.elementAt(idx).x, 'l',pathLumen1.elementAt(idx).y)
            idx += 1
        self.pathLumenItem1.setPath(pathLumen1)        
        self.pathLumenItem2.setPath(pathLumen2)  

        idx = 0
        print(len(self.lview_plaqueY), len(self.lview_plaque1), pathVessel1.elementCount())
        for i in range(len(self.lview_plaque1)):
            if self.lview_plaque1[i] is None:
                continue
            print(i, idx ,'p',pathVessel1.elementAt(idx).x, 'p',pathVessel1.elementAt(idx).y)
            pathVessel1.setElementPositionAt(idx, self.lview_plaqueY[i], self.lview_plaque1[i])
            pathVessel2.setElementPositionAt(idx, self.lview_plaqueY[i], self.lview_plaque2[i])
            idx += 1
        self.pathVesselItem1.setPath(pathVessel1)        
        self.pathVesselItem2.setPath(pathVessel2)  

                    
class Display(QGraphicsView):
    """Displays images and contours.

    Displays images and contours as well as allowing user to 
    interact and manipulate contours. 

    Attributes:
        scene: QGraphicsScene, all items
        frame: int, current frame
        lumen: tuple, lumen contours
        plaque: tuple: plaque contours
        hide: bool, indicates whether contours should be displayed or hidden
        activePoint: Point, active point in spline
        innerPoint: list, spline points for inner (lumen) contours
        outerPoint: list, spline points for outer (plaque) contours
    """
    lviewChangedSignal = pyqtSignal(int, int, int, int)
    frameChangedKeySignal = pyqtSignal(object)
    contourUpdatedSignal = pyqtSignal(bool)
    def __init__(self):
        super(Display, self).__init__()
        print("View Height: {}, View Width: {}".format(self.width(), self.height()))

        scene = QGraphicsScene(self)

        self.scene = scene
        self.pointIdx = None
        self.frame = 0
        self.lumen = ([], [])
        self.plaque = ([], [])
        self.stent = ([], [])
        self.hide = True
        self.draw = False
        self.drawPoints = []
        self.edit_selection = None
        self.splineDrawn = False
        self.newSpline = None
        self.enable_drag = True
        self.activePoint = None
        self.activeContour = 0
        self.innerPoint = []
        self.outerPoint = []
        self.display_size = 800
        self.allow_update = False

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.crossCoords = [0, 400, 800, 400] 
        self.cross = Line(self.crossCoords, self.display_size)
        self.scene.addItem(self.cross)

        self.image = QGraphicsPixmapItem(QPixmap(self.display_size, self.display_size))
        self.scene.addItem(self.image)
        self.setScene(self.scene)

    def findItem(self, item, eventPos):
        """Sets the active point for interaction"""

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

    def keyPressEvent(self, event):
        """Key events."""
        self.frameChangedKeySignal.emit(event)

    def mousePressEvent(self, event):
        super(Display, self).mousePressEvent(event)

        if self.draw:
            pos = self.mapToScene(event.pos())
            self.addManualSpline(pos)
        else:
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
                elif item == self.cross:
                    clickedPoint = self.mapToScene(event.pos())
                    dist = [np.sqrt((clickedPoint.x() - self.crossCoords[0])**2 +
                            (clickedPoint.y() - self.crossCoords[1])**2),
                            np.sqrt((clickedPoint.x() - self.crossCoords[2])**2 +
                            (clickedPoint.y() - self.crossCoords[3])**2)]

                    if min(dist) < 10:
                        self.allow_update = True
                    else:
                        self.allow_update = False

                    self.activeContour = 3
                    self.activePoint = item
                    
    def mouseReleaseEvent(self, event):
        print(f"Active item is {self.activeContour}")
        if self.pointIdx is not None and self.activeContour != 3 and self.activeContour != 0:
            contour_scaling_factor = self.display_size/self.imsize[1]
            item = self.activePoint
            item.resetColor()

            if self.activeContour == 1:
                self.lumen[0][self.frame] = [val/contour_scaling_factor for val in self.innerSpline.knotPoints[0]]
                self.lumen[1][self.frame] = [val/contour_scaling_factor for val in self.innerSpline.knotPoints[1]]
            elif self.activeContour == 2:
                self.plaque[0][self.frame] = [val/contour_scaling_factor for val in self.outerSpline.knotPoints[0]]  
                self.plaque[1][self.frame] = [val/contour_scaling_factor for val in self.outerSpline.knotPoints[1]]
            self.pointIdx = None
            self.contourUpdatedSignal.emit(True)
        if self.activeContour == 3:
            self.lviewChangedSignal.emit(self.crossCoords[0], self.crossCoords[1], self.crossCoords[2], self.crossCoords[3])
            self.activeContour = 0
            
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
        elif  self.activeContour == 3:
            if self.allow_update:
                item = self.activePoint
                pos = item.mapFromScene(self.mapToScene(event.pos()))
                newPos = item.update(pos)
                self.crossCoords = newPos
                #self.cross.setLine(0, 400, 800, 400)                 
                self.lviewChangedSignal.emit(self.crossCoords[0], self.crossCoords[1], self.crossCoords[2], self.crossCoords[3])


    def setData(self, lumen, plaque, stent, images):
        self.numberOfFrames = images.shape[0]
        #lumen, plaque = self.resizeContours(lumen, plaque, scale)
        self.lumen = self.downsample(lumen)
        self.plaque = self.downsample(plaque)
        self.stent = self.downsample(stent)
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
        """Gets the interpolated image contours

        Returns:
            lumenContour: list, first and second lists are lists of x and y points
            plaqueContour: list, first and second lists are lists of x and y points
        """

        lumenContour = [[], []]
        plaqueContour = [[], []]

        for frame in range(self.numberOfFrames):
            if self.lumen[0][frame]:
                lumen = Spline([self.lumen[0][frame], self.lumen[1][frame]], 'r')
                lumenContour[0].append(list(lumen.points[0]))
                lumenContour[1].append(list(lumen.points[1]))
            else:
                lumenContour[0].append([])
                lumenContour[1].append([])
            if self.plaque[0][frame]:
                plaque = Spline([self.plaque[0][frame], self.plaque[1][frame]], 'y')
                plaqueContour[0].append(list(plaque.points[0]))
                plaqueContour[1].append(list(plaque.points[1]))
            else:
                plaqueContour[0].append([])
                plaqueContour[1].append([]) 
                
        return lumenContour, plaqueContour


    def downsample(self, contours, num_points=20):
        """Downsamples input contour data by selecting n points from original contour"""

        numberOfFrames = len(contours[0])

        downsampled = [[] for idx in range(numberOfFrames)], [[] for idx in range(numberOfFrames)]

        for i in range(numberOfFrames):
            if contours[0][i]:
                idx = len(contours[0][i])//num_points
                downsampled[0][i] = [pnt for j, pnt in enumerate(contours[0][i]) if j % idx == 0]
                downsampled[1][i] = [pnt for j, pnt in enumerate(contours[1][i]) if j % idx == 0]

        return downsampled

    def displayImage(self):
        """Clears scene and displays current image and splines"""

        self.scene.clear()
        self.viewport().update()

        [self.removeItem(item) for item in self.scene.items()]

        self.activePoint = None
        self.pointIdx = None

        if len(self.images.shape) == 3:
            current_image = self.images[self.frame, : ,:]
            self.image=QImage(current_image, self.imsize[1], self.imsize[2], QImage.Format_Grayscale8).scaled(self.display_size, self.display_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            bytesPerLine = 3*self.imsize[2]
            current_image = self.images[self.frame, : ,:, :].astype(np.uint8, order='C', casting='unsafe')
            self.image=QImage(current_image.data, self.imsize[1], self.imsize[2], bytesPerLine, QImage.Format_RGB888).scaled(self.display_size, self.display_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 

        image = QPixmap.fromImage(self.image)
        self.image = QGraphicsPixmapItem(image)
        self.image.setZValue(1)
        self.scene.addItem(self.image)
        
        self.cross = Line(self.crossCoords, self.display_size)
        self.scene.addItem(self.cross)

        # create transparent image (opacity set in 4th channel)
        # calcium - white, hypoechogenic - red, hyperechogenic - greeen, other - gray
        mask = (current_image > 200).astype(int)
        mask = np.stack([mask, mask, mask, mask],2)
        idx = np.nonzero(mask)
        idx = idx[:2]

        opacity = 50
        
        plaque = np.zeros((self.imsize[1], self.imsize[2], 4), dtype=np.uint8)
        plaque[idx[0], idx[1]] = [255, 255, 255, opacity]
        plaque[:, :, 3] = opacity
        plaque[230:250, 230:250, :] = [255, 0, 0, opacity] #red
        plaque[250:280, 250:280, :] = [0, 255, 0, opacity] #green

        self.echo_image = QImage(plaque.data, self.imsize[1], self.imsize[2], 4*self.imsize[2], QImage.Format_RGBA8888).scaled(self.display_size, self.display_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) 
        pixmap = QPixmap.fromImage(self.echo_image)
        self.echoMap = QGraphicsPixmapItem(pixmap)
        self.echoMap.setZValue(2)
        #self.scene.addItem(self.echoMap)

        if not self.hide:
            if self.lumen[0] or self.plaque[0] or self.stent[0]:
                self.addInteractiveSplines(self.lumen, self.plaque, self.stent)

        self.setScene(self.scene)
        
    def addInteractiveSplines(self, lumen, plaque, stent):
        """Adds inner and outer splines to scene"""

        contour_scaling_factor = self.display_size/self.imsize[1]
        if lumen[0][self.frame]:
            lumen_x = [val*contour_scaling_factor for val in lumen[0][self.frame]]
            lumen_y = [val*contour_scaling_factor for val in lumen[1][self.frame]]
            self.innerSpline = Spline([lumen_x, lumen_y], 'r')
            self.innerPoint = [Point((self.innerSpline.knotPoints[0][idx], self.innerSpline.knotPoints[1][idx]), 'r') for idx in range(len(self.innerSpline.knotPoints[0])-1)]
            [self.scene.addItem(point) for point in self.innerPoint]        
            self.scene.addItem(self.innerSpline)

        if plaque[0][self.frame]:
            plaque_x = [val*contour_scaling_factor for val in plaque[0][self.frame]]
            plaque_y = [val*contour_scaling_factor for val in plaque[1][self.frame]]
            self.outerSpline = Spline([plaque_x, plaque_y], 'y')
            self.outerPoint = [Point((self.outerSpline.knotPoints[0][idx], self.outerSpline.knotPoints[1][idx]), 'y') for idx in range(len(self.outerSpline.knotPoints[0])-1)] # IMPORTANT TO NOT INCLUDE LAST COPIED KNOT POINT DUE TO PERIODICITY
            [self.scene.addItem(point) for point in self.outerPoint] 
            self.scene.addItem(self.outerSpline)

    def addManualSpline(self, point):
        """Creates an interactive spline manually point by point"""

        if not self.drawPoints:
            self.splineDrawn = False

        self.drawPoints.append(Point((point.x(), point.y()), 'b'))
        self.scene.addItem(self.drawPoints[-1])

        if len(self.drawPoints) > 3:
            if not self.splineDrawn:
                self.newSpline = Spline([[point.getPoint()[0] for point in self.drawPoints], [point.getPoint()[1] for point in self.drawPoints]], 'c')
                self.scene.addItem(self.newSpline)
                self.splineDrawn = True
            else:
                self.newSpline.update(point, len(self.drawPoints))

        if len(self.drawPoints) > 1:
            dist = math.sqrt((point.x() - self.drawPoints[0].getPoint()[0])**2 + (point.y() - self.drawPoints[0].getPoint()[1])**2)

            if dist < 10:
                self.draw = False
                self.drawPoints = []
                downsampled = self.downsample(([self.newSpline.points[0].tolist()], [self.newSpline.points[1].tolist()]))
                scaling_factor = self.display_size/self.imsize[1]
                if self.edit_selection == 0:
                    self.stent[0][self.frame] = [val/scaling_factor for val in downsampled[0][0]]
                    self.stent[1][self.frame] = [val/scaling_factor for val in downsampled[1][0]]
                elif self.edit_selection == 1:
                    self.plaque[0][self.frame] = [val/scaling_factor for val in downsampled[0][0]]
                    self.plaque[1][self.frame] = [val/scaling_factor for val in downsampled[1][0]]
                elif self.edit_selection == 2:
                    self.lumen[0][self.frame] = [val/scaling_factor for val in downsampled[0][0]]
                    self.lumen[1][self.frame] = [val/scaling_factor for val in downsampled[1][0]]

                # update image, contours and measurements
                self.displayImage()
                self.contourUpdatedSignal.emit(True)

    def run(self):
        self.displayImage()

    def new(self, edit_selection):
        self.draw = True
        self.edit_selection = edit_selection

        if self.edit_selection == 0:
            self.stent[0][self.frame] = []
            self.stent[1][self.frame] = []
        elif self.edit_selection == 1:
            self.plaque[0][self.frame] = []
            self.plaque[1][self.frame] = []
        else:
            self.lumen[0][self.frame] = []
            self.lumen[1][self.frame] = [] 

        self.displayImage()     
		
    def setFrame(self, value):
        self.frame = value

    def setDisplay(self, hide):
        self.hide = hide
