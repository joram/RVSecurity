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
    
    CurrentTime = int(time.time()) % 5

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

@app.get("/data")
async def data() -> DataResponse:
    global timesbase, LastTime

    #print('mqttclient.', mqttclient.AliasData["_var07"])
    #print(type(mqttclient.AliasData["_var02"]),type(mqttclient.AliasData["_var03"]), type(mqttclient.AliasData["_var15"]), type(mqttclient.AliasData["_var16"]))
   
    

    Charger_AC_current=float(mqttclient.AliasData["_var02Charger_AC_current"])                                #AC charger RMS current" 
    Invert_AC_voltage=float(mqttclient.AliasData["_var10Invert_AC_voltage"])                             #AC invertor RMS voltage" 
    Charger_AC_power = Invert_AC_voltage * Charger_AC_current                                                     #AC charger power   
   
    Invert_AC_current=float(mqttclient.AliasData["_var09Invert_AC_current"])                                #AC invertor RMS current"
    Invert_AC_power=Invert_AC_voltage *Invert_AC_current                                                      #AC invertor power

    Total_AC_power = Charger_AC_power + Invert_AC_power
    
    Charger_current=(mqttclient.AliasData["_var04Charger_current"])                                   #DC charger  current"  
    DC_volts=float(mqttclient.AliasData["_var05Charger_voltage"])                                #DC charger  voltage" 
    DC_Charger_power = DC_volts * Charger_current                                                     #DC charger power

    Invert_DC_Amp=float(mqttclient.AliasData["_var13Invert_DC_Amp"])                               #DC Invertor current"
    Invert_DC_power = DC_volts * Invert_DC_Amp                                                   #DC Invertor power

    Total_DC_power = DC_Charger_power + Invert_DC_power

    InvertorMaxPower = max(Total_AC_power, Total_DC_power)

    try:
        BatteryPower = (mqttclient.AliasData["_var18Batt_voltage"] * mqttclient.AliasData["_var19Batt_current"])                                #Battery power"
    except:
        BatteryPower = 0.0


    SolarPower = 0
    DC_Load = (DC_Charger_power + SolarPower)
    
    HoursRemaining = 11.5
    
    Invert_status_num = mqttclient.AliasData["_var16Invert_status_num"]                                   #DC Invertor numerical state"
    RightMotion, LeftMotion = FlowMotion()  
    if BatteryPower < 0:                  #Battery charging if negative power
        BatteryFlow = LeftMotion
    else:
        BatteryFlow = RightMotion

    if Invert_status_num == 1:          #DC Passthrough
        InvertFlow = LeftMotion
        ShorePwrFlow = '|'
        SolarPwrFlow = '?'                      #Solar power Flow
        LoadACPowerStr = str('%.0f' % Invert_AC_power)


    elif Invert_status_num == 2:        #AC Passthrough
        InvertFlow = RightMotion
        ShorePwrFlow = RightMotion
        SolarPwrFlow = '?'                      #Solar power Flow
        LoadACPowerStr = '??'

    else:
        InvertFlow = '??'
        ShorePwrFlow = ''                       
        SolarPwrFlow = '?'                      #Solar power Flow
        LoadACPowerStr = '??'

    return DataResponse(
        var1 ='?? Shore Watts',                            #shore power (watts)
        var2 =ShorePwrFlow,                  #shorepower or generator Flow
        var3 =str('%.0f' % mqttclient.AliasData["_var10Invert_AC_voltage"]) + " Volts AC",
        var4 =LoadACPowerStr + ' Watts AC Load',  
        var5 =str(SolarPower) + ' Watts Solar',
        var6 =SolarPwrFlow,                  #solar power Flow
        var7 =str('%.1f' % mqttclient.AliasData["_var14Invert_DC_Volt"]) + " Volts DC",
        var8 =str('%.0f' % DC_Load) + ' Watts + Solar=0',
        var9 ="not known watts",
        var10=InvertFlow,                                         #flow annimation   
        var11=mqttclient.AliasData["_var15Invert_status_name"],
        var12= str('%.0f' % InvertorMaxPower) + " Watts Transfer",
        var13=str(mqttclient.AliasData["_var07Red"]) + " Red Lamp", 
        var14=str(mqttclient.AliasData["_var08Yellow"]) + " Yellow Lamp", 
        #battery variables begin
        var15=str(HoursRemaining) + ' Est hours reamining',
        var16= str('?? Battery Status'),
        var17= 'unused',
        var18= BatteryFlow,                        #Battery power Flow
        var19= str('%.2f' % (BatteryPower)) + " Watts",
        #battery variables end 
        var20=str('%.1f' % ((float(mqttclient.AliasData["_var01Timestamp"])-timebase)/60)) + " Time (min)",
        battery_percent= int(mqttclient.AliasData["_var20Batt_charge"]),
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
    