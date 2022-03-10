import piplates.TINKERplate as TINK
import time

## Constants
BUTTONDELAY = 1
LOOPDELAY = 1
ALARM_MINUTES = 1
VOL_DELTA = .2              #Allowed voltage delta in trip wire

## Basic setup
TINK.setMODE(0,1,'BUTTON')  # Red Button
TINK.setMODE(0,2,'DOUT')    # Red LED
TINK.setMODE(0,3,'BUTTON')  # Blue Button
TINK.setMODE(0,4,'DOUT')    # Blue LED

TINK.clrLED(0,0)            # Bd LED off
BlueState = False
RedState = False
loopcount = 0
LastTime = time.time()      # time since epoch in seconds

def CheckBikeWire():
    Chan3 = abs(TINK.getADC(0,3) - Chan3_Base)
    Chan4 = abs(TINK.getADC(0,4) - Chan4_Base)
    if Chan3 > VOL_DELTA or Chan4 > VOL_DELTA:
        # Alarm triggered
        Alarm_Bike = True
        TINK.setLED(0,0)
        AlarmTime = time.time()


def CheckButtons(LastTime):
    print(LastTime, BlueState, RedState)
    NowTime = time.time() 
    RedButton = TINK.getBUTTON(0,1)
    BlueButton = TINK.getBUTTON(0,3)
    
    if(RedButton ==1 and ((NowTime-LastTime) > BUTTONDELAY)): 
        RedState = not(RedState)
        LastTime = time.time()
        loopcount += 1
        if RedState:    
            #Starting internal burgler alarm state
            TINK.setDOUT(0,2) #Red Button
        else: 
            TINK.clrDOUT(0,2)
    if(BlueButton ==1 and ((NowTime-LastTime) > BUTTONDELAY)):
        BlueState = not(BlueState)
        LastTime = time.time()
        if BlueState:
            TINK.setDOUT(0,4) #Blue Button
        else: 
            TINK.clrDOUT(0,4)


AlarmTime = 0
Chan3_Base = TINK.getADC(0,3)
Chan4_Base = TINK.getADC(0,4)
Alarm_Bike = FalseAlarm_Int = False

while True: #infinite loop
   
    print(LastTime, BlueState, RedState)
    CheckButtons(LastTime)    
    CheckBikeWire()
    if time.time() - AlarmTime > 60 * ALARM_MINUTES:
        # Alarm off
        TINK.clrLED(0,0)

    time.sleep(LOOPDELAY) #sleep
    print(LastTime, BlueState, RedState)

