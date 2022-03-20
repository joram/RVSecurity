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

            
    alarm_time: float = 0 
    bike_state: States = States.OFF


    AlarmState = { 
        "AlarmTime": 0,
        "BikeState": States.OFF,          #uses blue button
        "BikeTime": 0,
        "InteriorState": States.OFF,      #uses red button
        "InteriorTime": 0,
        "LastButtonTime": 0               #Time button weas last pressed 
    }

    #Global Constants
    ENTRYEXITDELAY  = 30            # Time in seconds where alarm won't go off after enable
    FASTBLINK       = 1             # time delay is = FASTBLINK * LoopDelay
    SLOWBLINK       = 6 * FASTBLINK # SLOWBLINK must be a muilti9ple of FASTBLINK
    MAXALARMTIME    = 1             # Number of minutes max that the alarm can be on

    #Local constants
    LOOPDELAY = .3 # time in seconds pausing between running loop
    TINKERADDR = 0 # IO bd address

    RVIO = AlarmIO(TINKERADDR, AlarmState)
    LoopCount = 0


    def __init__(self,TinkAddr, AlarmState):
        ## Basic setup   
        TINK.setMODE(TinkAddr,1,'BUTTON')  # Red Button
        TINK.setMODE(TinkAddr,2,'DOUT')    # Red LED
        TINK.setMODE(TinkAddr,3,'BUTTON')  # Blue Button
        TINK.setMODE(TinkAddr,4,'DOUT')    # Blue LED
        TINK.setMODE(TinkAddr,5,'DIN')     # PIR interior sensor 
        TINK.setMODE(TinkAddr,6,'DOUT')    # Surrogate for Alarm horn
        TINK.clrLED(TinkAddr,0)            # Note LED0 is surrogate for buzzer 
        TINK.clrDOUT(TinkAddr,2)
        TINK.clrDOUT(TinkAddr,4)
        TINK.clrDOUT(TinkAddr,6)
        TINK.relayOFF(TinkAddr,1)
        TINK.relayOFF(TinkAddr,2)
        
        self.bike_state = States.OFF
        self.interior_state = States.OFF

    def json(self): {
        return {
            "alarm_time": self.alarm_time,
            "bike_state": self.bike_state,
        }
    }
         
    def _check_bike_wire(self,TinkAddr, AlarmState, LoopCount, LoopTime):
        VOL_DELTA = .2              #Allowed voltage delta in trip wire
        if self.bike_state in [States.ON, States.STARTING]:
            Chan1_Base = TINK.getADC(TinkAddr,1)    #This measures the 5V supply used to generate Chan3_Base and Chan4_Base 
            Chan3_Base = Chan1_Base * 0.6666        #ratio set by resistive divider
            Chan4_Base = Chan1_Base * 0.3333
            Chan3 = abs(TINK.getADC(TinkAddr,3) - Chan3_Base)
            Chan4 = abs(TINK.getADC(TinkAddr,4) - Chan4_Base)
            if (Chan3 > VOL_DELTA) or (Chan4 > VOL_DELTA):
                # Error detected 
                if AlarmState["BikeState"] == States.STARTING:
                    # Starting errror
                    AlarmState["BikeState"] = States.STARTERROR 
                else:
                    # Alarm triggere; 
                    AlarmState["AlarmTime"] = LoopTime
                    AlarmState["BikeState"] = States.TRIGGERED   #Note: Bike has no alarm triggered delay.

    def _check_interior(self, TinkAddr, AlarmState, LoopCount, LoopTime):
        if AlarmState["InteriorState"] == States.STARTING and TINK.getDIN(TinkAddr, 5) == 1:
            #Alarm triggered but starting
             AlarmState["InteriorState"] = States.STARTERROR
        if AlarmState["InteriorState"] == States.ON and TINK.getDIN(TinkAddr, 5) == 1:
            #Alarm triggered
            AlarmState["AlarmTime"] = LoopTime
            AlarmState["InteriorState"] = States.TRIGDELAY

    def CheckButtons(self, TinkAddr, AlarmState, LoopCount, LoopTime):
        BUTTONDELAY = 1             # Time (sec) before button toggles

        NowTime = LoopTime
        RedButton = TINK.getBUTTON(TinkAddr,1)     #Interior Alarm control
        BlueButton = TINK.getBUTTON(TinkAddr,3)    #Bike Alarm control
        
        if(RedButton == 1 and ((NowTime-AlarmState["LastButtonTime"]) > BUTTONDELAY)): 
            #Toggle
            if AlarmState["InteriorState"] == States.OFF:
                AlarmState["InteriorState"] = States.STARTING
                AlarmState["InteriorTime"] = LoopTime
            else:
                AlarmState["InteriorState"] = States.OFF
            AlarmState["LastButtonTime"] = LoopTime

        if(BlueButton == 1 and ((NowTime-AlarmState["LastButtonTime"]) > BUTTONDELAY)): 
            #Toggle
            if AlarmState["BikeState"] == States.OFF:
                AlarmState["BikeState"] = States.STARTING 
                AlarmState["BikeTime"] = LoopTime
            else:
                AlarmState["BikeState"] = States.OFF
            AlarmState["LastButtonTime"] = LoopTime

    def Display(self, TinkAddr, AlarmState, LoopCount, LoopTime):
    #note: horn is relay 1 and buzzer is relay 2

        global FASTBLINK 
        global SLOWBLINK
        

        InteriorState = StateConsts[AlarmState["InteriorState"]]
        BikeState     = StateConsts[AlarmState["BikeState"]]
        if InteriorState[0] == 0:
            TINK.clrDOUT(TinkAddr,2) #Red light off
        elif InteriorState[0] == 1:
            TINK.setDOUT(TinkAddr,2) #Red light off
        if BikeState[0] == 0:
            TINK.clrDOUT(TinkAddr,4) #Blue light off
        elif BikeState[0] == 1:
            TINK.setDOUT(TinkAddr,4) #Blue light off
        
        # Combined Buzzer and Alarm values
        BuzzerVal = InteriorState[1] + BikeState[1]
        AlarmVal = InteriorState[2] + BikeState[2]

        if BuzzerVal == 0:
            TINK.relayOFF(TinkAddr,2)
            TINK.clrLED(TinkAddr,0)
        elif BuzzerVal == 1:
            TINK.relayON(TinkAddr,2)
            TINK.setLED(TinkAddr,0)
        
        if AlarmVal == 0:
            TINK.relayOFF(TinkAddr,1)
            TINK.clrDOUT(TinkAddr,6)
        elif AlarmVal == 1:
            TINK.relayON(TinkAddr,1)
            TINK.setLED(TinkAddr,6)

        if (BuzzerVal > 1 or AlarmVal > 1 or InteriorState[0] > 1 or BikeState[0] > 1):
             # Someone needs to toggle now
            if LoopCount % SLOWBLINK == 0:
            
                if InteriorState[0] > 2:            # Red Light
                    TINK.toggleDOUT(TinkAddr,2)
                if BikeState[0] > 2:                # Blue Light
                    TINK.toggleDOUT(TinkAddr,4)
                if BuzzerVal > 2:
                    TINK.relayTOGGLE(TinkAddr,2)
                    TINK.toggleLED(TinkAddr,0)
                if AlarmVal > 2:
                    TINK.relayTOGGLE(TinkAddr,1)
                    TINK.toggleLED(TinkAddr,6)
            elif (LoopCount % FASTBLINK) == 0:
                if InteriorState[0] > 8:            # Red Light
                    TINK.toggleDOUT(TinkAddr,2)
                if BikeState[0] > 8:                # Blue Light
                    TINK.toggleDOUT(TinkAddr,4)
                if BuzzerVal > 8:
                    TINK.relayTOGGLE(TinkAddr,2)
                    # TINK.toggleLED(TinkAddr,0)
                if AlarmVal > 8:
                    TINK.relayTOGGLE(TinkAddr,1)
                    TINK.toggleLED(TinkAddr,6)
                

       
    def UpdateTimedTransitions(self, TinkAddr, AlarmState, LoopCount, LoopTime):
    # Three announcement assets: button light (red and blue), buzzer, and alarm horn
    # Note: buzzer and alarm horn are shared by both alarm circuits

        global ENTRYEXITDELAY
        global MAXALARMTIME

        Inside = AlarmState["InteriorState"]
        if (Inside == States.STARTING or Inside == States.STARTERROR) and (LoopTime - AlarmState["InteriorTime"]) > ENTRYEXITDELAY:
            AlarmState["InteriorState"] = States.ON
        
        elif (Inside ==  States.TRIGDELAY) and ((LoopTime - AlarmState["AlarmTime"]) > ENTRYEXITDELAY):
            AlarmState["InternalState"] = States.TRIGGERED
      
        elif (Inside ==  States.TRIGGERED) and ((LoopTime - AlarmState["AlarmTime"]) > (60 * MAXALARMTIME)):
            AlarmState["InternalState"] = States.SILENCED
       
        Bike = AlarmState["BikeState"]
        if (Bike == States.STARTING or Bike == States.STARTERROR) and (LoopTime - AlarmState["BikeTime"]) > ENTRYEXITDELAY:
            AlarmState["BikeState"] = States.ON
      
        elif (Bike ==  States.TRIGGERED) and ((LoopTime - AlarmState["AlarmTime"]) > (60 * MAXALARMTIME)):
            AlarmState["BikeState"] = States.SILENCED
        


    def run_loop_infinitely(self):
        while True:                     #infinite loop
            LoopCount += 1
            LoopTime = time.time()
            RVIO.CheckButtons(AlarmState, LoopCount, LoopTime)    
            RVIO._check_bike_wire(TINKERADDR, AlarmState, LoopCount, LoopTime)
            RVIO._check_interior(TINKERADDR, AlarmState, LoopCount, LoopTime)
            RVIO.UpdateTimedTransitions(TINKERADDR, AlarmState, LoopCount, LoopTime)
            RVIO.Display(TINKERADDR, AlarmState, LoopCount, LoopTime)
            #if LoopCount % 40 == 0:
            #    print(AlarmState)
            time.sleep(LOOPDELAY) #sleep

   