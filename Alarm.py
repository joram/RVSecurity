import piplates.TINKERplate as TINK
import time
from enum import Enum

class States(Enum):
    OFF         = 1
    ON          = 2
    STARTING    = 3
    STARTERROR  = 4
    TRIGDELAY   = 5
    TRIGGERED   = 6
    SILENCED    = 7



class Alarm:

    StateConsts = {
    # Value list assignments: 1st: Light indicator state; 2nd: Buzzer State; 3rd: Alarm State
    # Value meaning: 0 = off; 1 = on; 4 = slow blink; 16 = fast blink 

    States.OFF:         [ 0,  0,  0],     
    States.STARTING:    [ 4,  4,  0],
    States.STARTERROR:  [16, 16,  0],
    States.ON:          [ 1,  0,  0],
    States.TRIGDELAY:   [16, 16,  0],
    States.TRIGGERED:   [16, 16,  1],
    States.SILENCED:    [16, 16,  0]
    }

    #Class Constants
    ENTRYEXITDELAY  = int(30)            # Time in seconds where alarm won't go off after enable
    FASTBLINK       = int(1)             # time delay is = FASTBLINK * LoopDelay
    SLOWBLINK       = int(6 * FASTBLINK) # SLOWBLINK must be a muilti9ple of FASTBLINK
    MAXALARMTIME    = int(1)             # Number of minutes max that the alarm can be on
    LOOPDELAY       = float(.3)          # time in seconds pausing between running loop
    TINKERADDR      = int(0)             # IO bd address

    # Class variables
    AlarmTime       = float(0)
    BikeState       = (States.OFF)   #uses blue button
    #BikeState       = StateConsts(States.OFF)   #uses blue button
    BikeTime        = float(0)
    InteriorState   = (States.OFF)   #uses red button
    #InteriorState   = StateConsts(States.OFF)   #uses red button
    InteriorTime    = float(0)
    LastButtonTime  = float(0)                  #Time button weas last pressed 
    LoopTime        = float(0)
    LoopCount       = int(0)

    def __init__(self):
        ## Basic setup   
        TINK.setMODE(self.TINKERADDR,1,'BUTTON')  # Red Button
        TINK.setMODE(self.TINKERADDR,2,'DOUT')    # Red LED
        TINK.setMODE(self.TINKERADDR,3,'BUTTON')  # Blue Button
        TINK.setMODE(self.TINKERADDR,4,'DOUT')    # Blue LED
        TINK.setMODE(self.TINKERADDR,5,'DIN')     # PIR interior sensor 
        TINK.setMODE(self.TINKERADDR,6,'DOUT')    # Surrogate for Alarm horn
        TINK.clrLED(self.TINKERADDR,0)            # Note LED0 is surrogate for buzzer 
        TINK.clrDOUT(self.TINKERADDR,2)           # Red LED
        TINK.clrDOUT(self.TINKERADDR,4)           # Blue LED
        TINK.clrDOUT(self.TINKERADDR,6)           # Surrogate Alarm horn
        TINK.relayOFF(self.TINKERADDR,1)          # Alarm Horn
        TINK.relayOFF(self.TINKERADDR,2)          # Buzzer

        
        self.BikeState = States.OFF
        self.InteriorState = States.OFF
     
    def _check_bike_wire(self):
        VOL_DELTA = .2              #Allowed voltage delta in trip wire
        if self.BikeState in [States.ON, States.STARTING]:
            Chan1_Base = TINK.getADC(self.TINKERADDR,1)    #This measures the 5V supply used to generate Chan3_Base and Chan4_Base 
            Chan3_Base = Chan1_Base * 0.6666        #ratio set by resistive divider
            Chan4_Base = Chan1_Base * 0.3333
            Chan3 = abs(TINK.getADC(self.TINKERADDR,3) - Chan3_Base)
            Chan4 = abs(TINK.getADC(self.TINKERADDR,4) - Chan4_Base)
            if (Chan3 > VOL_DELTA) or (Chan4 > VOL_DELTA):
                # Error detected 
                if(self.BikeState == States.STARTING):
                    # Starting errror
                    self.BikeState = States.STARTERROR 
                else:
                    # Alarm triggere; 
                    self.BikeState = States.TRIGGERED   #Note: Bike has no alarm triggered delay.
                    self.AlarmTime = self.LoopTime

    def _check_interior(self):
        if self.InteriorState == States.STARTING and TINK.getDIN(self.TINKERADDR, 5) == 1:
            #Alarm triggered but starting
             self.InteriorState = States.STARTERROR
        if self.InteriorState == States.ON and TINK.getDIN(self.TINKERADDR, 5) == 1:
            #Alarm triggered
            self.InteriorState = States.TRIGDELAY
            self.AlarmTime = self.LoopTime

    def _check_buttons(self):
        BUTTONDELAY = 1             # Time (sec) before button toggles

        NowTime = self.LoopTime
        RedButton = TINK.getBUTTON(self.TINKERADDR,1)     #Interior Alarm control
        BlueButton = TINK.getBUTTON(self.TINKERADDR,3)    #Bike Alarm control
        
        if(RedButton == 1 and ((NowTime-self.LastButtonTime) > BUTTONDELAY)): 
            #Toggle
            if self.InteriorState == States.OFF:
                self.InteriorState = States.STARTING
                self.InteriorTime = NowTime
            else:
                self.InteriorState = States.OFF
            self.LastButtonTime = NowTime

        if(BlueButton == 1 and ((NowTime-self.LastButtonTime) > BUTTONDELAY)): 
            #Toggle
            if self.BikeState == States.OFF:
                self.BikeState = States.STARTING 
                self.BikeTime = NowTime
            else:
                self.BikeState = States.OFF
            self.LastButtonTime = NowTime

    def _display(self):
    #note: horn is relay 1 and buzzer is relay 2
      

        IntState    = self.StateConsts[self.InteriorState]
        BkState     = self.StateConsts[self.BikeState]
        if IntState[0] == 0:
            TINK.clrDOUT(self.TINKERADDR,2) #Red light off
        elif IntState[0] == 1:
            TINK.setDOUT(self.TINKERADDR,2) #Red light off
        if BkState[0] == 0:
            TINK.clrDOUT(self.TINKERADDR,4) #Blue light off
        elif BkState[0] == 1:
            TINK.setDOUT(self.TINKERADDR,4) #Blue light off
        
        # Combined Buzzer and Alarm values
        BuzzerVal = IntState[1] + BkState[1]
        AlarmVal = IntState[2] + BkState[2]

        if BuzzerVal == 0:
            TINK.relayOFF(self.TINKERADDR,2)
            TINK.clrLED(self.TINKERADDR,0)
        elif BuzzerVal == 1:
            ##TINK.relayON(self.TINKERADDR,2)
            TINK.setLED(self.TINKERADDR,0)
        
        if AlarmVal == 0:
            TINK.relayOFF(self.TINKERADDR,1)
            TINK.clrDOUT(self.TINKERADDR,6)
        elif AlarmVal == 1:
            ##TINK.relayON(self.TINKERADDR,1)
            TINK.setDOUT(self.TINKERADDR,6)

        if (BuzzerVal > 1 or AlarmVal > 1 or IntState[0] > 1 or BkState[0] > 1):
             # Someone needs to toggle now
            if self.LoopCount % self.SLOWBLINK == 0:
                if IntState[0] > 2:            # Red Light
                    TINK.toggleDOUT(self.TINKERADDR,2)
                if BkState[0] > 2:                # Blue Light
                    TINK.toggleDOUT(self.TINKERADDR,4)
                if BuzzerVal > 2:
                    ##TINK.relayTOGGLE(self.TINKERADDR,2)
                    TINK.toggleLED(self.TINKERADDR,0)
                if AlarmVal > 2:
                    ##TINK.relayTOGGLE(self.TINKERADDR,1)
                    TINK.toggleDOUT(self.TINKERADDR,6)
            elif (self.LoopCount % self.FASTBLINK) == 0:
                if IntState[0] > 8:            # Red Light
                    TINK.toggleDOUT(self.TINKERADDR,2)
                if BkState[0] > 8:                # Blue Light
                    TINK.toggleDOUT(self.TINKERADDR,4)
                if BuzzerVal > 8:
                    ##TINK.relayTOGGLE(self.TINKERADDR,2)
                    TINK.toggleLED(self.TINKERADDR,0)
                if AlarmVal > 8:
                    ##TINK.relayTOGGLE(self.TINKERADDR,1)
                    TINK.toggleDOUT(self.TINKERADDR,6)
                

       
    def _update_timed_transitions(self):
    # Three announcement assets: button light (red and blue), buzzer, and alarm horn
    # Note: buzzer and alarm horn are shared by both alarm circuits

        
        Inside = self.InteriorState
        if Inside in [States.STARTING, States.STARTERROR] and (self.LoopTime - self.InteriorTime) > self.ENTRYEXITDELAY:
            self.InteriorState = States.ON
        
        elif (Inside ==  States.TRIGDELAY) and ((self.LoopTime - self.AlarmTime) > self.ENTRYEXITDELAY):
            self.InternalState = States.TRIGGERED
      
        elif (Inside ==  States.TRIGGERED) and ((self.LoopTime - self.AlarmTime) > (60 * self.MAXALARMTIME)):
            self.InternalState = States.SILENCED
       
        Bike = self.BikeState
        if (Bike in [States.STARTING, States.STARTERROR]) and (self.LoopTime - self.BikeTime) > self.ENTRYEXITDELAY:
            self.BikeState = States.ON
      
        elif (Bike ==  States.TRIGGERED) and ((self.LoopTime - self.AlarmTime) > (60 * self.MAXALARMTIME)):
            self.BikeState = States.SILENCED
    
    def run_alarm_infinite(self):
        # run alarm code forever
        while True:                    
            self.LoopCount += 1
            self.LoopTime = time.time()
            RVIO._check_buttons()    
            RVIO._check_bike_wire()
            RVIO._check_interior()
            RVIO._update_timed_transitions()
            RVIO._display()
            #if LoopCount % 40 == 0:
            #    print(AlarmState)
            time.sleep(self.LOOPDELAY) #sleep

if __name__ == "__main__":
    RVIO = Alarm()
    RVIO.run_alarm_infinite()
