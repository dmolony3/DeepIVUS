# DeepIVUS
**DeepIVUS** is a platform for deep learning based segmentation of Intrvascular Ultrasound (IVUS) images. The platform consists of a graphical user interface and serves to provide the following capabilities. 

* Viewer of IVUS pullbacks
* End diastolic gating of IVUS pullbacks
* Segmentation of internal and external elastic lamina.
* Phenotyping of IVUS pullbacks

**CURRENT VERSION ONLY SUPPORTS IVUS PULLBACK VIEWER**

## Reading and Display Images
IVUS pullbacks in DICOM (.dcm) format can be loaded. Contours are stored in a .xml format and can be loaded for display.

![Alt Text](/Media/GUI.gif)

## Requirements
pydicom  
numpy  
PyQt5  
tensorflow
