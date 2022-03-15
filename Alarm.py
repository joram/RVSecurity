import piplates.TINKERplate as TINK
import time
from enum import Enum

class States(Enum):
    OFF         = 1
    ON          = 2
    STARTING    = 3
    TRIGGERED   = 4
    SILENCED    = 5

class AlarmIO:

    def __init__(self,TinkAddr, AlarmState):
        ## Basic setup   
        TINK.setMODE(TinkAddr,1,'BUTTON')  # Red Button
        TINK.setMODE(TinkAddr,2,'DOUT')    # Red LED
        TINK.setMODE(TinkAddr,3,'BUTTON')  # Blue Button
        TINK.setMODE(TinkAddr,4,'DOUT')    # Blue LED
        TINK.setMODE(TinkAddr,5,'DIN')     # PIR interior sensor 
        AlarmState["BikeState"] = States.OFF
        AlarmState["InteriorState"] = States.OFF
     
    def CheckBikeWire(self,TinkAddr, AlarmState):
        VOL_DELTA = .2              #Allowed voltage delta in trip wire
        if AlarmState["BikeState"] == States.ON:
            Chan1_Base = TINK.getADC(TinkAddr,1)    #This measures the 5V supply used to generate Chan3_Base and Chan4_Base 
            Chan3_Base = Chan1_Base * 0.6666        #ratio set by resistive divider
            Chan4_Base = Chan1_Base * 0.3333
            Chan3 = abs(TINK.getADC(TinkAddr,3) - Chan3_Base)
            Chan4 = abs(TINK.getADC(TinkAddr,4) - Chan4_Base)
            if (Chan3 > VOL_DELTA or Chan4 > VOL_DELTA):
                # Alarm triggered
                AlarmState["AlarmTime"] = LoopTime
                AlarmState["BikeState"] = States.TRIGGERED

    def CheckInterior(self, TinkAddr, AlarmState):
        global LoopTime
        if AlarmState["InteriorState"] == States.ON and TINK.getDIN(TinkAddr, 5) == 1:
            #Alarm triggered
            AlarmState["AlarmTime"] = LoopTime
            AlarmState["InteriorState"] = States.TRIGGERED

    def CheckButtons(self, TinkAddr, AlarmState):
        global LoopTime
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

    def Blink(self, TinkAddr, SpeedDiv, RedLight, BlueLight, Buzzer, Horn):
    #note: horn is relay 1 and buzzer is relay 2
        global LoopCount
        if (LoopCount % SpeedDiv) == 0:
            if RedLight:
                TINK.toggleDOUT(TinkAddr,2)
            if BlueLight:
                TINK.toggleDOUT(TinkAddr,4)
            if Horn:
                TINK.relayTOGGLE(TinkAddr,1)
                TINK.toggleLED(TinkAddr,0)
            if Buzzer:
                TINK.relayTOGGLE(TinkAddr,2)
    
       
    def UpdateStateAnnouncements(self, TinkAddr, AlarmState):
    # Three announcement assets: button light (red and blue), buzzer, and alarm horn
    # Note: buzzer and alarm horn are shared by both alarm circuits
        SLOWBLINK = 5
        FASTBLINK = 1
        EXITDELAY = 30 

        global LoopTime
       
        Inside = AlarmState["InteriorState"]
        if Inside == States.OFF:
            TINK.clrDOUT(TinkAddr,2) #Red light off
        elif Inside == States.STARTING:
            #slow delay exit; 
            #slow blink light and buzzer; 
            RVIO.Blink(TinkAddr, SLOWBLINK, True, False, True, False)
            if (LoopTime - AlarmState["InteriorTime"]) > EXITDELAY:
                AlarmState["InteriorState"] = States.ON
        elif Inside == States.ON:
            #steady on light; horn off
            TINK.setDOUT(TinkAddr,2) #Red light on
        elif Inside ==  States.SILENCED:
            #light fast blink; horn slidenced
            RVIO.Blink(TinkAddr, FASTBLINK, True, False, False, False)
        elif Inside ==  States.TRIGGERED:
            #fast blink light; horn on
            RVIO.Blink(TinkAddr, FASTBLINK, True, False, False, True)
            if ((LoopTime - AlarmState["AlarmTime"]) > (60 * AlarmState["ALARM_MINUTES"])):
                AlarmState["InternalState"] = States.SILENCED
       
        Bike = AlarmState["BikeState"]
        if Bike == States.OFF:
            TINK.clrDOUT(TinkAddr,4) #Blue light off
        elif Bike ==States.STARTING:
            #slow delay exit; 
            #slow blink light and buzzer; 
            RVIO.Blink(TinkAddr, SLOWBLINK, False, True, True, False)
            if (LoopTime - AlarmState["BikeTime"]) > EXITDELAY:
                print(LoopTime - AlarmState["BikeTime"],LoopTime, AlarmState["AlarmTime"])
                AlarmState["BikeState"] = States.ON
        elif Bike == States.ON:
            #steady on light; horn off
            TINK.setDOUT(TinkAddr,4) #Blue light on
        elif Bike ==  States.SILENCED:
            #light fast blink; horn slidenced
            RVIO.Blink(TinkAddr, FASTBLINK, True, False, False, False)
        elif Bike ==  States.TRIGGERED:
            #fast blink light; horn on
            RVIO.Blink(TinkAddr, FASTBLINK, False, True, False, True)
            if ((LoopTime - AlarmState["AlarmTime"]) > (60 * AlarmState["ALARM_MINUTES"])):
                AlarmState["BikeState"] = States.SILENCED
        
             

        if(AlarmState["BikeState"] == States.TRIGGERED or AlarmState["InteriorState"] == States.TRIGGERED) and \
          ((LoopTime - AlarmState["AlarmTime"]) < (60 * AlarmState["ALARM_MINUTES"])):
            # Alarm on
            TINK.setLED(TinkAddr,0)
        else:
            #Alarm off
            TINK.clrLED(TinkAddr,0)
        



LOOPDELAY = .2                  # time in seconds pausing between running loop
TINKERADDR = 0                  # IO bd address

AlarmState = { 
    "ALARM_MINUTES": 1,          #Max number of minutes an alarm will ring
    "AlarmTime": 0,
    "BikeState": States.OFF,          #uses blue button
    "BikeTime": 0,
    "InteriorState": States.OFF,      #uses red button
    "InteriorTime": 0,
    "LastButtonTime": 0               #Time button weas last pressed  
}


RVIO = AlarmIO(TINKERADDR, AlarmState)
LoopCount = 0


while True:                     #infinite loop
    LoopCount += 1
    LoopTime = time.time()
    RVIO.CheckButtons(TINKERADDR, AlarmState)    
    RVIO.CheckBikeWire(TINKERADDR, AlarmState)
    RVIO.CheckInterior(TINKERADDR, AlarmState)
    RVIO.UpdateStateAnnouncements(TINKERADDR, AlarmState)
    time.sleep(LOOPDELAY) #sleep
    
