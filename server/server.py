#!/usr/bin/env python3
import threading
import uvicorn
#import alarm
import mqttclient
from typing import Annotated

from fastapi import FastAPI, Body
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import random
from server_calcs import *



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

bike_alarm_state = False
interior_alarm_state = False

class AlarmPostData(BaseModel):
    alarm: str
    state: bool

@app.post("/api/alarmpost")
async def alarm(data: Annotated[AlarmPostData, Body()]) -> dict:
    global bike_alarm_state, interior_alarm_state
    print(f"Alarm: {data.alarm} State: {data.state}")
    if data.alarm == "bike":
        bike_alarm_state = data.state
    elif data.alarm == "interior":
        interior_alarm_state = data.state

    #alarm.set_alarm(data.alarm, data.state)
    return {"status": "ok"}

@app.get("/api/alarmget")
async def alarms() -> dict:
    global bike_alarm_state, interior_alarm_state
    return {"bike": bike_alarm_state, "interior": interior_alarm_state}

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


# This is the POWER page function that is called by the front end client
@app.get("/data/power")
async def data()-> DataResponse:

    (InvertorMaxPower, DC_volts, Invert_AC_voltage, Invert_AC_power, Invert_status_num) = InvertCalcs()
    (ShorePower, GenPower)= ATS_Calcs()
    (SolarPower) = SolcarCalcs()
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs(DC_volts)
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, InvertorMaxPower, SolarPower)

    (BatteryFlow, InvertPwrFlow, ShorePwrFlow, GeneratorPwrFlow, SolarPwrFlow, AltPwrFlow, Invert_status_str) = \
        GenAllFlows(Invert_status_num, Batt_Power, SolarPower, ShorePower, GenPower, AlternatorPower)

    #Calc AC and DC Loads since not measured
    (AC_Load, DC_Load) = LoadCalcs(Invert_status_num, InvertorMaxPower, ShorePower, GenPower, Invert_AC_power, Batt_Power, SolarPower, AlternatorPower)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    return DataResponse(
        var1 =str(ShorePower) + ' Watts',      #shore power (watts)
        var2 =ShorePwrFlow,                                             #shorepower Flow
        var3 =str('%.0f' % Invert_AC_voltage) + " Volts AC",
        var4 =str('%.0f' % AC_Load) + ' Watts',  
        var5 =str(SolarPower) + ' Watts',
        var6 =SolarPwrFlow,                                             #solar power Flow
        var7 =str('%.1f' % DC_volts) + " Volts DC",
        var8 =str('%.0f' % DC_Load) + ' Watts',
        var9 = str(AlternatorPower) + " Watts",                                #Alternator power
        var10=InvertPwrFlow,                                            #flow annimation   
        var11=Invert_status_str,
        var12= str('%.0f' % InvertorMaxPower) + " Watts Transferring",
        var13=RedMsg, 
        var14=AltPwrFlow,                                               #Alternator power Flow
        #battery variables begin
        var15= Batt_Hours_Remaining_str,
        var16= 'Battery Status: ' + Batt_status_str,
        var17= GeneratorPwrFlow,
        var18= BatteryFlow,                        #Battery power Flow
        var19= str('%.0f' % Batt_Power) + " Watts",
        battery_percent= Batt_Charge,
        #battery variables end 
        var20=Time_Str,
        
    )

# This is the HOME page function that is called by the front end client
@app.get("/data/home")
async def data()-> DataResponse:

 return DataResponse(
        var1 = 'var1' + ' Watts', 
        var2 = 'var2',
        var3 =str('%.1f' % random.randint(10,13)) + " Volts AC",
        var4 = 'var4',
        var5 = 'var5',
        var6 = 'var6',
        var7 = 'var7',
        var8 = 'var8',
        var9 = 'var9',                                #Alternator power
        var10= 'var10',                                            #flow annimation
        var11= 'var11',
        var12= 'var12',
        var13= 'var13',
        var14= 'var14',
        var15= 'var15',
        var16= 'var16',
        var17= 'var17',
        var18= 'var18',
        var19= 'var19',
        battery_percent= '50',
        var20= 'var20',
        
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
    # default port is 8000.  Dockerfile sets port = 80 using environment variable

    
   
    print(constants["IPADDR"], constants["PORT"])
    

    uvicorn.run(app, host="0.0.0.0", port=constants["PORT"])
    