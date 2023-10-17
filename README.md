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

#### Installion
It is recommended to first setup a virtual environment using Anaconda or another environment manager
```
git clone https://github.com/dmolony3/DeepIVUS.git
cd DeepIVUS
python -m pip install .
```

#### Installation (detailed)
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
python -m pip install .
```
8. Run the program using the following command:
```
DeepIVUS gui
```
9. After installation to use the program again you just need to repeats steps 4-8 but skip step 5 and step 7.


#### Install binary
A Windows 11 binary is available from here
https://github.com/dmolony3/DeepIVUS/releases

#### Model weights
Model weights are accessible from here.


## Launching the GUI
DeepIVUS is launced directly from the command line. This will open the GUI and functionality is explained in more detail below 
```
DeepIVUS gui
```

## Reading and Display IVUS pullbacks
IVUS pullbacks in DICOM (.dcm) format can be loaded. Contours are stored in a .xml format and can be loaded for display.

![Alt Text](/Media/GUI.gif)

## End-diatolic gating of IVUS pullbacks
End diastolic images from the pullback can be extracted by presssing the *Extract Diastolic Frames* button.

![Automatic Gating](/Media/Gating.gif)

## Segmentation of IVUS pullbacks
IVUS pullbacks can be segmented by pressing the *Segment* button. It is highly recommended to extract end-diastolic frames prior to segmentation. Checking the *Gated Frames* box will segment only the end-diastolic images. If this is unchecked segmentation will take a significantly longer time. 

![Segmentation](/Media/Segmentation.gif)

## Manual contour editing
Contours can be manually edited by dragging anchor points. 

![Manual Editing](/Media/Editing.gif)

Contours can also be drawn from scratch by pressing the *Manual Contour* button

![Manual Segmentation](/Media/Manual_Segmentation.gif)

## Report Generation
A report in the form of a text file can be generated for each frame in the pullback by pressing *Write Report*. If *Gated Frames* is checked then the report will only include the end-diastolic images. The report consists of the following variables:  
**Frame, Lumen area, Plaque area, Vessel area, Plaque burden, Phenotype**

## Keyboard Shortcuts
:arrow_right: Next proximal image  
:arrow_left: Next distal image  
:arrow_up: Next (gated) proximal image  
:arrow_down: Next (gated) distal image  
<kbd>h</kbd> Hide contours  
<kbd>j</kbd> Jiggle current frame  
<kbd>q</kbd> Quit session  

## CLI reference
Alternatively to using the GUI DeepIVUS can be used directly from the command line. 

deepivus --help
```
Usage: [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit
  --help     Show this message and exit

Commands:
  gui        Launches the GUI
  segment    Segment IVUS images
  gate       Identify end diastolic images
```
deepivus segment --help
```
Usage: DeepIVUS segment dicom_path [OPTIONS]
  Segment dicom file from the given dicom_path
  
Options:
  -g, --gated  Select whether only gated images should be segmented (much quicker)
  -f, --fname  Output filename for the contours\
  --help       Show this message
```
deepivus gate --help
```
Usage: DeepIVUS gate dicom_path [OPTIONS]
  Write end diastolic frames from the given dicom_path
  
Options:
  -w, --write  Write gated frames as jpgs
  --help       Show this message
```


## DeepIVUS Project Roadmap
* Deep ensembles for model uncertainty
