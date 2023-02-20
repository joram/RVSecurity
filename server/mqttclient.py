#mqtt client to read values of interest from broker

import os
import time
import random
import json
import re       # regular expressions   
import paho.mqtt.client as mqtt
from pprint import pprint


#globals
topic_prefix = 'RVC'
msg_counter = 0
AllData = {}
TargetTopics = {}
MQTTNameToAliasName = {}
AliasData = {}
client = None
mode = 'sub'
debug = 0

class mqttclient():

    def __init__(self, initmode, mqttbroker,mqttport, mqtttopicjsonfile, varIDstr, topic_prefix, debug):
        global client, AllData, AliasData, MQTTNameToAliasName, TargetTopics, mode

        mode = initmode
        # read in the json file that defines the topics and variables of interest
        try:    
            with open(mqtttopicjsonfile,"r") as newfile: 
                try:
                    data = json.load(newfile)
                except: 
                    print('Json file format error --- exiting')
                    exit()
        except:
            print('dgn_variables.json file not found -- exiting')
            exit()
        AllData = data

        for item in data:
            if "instance" in data[item]:
                topic = topic_prefix + '/' + item + '/' + str(data[item]["instance"])
            else:   
                topic = topic_prefix + '/' + item
            for entryvar in data[item]:
                tmp = data[item][entryvar]
                if  isinstance(tmp, str) and tmp.startswith(varIDstr):
                    if topic not in TargetTopics:
                        TargetTopics[topic] = {}
                    TargetTopics[topic][entryvar] = tmp
                    local_topic = topic + '/' + entryvar
                    AliasData[tmp] = ''
                    MQTTNameToAliasName[local_topic] = tmp
        if debug > 0:
            #print('>>AllData:')
            #pprint(AllData)
            print('>>TargetTopics:')
            pprint(TargetTopics)
            print('>>MQTTnameToAliasName:')
            pprint(MQTTNameToAliasName)
            print('>>AliasData:')
            pprint(AliasData)
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

        # setup the MQTT client
        client = mqtt.Client()
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        try:
            client.connect(mqttbroker,mqttport, 60)
        except:
            print("Can't connect to MQTT Broker/port -- exiting",mqttbroker,":",mqttport)
            exit()

        

       
        

    # The callback for when the client receives a CONNACK response from the server.
    def _on_connect(self, client, userdata, flags, rc):
        global TargetTopics, mode

        if rc == 0:
            print("_on_connect to MQTT Server - OK")
        else:
            print('Failed _on_connect to MQTT server.  Result code = ', rc)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("$SYS/#")
        if mode == 'sub':
            for name in TargetTopics:
                if debug>3:
                    print('Subscribing to: ', name)
                client.subscribe(name,0)
        print('Running...')

    # The callback for when a PUBLISH message is received from the MQTT server.
    def _on_message(self, client, userdata, msg):
        global TargetTopics, msg_counter, AliasData, MQTTNameToAliasName
        if debug>3:
            print(msg.topic+ " " + str(msg.payload))
        msg_dict = json.loads(msg.payload.decode('utf-8'))

        for item in TargetTopics[msg.topic]:
            if item == 'instance':
                break
            if debug>3:
                print(item,'= ', msg_dict[item])
            tmp = msg.topic + '/' + item
            AliasData[MQTTNameToAliasName[tmp]] = msg_dict[item]

        if debug > 0:
            #This is a poor way to provide a UI but tkinter isn't working
            msg_counter += 1
            if msg_counter % 20 == 0:
                #os.system('clear')
                print('*******************************************************')
                pprint(AliasData)
                os.sys.stdout.flush()
                msg_counter = 0
    
    def pub(self, payload, qos=0, retain=False):
        global client, debug, topic_prefix
                
        if "instance" in payload:
            topic = topic_prefix + '/' + payload["name"] + '/' + str(payload["instance"])
        else:   
            topic = topic_prefix + '/' + payload["name"]             

        if debug > 0:
            print('Publishing: ', topic, payload)
        #quick check that topic is in TargetTopics
        if topic not in TargetTopics:
            print('Error: Publishing topic not in  specified json file: ', topic)
        client.publish(topic, json.dumps(payload), qos, retain)
                
    def run_mqtt_infinite(self):
        global client
        client.loop_forever()


if __name__ == "__main__":
    debug = 1
    mode = 'pub'
    RVC_Client = mqttclient(mode,"localhost", 1883, "dgn_variables.json",'_var', 'RVC', debug)
    if mode == 'sub':
        RVC_Client.run_mqtt_infinite()
    else:
        while True:
            time.sleep(6)
            #update AllData disctionary with new variable data
            """  target topic from json file 
            "BATTERY_STATUS":{                         
                    "instance":1,
                    "name":"BATTERY_STATUS",
                    "DC_voltage":                                               "_var18Batt_voltage",
                    "DC_current":                                               "_var19Batt_current",
                    "State_of_charge":                                          "_var20Batt_charge",
                    "Status":                                                    ""},
            """ 
            #Update the dictionary with new data and publish
            AllData['BATTERY_STATUS']["DC_voltage"] = 12.0 + random.random()
            AllData['BATTERY_STATUS']["DC_current"] =  20 * random.random() - 10
            AllData['BATTERY_STATUS']["State_of_charge"] = 100 - random.random()*100
            AllData['BATTERY_STATUS']["Status"] = "OK"
            RVC_Client.pub(AllData['BATTERY_STATUS'])
