#!/usr/bin/python3
# for this to work you need: 
# - https://github.com/cathiele/goecharger
# - https://github.com/mchwalisz/pysenec
from goecharger import GoeCharger
import aiohttp
import pysenec
import asyncio
import logging
from pprint import pprint

charger = GoeCharger('192.168.178.65')
senechost = '192.168.178.69'
cardtounlock = 0
logging.basicConfig(filename='pvload.log',format='%(asctime)s %(message)s', level=logging.DEBUG)
verbose = True

goestatus = charger.requestStatus()
if verbose:
    print("Actual Power: "+str(goestatus['charger_max_current']))
    print("PV Charging Power: "+str(goestatus['charger_pv_max_current']))
    print("Allow Charging: "+goestatus['allow_charging'])
    print("Car Status: "+goestatus['car_status'])
    print("Unlocked by Card: "+str(goestatus['unlocked_by_card']))
    print("Cable: "+str(goestatus['cable_max_current']))
    print("Charging Power: "+str((goestatus['p_all'] * 10)))
    print("\n\n")

#check connected RFID
if goestatus['unlocked_by_card'] != cardtounlock:
    if verbose:
        print("Charger not unlocked by PV RFID, exiting")
#    if goestatus['allow_charging'] == 'off':
#        if verbose:
#            print("Charger seems to be set to PV Loading, although PV RFID is not connected. Will set to default values")
#        logging.info("Charger seems to be set to PV Loading, although PV RFID is not connected. Will set to default values")
#        charger.setAllowCharging(0)
    exit(0)
else:
    # check for connected cable: (1 phase/ 16 A)
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
    overload = senec.solar_generated_power - senec.house_power - ( goestatus['p_all'] * 10 )
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
                charger.setPVMaxCurrent(16)
                logging.info("Setting Power to 16")
                exit(0)
            else:
                if verbose:
                    print("Correct power value set, exiting")
                exit(0)
        if verbose:
            print("Overload >1400 <3600 setting power to "+str(overloadamp))
        if maxcurrent != overloadamp:
            logging.info("Setting Power to "+str(overloadamp))
            charger.setPVMaxCurrent(overloadamp)
        else:
            if verbose:
                print("Correct power value set, exiting")
                exit(0)
    else:
        # disable charging
        if goestatus['allow_charging'] == 'off':
            exit(0)
        charger.setAllowCharging(False)
        logging.info("Overload too small, disabling charging")
        if verbose:
            print("PV Overload too small, disabling charging")
