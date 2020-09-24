from PyQt5.QtWidgets import (QMainWindow, QWidget, QSlider, QApplication, QHeaderView,
    QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QLabel, QSizePolicy, QInputDialog, QErrorMessage, QMessageBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QIcon
from IVUS_gating import IVUS_gating
from IVUS_prediction import predict
from write_xml import write_xml, get_contours, mask_image
from display import Display
import os, sys, time, read_xml
import pydicom as dcm
import numpy as np

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
        self.setMinimumSize(QSize(500, 25))
        self.setMaximumSize(QSize(500, 25))
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
            time.sleep(0.1)
            self.setValue(self.value() + 1)
            time.sleep(0.1)
            self.setValue(self.value() + 1)
            time.sleep(0.1)
            self.setValue(self.value() - 1)

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
        self.setGeometry(300, 100, 1000, 750)
        self.addToolBar("MY Window")

        layout = QHBoxLayout()
        vbox1 = QVBoxLayout()
        vbox2 = QVBoxLayout()
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
        writeButton = QPushButton('Write Contours')
        reportButton = QPushButton('Write Report')

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
        gatingButton.clicked.connect(self.gate)
        writeButton.clicked.connect(self.writeContours)
        reportButton.clicked.connect(self.report)

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
        vbox1.addWidget(self.slider)
        vbox1.addWidget(self.text)

        vbox2.addWidget(self.hideBox)
        vbox2.addWidget(self.useGatedBox)
        vbox2.addWidget(dicomButton)
        vbox2.addWidget(contoursButton)
        vbox2.addWidget(gatingButton)
        vbox2.addWidget(segmentButton)
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
            time.sleep(0.1)
            self.slider.setValue(currentFrame)

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
            self.ivusPullbackRate = self.dicom.IVUSPullbackRate
        # check Boston private tag
        elif self.dicom.get(0x000b1001):
            self.ivusPullbackRate = self.dicom[0x000b1001].value
        else:
            self.ivusPullbackRate = ''

        if self.dicom.get('FrameTimeVector'):
            frameTimeVector = self.dicom.get('FrameTimeVector')
            frameTimeVector = [float(frame) for frame in frameTimeVector]
            pullbackTime = np.cumsum(frameTimeVector)/1000 # assume in ms
            self.pullbackLength = pullbackTime*float(self.ivusPullbackRate)
        else:
            self.pullbackLength = np.zeros(self.images.shape[0], 1)

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
                self.dicom = dcm.read_file(fileName)
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

            self.wid.setData(self.lumen, self.plaque, self.images)
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
                    #self.resizeContours()
                    self.wid.setData(self.lumen, self.plaque, self.images)
                    self.hideBox.setChecked(False)

                    gatedFrames = [frame for frame in range(len(self.lumen[0])) if self.lumen[0][frame] or self.plaque[0][frame]]
                    self.gatedFrames = gatedFrames
                    self.useGatedBox.setChecked(True)
                    self.slider.addGatedFrames(self.gatedFrames)

    def writeContours(self):
        """Writes contours to an xml file compatible with Echoplaque"""

        patientName = self.infoTable.item(0, 1).text()
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

            write_xml(x, y, self.images.shape, self.resolution, self.ivusPullbackRate, frames, patientName)

            self.successMessage('Writing contours')

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
            f.write('Frame\tPosition\tLumen area\tPlaque area\tVessel area\tPlaque burden\tphenotype\n')

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

        save_path = os.path.join(os.getcwd(), 'model', 'saved_model.pb')
        if not os.path.isfile(save_path):
            message= "No saved weights have been found, segmentation will be unsuccessful, check that weights are saved in {}".format(os.path.join(os.getcwd(), 'model'))
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

        self.wid.setData(self.lumen, self.plaque, self.images)
        self.hideBox.setChecked(False)
        #self.resizeContours()
        self.successMessage('Segmentation')

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

    def resizeContours(self):
        """If image is not 500x500 resize the contours for appropriate display"""

        scale = 500/self.images.shape[1]
        print('Scaling images by {} for display'.format(scale))
        self.lumenCopy = (self.lumen[0][:], self.lumen[1][:])
        self.plaqueCopy = (self.plaque[0][:], self.plaque[1][:])
        self.stentCopy = (self.stent[0][:], self.stent[1][:])
        self.lumen = self.resize(self.lumen, scale)
        self.plaque = self.resize(self.plaque, scale)
        self.stent = self.resize(self.stent, scale)

    def resize(self, contours, scale):
        for idx in range(len(contours[0])):
            if contours[0][idx]:
                contours[0][idx] = [int(val*scale) for val in contours[0][idx]]
        for idx in range(len(contours[1])):
            if contours[0][idx]:
                contours[1][idx] = [int(val*scale) for val in contours[1][idx]]
        return (contours[0], contours[1])

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

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = Master()
    sys.exit(app.exec_())
