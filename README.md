# DeepIVUS
**DeepIVUS** is a platform for deep learning based segmentation of Intrvascular Ultrasound (IVUS) images. The platform consists of a graphical user interface and serves to provide the following capabilities. 

* Viewer of IVUS pullbacks
* End diastolic gating of IVUS pullbacks
* Segmentation of internal and external elastic lamina
* Phenotyping of IVUS pullbacks
* Generation of IVUS pullback report

**CURRENT VERSION DOES NOT SUPPORT PHENOTYPING**

## Reading and Display IVUS pullbacks
IVUS pullbacks in DICOM (.dcm) format can be loaded. Contours are stored in a .xml format and can be loaded for display.

![Alt Text](/Media/GUI.gif)

## End-diatolic gating of IVUS pullbacks
End diastolic images from the pullback can be extracted by presssing the *Extract Diastolic Frames* button.

![Alt Text](/Media/Gating.gif)

## Segmentation of IVUS pullbacks
IVUS pullbacks can be segmented by pressing the *Segment* button. It is highly recommended to extract end-diastolic frames prior to segmentation. Checking the *Gated Frames* box will segment only the end-diastolic images. If this is unchecked segmentation will take a significantly longer time. 

![Alt Text](/Media/Segmentation.gif)

## Report Generation
A report in the form of a text file can be generated for each frame in the pullback by pressing *Write Report*. If *Gated Frames* is checked then the report will only include the end-diastolic images. The report consists of the following variables  
**Frame, Lumen area, Plaque area, Vessel area, Plaque burden, Phenotype**

## Requirements
pydicom  
numpy  
PyQt5  
scikit-image  
tensorflow
