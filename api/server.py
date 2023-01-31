#!/usr/bin/env python3
import threading
import time
import uvicorn
#import alarm
import mqttwebclient

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import random
import math

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


@app.get("/data")
async def data() -> DataResponse:

    #print('mqttwebclient.', mqttwebclient.AliasData["_var07"])
    print(type(mqttwebclient.AliasData["_var02"]),type(mqttwebclient.AliasData["_var03"]), type(mqttwebclient.AliasData["_var15"]), type(mqttwebclient.AliasData["_var16"]))

    # TODO: get real data
    return DataResponse(
        var1=str('??'),               # Shore Power Watts
        var2=str('??'),  # Solar Output Watts
        var3=str('??'),  # Generator Watts
        var4='%.2f' % (mqttwebclient.AliasData["_var02"] * mqttwebclient.AliasData["_var03"]),  # Invertor AC Watts =  (_var02 * _var03;  mode = _var01)
        var5='%.2f' % (mqttwebclient.AliasData["_var15"] * mqttwebclient.AliasData["_var16"]),  # Invertor DC Watts  = (_var15 * _var16)
        var6=str('??'),  # Battery % remaining
        var7=str('??'),  # Battery Watts I/O
        var8=mqttwebclient.AliasData["_var07"],  # Battery charge status = _var07
        var9=str('??'),  # AC Load Watts
        var10=str('??'), # DC Load Watts
        var11='%.2f' % (mqttwebclient.AliasData["_var03"]), # AC Volts = _var03
        var12='%.2f' % (mqttwebclient.AliasData["_var16"]), # DC Volts = _var16
    )

@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}


app.mount("/", StaticFiles(directory="build"), name="ui")


if __name__ == "__main__":
    #kick off threads here    
    t1 = threading.Thread(target=mqttwebclient.webmqttclient().run_webMQTT_infinite)
    #t1 = threading.Thread(target=mqttwebclient.webmqttclient().printhello)
    t1.start()

    # "0.0.0.0" => accept requests from any IP addr
    #uvicorn.run("app", host="0.0.0.0", port=80, reload=True)

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print('keyboard inetrrupt ')
