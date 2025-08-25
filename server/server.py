#!/usr/bin/env python3
import threading
import uvicorn
import os
import subprocess
import tempfile
import sys
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
try:
    index_content = open("build/index.html").read()
except FileNotFoundError:
    index_content = "<html><body><h1>RV Security Server Running</h1><p>Build the client first with 'make build'</p></body></html>"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/power")
@app.get("/wifi")
async def index():
    return Response(index_content)

bike_alarm_state = False
interior_alarm_state = False

class AlarmPostData(BaseModel):
    alarm: str
    state: bool

class WiFiConfigData(BaseModel):
    ssid: str
    password: str
    permanent: bool = False

class WiFiConfigData(BaseModel):
    ssid: str
    password: str
    permanent: bool = False

class WiFiConfigResponse(BaseModel):
    exit_code: int
    output: str
    success: bool

@app.post("/api/alarmpost")
async def alarm(data: Annotated[AlarmPostData, Body()]) -> dict:
    global bike_alarm_state, interior_alarm_state
    if debug > 0:
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

@app.post("/api/wifi-config")
async def wifi_config(data: Annotated[WiFiConfigData, Body()]) -> dict:
    """
    Configure WiFi on RP2W device by calling the RP5toRPZero2WControl.py script
    """
    try:
        # Path to the WiFi control script - adjust this path as needed
        script_path = "/home/tblank/code/tblank1024/WifitoHostBridge/RP5toRPZero2WControl.py"
        
        # Prepare the command arguments
        cmd_args = [sys.executable, script_path, data.ssid, data.password]
        
        # If permanent storage is requested, add a profile name
        if data.permanent:
            profile_name = f"Profile_{data.ssid}"
            cmd_args.append(profile_name)
        
        # Execute the WiFi configuration script
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Capture the output
        output = result.stdout
        if result.stderr:
            output += f"\nError output: {result.stderr}"
        
        return {
            "exit_code": result.returncode,
            "output": output,
            "command": " ".join(cmd_args[:-2] + ["<ssid>", "<password>"] + cmd_args[-1:] if len(cmd_args) > 4 else ["<ssid>", "<password>"])
        }
        
    except subprocess.TimeoutExpired:
        return {
            "exit_code": 1,
            "output": "Error: WiFi configuration timed out after 30 seconds",
            "command": "timeout"
        }
    except FileNotFoundError:
        return {
            "exit_code": 1,
            "output": f"Error: WiFi configuration script not found at {script_path}",
            "command": "not_found"
        }
    except Exception as e:
        return {
            "exit_code": 1,
            "output": f"Error: Unexpected error occurred: {str(e)}",
            "command": "error"
        }

@app.post("/api/wifi-config")
async def wifi_config(data: Annotated[WiFiConfigData, Body()]) -> WiFiConfigResponse:
    """
    Configure WiFi settings on RP2W device using the RP5toRPZero2WControl.py script
    """
    try:
        # Path to the WiFi control script - adjust this path as needed
        script_path = "/home/tblank/code/tblank1024/WifitoHostBridge/RP5toRPZero2WControl.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            return WiFiConfigResponse(
                exit_code=1,
                output=f"WiFi control script not found at {script_path}",
                success=False
            )
        
        # Prepare command arguments
        cmd = [sys.executable, script_path, data.ssid, data.password]
        
        # Add profile name if permanent storage is requested
        if data.permanent:
            profile_name = f"RV_{data.ssid.replace(' ', '_')}"
            cmd.append(profile_name)
        
        # Execute the WiFi configuration script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Determine success based on exit code
        success = result.returncode == 0
        
        # Combine stdout and stderr for output
        output_lines = []
        if result.stdout:
            output_lines.append("STDOUT:")
            output_lines.append(result.stdout)
        if result.stderr:
            output_lines.append("STDERR:")
            output_lines.append(result.stderr)
        
        output = "\n".join(output_lines) if output_lines else "No output received"
        
        return WiFiConfigResponse(
            exit_code=result.returncode,
            output=output,
            success=success
        )
        
    except subprocess.TimeoutExpired:
        return WiFiConfigResponse(
            exit_code=1,
            output="WiFi configuration timed out after 30 seconds",
            success=False
        )
    except Exception as e:
        return WiFiConfigResponse(
            exit_code=1,
            output=f"Error executing WiFi configuration: {str(e)}",
            success=False
        )

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
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs(debug)
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
        var16= 'Status: ' + Batt_status_str,
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
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs(debug)
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, Invert_DC_power, SolarPower)

    #Calc AC and DC Loads since not measured
    (AC_HeatPump_Load, DC_Load) = LoadCalcs(Invert_status_num, Charger_AC_power, DC_Charger_power, ShorePower, GenPower, Batt_Power, SolarPower, AlternatorPower, Invert_DC_power)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    Tank_Fresh = round(rvglue.rvglue.AliasData["_var29Tank_Level"]/rvglue.rvglue.AliasData["_var30Tank_Resolution"] * 100 )  
    Tank_Black = round(rvglue.rvglue.AliasData["_var32Tank_Level"]/rvglue.rvglue.AliasData["_var33Tank_Resolution"] * 100)
    Tank_Gray = round(rvglue.rvglue.AliasData["_var35Tank_Level"]/rvglue.rvglue.AliasData["_var36Tank_Resolution"] * 100)   
    Tank_Propane = round(rvglue.rvglue.AliasData["_var38Tank_Level"]/rvglue.rvglue.AliasData["_var39Tank_Resolution"] * 100)  

    if debug > 0:
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
        var16= 'Status: ' + Batt_status_str,
        var17= Tank_Fresh,
        var18= Tank_Propane,
        var19= str('%.0f' % Batt_Power) + " Watts",
        battery_percent= Batt_Charge,
        var20= Time_Str,
        
    )

@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}

import os
if os.path.exists("build") and os.path.isdir("build"):
    static_files = StaticFiles(directory="build")
    app.mount("/", static_files, name="ui")


if __name__ == "__main__":
    #kick off threads here  
    # MQTTClient("pub","localhost", 1883, "dgn_variables.json",'_var', 'RVC', debug) 
    debug = 0
    client = MQTTClient("sub","localhost", 1883, '_var', 'RVC', debug)
    t1 = threading.Thread(target=client.run_mqtt_infinite)
    #t1 = threading.Thread(target=MQTTClient.MQTTClient().printhello)
    t1.start()

    # "0.0.0.0" => accept requests from any IP addr
    # default port is 8000.  Dockerfile sets port = 80 using environment variable

    
   
    print(constants["IPADDR"], constants["PORT"])
    

    uvicorn.run(app, host="0.0.0.0", port=int(constants["PORT"]), log_level="warning")
