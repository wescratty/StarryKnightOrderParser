 ***Convert .xml to html or populate a xmls for excel***
=========================================================

## HTML:
### HTML field set contains two buttons. Open and Create.
Open:
* Open file chooser and select a file in xml format.
* Displayed will be the parent tag as a button. Navigate into the depths of the tree.

Create:
* Recursively navigates the tree from the selected location and creates an html table from the data.

OBJ Path:
* Displays path user has traveled through tags
---
## CSV:

### Search for Files Ends With label:
* Enter a file ending pattern, will exclude all non-matching files
    CSV field set also contains two buttons. Find and Create.

Find:
* Open a directory chooser and select a directory that contains files with xml format.
* Displays cardinality of files in the set.

Export:
* Parse all xml files and Calibration Data xlsm workbook by populating the esu_temp.xlsm
    
*Note: Currently only supports Calibration.config file structure to create workbook*