Video on YouTube: https://www.youtube.com/watch?v=IhyNcFJs6Cw

A simple bot that automatically plays 2048 on a phone or tablet by using a CNC machine and some software to stream the devices screen to a PC (such as Microsoft Teams or TeamViewer). It does some very basic image processing to detect the boards current state, compute the best move and then send the command to the CNC. 

For the AI, it uses the 2048 AI developed by nneonneo: https://github.com/nneonneo/2048-ai

To control the CNC machine, it uses Repetier-Server to send gcode-commands to the machine: https://www.repetier-server.com/ 

Run **SolverMain.py** (with Python 3) to the start the bot. Before running the program you should edit the following lines in **Solver.py** to tell the program where on the computer screen it should look for the 2048 tiles: 

~~~
tiles_origin = (395, 730)  # (y, x)
tiles_spacing = (7, 8)  # (y, x)
tiles_size = (110, 109)  # (height, width)
tiles_crop = 4  # pixels
~~~

Have fun :)
