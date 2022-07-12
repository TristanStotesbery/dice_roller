import re
import time
import argparse
import random
import threading
import RPi.GPIO as GPIO
from max7219.luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, LCD_FONT, TINY_FONT, CP437_FONT


ROLL_BTN = 12
NUM_SEL_BTN = 13
FACE_SEL_BTN = 15
SEED_GEN_BTN_1 = 16
SEED_GEN_BTN_2 = 18

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(ROLL_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(NUM_SEL_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(FACE_SEL_BTN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SEED_GEN_BTN_1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SEED_GEN_BTN_2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)



class roller:
    def __init__(self):
        self.possible_screen_tasks = ["SELECT" , "ROLLING" , "DISPLAY"]
        self.possible_dice_faces = ["4", "6", "8", "10", "12", "20"]
        self.current_screen_task = "SELECT"
        self.current_num_dice = 4
        self.current_dice_face = "6"
        self.dice_results = []
        self.roll_started = False
        self.current_seed = 1
        self.seeds = [1,2,3,4]
        
    def start(self):
        self.screenThread = threading.Thread(target=self.screen_task)
        self.btnThread = threading.Thread(target=self.button_task)
        self.lock = threading.Lock()
        self.screenThread.start()
        self.btnThread.start()
        
    def roll_dice(self,faces, seed):
        random.seed(seed + int(time.time()));
        return (random.randrange(1,faces+1,1))
        
        
    def screen_task(self):
        serial = spi(port=0, device=0, gpio=noop())
        device = max7219(serial, cascaded=4, block_orientation=90,
                         rotate=1 or 0, blocks_arranged_in_reverse_order=True)
        print("Created device")
        while True:
            #thread lock
            self.lock.acquire()
            cur_task = self.current_screen_task
            cur_num = self.current_num_dice
            cur_dice = self.current_dice_face
            cur_results = self.dice_results
            #thread unlock
            self.lock.release()
            if cur_task == "SELECT":
                words = [ str(cur_num), "d" , str(cur_dice), " "]
                virtual = viewport(device, width=device.width, height=len(words) * 8)
                with canvas(virtual) as draw:
                    for i, word in enumerate(words):
                        text(draw, (0, i*8), word, fill="white", font=proportional(TINY_FONT))
                for i in range(virtual.height - device.height):
                    virtual.set_position((0,i))
            elif cur_task == "ROLLING":
                words = []
                for i in range(cur_num):
                    words.append(str(random.randrange(1,int(cur_dice)+1,1)))
                while(len(words) < 4):
                    words.append(" ")

                virtual = viewport(device, width=device.width, height=len(words) * 8)
                with canvas(virtual) as draw:
                    for i, word in enumerate(words):
                        text(draw, (0, i*8), word, fill="white", font=proportional(TINY_FONT))
                for i in range(virtual.height - device.height):
                    virtual.set_position((0,i))
                time.sleep(0.05)
            elif cur_task == "DISPLAY":
                words = cur_results
                while(len(words) < 4):
                    words.append(" ")
                virtual = viewport(device, width=device.width, height=len(words) * 8)
                with canvas(virtual) as draw:
                    for i, word in enumerate(words):
                        text(draw, (0, i*8), word, fill="white", font=proportional(TINY_FONT))
                for i in range(virtual.height - device.height):
                    virtual.set_position((0,i))
                
    def button_task(self):
        roll_started = False
        while True:
            ROLL_BTN_STATE = GPIO.input(ROLL_BTN)
            NUM_SEL_STATE = GPIO.input(NUM_SEL_BTN)
            FACE_SEL_STATE = GPIO.input(FACE_SEL_BTN)
            SEED_GEN_STATE_1 = GPIO.input(SEED_GEN_BTN_1)
            SEED_GEN_STATE_2 = GPIO.input(SEED_GEN_BTN_2)
            self.lock.acquire()
            TASK = self.current_screen_task
            self.lock.release()
            ##SELECTION TASK
            if(TASK == "SELECT"):
                if(ROLL_BTN_STATE == GPIO.HIGH and not roll_started):
                    print("Here")
                    roll_started = True
                    print("rolling")
                    #thread lock
                    self.lock.acquire()
                    self.current_screen_task = "ROLLING"
                    self.current_seed = 2
                    #thread unlock
                    self.lock.release()
                
                elif(NUM_SEL_STATE == GPIO.HIGH):
                    self.lock.acquire()
                    if(self.current_num_dice == 4):
                        self.current_num_dice = 1
                    else:
                        self.current_num_dice = self.current_num_dice + 1
                    self.lock.release()
                    time.sleep(0.5)
                elif(FACE_SEL_STATE == GPIO.HIGH):
                    self.lock.acquire()
                    if(self.current_dice_face == "6"):
                        self.current_dice_face = "8"
                    elif(self.current_dice_face == "8"):
                        self.current_dice_face = "10"
                    elif(self.current_dice_face == "10"):
                        self.current_dice_face = "12"
                    elif(self.current_dice_face == "12"):
                        self.current_dice_face = "20"
                    elif(self.current_dice_face == "20"):
                        self.current_dice_face = "4"
                    elif(self.current_dice_face == "4"):
                        self.current_dice_face = "6"
                    self.lock.release()
                    time.sleep(0.5)
                    
                    
                    
            ##ROLLINGTASK
            elif(TASK == "ROLLING"):   
                if(ROLL_BTN_STATE == GPIO.LOW and roll_started):
                    print("heeer")
                    roll_started = False                
                    new_results = []
                    for i in range(int(self.current_num_dice)):
                        new_results.append(str(self.roll_dice(int(self.current_dice_face),
                                                          self.seeds[i])))
                    #thread lock
                    self.lock.acquire()
                    self.dice_results = new_results
                    self.current_screen_task = "DISPLAY"
                    #thread unlock
                    self.lock.release()
                elif(NUM_SEL_STATE == GPIO.HIGH):
                    self.lock.acquire()
                    self.current_seed += random.randrange(1,50,1)
                    self.seeds[0] = self.current_seed>>4
                    self.seeds[1] = self.current_seed>>6
                    self.seeds[2] = self.current_seed>>8
                    self.seeds[3] = self.current_seed
                    self.lock.release()
                elif(FACE_SEL_STATE == GPIO.HIGH):
                    self.lock.acquire()
                    self.current_seed *= random.randrange(3,7,2)
                    self.seeds[0] = self.current_seed>>4
                    self.seeds[1] = self.current_seed>>6
                    self.seeds[2] = self.current_seed>>8
                    self.seeds[3] = self.current_seed
                    self.lock.release()
                elif(SEED_GEN_STATE_1 == GPIO.HIGH):
                    self.lock.acquire()
                    self.current_seed << random.randrange(1,4,1)
                    self.seeds[0] = self.current_seed>>4
                    self.seeds[1] = self.current_seed>>6
                    self.seeds[2] = self.current_seed>>8
                    self.seeds[3] = self.current_seed
                    self.lock.release()
                
                
                    
            ##DISPLAYTASK
            elif(TASK == "DISPLAY"):
                if(NUM_SEL_STATE == GPIO.HIGH):
                    #thread lock
                    self.lock.acquire()
                    self.current_screen_task = "SELECT"
                    #thread unlock
                    self.lock.release()
                    time.sleep(1)
            
            
            else:
                print("didn't get state, button was " + str(ROLL_BTN_STATE))
                time.sleep(0.5)
            
if __name__ == "__main__":
    roll = roller()
    roll.start()
    
            

