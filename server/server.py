#!/usr/bin/env python3
import threading
import uvicorn
#import alarm
#import MQTTClient
import rvglue
from typing import Annotated

from fastapi import FastAPI, Body
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import random
from server_calcs import *



app = FastAPI()
index_content = open("build/index.html").read()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/power")
@app.get("/contact")
async def index():
    return Response(index_content)

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

    (Charger_AC_power, Charger_AC_voltage, Invert_AC_power, DC_Charger_power, DC_Charger_volts, Invert_DC_power, Invert_status_num)= InvertCalcs()
    (ShorePower, GenPower)= ATS_Calcs()
    (SolarPower) = SolcarCalcs()
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs()
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, Invert_DC_power, SolarPower)

    (BatteryFlow, InvertPwrFlow, ShorePwrFlow, GeneratorPwrFlow, SolarPwrFlow, AltPwrFlow, Invert_status_str) = \
        GenAllFlows(Invert_status_num, Batt_Power, SolarPower, ShorePower, GenPower, AlternatorPower)

    #Calc AC and DC Loads since not measured
    (AC_HeatPump_Load, DC_Load) = LoadCalcs(Invert_status_num, Charger_AC_power, DC_Charger_power, ShorePower, GenPower, Batt_Power, SolarPower, AlternatorPower, Invert_DC_power)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    return DataResponse(
        var1 =str(max(ShorePower, GenPower)) + ' Watts',      #shore or gen power (watts)
        var2 =ShorePwrFlow,                                             #shorepower Flow
        var3 =str('%.0f' % Charger_AC_voltage) + " Volts AC",
        var4 =str('%.0f' % AC_HeatPump_Load) + ' Watts',  
        var5 =str(SolarPower) + ' Watts',
        var6 =SolarPwrFlow,                                             #solar power Flow
        var7 =str('%.1f' % Batt_Voltage) + " Volts DC",
        var8 =str('%.0f' % DC_Load) + ' Watts',
        var9 = str('%.0f' % AlternatorPower) + " Watts",                                #Alternator power
        var10=InvertPwrFlow,                                            #flow annimation   
        var11=str('%.0f' % Charger_AC_power) + " Watts", 
        var12= str('%.0f' % max(Invert_AC_power, .8 * (Invert_DC_power)) + " Watts"),      #note: .8 is efficiency estimate of inverter
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

    (Charger_AC_power, Charger_AC_voltage, Invert_AC_power, DC_Charger_power, DC_Charger_volts, Invert_DC_power, Invert_status_num)= InvertCalcs()
    (ShorePower, GenPower)= ATS_Calcs()
    (SolarPower) = SolcarCalcs()
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs()
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, Invert_DC_power, SolarPower)

    #Calc AC and DC Loads since not measured
    (AC_HeatPump_Load, DC_Load) = LoadCalcs(Invert_status_num, Charger_AC_power, DC_Charger_power, ShorePower, GenPower, Batt_Power, SolarPower, AlternatorPower, Invert_DC_power)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    Tank_Fresh = round(rvglue.rvglue.AliasData["_var29Tank_Level"]/rvglue.rvglue.AliasData["_var30Tank_Resolution"] * 100 )  
    Tank_Black = round(rvglue.rvglue.AliasData["_var32Tank_Level"]/rvglue.rvglue.AliasData["_var33Tank_Resolution"] * 100)
    Tank_Gray = round(rvglue.rvglue.AliasData["_var35Tank_Level"]/rvglue.rvglue.AliasData["_var36Tank_Resolution"] * 100)   
    Tank_Propane = round(rvglue.rvglue.AliasData["_var38Tank_Level"]/rvglue.rvglue.AliasData["_var39Tank_Resolution"] * 100)  

    print('invert power= ', round(Invert_AC_power), round(Invert_DC_power*.8))

    return DataResponse(
        var1 = 'Outside 60? psi',   # LR outside
        var2 = 'Inside 60? psi',    # LR inside
        var3 = 'Inside 60? psi',   # RR inside
        var4 = 'Outside 60? psi',    # RR outside
        var5 = str(SolarPower) + ' Watts',
        var6 = 'not used',                                            
        var7 = str('%.1f' % Batt_Voltage) + " Volts DC",
        var8 = str('%.0f' % DC_Load) + ' Watts',
        var9 = '60? psi',    # LF
        var10= '60? psi',    # RF
        var11= 'not used',  
        var12= str('%.0f' % max(Invert_AC_power, .8 * (Invert_DC_power)) + " Watts"),      #note: .8 is efficiency estimate of inverter
        var13= Tank_Gray,
        var14= Tank_Black,
        var15= Batt_Hours_Remaining_str,
        var16= 'Battery Status: ' + Batt_status_str,
        var17= Tank_Fresh,
        var18= Tank_Propane,
        var19= str('%.0f' % Batt_Power) + " Watts",
        battery_percent= Batt_Charge,
        var20= Time_Str,
        
    )

@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}

static_files = StaticFiles(directory="build")
app.mount("/", static_files, name="ui")


if __name__ == "__main__":
    #kick off threads here  
    # MQTTClient("pub","localhost", 1883, "dgn_variables.json",'_var', 'RVC', debug) 
    debug = 1
    client = MQTTClient("sub","localhost", 1883, '_var', 'RVC', debug)
    t1 = threading.Thread(target=client.run_mqtt_infinite)
    #t1 = threading.Thread(target=MQTTClient.MQTTClient().printhello)
    t1.start()

    # "0.0.0.0" => accept requests from any IP addr
    # default port is 8000.  Dockerfile sets port = 80 using environment variable

    
   
    print(constants["IPADDR"], constants["PORT"])
    

    uvicorn.run(app, host="0.0.0.0", port=constants["PORT"])
    