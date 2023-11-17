from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsLineItem, QHBoxLayout, QWidget, QFrame, QLabel, QVBoxLayout, QFileDialog
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QPoint, QLineF
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor, QFont, QPainter, QPainterPath
import math
import numpy as np
from PIL import ImageDraw, Image
import xml.etree.ElementTree as ET
import os

class FileDialog(QFileDialog):
    def __init__(self):
        QFileDialog.__init__(self)
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        box = QVBoxLayout()
        
        self.setFixedSize(self.width() + 500, self.height() + 100)
        
        self.preview = QLabel("Preview", self)
        self.preview.setFixedSize(500, 250)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setObjectName("preview")
        self.setNameFilter("project (*.proj);;All files (*)")
        
        self.previewInfo = QLabel("", self)
        self.previewInfo.setFixedSize(500, 150)
        self.previewInfo.setAlignment(Qt.AlignLeft)
        self.previewInfo.setObjectName("previewInfo")

        box.addWidget(self.preview)
        #box.addStretch()
        box.addWidget(self.previewInfo)
        #box.addStretch()
        
        self.layout().addLayout(box, 1, 3, 1, 1)
        
        self.currentChanged.connect(self.onChange)
        #self.fileSelected.connect(self.onFileSelected)
        self.validFile = False
        
    def sendErrorMessage():
        error = QMessageBox()
        error.setIcon(QMessageBox.Critical)
        error.setWindowTitle("Error")
        error.setModal(True)
        error.setWindowModality(Qt.WindowModal)
        error.setText("File is not a valid project file and could not be loaded")
        error.exec_()
        
    def onChange(self, path):
        """Updates the preview if a valid project is selected"""
        if  os.path.splitext(path)[-1] == ".proj":
            project_info = self.readProject(path)
        else:
            self.files = {}
            self.validFile = False
            lview = None
       
        if not self.validFile:
            self.preview.setText("Preview")
            self.previewInfo.setText("")
        else:
            lview = project_info["lview"]
            pixmap = QPixmap(lview)
            lumenvolume = project_info["lumenvolume"]
            plaquevolume = project_info["plaquevolume"]
            minimumlumenarea = project_info["minimumlumenarea"]
            print(lumenvolume)
            
            self.preview.setPixmap(pixmap.scaled(self.preview.width(), self.preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.previewInfo.setText(f"Lumen volume: {lumenvolume}mm\u00b3\nPlaque volume: {plaquevolume}mm\u00b3\nMinium lumen area: {minimumlumenarea}mm\u00b2")
        
    def getFileSelected(self):
        return self.files
        
    def readProject(self, path):
        # save as pickled dicom?
        tree = ET.parse(path)
        root = tree.getroot()

        project_info = {}
        if root.tag != "DeepIVUSProject":
            self.validFile = False
            return
        else:
            self.validFile = True
        
        self.files = {}
        for child in root.getchildren():
            if child.tag == "dicompath":
                project_info["dicom"] = child.text
                self.files["dicom"] = child.text
            if child.tag == "contourpath":
                project_info["contours"] = child.text
                self.files["contours"] = child.text
            if child.tag == "previewpath":
                project_info["lview"] = child.text
            if child.tag == "measurements":
                for subchild in child.getchildren():
                    if subchild.tag == "lumenvolume":
                        project_info["lumenvolume"] = subchild.text
                    if subchild.tag == "plaquevolume":
                        project_info["plaquevolume"] = subchild.text
                    if subchild.tag == "minimumlumenarea":
                        project_info["minimumlumenarea"] = subchild.text
        return project_info