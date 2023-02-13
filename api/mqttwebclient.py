#mqtt client to read values of interest from broker

import os
import time
import json
import paho.mqtt.client as mqtt
from pprint import pprint


#globals
topic_prefix = 'RVC'
msg_counter = 0
TargetTopics = {}
MQTTNameToAliasName = {}
AliasData = {}
client = None

debug = 0

class webmqttclient():

    def __init__(self,mqttbroker,mqttport, mqtttopicjsonfile, varIDstr, topic_prefix, append_instance, debug):
        global client, AliasData, MQTTNameToAliasName, TargetTopics

        client = mqtt.Client()
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        try:
            client.connect(mqttbroker,mqttport, 60)
        except:
            print("Can't connect to MQTT Broker/port -- exiting",mqttbroker,":",mqttport)
            exit()

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

       
        for item in data:
            if append_instance and "instance" in data[item]:
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
            print('>>TargetTopics:')
            pprint(TargetTopics)
            print('>>MQTTnameToAliasName:')
            pprint(MQTTNameToAliasName)
            print('>>AliasData:')
            pprint(AliasData)
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

    # The callback for when the client receives a CONNACK response from the server.
    def _on_connect(self, client, userdata, flags, rc):
        global TargetTopics

        if rc == 0:
            print("_on_connect to MQTT Server - OK")
        else:
            print('Failed _on_connect to MQTT server.  Result code = ', rc)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("$SYS/#")
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
    
    def pub(self,topic, payload, qos=0, retain=False):
        global client
        if debug > 3:
            print('Publishing: ', topic, payload)
        if payload(0:3) == '_var':
            payload = AliasData[payload]
        client.publish(topic, payload, qos, retain)
        
    def run_webMQTT_infinite(self):
        global client
        client.loop_forever()


if __name__ == "__main__":
    debug = 1
    RVCWeb = webmqttclient("localhost", 1883, "dgn_variables.json",'_var', 'RVC', True, debug)
    RVCWeb.run_webMQTT_infinite()