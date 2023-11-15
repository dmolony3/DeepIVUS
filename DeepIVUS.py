from PyQt5.QtWidgets import (QMainWindow, QWidget, QSlider, QApplication, QHeaderView, QStyle, QFrame, QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox,  QLabel, QSizePolicy, QInputDialog, QErrorMessage, QMessageBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QSize, QTimer, QPointF
from PyQt5.QtGui import QIcon, QFont, QPixmap, QImage, QPen, QColor, QPainterPath
from IVUS_gating import IVUS_gating
from IVUS_prediction import predict
from write_xml import write_xml, get_contours, mask_image
from display import Display, LView, LesionView
from PIL import Image
from itertools import groupby
from operator import itemgetter
import os, sys, time, read_xml
import pydicom as dcm
import numpy as np
import subprocess
import click


class Settings():
    def __init__(self):
        self.autoSave = True
        self.lesion_length = 3
        self.lesion_merge_length = 1.5

class LViewData():
    """Creates an lview and returns the image"""
    def __init__(self, image_dim):

        self.current_angle = 0
        spacing = np.linspace(0, image_dim[1], image_dim[2])
        x, y = np.meshgrid(spacing, spacing)
        half_dim = image_dim[1]//2
        x = x - half_dim
        y = y - half_dim
        self.rho = np.sqrt(x**2 + y**2)
        phi = np.arctan2(y, x)
        phi += np.pi
        phi = phi*180/np.pi
        self.phi1 = phi[:, :half_dim]
        self.phi2 = phi[:, half_dim:]   
        self.phi3 = phi[:half_dim, :]
        self.phi4 = phi[half_dim:, :]
        self.phi = phi
        self.idx1_1 = np.linspace(0, half_dim - 1, half_dim, dtype=np.uint16)
        self.idx2_1 = np.linspace(half_dim, image_dim[1] - 1, half_dim, dtype=np.uint16)

    def update(self, images, current_angle):  
        self.current_angle = current_angle
        #if self.current_angle > 90 and self.current_angle < 270:
        #    self.current_angle = 360 - self.current_angle
        #print("New angle:", self.current_angle, (180 + self.current_angle)%360)
        if 45 < self.current_angle <= 135:
        #if self.current_angle <= 45 or self.current_angle > 315:
            idx1_2 = np.abs((self.phi3 - self.current_angle)).argmin(axis=1)
            idx2_2 = np.abs((self.phi4 - (180 + self.current_angle)%360)).argmin(axis=1)
            idx1 = np.concatenate([self.idx1_1, self.idx2_1])
            idx2 = np.concatenate([idx1_2, idx2_2])    
            #lview_array = images[:, idx1, idx2].astype(np.uint8, order='C', casting='unsafe')
        elif 225 < self.current_angle <= 315:
            idx1_2 = np.abs((self.phi3 - (180 + self.current_angle)%360)).argmin(axis=1)
            idx2_2 = np.abs((self.phi4 - self.current_angle)).argmin(axis=1)
            idx1 = np.concatenate([self.idx1_1, self.idx2_1])
            idx2 = np.concatenate([idx1_2, idx2_2])    
            #lview_array = images[:, idx1, idx2].astype(np.uint8, order='C', casting='unsafe')        
        elif 135 < self.current_angle <= 225:
            idx1_2 = np.abs((self.phi1 - (180 + self.current_angle)%360)).argmin(axis=0)
            idx2_2 = np.abs((self.phi2 - self.current_angle)).argmin(axis=0)
            idx2 = np.concatenate([self.idx1_1, self.idx2_1])
            idx1 = np.concatenate([idx1_2, idx2_2])        
            #lview_array = images[:, idx2, idx1].astype(np.uint8, order='C', casting='unsafe')
        else:
            idx1_2 = np.abs((self.phi1 - self.current_angle)).argmin(axis=0)
            idx2_2 = np.abs((self.phi2 - (180 + self.current_angle)%360)).argmin(axis=0)
            idx2 = np.concatenate([self.idx1_1, self.idx2_1])
            idx1 = np.concatenate([idx1_2, idx2_2])
        
        
        lview_array = images[:, idx1, idx2].astype(np.uint8, order='C', casting='unsafe')
        lview_array = np.transpose(lview_array, (1, 0)).copy()
        if 135 <= self.current_angle <= 315:
            lview_array = np.flipud(lview_array).copy()

        return lview_array
        
class Communicate(QObject):
    updateBW = pyqtSignal(int)
    updateBool = pyqtSignal(bool)

class Slider(QSlider):
    """Slider for changing the currently displayed image."""
    def __init__(self, orientation):
        super().__init__()
        self.setOrientation(orientation)
        self.setRange(0, 0)
        self.setValue(0)
        self.setFocusPolicy(Qt.StrongFocus)
        sizePolicy = QSizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Fixed)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(800, 25))
        self.setMaximumSize(QSize(800, 25))
        self.gatedFrames = []

    def keyPressEvent(self, event):
        """Key events."""

        key = event.key()
        if key == Qt.Key_Right:
            self.setValue(self.value() + 1)
        elif key == Qt.Key_Left:
            self.setValue(self.value() - 1)
        elif key == Qt.Key_Up:
            if self.gatedFrames:
                currentGatedFrame = self.findFrame(self.value())
                currentGatedFrame = currentGatedFrame + 1
                if currentGatedFrame > self.maxFrame:
                    currentGatedFrame = self.maxFrame
                self.setValue(self.gatedFrames[currentGatedFrame])
            else:
                self.setValue(self.value() + 1)
        elif key == Qt.Key_Down:
            if self.gatedFrames:
                currentGatedFrame = self.findFrame(self.value())
                currentGatedFrame = currentGatedFrame - 1
                if currentGatedFrame < 0:
                    currentGatedFrame = 0
                self.setValue(self.gatedFrames[currentGatedFrame])                
            else:
                self.setValue(self.value() - 1)
        elif key == Qt.Key_J:
            self.setValue(self.value() - 1)
            QApplication.processEvents()
            time.sleep(0.1)
            self.setValue(self.value() + 1)
            QApplication.processEvents()
            time.sleep(0.1)
            self.setValue(self.value() + 1)
            QApplication.processEvents()
            time.sleep(0.1)
            self.setValue(self.value() - 1)
            QApplication.processEvents()

    def findFrame(self, currentFrame):
        """Find the closest gated frame.

        Args:
            currentFrame: int, current displayed frame
        Returns:
            currentGatedFrame: int, gated frame closeset to current displayed frame
        """

        frameDiff = [abs(val - currentFrame) for val in self.gatedFrames]
        currentGatedFrame = [idx for idx in range(len(frameDiff)) 
            if frameDiff[idx] == min(frameDiff)][0]

        return currentGatedFrame

    def addGatedFrames(self, gatedFrames):
        """Stores the gated frames."""

        self.gatedFrames = gatedFrames
        self.maxFrame = len(self.gatedFrames) - 1

