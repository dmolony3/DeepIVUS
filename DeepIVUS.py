from PyQt5.QtWidgets import (QMainWindow, QWidget, QSlider, QApplication, 
    QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QLabel, QSizePolicy, QInputDialog, QErrorMessage, QMessageBox, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QSize, QTimer
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPolygon, QImage, QPixmap, QIcon
import sys
import time
import read_xml, pydicom as dcm
from IVUS_gating import *
from IVUS_prediction import predict
from write_xml import *

class Communicate(QObject):
    updateBW = pyqtSignal(int)
    updateBool = pyqtSignal(bool)

class Slider(QSlider):
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
            self.setValue(self.value() + 1)
            time.sleep(0.1)
            self.setValue(self.value() - 1)

    def findFrame(self, currentFrame):
        frameDiff = [abs(val - currentFrame) for val in self.gatedFrames]
        currentGatedFrame = [idx for idx in range(len(frameDiff)) if frameDiff[idx] == min(frameDiff)][0]
        return currentGatedFrame

    def addGatedFrames(self, gatedFrames):
        """Stores the gated frames so that these can be cycled through"""
        self.gatedFrames = gatedFrames
        self.maxFrame = len(self.gatedFrames) - 1

class Display(QWidget):
    def __init__(self):
        super().__init__()
        self.frame=0
        self.image=QImage(QPixmap(500, 500).toImage())
        self.lumen = ([], [])
        self.plaque = ([], [])
        self.hide = True
        sizePolicy = QSizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Fixed)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(500, 500))
        self.setMaximumSize(QSize(500, 500))

    def setData(self, lumen, plaque, images):
        self.lumen = lumen
        self.plaque = plaque
        self.images = images
        self.imsize = self.images.shape
        self.poly1, _, _ = self.polygon(self.lumen[0], self.lumen[1])
        self.poly2, _, _ = self.polygon(self.plaque[0], self.plaque[1])
        self.displayImage()

    def displayImage(self):
        if len(self.images.shape) == 3:
            self.image=QImage(self.images[self.frame, : ,:], self.imsize[1], self.imsize[2], QImage.Format_Grayscale8)
        else:
            bytesPerLine = 3*self.imsize[2]
            current_image = self.images[self.frame, : ,:, :].astype(np.uint8, order='C', casting='unsafe')
            self.image=QImage(current_image.data, self.imsize[1], self.imsize[2], bytesPerLine, QImage.Format_RGB888)       

    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap(self.image)
        painter.drawPixmap(self.rect(), pixmap)
        pen1 = QPen(Qt.red, 1)
        painter.setPen(pen1)
        if self.hide == False:
            painter.drawPolyline(self.poly1)
        pen2 = QPen(Qt.yellow, 1)
        painter.setPen(pen2)
        if self.hide == False:
            painter.drawPolyline(self.poly2)

    def polygon(self, x, y):
        x = x[self.frame]
        y = y[self.frame]
        poly = QPolygon([QPoint(x[i], y[i]) for i in range(len(x))])
        return poly, x, y

    def run(self):
        self.poly1, x, y = self.polygon(self.lumen[0], self.lumen[1])
        self.poly2, _, _ = self.polygon(self.plaque[0], self.plaque[1])
        self.displayImage()

    def setFrame(self, value):
        self.frame = value

    def setDisplay(self, hide):
        self.hide = hide

