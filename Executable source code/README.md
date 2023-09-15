# General information on Python files

## gui.py
This file contains code related to the user interface. A dictionary of user defined options is created and used by the fitter function, defined in fitter.py.

## fitter.py
Defines the fitting funciton depending on user input, and calls on functions defined in library.py to perform fitting and generate a plot and summary data. For scripting and processing many CV files use the fitter function and helper functions saved in library.py.

## library.py
This file contains some simple functions used to process the CV data; including functions used for reading various CV data files, a CV class which calculates various parameters of interest (eg. time of switching potential), and other functions for automated fitting and report creation.
