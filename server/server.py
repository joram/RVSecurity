#!/usr/bin/env python3
import threading
import time
import uvicorn
#import alarm
import mqttclient

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
#import random
#import math

timebase = 1672772504.9141579 #from replay file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index():
    return RedirectResponse(url="/index.html")


class DataResponse(BaseModel):
    var1: str
    var2: str
    var3: str
    var4: str
    var5: str
    var6: str
    var7: str
    var8: str
    var9: str
    var10: str
    var11: str
    var12: str
    var13: str
    var14: str
    var15: str
    var16: str
    var17: str
    var18: str
    var19: str
    var20: str
    battery_percent: int

#routine to generation Flow motion text
def FlowMotion():
    
    CurrentTime = int(time.time()) % 5          #determines motion update period; updates per second

    if CurrentTime == 0:
        RightMotion = LeftMotion = "\u2002\u00A0\u2002\u00A0\u2002\u00a0\u2002"
    elif CurrentTime == 1:
        RightMotion = ">\u2002\u00A0\u2002\u00A0\u2002\u00A0"
        LeftMotion  = "\u2002\u00A0\u2002\u00A0\u2002\u00A0<"
    elif CurrentTime == 2: 
        RightMotion = "> >\u2002\u00A0\u2002\u00A0"
        LeftMotion  = "\u2002\u00A0\u2002\u00A0< <"
    elif CurrentTime == 3:
        RightMotion = "> > >\u2002\u00A0"
        LeftMotion  = "\u2002\u00A0< < <"
    elif CurrentTime == 4:
        RightMotion = "> > > >"
        LeftMotion  = "< < < <"
    return(RightMotion, LeftMotion)

def GenAllFlows(Invert_status_num, BatteryPower, SolarPower, ShorePower, GenPower, AltPower):
    
    Invert_status_str = mqttclient.AliasData["_var15Invert_status_name"]                                  #Invertor string meaning"

    RightMotion, LeftMotion = FlowMotion()  
    if BatteryPower < 0:                  #Battery charging if negative power  TODO check if this is correct
        BatteryFlow = LeftMotion
    else:
        BatteryFlow = RightMotion

    if Invert_status_num == 1:          #DC Passthrough
        if BatteryPower < 0:                  #Battery charging if negative power
            Invert_status_str = 'Alternator Powered'
        else:
            Invert_status_str = 'Battery Powered'
        InvertPwrFlow = LeftMotion

    elif Invert_status_num == 2:        #AC Passthrough
        Invert_status_str = 'Shore Powered'
        InvertPwrFlow = RightMotion

    else:
        InvertPwrFlow = '??'

    if AltPower > 0:
        AltPwrFlow = RightMotion
    else:
        AltPwrFlow = ''
        
    if SolarPower > 0:
        SolarPwrFlow = RightMotion
    else:
        SolarPwrFlow = ''

    if ShorePower > 0:
        ShorePwrFlow = RightMotion
    else:
        ShorePwrFlow = ''

    if GenPower > 0:
        GeneratorPwrFlow = LeftMotion
    else:
        GeneratorPwrFlow = ''

    return(BatteryFlow, InvertPwrFlow, ShorePwrFlow, GeneratorPwrFlow, SolarPwrFlow, AltPwrFlow, Invert_status_str)