class Master(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image=False
        self.contours=False
        self.segmentation = 0
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 100, 1000, 750)
        self.lumen = ()
        self.plaque = ()

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

        self.wid = Display()
        #self.wid.setData(self.lumen, self.plaque, self.images)

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
            if self.hideBox.isChecked() == False:
                self.hideBox.setChecked(True)
            elif self.hideBox.isChecked() == True:
                self.hideBox.setChecked(False)
            self.hideBox.setChecked(self.hideBox.isChecked())
        elif key == Qt.Key_J:
            currentFrame = self.slider.value()
            self.slider.setValue(currentFrame+1)
            time.sleep(0.1)
            self.slider.setValue(currentFrame)

    def parseDICOM(self):
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
            self.rows = self.dicom.shape[1]

        if self.dicom.get('Manufacturer'):
            self.manufacturer = self.dicom.Manufacturer
        else:
            self.manufacturer = 'Unknown'

        if self.dicom.get('ManufacturerModelName'):
            self.model = self.dicom.ManufacturerModelName
        else:
            self.model = 'Unknown'

    def readDICOM(self):
        options=QFileDialog.Options()
        options = QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "DICOM files (*.dcm);;All files (*)", options=options)

        if fileName:
            self.dicom = dcm.read_file(fileName)
            self.images = self.dicom.pixel_array
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
        """Reads contours saved in xml format (Echoplaque compatible)"""
        if self.image==False:
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
                self.lumen = self.mapToList(self.lumen)
                self.plaque = self.mapToList(self.plaque)
                self.stent = self.mapToList(self.stent)
                self.contours=True
                self.resizeContours()
                self.wid.setData(self.lumen, self.plaque, self.images)
                self.hideBox.setChecked(False)

    def writeContours(self):
        """Writes contours to an xml file compatible with Echoplaque"""
        patientName = self.infoTable.item(0, 1).text()
        # reformat data for compatibility with write_xml function
        x, y = [], []
        for i in range(len(self.lumenCopy[0])):
            x.append(self.lumenCopy[0][i])
            x.append(self.plaqueCopy[0][i])
            y.append(self.lumenCopy[1][i])
            y.append(self.plaqueCopy[1][i])
        if self.segmentation == 0:
            self.errorMessage()
        else:
            frames = list(range(self.numberOfFrames))
            write_xml(x, y, self.images.shape, self.resolution, self.ivusPullbackRate, frames, patientName)
        self.successMessage('Writing contours')

    def report(self):
        """Writes a report file containing lumen area, plaque, area, vessel area, plaque burden, phenotype"""
        if self.segmentation == 0:
            self.errorMessage()
        else:
            phenotype = [0]*self.numberOfFrames
            patientName = self.infoTable.item(0, 1).text()
            lumen_area, plaque_area, plaque_burden = self.metrics
            vessel_area = lumen_area + plaque_area
            if self.useGatedBox.isChecked() == True:
                frames = self.gatedFrames
            else:
                frames = list(range(self.numberOfFrames))

            f = open(patientName + '_report.txt', 'w')
            f.write('Frame\tLumen area\tPlaque area\tVessel area\tPlaque burden\tphenotype\n')
            for i, frame in enumerate(frames):
                f.write('{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t{}\n'.format(frame, lumen_area[frame], plaque_area[frame], vessel_area[frame], plaque_burden[frame], phenotype[frame]))
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
        if self.useGatedBox.isChecked() == True:
            masks = np.zeros((self.numberOfFrames, image_dim[1], image_dim[2]), dtype=np.uint8)
            masks_gated = predict(self.images[self.gatedFrames, : ,:])
            masks[self.gatedFrames, :, :] = masks_gated
        else:
            masks = predict(self.images)
        # compute metrics such as plaque burden
        self.metrics = self.computeMetrics(masks)
        self.segmentation = 1

        # convert masks to contours
        self.lumen, self.plaque = self.maskToContours(masks)

        # stent contours currently unsupported so create empty list
        self.stent = [[[] for i in range(image_dim[0])], [[] for i in range(image_dim[0])]]
        self.wid.setData(self.lumen, self.plaque, self.images)
        self.hideBox.setChecked(False)
        self.resizeContours()
        self.successMessage('Segmentation')

    def maskToContours(self, masks):
        """Convert numpy mask to IVUS contours """
        levels = [1.5, 2.5]
        image_shape = masks.shape[1:3]
        masks = mask_image(masks, catheter=0)
        _, _, lumen_pred, plaque_pred = get_contours(masks, levels, image_shape) 

        return lumen_pred, plaque_pred

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
        x, y = contours
        x = [list(x[i]) for i in range(0, len(x))]
        y = [list(y[i]) for i in range(0, len(y))]
        return (x, y)

    def changeValue(self, value):
        self.c.updateBW.emit(value)
        self.wid.run()
        self.wid.repaint()
        self.text.setText("Frame {}".format(value))        

    def changeState(self, value):
        self.c.updateBool.emit(value)
        self.wid.run()
        self.wid.repaint()

    def useGated(self, value):
        self.gated = value

    def errorMessage(self):
        warning = QMessageBox()
        warning.setWindowModality(Qt.WindowModal)
        warning.setWindowTitle('Error')
        warning.setText('Segmentation must be performed first')
        warning.exec_()

    def successMessage(self, task):
        success = QMessageBox()
        success.setWindowModality(Qt.WindowModal)
        success.setWindowTitle('Status')
        success.setText(task + ' has been successfully completed')
        success.exec_()

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = Master()
    sys.exit(app.exec_())
