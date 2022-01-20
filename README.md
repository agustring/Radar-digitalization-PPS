# Radar digitalization

A proyect for professional practices subject about a radar digitalization using Python.

testpaq.py: First assigment consists of simulating the reception of 32-bit words over ethernet, same protocol as real radar, to solve this problem needed to test the temporal qualities and meet the requirements of the real time system. 

Words details available in palabra.png

RadarGUI.py: the python script given did not meet the execution deadlines. The application received eth packages through an external network device which came in hexadecimal form and were entered directly into a queue, all this action was performed in a thread dedicated to receiving packets only. This queue was used from another part of the program to extract these words in order to build the matrix which will later be plotted in polar form. Between each HM bit (it means Heading Mark and is set to 1 when the radar pass thru north point) bit the expectation was 2 seconds when this app took about 20 seconds.
