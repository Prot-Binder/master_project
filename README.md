path to this github repository:

potential error: currently, we use absolut paths to specify the DISANG etc. file locations. If the filepaths are too long (probably > 80 characters), AMBER might throw and error that the file could not be opened. So shorten the filepath or ajdust it to relative filepaths.