@app.get("/data")
async def data() -> DataResponse:
    global timesbase, LastTime

   
    #Power Calculations
    Invert_status_num = mqttclient.AliasData["_var16Invert_status_num"]                                   #DC Invertor numerical state"
    """note: Invert_status_num meaning = 
        0 - Disabled
        1 - Invert
        2 - AC passthru
        3 - APS Only
        4 - Load sense (Unit is waiting for a load.)
        5 - Waiting to Invert
        6. Generator support
    """
    #AC Inverter
    Charger_AC_current=float(mqttclient.AliasData["_var02Charger_AC_current"])                                #AC charger RMS current" 
    Invert_AC_voltage=float(mqttclient.AliasData["_var10Invert_AC_voltage"])                             #AC invertor RMS voltage" 
    Charger_AC_power = Invert_AC_voltage * Charger_AC_current                                                     #AC charger power   
    Invert_AC_current=float(mqttclient.AliasData["_var09Invert_AC_current"])                                #AC invertor RMS current"
    Invert_AC_power=Invert_AC_voltage *Invert_AC_current                                                      #AC invertor power
    Total_Invertor_AC_power = Charger_AC_power + Invert_AC_power
    #DC Invertor
    DC_Charger_current=(mqttclient.AliasData["_var04Charger_current"])                                   #DC charger  current"  
    DC_volts=float(mqttclient.AliasData["_var05Charger_voltage"])                                #DC charger  voltage" 
    DC_volts2 = float(mqttclient.AliasData["_var14Invert_DC_Volt"])
    if DC_volts != DC_volts2:
        print('DC voltages do not match', DC_volts, DC_volts2)
    DC_Charger_power = DC_volts * DC_Charger_current                                                     #DC charger power
    Invert_DC_Amp=float(mqttclient.AliasData["_var13Invert_DC_Amp"])                               #DC Invertor current"
    Invert_DC_power = DC_volts * Invert_DC_Amp                                                   #DC Invertor power
    Total_Invert_DC_power = DC_Charger_power + Invert_DC_power

    InvertorMaxPower = max(Total_Invertor_AC_power, Total_Invert_DC_power)

    try:
        BatteryPower = (mqttclient.AliasData["_var18Batt_voltage"] * mqttclient.AliasData["_var19Batt_current"])                                #Battery power"
    except:
        BatteryPower = 0.0

    try:
        ATS_Power = mqttclient.AliasData["_var23ATS_AC_voltage"] * mqttclient.AliasData["_var22ATS_AC_current"] 
        ATS_Line = mqttclient.AliasData["_var21ATS_Line"]
    except:
        ATS_Power = 0
        ATS_Line = 0

    if ATS_Line == 1:
        Shore_power = ATS_Power
        GenPower = 0
    else:
        Shore_power = 0
        GenPower = ATS_Power                                     #Shore power"

    try:
        SolarPower = (mqttclient.AliasData["_var26Solar_voltage"] * mqttclient.AliasData["_var27Solar_current"])                                #Battery power"
    except:
        SolarPower = 0

    #Note: Alternator power not measured so using estimate  
    if BatteryPower < 0 and Invert_status_num == 1:                  # DC Pass and Battery charging if negative power
        #Assume that the battery is charging from the Alternator and DC_Load is unchanged
        #AC_Load = mqttclient.AliasData["_var24RV_Loads_AC"]
        try:
            DC_Load = mqttclient.AliasData["_var25RV_Loads_DC"]
            if DC_Load == '':
                DC_Load = 54
        except:
            DC_Load = 54
        AlternatorPower = -BatteryPower + DC_Load + InvertorMaxPower - SolarPower
    else:
        AlternatorPower = 0


    #Calc AC and DC Loads since not measured
    if Invert_status_num == 1:          #DC Passthrough
        #Only power source on AC side is the inverter; therefor, AC_Load = inverter power
        AC_Load = Invert_AC_power
        DC_Load = BatteryPower + SolarPower + AlternatorPower - InvertorMaxPower
    elif Invert_status_num == 2:        #AC Passthrough
        AC_Load = ATS_Power - Invert_AC_power
        DC_Load = InvertorMaxPower + BatteryPower + SolarPower + AlternatorPower
    else:
        #Shouldn't get here
        AC_Load = -1     
        DC_Load = -1

    #publish AC_Load and DC Load TODO


    

    HoursRemaining = 11.5
    Batt_Charge = int(mqttclient.AliasData["_var20Batt_charge"])                                   #Battery charge"

    (BatteryFlow, InvertPwrFlow, ShorePwrFlow, GeneratorPwrFlow, SolarPwrFlow, AltPwrFlow, Invert_status_str) = \
        GenAllFlows(Invert_status_num, BatteryPower, SolarPower, Shore_power, GenPower, AlternatorPower)

    #House Keeping Messages
    RedLamp = mqttclient.AliasData["_var07Red"]
    if RedLamp == '00':
        RedMsg = ''
    else:
        RedMsg = RedLamp + ' Red Lamp Fault'
    YellowLamp =str(mqttclient.AliasData["_var08Yellow"]) + " Yellow Lamp" 
    YellowMsg = ''
    Time_Str =str('%.1f' % ((float(mqttclient.AliasData["_var01Timestamp"])-timebase)/60)) + " Time"

    return DataResponse(
        var1 =str(Shore_power) + ' Watts',      #shore power (watts)
        var2 =ShorePwrFlow,                                             #shorepower Flow
        var3 =str('%.0f' % Invert_AC_voltage) + " Volts AC",
        var4 =str('%.0f' % AC_Load) + ' Watts',  
        var5 =str(SolarPower) + ' Watts',
        var6 =SolarPwrFlow,                                             #solar power Flow
        var7 =str('%.1f' % DC_volts2) + " Volts DC",
        var8 =str('%.0f' % DC_Load) + ' Watts',
        var9 = str(AlternatorPower) + " Watts",                                #Alternator power
        var10=InvertPwrFlow,                                            #flow annimation   
        var11=Invert_status_str,
        var12= str('%.0f' % InvertorMaxPower) + " Watts Transferring",
        var13=RedMsg, 
        var14=AltPwrFlow,                                               #Alternator power Flow
        #battery variables begin
        var15=str(HoursRemaining) + ' Est hours reamining',
        var16= str('?? Battery Status'),
        var17= GeneratorPwrFlow,
        var18= BatteryFlow,                        #Battery power Flow
        var19= str('%.0f' % (BatteryPower)) + " Watts",
        #battery variables end 
        var20=Time_Str,
        battery_percent= Batt_Charge,
    )

@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}


app.mount("/", StaticFiles(directory="build"), name="ui")


if __name__ == "__main__":
    #kick off threads here  
    # mqttclient("pub","localhost", 1883, "dgn_variables.json",'_var', 'RVC', debug) 
    t1 = threading.Thread(target=mqttclient.mqttclient("sub","localhost", 1883, "dgn_variables.json",'_var', 'RVC', 0).run_mqtt_infinite)
    #t1 = threading.Thread(target=mqttclient.mqttclient().printhello)
    t1.start()

    # "0.0.0.0" => accept requests from any IP addr
    #uvicorn.run("app", host="0.0.0.0", port=80, reload=True)

    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    