class Master(QMainWindow):
    """Main Window Class

    Attributes:
        image: bool, indicates whether images have been loaded (true) or not
        contours: bool, indicates whether contours have been loaded (true) or not
        segmentation: bool, indicates whether segmentation has been performed (true) or not
        lumen: tuple, contours for lumen border
        plaque: tuple, contours for plaque border
    """

    def __init__(self):
        super().__init__()
        self.image = False
        self.contours = False
        self.segmentation = False
        self.displayTopSize = 800
        self.current_angle = 0
        self.gatedFrames = []
        self.metrics = ([], [], [])
        self.lesion_info = []
        self.lumen = ()
        self.plaque = ()
        self.settings = Settings()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1200, 1200)
        self.addToolBar("MY Window")
        self.showMaximized()

        layout = QHBoxLayout()
        vbox1 = QVBoxLayout()
        vbox2 = QVBoxLayout()
        vbox1hbox1 = QHBoxLayout()
        vbox1hbox2 = QVBoxLayout()

        vbox1.setContentsMargins(0, 0, 100, 100)
        vbox2.setContentsMargins(100, 0, 0, 0)
        layout.addLayout(vbox1)
        layout.addLayout(vbox2)

        self.dicomButton = QPushButton('Read DICOM')
        self.contoursButton = QPushButton('Read Contours')
        self.gatingButton = QPushButton('Extract Diastolic Frames')
        self.segmentButton = QPushButton('Segment')
        self.splineButton = QPushButton('Manual Contour')
        self.writeButton = QPushButton('Write Contours')
        self.reportButton = QPushButton('Write Report') 
        self.contoursButton.setEnabled(False)        
        self.gatingButton.setEnabled(False)        
        self.segmentButton.setEnabled(False)        
        self.splineButton.setEnabled(False)        
        self.writeButton.setEnabled(False)        
        self.reportButton.setEnabled(False)        

        self.dicomButton.setToolTip("Load images in .dcm format")
        self.contoursButton.setToolTip("Load saved contours in .xml format")
        self.gatingButton.setToolTip("Extract end diastolic images from pullback")
        self.segmentButton.setToolTip("Run deep learning based segmentation of lumen and plaque")
        self.splineButton.setToolTip("Manually draw new contour for lumen, plaque or stent")
        self.writeButton.setToolTip("Save contours in .xml file")
        self.reportButton.setToolTip("Write report containing, lumen, plaque and vessel areas and plaque burden")

        self.info_lumen = QLabel()
        self.info_vessel = QLabel()
        self.info_plaque = QLabel()
        self.info_burden = QLabel()
        self.info_lumen.setText("Lumen area:     mm<sup>2</sup>")
        self.info_vessel.setText("Vessel area:     mm<sup>2</sup>")
        self.info_plaque.setText("Plaque area:     mm<sup>2</sup>")
        self.info_burden.setText("Plaque burden:     %")
        self.info_lumen.setAlignment(Qt.AlignLeft)
        self.info_vessel.setAlignment(Qt.AlignLeft)
        self.info_plaque.setAlignment(Qt.AlignLeft)
        self.info_burden.setAlignment(Qt.AlignLeft)
        self.info_lumen.setFont(QFont('Arial', 11))
        self.info_vessel.setFont(QFont('Arial', 11))
        self.info_plaque.setFont(QFont('Arial', 11))
        self.info_burden.setFont(QFont('Arial', 11))
        
        hideHeader1 = QHeaderView(Qt.Vertical)
        hideHeader1.hide()
        hideHeader2 = QHeaderView(Qt.Horizontal)
        hideHeader2.hide()
        vbox2hbox1 = QHBoxLayout()
        self.infoTable = QTableWidget()
        self.infoTable.setRowCount(8)
        self.infoTable.setColumnCount(2)
        self.infoTable.setItem(0, 0, QTableWidgetItem('Patient Name'))
        self.infoTable.setItem(1, 0, QTableWidgetItem('Patient DOB'))
        self.infoTable.setItem(2, 0, QTableWidgetItem('Patient Sex'))
        self.infoTable.setItem(3, 0, QTableWidgetItem('Pullback Speed'))
        self.infoTable.setItem(4, 0, QTableWidgetItem('Resolution (mm)'))
        self.infoTable.setItem(5, 0, QTableWidgetItem('Dimensions'))
        self.infoTable.setItem(6, 0, QTableWidgetItem('Manufacturer'))
        self.infoTable.setItem(7, 0, QTableWidgetItem('Model'))
        self.infoTable.setVerticalHeader(hideHeader1)
        self.infoTable.setHorizontalHeader(hideHeader2)
        self.infoTable.resizeRowsToContents()
        self.infoTable.resizeColumnsToContents()
        #self.infoTable.verticalHeader().setStretchLastSection(True)
        #self.infoTable.setSizePolicy(QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Minimum)
        self.infoTable.horizontalHeader().setStretchLastSection(True)
        iHeight = 0
        for i in range(self.infoTable.rowCount()):
            iHeight += self.infoTable.verticalHeader().sectionSize(i)

        self.infoTable.setMaximumHeight(iHeight)
        self.infoTable.verticalScrollBar().setDisabled(True)
        self.infoTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vbox2.addLayout(vbox2hbox1)
        
        vbox2hbox2 = QHBoxLayout()
        vbox2hbox3 = QHBoxLayout()
        vbox2hbox4 = QHBoxLayout()
        vbox2hbox5 = QHBoxLayout()
        vbox2.addLayout(vbox2hbox2)
        vbox2.addLayout(vbox2hbox3)
        vbox2.addLayout(vbox2hbox4)
        vbox2.addLayout(vbox2hbox5)

        self.dicomButton.clicked.connect(self.readDICOM)
        self.contoursButton.clicked.connect(self.readContours)
        self.segmentButton.clicked.connect(self.segment)
        self.splineButton.clicked.connect(self.newSpline)
        self.gatingButton.clicked.connect(self.gate)
        self.reportButton.clicked.connect(self.report)
        self.writeButton.clicked.connect(lambda: self.writeContours())

        self.playButton = QPushButton()
        pixmapi1 = getattr(QStyle, 'SP_MediaPlay')
        pixmapi2 = getattr(QStyle, 'SP_MediaPause')
        self.playIcon = self.style().standardIcon(pixmapi1)
        self.pauseIcon = self.style().standardIcon(pixmapi2)
        self.playButton.setIcon(self.playIcon)
        self.playButton.clicked.connect(self.play)
        self.paused = True

        self.slider = Slider(Qt.Horizontal)     
        self.slider.valueChanged[int].connect(self.changeValue)

        self.hideBox = QCheckBox('Hide Contours')
        self.hideBox.setChecked(True)
        self.hideBox.stateChanged[int].connect(self.changeState)
        self.useGatedBox = QCheckBox('Gated Frames')
        self.useGatedBox.stateChanged[int].connect(self.useGated)
        self.useGatedBox.setToolTip("When this is checked only gated frames will be segmented and only gated frames statistics will be written to the report")
        self.useGatedBox.setToolTipDuration(200)
           
        self.wid = Display()
        self.c = Communicate()        
        self.c.updateBW[int].connect(self.wid.setFrame)
        self.c.updateBool[bool].connect(self.wid.setDisplay)
        self.wid.lviewChangedSignal.connect(self.updateLview)
        self.wid.contourUpdatedSignal.connect(self.changeContour)
        self.wid.frameChangedKeySignal.connect(self.keyPressDisplay)
        
        self.text = QLabel()
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setText("Frame {}".format(self.slider.value())) 
        self.text.setFont(QFont('Arial', 11))

        vbox1.addWidget(self.wid)
        vbox1hbox1.addWidget(self.playButton)
        vbox1hbox1.addWidget(self.slider)
        vbox1.addLayout(vbox1hbox1)
        vbox1.addWidget(self.text)

        vbox2.addWidget(self.hideBox)
        vbox2.addWidget(self.useGatedBox)
        #vbox2.addWidget(self.dicomButton)
        #vbox2.addWidget(self.contoursButton)
        #vbox2.addWidget(self.gatingButton)
        #vbox2.addWidget(self.segmentButton)
        #vbox2.addWidget(self.splineButton)
        #vbox2.addWidget(self.writeButton)
        #vbox2.addWidget(self.reportButton)
        vbox2hbox2.addWidget(self.dicomButton)
        vbox2hbox2.addWidget(self.contoursButton)
        vbox2hbox3.addWidget(self.gatingButton)
        vbox2hbox3.addWidget(self.segmentButton)
        vbox2hbox4.addWidget(self.splineButton)
        vbox2hbox5.addWidget(self.writeButton)
        vbox2hbox5.addWidget(self.reportButton)

        vbox2hbox1.addWidget(self.infoTable)
        vbox1.addLayout(vbox1hbox2)
        vbox1hbox2.addWidget(self.info_lumen)
        vbox1hbox2.addWidget(self.info_vessel)
        vbox1hbox2.addWidget(self.info_plaque)
        vbox1hbox2.addWidget(self.info_burden)
        
        # layouts dont provide fixed size functionality so make a widget with a layout instead
        self.lview_length = 1600
        self.lview_height = 400
        displayBottom = QWidget()
        displayBottom.setFixedHeight(self.lview_height)
        lay = QHBoxLayout(displayBottom)
        
        self.lview = LView(self.displayTopSize)
        self.lview.markerChangedSignal.connect(self.changeValue2)
        self.lview.markerChangedKeySignal.connect(self.keyPressDisplay)

        lay.addWidget(self.lview)
        vbox2.addWidget(displayBottom)
        vbox2.addLayout(lay)
        
        displayBottom1 = QWidget()
        displayBottom1.setFixedHeight(self.lview_height//2)
        lay1 = QHBoxLayout(displayBottom1)
        
        self.lesionView = LesionView()
        #self.lview.markerChangedSignal.connect(self.lesionView.updateMarker)
        #self.lview.markerChangedKeySignal.connect(self.lesionView.updateMarkerFromKey)
        self.slider.valueChanged[int].connect(self.lesionView.updateMarker)
        self.lesionView.updateFrameFromLesionViewSignal.connect(self.changeValue)

        lay1.addWidget(self.lesionView)
        vbox2.addWidget(displayBottom1)
        vbox2.addLayout(lay1)

        self.lview.horizontalScrollBar().valueChanged.connect(self.lesionView.horizontalScrollBar().setValue)
        self.lesionView.horizontalScrollBar().valueChanged.connect(self.lview.horizontalScrollBar().setValue)
        
        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setWindowIcon(QIcon('Media/thumbnail.png'))
        self.setWindowTitle('DeepIVUS')
        self.setCentralWidget(centralWidget)
        self.show()
        disclaimer = QMessageBox.about(self, 'DeepIVUS', 'DeepIVUS is not FDA approved and should not be used for medical decisions.')

        #pipe = subprocess.Popen(["rm","-r","some.file"])
        #pipe.communicate() # block until process completes.
        timer = QTimer(self)
        timer.timeout.connect(self.autoSave) 
        timer.start(180000) # autosaves every 3 minutes
    
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Q:
            self.close()
        elif key == Qt.Key_H:
            if not self.hideBox.isChecked():
                self.hideBox.setChecked(True)
            elif self.hideBox.isChecked():
                self.hideBox.setChecked(False)
            self.hideBox.setChecked(self.hideBox.isChecked())
        elif key == Qt.Key_J:
            currentFrame = self.slider.value()
            self.slider.setValue(currentFrame+1)
            QApplication.processEvents()
            time.sleep(0.1)
            self.slider.setValue(currentFrame)
            QApplication.processEvents()
            time.sleep(0.1)
            self.slider.setValue(currentFrame-1)
            QApplication.processEvents()
            time.sleep(0.1)
            self.slider.setValue(currentFrame)
            QApplication.processEvents()
            
    def keyPressDisplay(self, event):
        key = event.key()
        if key == Qt.Key_Q:
            self.close()
        elif key == Qt.Key_H:
            if not self.hideBox.isChecked():
                self.hideBox.setChecked(True)
            elif self.hideBox.isChecked():
                self.hideBox.setChecked(False)
            self.hideBox.setChecked(self.hideBox.isChecked())
        self.slider.keyPressEvent(event)
        
    def parseDICOM(self):
        """Parses DICOM metadata"""

        if (len(self.dicom.PatientName.encode('ascii')) > 0):
            self.patientName = self.dicom.PatientName.original_string.decode('utf-8').replace("^", " ").strip()
            print(self.patientName)
        else:
            self.patientName = 'Unknown'

        if len(self.dicom.PatientBirthDate) > 0:
            self.patientBirthDate = self.dicom.PatientBirthDate
        else:
            self.patientBirthDate = 'Unknown'

        if len(self.dicom.PatientSex) > 0:
            self.patientSex = self.dicom.PatientSex
        else:
            self.patientSex = 'Unknown'

        if self.dicom.get('IVUSPullbackRate'):
            self.ivusPullbackRate = float(self.dicom.IVUSPullbackRate)
        # check Boston private tag
        elif self.dicom.get(0x000b1001):
            self.ivusPullbackRate = float(self.dicom[0x000b1001].value)
        else:
            self.ivusPullbackRate, _ = QInputDialog.getText(self, "Pullback Speed", "No pullback speed found, please enter pullback speeed (mm/s)", QLineEdit.Normal, "0.5")
            self.ivusPullbackRate = float(self.ivusPullbackRate)

        if self.dicom.get('FrameTimeVector'):
            frameTimeVector = self.dicom.get('FrameTimeVector')
            frameTimeVector = [float(frame) for frame in frameTimeVector]
            pullbackTime = np.cumsum(frameTimeVector)/1000 # assume in ms
            self.pullbackLength = pullbackTime*float(self.ivusPullbackRate)
        else:
            self.pullbackLength = np.zeros((self.images.shape[0], ))

        if self.dicom.get('SequenceOfUltrasoundRegions'):
            if self.dicom.SequenceOfUltrasoundRegions[0].PhysicalUnitsXDirection == 3:
                # pixels are in cm, convert to mm 
                self.resolution = self.dicom.SequenceOfUltrasoundRegions[0].PhysicalDeltaX*10
            else:
                # assume mm
                self.resolution = self.dicom.SequenceOfUltrasoundRegions[0].PhysicalDeltaX
        elif self.dicom.get('PixelSpacing'):
            self.resolution = float(self.dicom.PixelSpacing[0])
        else:
            resolution, done = QInputDialog.getText(self, "Pixel Spacing", "No pixel spacing info found, please enter pixel spacing (mm)", QLineEdit.Normal, "")
            self.resolution = float(resolution)
        
        if self.dicom.get('Rows'):
            self.rows = self.dicom.Rows
        else:
            self.rows = self.images.shape[1]

        if self.dicom.get('Manufacturer'):
            self.manufacturer = self.dicom.Manufacturer
        else:
            self.manufacturer = 'Unknown'

        if self.dicom.get('ManufacturerModelName'):
            self.model = self.dicom.ManufacturerModelName
        else:
            self.model = 'Unknown'

        # if pixel data is described by luminance (Y) and chominance (B & R)
        # only occurs when SamplesPerPixel==3
        #if self.dicom.get('PhotometricInterpretation') == 'YBR_FULL_422':
        #    #self.images = np.mean(self.images, 3, dtype=np.uint8)
        #    self.images = np.ascontiguousarray(self.images)[:, :, :, 0]
        

    def readDICOM(self):
        """Reads DICOM images.

        Reads the dicom images and metadata. Places metatdata in a table.
        Images are displayed in the graphics scene.
        """

        options=QFileDialog.Options()
        options = QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "DICOM files (*.dcm);;All files (*)", options=options)

        if fileName:
            try :
                self.dicom = dcm.read_file(fileName, force=True)
                self.images = self.dicom.pixel_array
            except:
                error = QMessageBox()
                error.setIcon(QMessageBox.Critical)
                error.setWindowTitle("Error")
                error.setModal(True)
                error.setWindowModality(Qt.WindowModal)
                error.setText("File is not a valid IVUS file and could not be loaded")
                error.exec_()
                return None
                
            self.slider.setMaximum(self.dicom.NumberOfFrames-1)
            self.image = True
            self.parseDICOM()
            self.numberOfFrames = int(self.dicom.NumberOfFrames)
            self.infoTable.setItem(0, 1, QTableWidgetItem(self.patientName))
            self.infoTable.setItem(1, 1, QTableWidgetItem(self.patientBirthDate))
            self.infoTable.setItem(2, 1, QTableWidgetItem(self.patientSex))
            self.infoTable.setItem(3, 1, QTableWidgetItem(str(self.ivusPullbackRate)))
            self.infoTable.setItem(4, 1, QTableWidgetItem(str(self.resolution)))
            self.infoTable.setItem(5, 1, QTableWidgetItem(str(self.rows)))
            self.infoTable.setItem(6, 1, QTableWidgetItem(self.manufacturer))        
            self.infoTable.setItem(7, 1, QTableWidgetItem((self.model)))
            
            if len(self.lumen) != 0:
                reinitializeContours = len(self.lumen) != self.numberOfFrames
            else:
                reinitializeContours = False

            if not self.lumen or reinitializeContours:
                self.lumen = ([[] for idx in range(self.numberOfFrames)], [[] for idx in range(self.numberOfFrames)])
                self.plaque = ([[] for idx in range(self.numberOfFrames)], [[] for idx in range(self.numberOfFrames)])
                self.stent = ([[] for idx in range(self.numberOfFrames)], [[] for idx in range(self.numberOfFrames)])

            self.wid.setData(self.lumen, self.plaque, self.stent, self.images)

            # creaet lview data
            self.lview_data = LViewData(self.images.shape)
            lview_array = self.lview_data.update(self.images, self.current_angle)

            # lview
            self.lview.createScene(lview_array)
            
            self.slider.setValue(self.numberOfFrames-1)

            self.contoursButton.setEnabled(True)        
            self.gatingButton.setEnabled(True)        
            self.segmentButton.setEnabled(True)        
            self.splineButton.setEnabled(True)        

        
    def angle3pt(self, a, b, c):
        """Counterclockwise angle in degrees by turning from a to c around b
        Returns a float between 0.0 and 360.0"""
        ang = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        ang = np.rad2deg(ang)
        return ang + 360 if ang < 0 else ang
    
    def readContours(self):
        """Reads contours.

        Reads contours  saved in xml format (Echoplaque compatible) and 
        displays the contours in the graphics scene
        """

        if not self.image:
            warning = QErrorMessage()
            warning.setWindowModality(Qt.WindowModal)
            warning.showMessage('Reading of contours failed. Images must be loaded prior to loading contours')
            warning.exec_()
        else:
            options=QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "XML file (*.xml)", options=options)
            if fileName:
                self.lumen, self.plaque, self.stent, self.resolution, frames = read_xml.read(fileName)
                if len(self.lumen[0]) != self.dicom.NumberOfFrames:
                    warning = QErrorMessage()
                    warning.setWindowModality(Qt.WindowModal)
                    warning.showMessage('Reading of contours failed. File must contain the same number of frames as loaded dicom')
                    warning.exec_()
                else:
                    self.resolution = float(self.resolution[0])
                    self.lumen = self.mapToList(self.lumen)
                    self.plaque = self.mapToList(self.plaque)
                    self.stent = self.mapToList(self.stent)
                    self.contours=True
                    self.wid.setData(self.lumen, self.plaque, self.stent, self.images)
                    self.hideBox.setChecked(False)

                    gatedFrames = [frame for frame in range(len(self.lumen[0])) if self.lumen[0][frame] or self.plaque[0][frame]]
                    self.gatedFrames = gatedFrames
                    self.useGatedBox.setChecked(True)
                    self.slider.addGatedFrames(self.gatedFrames)

                    self.metrics = self.computeContourMetrics(self.lumen, self.plaque)
                    lumen_area, plaque_area, plaque_burden = self.metrics
                    self.updateAreaDisplay(lumen_area, plaque_area, plaque_burden, self.slider.value())
            
                    self.lview_lumenY = [self.lview_length*(frame/self.numberOfFrames) for frame in self.gatedFrames]
                    self.lview_plaqueY = [self.lview_length*(frame/self.numberOfFrames) for frame in self.gatedFrames]
                    self.lview_lumen, self.lview_lumen1, self.lview_lumen2 = self.getLviewCoordinates(self.lumen)
                    self.lview_plaque, self.lview_plaque1, self.lview_plaque2 = self.getLviewCoordinates(self.plaque)
                    self.lview.createLViewContours(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen1, self.lview_lumen2, self.lview_plaque1, self.lview_plaque2)
                    
                    self.lesion_info = self.lesion_analysis(lumen_area, plaque_area, plaque_burden)
                    self.lesionView.setNumberOfFrames(self.numberOfFrames)
                    self.lesionView.createScene(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen, self.lview_plaque, self.lesion_info, self.lview_length)
            self.reportButton.setEnabled(True) 
            self.writeButton.setEnabled(True)

    def lesion_analysis(self, lumen_area, plaque_area, plaque_burden):
        """identifies which frames are part of a lesion where lesion is defined 
        as >=3 frames wiht plaque burden >40%
        """

        lumen_area = lumen_area[self.gatedFrames]
        plaque_area = plaque_area[self.gatedFrames]
        plaque_burden = plaque_burden[self.gatedFrames]
        
        # result is a dictionary contaning tuples of the value and the indices containing the value
        # if lesions are within 5mm of each other they are considered a single lesion
        lesion_idx = (plaque_burden > 40).astype(int)
        num_frames = 3
        result = []
        for k, g in groupby(enumerate(lesion_idx), key=itemgetter(1)):
            group = list(g)
            if len(group) >= num_frames:
                if k != 0:
                    result.append((k, list(map(itemgetter(0), group))))
                    
        num_lesions = len(result)
    
        lesion_info = []
        for i in range(num_lesions):
            lesion = {}
            lesion['MLA'] = lumen_area[result[i][1]].min()
            lesion['idx' ] = [self.gatedFrames[idx] for idx in result[i][1]]
            lesion['MLA idx'] = self.gatedFrames[result[i][1][0] + lumen_area[result[i][1]].argmin()]
            lesion['MPB idx'] = self.gatedFrames[result[i][1][0] + plaque_burden[result[i][1]].argmax()]
            lesion_length = self.pullbackLength[self.gatedFrames[result[i][1][-1]]] - self.pullbackLength[self.gatedFrames[result[i][1][0]]]
            lesion['length'] = lesion_length
            
            
            # merge lesions that are within n mm of each other
            if i == 0:
                lesion_info.append(lesion)
            else:
                lesion_distance = (lesion['idx'][0] - lesion_info[-1]['idx'][-1])*self.pullbackLength[1]
                if lesion_distance <= self.settings.lesion_merge_length:
                    frame_idx = [idx for idx, frame in enumerate(self.gatedFrames) if frame in lesion_info[-1]['idx']]
                    missing_idx = list(range(frame_idx[-1] + 1, result[i][1][0]))
                    frame_idx.extend(missing_idx)
                    frame_idx.extend(result[i][1])
                    lesion['MLA'] = lumen_area[frame_idx].min()
                    lesion['idx' ] = [self.gatedFrames[idx] for idx in frame_idx]
                    lesion['MLA idx'] = self.gatedFrames[frame_idx[0] + lumen_area[frame_idx].argmin()]
                    lesion['MPB idx'] = self.gatedFrames[frame_idx[0] + plaque_burden[frame_idx].argmax()]
                    lesion_length = self.pullbackLength[self.gatedFrames[frame_idx[-1]]] - self.pullbackLength[self.gatedFrames[frame_idx[0]]]
                    lesion['length'] = lesion_length    
                    lesion_info[-1] = lesion

        # remove any lesions that are less than minimum lesion length
        for i in range(len(lesion_info)):
            if lesion_info[i]['length'] < self.settings.lesion_length:
                lesion_info.pop(i)
                print(f"Removed lesion {i} of {lesion_info[i]['length']} mm length")

        return lesion_info        
            
    def play(self):
        "Plays all frames until end of pullback starting from currently selected frame"""
        start_frame = self.slider.value()

        if self.paused:
            self.paused = False
            self.playButton.setIcon(self.pauseIcon)        
        else:
            self.paused = True
            self.playButton.setIcon(self.playIcon)        

        for frame in range(start_frame, self.numberOfFrames):
            if not self.paused: 
                self.slider.setValue(frame)
                QApplication.processEvents()
                time.sleep(0.05)
                self.text.setText("Frame {}".format(frame))     

        self.playButton.setIcon(self.playIcon)        

    def writeContours(self, fname=None):
        """Writes contours to an xml file compatible with Echoplaque"""

        patientName = self.infoTable.item(0, 1).text()
        saveName = patientName if fname is None else fname

        self.lumen, self.plaque = self.wid.getData()

        # reformat data for compatibility with write_xml function
        x, y = [], []
        for i in range(len(self.lumen[0])):
            x.append(self.lumen[0][i])
            x.append(self.plaque[0][i])
            y.append(self.lumen[1][i])
            y.append(self.plaque[1][i])

        if not self.segmentation and not self.contours:
            self.errorMessage()
        else:
            frames = list(range(self.numberOfFrames))

            write_xml(x, y, self.images.shape, self.resolution, self.ivusPullbackRate, frames, saveName)
            if fname is None:
                self.successMessage('Writing contours')

    def autoSave(self):
        """Automatically saves contours to a temporary file every 180 seconds"""

        if self.contours and self.settings.autoSave:
            print('Automatically saving current contours')
            self.writeContours('temp')

    def report(self):
        """Writes a report file containing lumen area, plaque, area, vessel area, plaque burden, phenotype"""

        if self.segmentation and not self.contours:
            self.errorMessage()
        else:
            self.lumen, self.plaque = self.wid.getData()
            lumen_area, plaque_area, plaque_burden = self.computeContourMetrics(self.lumen, self.plaque)
            phenotype = [0]*self.numberOfFrames
            patientName = self.infoTable.item(0, 1).text()
            vessel_area = lumen_area + plaque_area

            if self.useGatedBox.isChecked():
                frames = self.gatedFrames
            else:
                frames = list(range(self.numberOfFrames))

            f = open(patientName + '_report.txt', 'w')
            f.write('Frame\tPosition (mm)\tLumen area (mm\N{SUPERSCRIPT TWO})\tPlaque area (mm\N{SUPERSCRIPT TWO})\tVessel area (mm\N{SUPERSCRIPT TWO})\tPlaque burden (%)\tphenotype\n')

            for i, frame in enumerate(frames):
                f.write('{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{}\n'.format(frame, self.pullbackLength[frame], lumen_area[frame], plaque_area[frame], vessel_area[frame], plaque_burden[frame], phenotype[frame]))
            f.close()

            self.successMessage('Write report')

    def computeMetrics(self, masks):
        """Measures lumen area, plaque area and plaque burden"""

        lumen, plaque = 1, 2  
        lumen_area = np.sum(masks == lumen, axis=(1, 2))*self.resolution**2
        plaque_area = np.sum(masks == plaque, axis=(1,2))*self.resolution**2
        plaque_burden = (plaque_area/(lumen_area + plaque_area))*100

        return (lumen_area, plaque_area, plaque_burden)

    def gate(self):
        """Extract end diastolic frames and stores in new variable"""

        self.gatedFrames = IVUS_gating(self.images, self.ivusPullbackRate, self.dicom.CineRate)
        if self.gatedFrames:
            self.slider.addGatedFrames(self.gatedFrames)
            self.useGatedBox.setChecked(True)
            self.successMessage("Diastolic frame (change with up and down arrows) extraction")
        else:
            warning = QErrorMessage()
            warning.setWindowModality(Qt.WindowModal)
            warning.showMessage('Diastolic frame extraction was unsuccessful')
            warning.exec_()            

    def segment(self):
        """Segmentation and phenotyping of IVUS images"""

        save_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'model', 'saved_model.pb')
        #save_path = os.path.join('/home/microway/Documents/IVUS', 'model_2021', 'saved_model.pb')

        if not os.path.isfile(save_path):
            message= "No saved weights have been found, segmentation will be unsuccessful, check that weights are saved in {}".format(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'model'))
            error = QMessageBox()
            error.setIcon(QMessageBox.Critical)
            error.setWindowTitle("Error")
            error.setModal(True)
            error.setWindowModality(Qt.WindowModal)
            error.setText(message)
            error.exec_()
            return -1

        warning = QErrorMessage()
        warning.setWindowModality(Qt.WindowModal)
        warning.showMessage('Warning: IVUS Phenotyping is currently only supported for 20MHz images. Interpret other images with extreme caution')
        warning.exec_()

        image_dim = self.images.shape

        if self.useGatedBox.isChecked():
            masks = np.zeros((self.numberOfFrames, image_dim[1], image_dim[2]), dtype=np.uint8)
            masks_gated = predict(self.images[self.gatedFrames, : ,:])
            masks[self.gatedFrames, :, :] = masks_gated
        else:
            masks = predict(self.images)

        # compute metrics such as plaque burden
        self.metrics = self.computeMetrics(masks)
        self.segmentation = True

        # convert masks to contours
        self.lumen, self.plaque = self.maskToContours(masks)
        self.contours = True

        # stent contours currently unsupported so create empty list
        self.stent = [[[] for i in range(image_dim[0])], [[] for i in range(image_dim[0])]]

        self.wid.setData(self.lumen, self.plaque, self.stent, self.images)
        self.hideBox.setChecked(False)
        self.successMessage('Segmentation')
        
        lumen_frames = [i for i in range(len(self.lumen[0])) if self.lumen[0][i]]
        plaque_frames = [i for i in range(len(self.plaque[0])) if self.plaque[0][i]]


        self.lview_lumenY = [self.lview_length*(frame/self.numberOfFrames) for frame in lumen_frames]
        self.lview_plaqueY = [self.lview_length*(frame/self.numberOfFrames) for frame in plaque_frames]
        self.lview_lumen, self.lview_lumen1, self.lview_lumen2 = self.getLviewCoordinates(self.lumen)
        self.lview_plaque, self.lview_plaque1, self.lview_plaque2 = self.getLviewCoordinates(self.plaque)
        self.lview.createLViewContours(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen1, self.lview_lumen2, self.lview_plaque1, self.lview_plaque2)
        
        self.lesion_info = self.lesion_analysis(*self.metrics)
        self.lesionView.setNumberOfFrames(self.numberOfFrames)
        self.lesionView.createScene(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen, self.lview_plaque, self.lesion_info, self.lview_length)

        self.writeButton.setEnabled(True)        
        self.reportButton.setEnabled(True) 
            
    def newSpline(self):
        """Create a message box to choose what spline to create"""

        b3 = QPushButton("lumen")
        b2 = QPushButton("Vessel")
        b1 = QPushButton("Stent")
        
        checkbox = QCheckBox("Include current frame in gated contours?")
        checkbox.setChecked(True)
        d = QMessageBox()
        d.setCheckBox(checkbox)
        d.setText("Select which contour to draw")
        d.setInformativeText("Contour must be closed before proceeding by clicking on initial point")
        d.setWindowModality(Qt.WindowModal)
        d.addButton(b1, 0)
        d.addButton(b2, 1)
        d.addButton(b3, 2)
         
        result = d.exec_()

        self.wid.new(result)
        self.gatedFrames.append(self.slider.value())
        self.gatedFrames = list(set(self.gatedFrames))
        self.gatedFrames.sort()

        self.slider.addGatedFrames(self.gatedFrames)
        self.hideBox.setChecked(False)

        self.writeButton.setEnabled(True)        
        self.reportButton.setEnabled(True) 
    
    def maskToContours(self, masks):
        """Convert numpy mask to IVUS contours """

        levels = [1.5, 2.5]
        image_shape = masks.shape[1:3]
        masks = mask_image(masks, catheter=0)
        _, _, lumen_pred, plaque_pred = get_contours(masks, levels, image_shape) 

        return lumen_pred, plaque_pred

    def contourArea(self, x, y):
        """Calculate contour/polygon area using Shoelace formula"""

        area = 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

        return area

    def computeContourMetrics(self, lumen, plaque):
        """Computes lumen area, plaque area and plaque burden from contours"""

        numberOfFrames = len(lumen[0])
        lumen_area = np.zeros((numberOfFrames))
        plaque_area = np.zeros_like(lumen_area)
        plaque_burden = np.zeros_like(lumen_area)
        for i in range(numberOfFrames):
            if lumen[0][i]:
                lumen_area[i] = self.contourArea(lumen[0][i], lumen[1][i])*self.resolution**2
            else:
                lumen_area[i] = 0
            if plaque[0][i]:
                plaque_area[i] = self.contourArea(plaque[0][i], plaque[1][i])*self.resolution**2 - lumen_area[i]
            else:
                plaque_area[i] = 0
            if lumen[0][i] and plaque[0][i]:
                plaque_burden[i] = (plaque_area[i]/(lumen_area[i] + plaque_area[i]))*100
            else:
                plaque_burden[i] = 0
        return (lumen_area, plaque_area, plaque_burden)

    def mapToList(self, contours):
        """Converts map to list"""

        x, y = contours
        x = [list(x[i]) for i in range(0, len(x))]
        y = [list(y[i]) for i in range(0, len(y))]

        return (x, y)
        
    def updateAreaDisplay(self, lumen_area, plaque_area, plaque_burden, frame):
        """Updates the display of lumen, plaque area"""
        if len(lumen_area) > 0:
            self.info_lumen.setText(f"Lumen area:  {lumen_area[frame]:.2f} mm<sup>2</sup>")
        if len(plaque_area) > 0:
            self.info_plaque.setText(f"Plaque area: {plaque_area[frame]:.2f} mm<sup>2</sup>")
        if len(lumen_area) > 0 and len(plaque_area) > 0:
            self.info_vessel.setText(f"Vessel area: {(plaque_area[frame] + lumen_area[frame]):.2f} mm<sup>2</sup>")
            self.info_burden.setText(f"Plaque burden: {plaque_burden[frame]:.2f} %")  


    def angle_to_vector(self, angle):
        angle = np.deg2rad(angle)
        x = np.cos(angle)
        y = np.sin(angle)
        return (x, y)

    def getLviewCoordinates(self, contour):
        lviewX1, lviewX2 = [], []
        lviewX1_normalized, lviewX2_normalizec = [], []
        lviewX = []
        image_dim = self.images.shape

        #line1=[[0,0], [500,0]]
        #p = np.array(self.angle_to_vector(self.current_angle))
        #print(p)
        #p1 = 250 + p*image_dim[1]
        #radius_normalizing_value = (p*500).max()
        #line2 = [[250, 250], [p1[0],p1[1]]]
        #get_intersect(line1[0], line1[1], line2[0], line2[1])
        #slope1 = (line1[1][1] - line1[0][1])/(line1[1][0] - line1[0][0])
        #slope2 = (line2[1][1] - line2[0][1])/(line2[1][0] - line2[0][0])
        #intercept1 = line1[0][1] - slope1*line1[0][0]
        #intercept2 = line2[0][1] - slope2*line2[0][0]
        #xi = (intercept1 - intercept2) / (slope2 - slope1)
        #yi = slope1 * xi + intercept1
        if 45 <= self.current_angle < 135:
            radius_normalizing_value = self.lview_data.rho[0, np.abs(np.round(self.lview_data.phi[0,:])-self.current_angle).argmin()]
        elif 135 <= self.current_angle < 225:
            radius_normalizing_value = self.lview_data.rho[np.abs(np.round(self.lview_data.phi[:, -1])-self.current_angle).argmin(), -1]
        elif 225 <= self.current_angle < 315:
            radius_normalizing_value = self.lview_data.rho[-1, np.abs(np.round(self.lview_data.phi[-1, :])-self.current_angle).argmin()]
        else:
            radius_normalizing_value = self.lview_data.rho[np.abs(np.round(self.lview_data.phi[:, 0])-self.current_angle).argmin(), 0]

        for i in range(len(contour[0])):
            if contour[0][i]:
                
                x = np.array([val - image_dim[1]//2 for val in contour[0][i]])
                y = np.array([val - image_dim[1]//2 for val in contour[1][i]])

                theta = np.rad2deg(np.arctan2(y, x)) + 180

                rho = np.sqrt(x**2 + y**2)
                angle_idx1 = np.abs(theta - self.current_angle).argmin()
                angle_idx2 = np.abs(theta - (180 + self.current_angle)%360).argmin()
                #print(angle_idx1, angle_idx2)
                lviewX.append(((rho[angle_idx1] + rho[angle_idx2])/2)/(radius_normalizing_value))
                
                lviewX1.append(self.lview_height//2 - rho[angle_idx1]/(radius_normalizing_value)*(self.lview_height//2))
                lviewX2.append(self.lview_height//2 + rho[angle_idx2]/(radius_normalizing_value)*(self.lview_height//2))
        return lviewX, lviewX1, lviewX2
        
    def updateLview(self, x1, y1, x2, y2):
        """this is triggered if the lview is changed via the crossbar"""
        if not self.image:
            return
        #self.scenelong.clear()
        #self.lview.viewport().update()

        #[self.removeItem(item) for item in self.scenelong.items()]

        #print(x1,y1, x2, y2)
        line1 = [[0, self.displayTopSize//2], [self.displayTopSize//2, self.displayTopSize//2]]
        line2 = [[x1, y1], [x2, y2]]
        current_angle = round(self.angle3pt(line1[0], line1[1], line2[0]))
        #print(current_angle)
        
        # current_angle is returned where 9pm is 180 degress and angle increase clockwise
        # need to subtract 180 in order to match image polar coordinates where 9pm is 0 degrees
        current_angle = current_angle  - 180
        current_angle = current_angle + 360 if current_angle < 0 else current_angle
        self.current_angle = current_angle
        #print(current_angle)
        
        lview_array = self.lview_data.update(self.images, current_angle)

        # lview
        self.lview.updateImage(lview_array)
        
        lumen_frames = [i for i in range(len(self.lumen[0])) if self.lumen[0][i]]
        plaque_frames = [i for i in range(len(self.plaque[0])) if self.plaque[0][i]]

        if self.contours:
            self.lview_lumenY = [self.lview_length*(frame/self.numberOfFrames) for frame in lumen_frames]
            self.lview_plaqueY = [self.lview_length*(frame/self.numberOfFrames) for frame in plaque_frames]
            self.lview_lumen, self.lview_lumen1, self.lview_lumen2 = self.getLviewCoordinates(self.lumen)
            self.lview_plaque, self.lview_plaque1, self.lview_plaque2 = self.getLviewCoordinates(self.plaque)
            self.lview.updateLViewContours(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen1, self.lview_lumen2, self.lview_plaque1, self.lview_plaque2)
                                 
    def changeContour(self, is_true):
        if is_true:
            self.lumen, self.plaque = self.wid.getData()
            self.metrics = self.computeContourMetrics(self.lumen, self.plaque)
            lumen_area, plaque_area, plaque_burden = self.metrics
            self.updateAreaDisplay(lumen_area, plaque_area, plaque_burden, self.slider.value())
           
            lumen_frames = [i for i in range(len(self.lumen[0])) if self.lumen[0][i]]
            plaque_frames = [i for i in range(len(self.plaque[0])) if self.plaque[0][i]]
            
            # add changing coordinates when lview is changed
            self.lview_lumenY = [self.lview_length*(frame/self.numberOfFrames) for frame in lumen_frames]
            self.lview_plaqueY = [self.lview_length*(frame/self.numberOfFrames) for frame in plaque_frames]
            self.lview_lumen, self.lview_lumen1, self.lview_lumen2 = self.getLviewCoordinates(self.lumen)
            self.lview_plaque, self.lview_plaque1, self.lview_plaque2 = self.getLviewCoordinates(self.plaque)
            self.lview.updateLViewContours(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen1, self.lview_lumen2, self.lview_plaque1, self.lview_plaque2)
            
            self.lesion_info = self.lesion_analysis(*self.metrics)
            self.lesionView.createScene(self.lview_lumenY, self.lview_plaqueY, self.lview_lumen, self.lview_plaque, self.lesion_info, self.lview_length)

    def changeValue2(self, value):
        """runs when lview marker is changed"""
        value = round(value*(self.numberOfFrames - 1))
        self.c.updateBW.emit(value)
        self.wid.run()
        self.text.setText(f"Frame {value}")
        self.slider.setValue(value)

            
    def changeValue(self, value):
        """runs when slider is moved"""
        self.c.updateBW.emit(value)
        self.wid.run()
        self.text.setText(f"Frame {value}")
        self.slider.setValue(value)
        lumen_area, plaque_area, plaque_burden = self.metrics
        self.updateAreaDisplay(lumen_area, plaque_area, plaque_burden, value)       

        lview_length = self.lview.sceneRect().width()
        lview_height = self.lview.sceneRect().height()
        
        xpos = round(self.lview_length*value/self.numberOfFrames)
        self.lview.updateMarker(xpos)
        
    def changeState(self, value):
        self.c.updateBool.emit(value)
        self.wid.run()

    def useGated(self, value):
        self.gated = value

    def errorMessage(self):
        """Helper function for errors"""

        warning = QMessageBox()
        warning.setWindowModality(Qt.WindowModal)
        warning.setWindowTitle('Error')
        warning.setText('Segmentation must be performed first')
        warning.exec_()

    def successMessage(self, task):
        """Helper function for success messages"""

        success = QMessageBox()
        success.setWindowModality(Qt.WindowModal)
        success.setWindowTitle('Status')
        success.setText(task + ' has been successfully completed')
        success.exec_()

@click.group()
def cli():
    pass
    
@cli.command()
@click.argument("dicom_path")
@click.option('--gated', '-g', is_flag=True, help="Select whether gated images should be segmented")
@click.option('--fname', '-f', default="contours", type=str, help="Output filename for the contours")
def segment(dicom_path, gated, fname):
    #"python DeepIVUS.py segment C:\Users\David\Downloads\FILE0000 -g=True"
    click.echo(dicom_path)
    dicom = dcm.read_file(dicom_path, force=True)
    images = dicom.pixel_array
    click.echo("Successfully read dicom file")
    numberOfFrames = dicom.NumberOfFrames
    resolution = dicom.PixelSpacing[0]

    if dicom.get('IVUSPullbackRate'):
       ivusPullbackRate = float(dicom.IVUSPullbackRate)
    elif dicom.get('0x000b1001'):
        # check Boston private tag
        ivusPullbackRate = float(dicom[0x000b1001].value)
    else:
        ivusPullbackRate = 0.5

    if gated:
        gatedFrames = IVUS_gating(images, ivusPullbackRate, dicom.CineRate, False)
        click.echo("Segmenting gated images")
        image_dim = images.shape
        masks = np.zeros((numberOfFrames, image_dim[1], image_dim[2]), dtype=np.uint8)
        #masks_gated = predict(images[gatedFrames, : ,:])
        masks_gated = np.ones((numberOfFrames, image_dim[1], image_dim[2]), dtype=np.uint8)
        masks[gatedFrames, :, :] = masks_gated
    else:
        masks = predict(images)

    levels = [1.5, 2.5]
    #metrics = self.computeMetrics(masks)
    image_shape = masks.shape[1:3]
    masks = mask_image(masks, catheter=0)
    _, _, lumen, plaque = get_contours(masks, levels, image_shape) 
    
    x, y = [], []
    for i in range(len(lumen[0])):
        x.append(lumen[0][i])
        x.append(plaque[0][i])
        y.append(lumen[1][i])
        y.append(plaque[1][i])

    frames = list(range(numberOfFrames))
    write_xml(x, y, images.shape, resolution, ivusPullbackRate, frames, fname)

    """Writes a report file containing lumen area, plaque, area, vessel area, plaque burden, phenotype"""
    numberOfFrames = len(lumen[0])
    lumen_area = np.zeros((numberOfFrames))
    plaque_area = np.zeros_like(lumen_area)
    plaque_burden = np.zeros_like(lumen_area)
    for i in range(numberOfFrames):
        if lumen[0][i]:
            lumen_area[i] = (0.5*np.abs(np.dot(lumen[0][i],np.roll(lumen[1][i],1))-np.dot(lumen[1][i],np.roll(lumen[0][i],1))))*resolution**2
            plaque_area[i] = (0.5*np.abs(np.dot(plaque[0][i],np.roll(plaque[1][i],1))-np.dot(plaque[1][i],np.roll(plaque[0][i],1))))*resolution**2
            plaque_burden[i] = (plaque_area[i]/(lumen_area[i] + plaque_area[i]))*100

    phenotype = [0]*numberOfFrames
    patientName = self.infoTable.item(0, 1).text()
    vessel_area = lumen_area + plaque_area

    f = open(patientName + '_report.txt', 'w')
    f.write('Frame\tPosition (mm)\tLumen area (mm\N{SUPERSCRIPT TWO})\tPlaque area (mm\N{SUPERSCRIPT TWO})\tVessel area (mm\N{SUPERSCRIPT TWO})\tPlaque burden (%)\tphenotype\n')

    click.echo("Writing report")
    for i, frame in enumerate(frames):
        f.write('{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{}\n'.format(frame, self.pullbackLength[frame], lumen_area[frame], plaque_area[frame], vessel_area[frame], plaque_burden[frame], phenotype[frame]))
    f.close()
            
@cli.command()
@click.argument("dicom_path")
@click.option('--write', '-w', is_flag=True, help="Write gated frames as jpgs")
def gate(dicom_path, write):
    dicom = dcm.read_file(dicom_path, force=True)
    images = dicom.pixel_array
    click.echo("Successfully read dicom file")

    if dicom.get('IVUSPullbackRate'):
       ivusPullbackRate = float(dicom.IVUSPullbackRate)
    elif dicom.get('0x000b1001'):
        # check Boston private tag
        ivusPullbackRate = float(dicom[0x000b1001].value)
    else:
        ivusPullbackRate = 0.5

    click.echo("Writing end diastolic frame numbers to file")
    gatedFrames = IVUS_gating(images, ivusPullbackRate, dicom.CineRate, False)
    f = open("gated_idx.txt", "w")
    [f.write(f"{val}\n") for val in gatedFrames]
    f.close()
    
    if write is not None:
        click.echo("Writing end diastolic images")
        for i in range(len(gatedFrames)):
            img = Image.fromarray(images[gatedFrames[i], :, :])
            img.save(f"{gatedFrames[i]}.jpg")

@cli.command()
def gui():
    click.echo("Launching DeepIVUS from CLI")
    app = QApplication(sys.argv)
    ex = Master()
    sys.exit(app.exec_())


if __name__ == '__main__':
    cli()