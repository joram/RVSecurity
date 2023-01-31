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
TopicData = {}
TargetAlias = {}
AliasData = {}

debug = 0

class webmqttclient():

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
                print('Subscribing to: ', key)
            client.subscribe(name,0)
        print('Running...')

    # The callback for when a PUBLISH message is received from the MQTT server.
    def _on_message(self, client, userdata, msg):
        global TargetTopics, TopicData, msg_counter, AliasData, TargetAlias
        if debug>3:
            print(msg.topic+ " " + str(msg.payload))
        msg_dict = json.loads(msg.payload.decode('utf-8'))

        for item in TargetTopics[msg.topic]:
            if item == 'instance':
                break
            if debug>3:
                print(item,'= ', msg_dict[item])
            tmp = msg.topic + '/' + item
            TopicData[tmp] = msg_dict[item]
            AliasData[TargetAlias[tmp]] = msg_dict[item]

        if debug > 0:
            #This is a poor way to provide a UI but tkinter isn't working
            msg_counter += 1
            if msg_counter % 20 == 0:
                #os.system('clear')
                print('*******************************************************')
                pprint(AliasData)
                os.sys.stdout.flush()
                msg_counter = 0
        
    def run_webMQTT_infinite(self):
        global TopicData, AliasData, TargetAlias, TargetTopics, topic_prefix

        client = mqtt.Client()
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        try:
            client.connect("localhost", 1883, 60)
        except:
            print("Can't connect to MQTT Broker -- exiting")
            exit()

        try:    
            with open("/home/pi/Code/joram/RVSecurity/api/dgn_variables.json","r") as newfile: 
                try:
                    data = json.load(newfile)
                except: 
                    print('Json file format error --- exiting')
                    exit()
        except:
            print('dgn_variables.json file not found -- exiting')
            exit()

       
        for item in data:
            if "instance" in data[item]:
                topic = topic_prefix + '/' + item + '/' + str(data[item]["instance"])
            else:   
                topic = topic_prefix + '/' + item
            for entryvar in data[item]:
                tmp = data[item][entryvar]
                if  isinstance(tmp, str) and tmp.startswith("_var"):
                    if topic not in TargetTopics:
                        TargetTopics[topic] = {}
                    TargetTopics[topic][entryvar] = tmp
                    local_topic = topic + '/' + entryvar
                    TopicData[local_topic] = ''
                    AliasData[tmp] = ''
                    TargetAlias[local_topic] = tmp
        if debug > 0:
            pprint(TargetTopics)
            pprint(TopicData)
            pprint(TargetAlias)
            pprint(AliasData)

        client.loop_forever()

    def printhello(self):
        global TargetTopics, TargetAlias, TopicData, AliasData
        print('Hello*****************')
        pprint(TargetTopics)
        pprint(TopicData)
        pprint(TargetAlias)
        pprint(AliasData)
        os.sys.stdout.flush()

if __name__ == "__main__":
    debug = 1
    RVCWeb = webmqttclient()
    RVCWeb.run_webMQTT_infinite()