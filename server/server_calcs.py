import json
import time
import random
import mqttclient


try:
    fp = open("../constants.json", "r")
    constants = json.load(fp)
except:
    print(" ")
    exit("constants.json file not found or mal formed")

print("hello world!!!")
#Global constants

#BATT_VOLTS-- Battery voltage
#BATT_AH --   Total Battery capacity in amp hours 

BATT_POWER_MAX = float(constants["BATT_VOLTS"]) * float(constants["BATT_AH"])

#Global variables
timebase = 1672772504.9141579 #from replay file
Batt_Power_Last = 0
Batt_Power_Running_Avg = 0
Batt_Power_Remaining = 0

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

def BatteryCalcs(DC_volts):
    global Batt_Power_Last, Batt_Power_Running_Avg, Batt_Power_Remaining, BATT_POWER_MAX

    #Assumptions: 
    #   BatteryPower is negative when charging
    #   Loop is activated once per second
    #   2 x 125 Amp-Hr batteries in system (250 Amp-Hr total)
    #   12V battery system => 12V * 250 Amp-Hr = 3000 Watt-Hr battery capacity
    Batt_Charge = int(mqttclient.AliasData["_var20Batt_charge"])                                    #Battery % charged"
    Batt_Current = mqttclient.AliasData["_var19Batt_current"]                                       #Battery current
    Batt_Voltage = float(mqttclient.AliasData["_var18Batt_voltage"])                                #Battery voltage"  TODO which DC voltage to use???
    Batt_Voltage = DC_volts                                                                         #Battery voltage"  TODO which DC voltage to use???                   
    Batt_Power = Batt_Voltage * Batt_Current
                             
    if Batt_Voltage > 14.8:
        Batt_status_str = 'Over-Voltage Fault'
    elif Batt_Voltage > 14.4:
        Batt_status_str = 'Absorption Charging'
    elif Batt_Voltage > 13.8:
        Batt_status_str = 'Bulk Charging'
    elif Batt_Voltage > 13.6:
        Batt_status_str = 'Float Charging'
    else:
        Batt_status_str = 'Discharging'

    # Calc running average of battery power all in Watt-hours and remaining batter life
    if Batt_Charge > 99:
        Batt_Power_Remaining = BATT_POWER_MAX       #might want a timebased derating factor here
    else:
        Batt_Power_Remaining = Batt_Power_Remaining - Batt_Power / 3600
    if Batt_Power > 0:
        #discharging
        Batt_Power_Running_Avg = (Batt_Power_Running_Avg * 9 + (Batt_Power / 3600)) / 10            #Watt-hours discharging  
        Batt_Hours_Remaining_str = 'Est hours remaining: ' + str('%.1f' % (Batt_Power_Remaining  / Batt_Power_Running_Avg))
    else:
        #charging
        Batt_Power_Running_Avg = 0
        #use charging power to calculate time to 100% charge (assuming 100% charge is BATT_POWER_MAX Watt-hours)
        Batt_Hrs_to_Full = (BATT_POWER_MAX * (100 - Batt_Charge)/100) / abs(Batt_Power/3600)          
        Batt_Hours_Remaining_str = 'Est hours to 100%:   ' + str('%.1f' % Batt_Hrs_to_Full)        
    
    
    #print('Batt_Power_Running_Avg: ', Batt_Power_Running_Avg, ' Batt_Power_Remaining:', Batt_Power_Remaining, ' Batt_Hours_Remaining: ' + Batt_Hours_Remaining_str)


    #TODO heursitic to determine if the battery is charging;  Delete this section when real data is available
    if int(time.time()) % 10 == 0:
        Batt_Charge = 100
    Batt_Power = Batt_Power_Last
    if int(time.time()) % 5 == 0:
        if DC_volts < 13.6:
            #Discharging
            Batt_Power = random.randint(1, 1000)
        else:
            #Charging
            Batt_Power = random.randint(-1000, -1)
        Batt_Power_Last = Batt_Power
    ### end of hueristic

    return(Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str)

def InvertCalcs():
    #Inverter Power Calculations
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

    return(InvertorMaxPower, DC_volts, Invert_AC_voltage, Invert_AC_power, Invert_status_num)

def ATS_Calcs():
    try:
        ATS_Power = mqttclient.AliasData["_var23ATS_AC_voltage"] * mqttclient.AliasData["_var22ATS_AC_current"] 
        ATS_Line = mqttclient.AliasData["_var21ATS_Line"]
    except:
        ATS_Power = 0
        ATS_Line = 0

    if ATS_Line == 1:
        ShorePower = ATS_Power
        GenPower = 0
    else:
        ShorePower = 0
        GenPower = ATS_Power  

    return(ShorePower, GenPower)  

def SolcarCalcs():
    try:
        SolarPower = (mqttclient.AliasData["_var26Solar_voltage"] * mqttclient.AliasData["_var27Solar_current"])                                #Battery power"
    except:
        SolarPower = 0

    return(SolarPower)

def AlternatorCalcs(Batt_Power, Invert_status_num, InvertorMaxPower, SolarPower):
    #Note: Alternator power not measured so using estimate  
    if Batt_Power < 0 and Invert_status_num == 1:                  # DC Pass and Battery charging if negative power
        #Assume that the battery is charging fr(Batt_Power, Batt_Voltage, Batt_Hours_Remaining_str, Batt_Hrs_to_Full )om the Alternator and DC_Load is unchanged
        #AC_Load = mqttclient.AliasData["_var24RV_Loads_AC"]
        try:
            DC_Load = mqttclient.AliasData["_var25RV_Loads_DC"]
            if DC_Load == '':
                DC_Load = 54
        except:
            DC_Load = 54
        AlternatorPower = -Batt_Power + DC_Load + InvertorMaxPower - SolarPower
    else:
        AlternatorPower = 0

    return(AlternatorPower)

def LoadCalcs(Invert_status_num, InvertorMaxPower, ShorePower, GenPower, Invert_AC_power, Batt_Power, SolarPower, AlternatorPower):
#Calc AC and DC Loads since not measured
    if Invert_status_num == 1:          #DC Passthrough
        #Only power source on AC side is the inverter; therefor, AC_Load = inverter power
        AC_Load = Invert_AC_power
        DC_Load = Batt_Power + SolarPower + AlternatorPower - InvertorMaxPower
    elif Invert_status_num == 2:        #AC Passthrough
        AC_Load = ShorePower + GenPower - Invert_AC_power
        DC_Load = InvertorMaxPower + Batt_Power + SolarPower + AlternatorPower
    else:
        #Shouldn't get here
        AC_Load = -1     
        DC_Load = -1
    
    #publish AC_Load and DC Load to mqtt TODO   
    #  
    return(AC_Load, DC_Load)



def HouseKeeping():
    #House Keeping Messages
    RedLamp = mqttclient.AliasData["_var07Red"]
    if RedLamp == '00':
        RedMsg = ''
    else:
        RedMsg = RedLamp + ' Red Lamp Fault'
    YellowLamp =str(mqttclient.AliasData["_var08Yellow"]) + " Yellow Lamp" 
    YellowMsg = ''
    #TODO replace time with wall clock time
    Time_Str =str('%.1f' % ((float(mqttclient.AliasData["_var01Timestamp"])-timebase)/60)) + " Time"
    return(RedMsg, YellowMsg, Time_Str)

