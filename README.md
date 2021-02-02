# pvload
pvload is a little python script that manages pv-based charging of an electric car using a SENEC battery and GoECharger

Right now this script will check for PV overhead on the (local) SENEC lala.cgi and will then set the GoeCharger accordingly.

You will have to use a 1-Phase cable for this to work correctly, maybe I will add 3-Phase later.
You just need to replace the IPs of the SENEC and goecharger in the script.
