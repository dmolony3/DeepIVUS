from PyQt5.QtWidgets import (QMainWindow, QWidget, QSlider, QApplication, 
    QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QLabel, QSizePolicy, QErrorMessage, QFileDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QPainter, QFont, QColor, QPen, QPolygon, QImage, QPixmap
import sys
import read_xml, pydicom as dcm
from IVUS_gating import *

class Communicate(QObject):
    updateBW = pyqtSignal(int)
    updateBool = pyqtSignal(bool)

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
        self.image=QImage(self.images[self.frame, : ,:], self.imsize[1], self.imsize[2], QImage.Format_Grayscale8)

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
        self.image=QImage(self.images[self.frame, : ,:], self.imsize[1], self.imsize[2], QImage.Format_Grayscale8) 

    def setFrame(self, value):
        self.frame = value

    def setDisplay(self, hide):
        self.hide = hide

class Master(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image=False
        self.contours=False
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
        writeButton = QPushButton('Write Report')

        self.infoTable = QTableWidget()
        self.infoTable.setRowCount(8)
        self.infoTable.setColumnCount(2)
        self.infoTable.setItem(0, 0, QTableWidgetItem('Patient Name'))
        self.infoTable.setItem(1, 0, QTableWidgetItem('Patient DOB'))
        self.infoTable.setItem(2, 0, QTableWidgetItem('Patient Sex'))
        self.infoTable.setItem(3, 0, QTableWidgetItem('Pullback Speed'))
        self.infoTable.setItem(4, 0, QTableWidgetItem('Resolution'))
        self.infoTable.setItem(5, 0, QTableWidgetItem('Dimensions'))
        self.infoTable.setItem(6, 0, QTableWidgetItem('Manufacturer'))
        self.infoTable.setItem(7, 0, QTableWidgetItem('Model'))

        dicomButton.clicked.connect(self.readDICOM)
        contoursButton.clicked.connect(self.readContours)
        segmentButton.clicked.connect(self.segment)
        gatingButton.clicked.connect(self.gate)
        """
        self.lumen, self.plaque, self.stent, self.resolution, frames = read_xml.read('/home/ubuntu/Documents/Qt/1-63/1-63.xml')
        self.lumen = self.mapToList(self.lumen)
        self.plaque = self.mapToList(self.plaque)
        self.stent = self.mapToList(self.stent)
        dicom = dcm.read_file('/home/ubuntu/Documents/Qt/1-63/2.16.840.1.114380.1.1.347327.186.1.1.20100506085134890.3.dcm')
        self.images = dicom.pixel_array
        """

        self.slider = QSlider(Qt.Horizontal)     
        #self.slider.setRange(0, self.images.shape[0])
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        sizePolicy = QSizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Fixed)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.slider.setSizePolicy(sizePolicy)
        self.slider.setMinimumSize(QSize(500, 25))
        self.slider.setMaximumSize(QSize(500, 25))
        self.slider.valueChanged[int].connect(self.changeValue)
        #self.slider.keyPressEvent = self.keyPressEvent()

        self.hideBox = QCheckBox('Hide Contours')
        self.hideBox.setChecked(True)
        self.hideBox.stateChanged[int].connect(self.changeState)
        self.useGatedBox = QCheckBox('Display Gated Frames')
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
        vbox2hbox1.addWidget(self.infoTable)


        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.show()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Right:
            self.slider.setFrame(self.slider.value() + 1)
            """
            if self.useGatedBox.isChecked() == True:
                print('Using gated frames')
                currentFrame = [abs(val - self.slider.value()) for val in gatedFrames]
                difference = min(currentFrame)
                currentGatedFrame = [idx for idx in range(len(currentFrame)) if currentFrame[idx] == difference][0]
                currentGatedFrame = currentGatedFrame + 1
                self.slider.setFrame(self.gatedFrames[currentGatedFrame])"""
        elif key == Qt.Key_Left:
            self.slider.setFrame(self.slider.value() - 1)
        elif key == Qt.Key_Q:
            self.close()
        elif key == Qt.Key_H:
            if self.hideBox.isChecked() == False:
                self.hideBox.setChecked(True)
            elif self.hideBox.isChecked() == True:
                self.hideBox.setChecked(False)
            self.hideBox.setChecked(self.hideBox.isChecked())

    def parseDICOM(self):
        if len(self.dicom.PatientName.encode('ascii')) > 0:
            self.patientName = self.dicom.PatientName
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
        self.ivusPullbackRate = self.dicom.IVUSPullbackRate
        self.pixelSpacing = self.dicom.SequenceOfUltrasoundRegions[0].PhysicalDeltaX
        self.rows = self.dicom.Rows
        if len(self.dicom.Manufacturer) > 0:
            self.manufacturer = self.dicom.Manufacturer
        else:
            self.manufacturer = 'Unknown'
        if len(self.dicom.ManufacturerModelName) > 0:
            self.model = self.dicom.ManufacturerModelName
        else:
            self.model = 'Unknown'

    def readDICOM(self):
        options=QFileDialog.Options()
        options = QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "DICOM files (*.dcm);;All files (*)", options=options)

        self.dicom = dcm.read_file(fileName)
        self.images = self.dicom.pixel_array
        self.slider.setMaximum(self.dicom.NumberOfFrames)
        self.image=True
        self.parseDICOM()
        self.numberOfFrames = int(self.dicom.NumberOfFrames)
        self.infoTable.setItem(0, 1, QTableWidgetItem(self.patientName))
        self.infoTable.setItem(1, 1, QTableWidgetItem(self.patientBirthDate))
        self.infoTable.setItem(2, 1, QTableWidgetItem(self.patientSex))
        self.infoTable.setItem(3, 1, QTableWidgetItem(str(self.ivusPullbackRate)))
        self.infoTable.setItem(4, 1, QTableWidgetItem(str(self.pixelSpacing)))
        self.infoTable.setItem(5, 1, QTableWidgetItem(str(self.rows)))
        self.infoTable.setItem(6, 1, QTableWidgetItem(self.manufacturer))        
        self.infoTable.setItem(7, 1, QTableWidgetItem((self.model)))
        
        if not self.lumen:
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
            self.lumen, self.plaque, self.stent, self.resolution, frames = read_xml.read(fileName)
            self.lumen = self.mapToList(self.lumen)
            self.plaque = self.mapToList(self.plaque)
            self.stent = self.mapToList(self.stent)
            self.contours=True
            self.resizeContours()
            self.wid.setData(self.lumen, self.plaque, self.images)
            self.hideBox.setChecked(False)

    def gate(self):
        """Extract end diastolic frames and stores in new variable"""
        self.gatedFrames = IVUS_gating(self.images, self.ivusPullbackRate, self.dicom.CineRate)

    def segment(self):
        """Segmentation and phenotyping of IVUS images"""
        warning = QErrorMessage()
        warning.setWindowModality(Qt.WindowModal)
        warning.showMessage('Warning: IVUS Phenotyping is currently only supported for 20MHz images. Interpret other images with extreme caution')
        warning.exec_()


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

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = Master()
    sys.exit(app.exec_())
