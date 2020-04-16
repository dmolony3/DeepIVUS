<p align="center">
  <br> 
  <img src="/Media/DeepIVUS_logo.png">
  <br>
<p>
<h3 align="center">A Platform for Coronary Artery Intravascular Ultrasound Segmentation and Analysis </h3>

**DeepIVUS** is a platform for deep learning based segmentation of coronary artery Intravascular Ultrasound (IVUS) images. The platform consists of a graphical user interface and serves to provide the following capabilities. 

* Viewer of IVUS pullbacks
* End diastolic gating of IVUS pullbacks
* Segmentation of internal and external elastic lamina
* Phenotyping of IVUS pullbacks
* Generation of IVUS pullback report

**CURRENT VERSION DOES NOT SUPPORT PHENOTYPING**

## Installation
Recommended way to install is as a virtual environment with Anaconda.
On a windows computer follow the following instructions
1. Download and install Anaconda from [here](https://www.anaconda.com/distribution/#download-section).
2. Download DeepIVUS from [here](https://github.com/dmolony3/DeepIVUS/archive/master.zip).
3. Download the trained weights from [here](https://drive.google.com/open?id=1GlMc7uqZhI6yt9PFv-HhrO14PXDqA4FL) and extract to the DeepIVUS folder. After extraction the files should be in the **model** folder contained within DeepIVUS. If not, create this folder and move the files here.
4. Open Anaconda Prompt and navigate to the folder containing the model using the following command (just remember to switch "C:/Users/David/Documents/" to whereever you downloaded DeepIVUS to):
```
cd C:/Users/David/Documents/DeepIVUS
```
5. Create a virtual environment with the following command:
```
conda create -n DeepIVUS python=3.6
```
6. Activate the virtual environment with the following command:
```
conda activate DeepIVUS
```
7. Install all the dependency packages using the following commmand:
```
pip install -r requirements.txt
```
8. Run the program using the following command:
```
python DeepIVUS.py
```
9. After installation to use the program again you just need to repeats steps 4-8 but skip step 5 and step 7.

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

## DeepIVUS Project Roadmap
* Ability to manually edit contours  
* Deep ensembles for model uncertainty
