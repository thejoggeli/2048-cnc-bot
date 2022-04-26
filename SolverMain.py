import Solver
import numpy as np
import matplotlib.pyplot as plt
from websocket import create_connection
import json
import time
import requests
from urllib.parse import quote_plus

def test2():
    
    solver = Solver.Solver()
    
    image = solver.capture_image()
    
    numbers = solver.detect_numbers(image)
    print(numbers)
    
    plt.imshow(image)
    plt.show()

def test():

    solver = Solver.Solver()

    numbers = [
        [2, 4, 8, 16],
        [2, 4, 8, 16],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    numbers = np.array(numbers, dtype="uint")
    print(numbers)

    move = solver.compute_move(numbers)
    print(f"move={move}")

    result = solver.simulate_move(move, numbers)
    print(result)

def main():
    controller = Controller("cnc")
    solver = Solver.Solver()
    
    # get initial image and detect the numbers
    image = solver.capture_image()
    numbers = solver.detect_numbers(image)

    # loop forever
    while True:

        # compute move
        print(f"computing move for numbers:")
        print(numbers)
        move = solver.compute_move(numbers)

        # execute move on cnc
        movename = Solver.movename(move)
        print(f"executing move={move}, name={movename}")
        controller.execute_move(move)

        # simulate move to get expected result
        numbers_expected = solver.simulate_move(move, numbers)
        print("expecting numbers")
        print(numbers_expected)

        # wait until the expected results appears on stream
        print("waiting for result")
       
        loops = 0
        expected_count = 0
        same_count = 0
        valid = False
        msg = ""
        while not valid:
            time.sleep(0.01)
            # wait for new picture
            try:
                image = solver.capture_image()
                numbers_new = solver.detect_numbers(image)
                n_same = np.count_nonzero(numbers_new == numbers)
                n_expected = np.count_nonzero(numbers_new == numbers_expected)
                # print(f"nSame={nSame}")
                if(n_same == 16):
                    expected_count = 0
                    same_count += 1
                    if(same_count >= 25):
                        valid = True
                        msg = "unregistered move detected, trying again"
                elif (n_expected == 15):
                    same_count = 0
                    expected_count += 1
                    if(expected_count >= 3):
                        numbers = numbers_new
                        valid = True
                        msg = "expected state detected"
                else:   
                    expected_count = 0
                    same_count = 0
                loops += 1
                print(f"\rloops={loops}, expected_count={expected_count}, same_count={same_count}", end="\r")
            except Exception as e:            
                print(f"\r{Exception}", end="\r")
        print()
        print(msg)
        
        
def on_message(ws, message):
    print(f"on_message: {message}")

def on_error(ws, error):
    print(f"on_error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"on_close: {close_status_code}, {close_msg}")

def on_open(ws):
    print("on_open")

class Controller:
    def __init__(self, printer):
        self.printer = printer
        self.apikey = "4f710ec2-8f32-479e-8683-b6cb9b29684d"
        """
        self.ws = create_connection(
            f"ws://127.0.0.1:3344/socket?lang=en&apikey={self.apikey}", 
            timeout=15,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        """
        self.send_gcodes([
            "G90",
            "G92 X100 Y100 Z0",
            "M18 X Y Z",
        ])
        print("press enter to enable steppers: ", end="")
        input()
        self.send_gcodes([
            "M17 X Y Z",
            self.gcode_move(x=100, y=100, z=5, speed=20*60),
        ])
        
    def send_gcodes(self, gcodes):
        gcode = "\n".join(gcodes)
        return self.send_gcode(gcode)
        
    def send_gcode(self, gcode):
        data = {"cmd": gcode}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'
        }
        url = f"http://127.0.0.1:3344/printer/api/{self.printer}?a=send&data={quote_plus(json.dumps(data))}&apikey={self.apikey}"
        print(url)
        print(f"{gcode} ... ", end="")
        response = requests.get(url, timeout=15, headers=headers)
        print(f"{response.status_code}, {response.text}")
        return response
        """
        cmd = {
            "printer": self.printer,
            "callback_id": -1,
            "action": "send", 
            "data": {
                "cmd": gcode,
            },
        }
        print(f"{gcode}")
        self.ws.send(json.dumps(cmd))
        return self.ws.recv()    
        """
    
    def gcode_move(self, x=0, y=0, z=0, speed=10*60):
        """
        return None
        cmd = {
            "printer": self.printer,
            "callback_id": -1,
            "action": "move", 
            "data": {
                "x": x,
                "y": y,
                "z": z,
                "speed": speed,
                "relative": relative,
            },
        }
        self.ws.send(json.dumps(cmd))
        return self.ws.recv()
        """
        gcode = f"G01 X{x} Y{y} Z{z} F{speed}"
        return gcode

    def execute_move(self, move):
        # assumes the touch pen is centered at x=100, y=100, z=10
        ox = 100
        oy = 100
        dx = 0
        dy = 0
        xy_travel = 15
        z_travel = 5
        if(move == 0):
            # up
            dy = xy_travel
        elif(move == 1):
            # down
            dy = -xy_travel
        elif(move == 2):
            # left
            dx = -xy_travel
        elif(move == 3):
            # right
            dx = xy_travel
        else:
            print("INVALID MOVE")
            return False
        speed = 100
        self.send_gcodes([
            self.gcode_move(x=ox, y=oy, z=0, speed=speed*60), # move pen down
            self.gcode_move(x=ox+dx, y=oy+dy, z=0, speed=speed*60), # swipe pen
            self.gcode_move(x=ox+dx, y=oy+dy, z=z_travel, speed=speed*60), # move pen up
            self.gcode_move(x=ox, y=oy, z=z_travel, speed=speed*60), # center pen
        ])
        
        return True
            

main()