from PyQt5.QtWidgets import (QMainWindow, QWidget, QSlider, QApplication, QHeaderView, QStyle, 
    QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QLabel, QSizePolicy, QInputDialog, QErrorMessage, QMessageBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon
from IVUS_gating import IVUS_gating
from IVUS_prediction import predict
from write_xml import write_xml, get_contours, mask_image
from display import Display
from PIL import Image
import os, sys, time, read_xml
import pydicom as dcm
import numpy as np
import subprocess
import click

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
        self.lumen = ()
        self.plaque = ()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1200, 1200)
        self.display_size = 800
        self.addToolBar("MY Window")
        self.showMaximized()

        layout = QHBoxLayout()
        vbox1 = QVBoxLayout()
        vbox2 = QVBoxLayout()
        vbox1hbox1 = QHBoxLayout()

        vbox1.setContentsMargins(0, 0, 100, 100)
        vbox2.setContentsMargins(100, 0, 0, 100)
        vbox2hbox1 = QHBoxLayout()
        vbox2.addLayout(vbox2hbox1)
        layout.addLayout(vbox1)
        layout.addLayout(vbox2)

        dicomButton = QPushButton('Read DICOM')
        contoursButton = QPushButton('Read Contours')
        gatingButton = QPushButton('Extract Diastolic Frames')
        segmentButton = QPushButton('Segment')
        splineButton = QPushButton('Manual Contour')
        writeButton = QPushButton('Write Contours')
        reportButton = QPushButton('Write Report')

        dicomButton.setToolTip("Load images in .dcm format")
        contoursButton.setToolTip("Load saved contours in .xml format")
        gatingButton.setToolTip("Extract end diastolic images from pullback")
        segmentButton.setToolTip("Run deep learning based segmentation of lumen and plaque")
        splineButton.setToolTip("Manually draw new contour for lumen, plaque or stent")
        writeButton.setToolTip("Save contours in .xml file")
        reportButton.setToolTip("Write report containing, lumen, plaque and vessel areas and plaque burden")

        hideHeader1 = QHeaderView(Qt.Vertical)
        hideHeader1.hide()
        hideHeader2 = QHeaderView(Qt.Horizontal)
        hideHeader2.hide()
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
        self.infoTable.horizontalHeader().setStretchLastSection(True)

        dicomButton.clicked.connect(self.readDICOM)
        contoursButton.clicked.connect(self.readContours)
        segmentButton.clicked.connect(self.segment)
        splineButton.clicked.connect(self.newSpline)
        gatingButton.clicked.connect(self.gate)
        writeButton.clicked.connect(self.writeContours)
        reportButton.clicked.connect(self.report)

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

        self.text = QLabel()
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setText("Frame {}".format(self.slider.value())) 

        vbox1.addWidget(self.wid)
        vbox1hbox1.addWidget(self.playButton)
        vbox1hbox1.addWidget(self.slider)
        vbox1.addLayout(vbox1hbox1)
        vbox1.addWidget(self.text)

        vbox2.addWidget(self.hideBox)
        vbox2.addWidget(self.useGatedBox)
        vbox2.addWidget(dicomButton)
        vbox2.addWidget(contoursButton)
        vbox2.addWidget(gatingButton)
        vbox2.addWidget(segmentButton)
        vbox2.addWidget(splineButton)
        vbox2.addWidget(writeButton)
        vbox2.addWidget(reportButton)
        vbox2hbox1.addWidget(self.infoTable)


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

    def parseDICOM(self):
        """Parses DICOM metadata"""

        if (len(self.dicom.PatientName.encode('ascii')) > 0):
            self.patientName = self.dicom.PatientName.original_string.decode('utf-8')
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
            self.slider.setValue(self.numberOfFrames-1)

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

        if self.contours:
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
   
    def newSpline(self):
        """Create a message box to choose what spline to create"""

        b3 = QPushButton("lumen")
        b2 = QPushButton("Vessel")
        b1 = QPushButton("Stent")

        d = QMessageBox()
        d.setText("Select which contour to draw")
        d.setInformativeText("Contour must be closed before proceeding by clicking on initial point")
        d.setWindowModality(Qt.WindowModal)
        d.addButton(b1, 0)
        d.addButton(b2, 1)
        d.addButton(b3, 2)
 
        result = d.exec_()

        self.wid.new(result)
        self.hideBox.setChecked(False)
    
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
                plaque_area[i] = self.contourArea(plaque[0][i], plaque[1][i])*self.resolution**2 - lumen_area[i]
                plaque_burden[i] = (plaque_area[i]/(lumen_area[i] + plaque_area[i]))*100

        return (lumen_area, plaque_area, plaque_burden)

    def mapToList(self, contours):
        """Converts map to list"""

        x, y = contours
        x = [list(x[i]) for i in range(0, len(x))]
        y = [list(y[i]) for i in range(0, len(y))]

        return (x, y)

    def changeValue(self, value):
        self.c.updateBW.emit(value)
        self.wid.run()
        self.text.setText("Frame {}".format(value))        

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