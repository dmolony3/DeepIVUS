from setuptools import setup, find_packages
import os

VERSION = "0.2"

def get_long_description():
  with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
            encoding="UTF-8",) as fp:
    return fp.read()

setup(
  name="DeepIVUS",
  description="A program for segmenting and analyzing intravascular ultrasound images",
  long_description=get_long_description(),
  long_description_content_type='text/markdown',
  author="David Molony",
  url="https://github.com/dmolony3/DeepIVUS",
  project_urls={
    "Documentation": "https://github.com/dmolony3/DeepIVUS",
	"Issues": "https://github.com/dmolony3/DeepIVUS/issues",
	"Changelog": "https://github.com/dmolony3/DeepIVUS/releases",
	},
  license="Apache License, Version 2.0",
  version=VERSION,
  packages=find_packages(),
  entry_points="""
    [console_scripts]
    deepivus=DeepIVUS:cli
  """,
  install_requires=[
    "click==8.0.4",
    "numpy==1.16.2",
    "pydicom==1.3.0",
    "PyQt5==5.14.0",
    "scikit-image==0.16.2",
    "scipy==1.4.1",
    "tensorflow==2.2.0",
  ],
  python_requires=">=3.6",
)
	