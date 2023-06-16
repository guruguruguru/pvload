#!/usr/bin/python3
# for this to work you need: 
# - https://github.com/cathiele/goecharger
# - https://github.com/mchwalisz/pysenec
import sys
from goecharger import GoeCharger
import aiohttp
import pysenec
import asyncio
import logging
from pprint import pprint

logfile = '/var/www/html/pvload/pvload.log'

charger = GoeCharger('192.168.178.65')
senechost = '192.168.178.69'
logging.basicConfig(filename=(logfile),format='%(asctime)s %(message)s', level=logging.INFO)
if len(sys.argv) > 1:
    if str(sys.argv[1]) == "-v":
        verbose = True
    else:
        verbose = False
else:
    verbose = False

goestatus = charger.requestStatus()
if verbose:
    print("Actual Power: "+str(goestatus['charger_max_current']))
    print("Allow Charging: "+goestatus['allow_charging'])
    print("Car Status: "+goestatus['car_status'])
    print("Unlocked by Card: "+str(goestatus['unlocked_by_card']))
    print("Cable: "+str(goestatus['cable_max_current']))
    print("Load since connected: "+str(goestatus['current_session_charged_energy']))

    print("\n\n")

# check if car is connected
if goestatus['car_status'] == 'Charger ready, no vehicle':
    if verbose:
        print("No car connected, exiting")
    exit(0)

#check connected cable
if goestatus['cable_max_current'] != 20:
    # if 32A cable is connected set loading to allowed and charge with max power
    if goestatus['cable_max_current'] == 32:
        if int(goestatus['charger_max_current']) != 16:
            charger.setTmpMaxCurrent(16)
            logging.info("Setting Power to Max")
    if verbose:
        print("Wrong Cable connected, exiting")
    exit(0)
else:
    # start senec stuff
    async def run(host, verbose=False):
        global senec
        async with aiohttp.ClientSession() as session:
            senec = pysenec.Senec(host, session)
            await senec.update()
            '''
            print(f"System state: {senec.system_state}")
            print(f"House energy use: {senec.house_power / 1000 :.3f} kW")
            print(f"Solar Panel generate: {senec.solar_generated_power / 1000 :.3f} kW")
            print(
                f"Battery: {senec.battery_charge_percent :.1f} % charge: {senec.battery_charge_power / 1000 :.3f} kW, discharge {senec.battery_discharge_power / 1000 :.3f} kW"
            )
            print(
                f"Grid: exported {senec.grid_exported_power / 1000 :.3f} kW, imported {senec.grid_imported_power / 1000 :.3f} kW"
            )
            if verbose:
                pprint(senec.raw_status)
            '''

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(senechost, verbose=False))
    maxcurrent = int(goestatus['charger_max_current'])
    overload = senec.solar_generated_power - senec.house_power + ( goestatus['p_all'] * 1000 )
    charge = round(senec.battery_charge_percent, 0)

    if verbose:
        print(f"Solar Panel generate: {senec.solar_generated_power} W")
        print(f"House energy use: {senec.house_power} W")
        print(f"Charging Power: "+str((goestatus['p_all'] * 1000)))
        print(f"Battery Charge Percent: {charge}")
        if charge > 50:
            print(f"load from battery ok")
        else:
            print(f"battery too low")

    ##################################
    # overwriting overload for testing
    #overload = 1401
    ##################################
    overloadamp = int(overload/230)

    if verbose:
        print(f"Overload: {overload /1000 :.3f} kW")

    if overload > 1400:
        if goestatus['allow_charging'] == 'off':
            charger.setAllowCharging(True)
            logging.info("Setting Charging to True")
        if overload > 3600:
            if verbose:
                print("Overload > 3600, setting power to 16")
            if maxcurrent != 16:
                charger.setTmpMaxCurrent(16)
                logging.info("Setting Power to 16")
                exit(0)
            else:
                if verbose:
                    print("Correct power value set, exiting")
                exit(0)
        if verbose:
            print("Overload >1400 <3600 setting power to "+str(overloadamp)," Load since connected:"+str(goestatus['current_session_charged_energy']))
        if maxcurrent != overloadamp:
            logging.info("Setting Power to %s - Load since connected %s", str(overloadamp), str(goestatus['current_session_charged_energy']))
            charger.setTmpMaxCurrent(overloadamp)
        else:
            if verbose:
                print("Correct power value set, exiting")
                exit(0)
    else:
        #check for battery state
        if ((charge > 50) and (overload > 500)):
            if maxcurrent == 6:
                if verbose:
                    print("Correct power value set, exiting")
                exit (0)
            charger.setTmpMaxCurrent(6)
            logging.info("Setting Power to 6 as battery has more than 50% and overload is still over 500 - Load since connected: "+str(goestatus['current_session_charged_energy']))
            #logging.info("Setting Power to 6 as battery has more than 50% and overload is still > 500")
            exit(0)
        # disable charging
        if goestatus['allow_charging'] == 'off':
            exit(0)
        charger.setAllowCharging(False)
        logging.info("Overload too small, disabling charging - Load since connected:"+str(goestatus['current_session_charged_energy']))
        if verbose:
            print("PV Overload too small, disabling charging")

