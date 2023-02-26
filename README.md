# YSFBMGateway
Experimental gateway for using YSF Direct on BM servers.

Antonio IU5JAE's YSFBMGateway works in conjunction with G4KLX's MMDVMHost software. It allows C4FM hotspots and repeaters to connect directly to the Brandmeister Master Server that has the YSF Direct protocol active, logging in with the Callsign and Password set in BM self-care.

Gateway features:

- sending of the default TG at login, also used for the back to home function after a certain amount of time, if enabled;
- sending of TG change (up to 5 digits) via DTMF tones in Wires-X mode;
- sending the change of any TG through the use of DG-IDs, useful for TGs greater than 5 digits;
- sending the change of any YSF Rooms through the use of DG-IDs;
- possibility to set the prefix for displaying the DG-ID in use (e.g. nn/Callsign);
- TG block management, useful for the sysop that doesn't want to allow access to a TG.

The gateway reads a file called dgid.db which contains the management of the blocked TGs and the DG-IDs associated with the TGs/YSF Rooms, and relative description. This is the syntax:

DG-ID(-1 to block the TG):TG:DESCR(up to 13chars)

If present, the description is displayed on the radio, otherwise only the TG (search in W-X mode).

-1:222:IT NATIONAL<br>
22:22292:ITALY MULTIP<br>
41:2241:<br>
55:222555:CLS GRF<br>

For this example: impossible to send TG 222, TG 22292 and 2241 can also be called via DG-ID. TG 222555 can only be sent via DG-ID (greater than 5 digits).
Compiling a dgid.db file can be useful for creating a usage standard.
Again in Wires-X mode, for example, TG-2241/41 on the Yaesu radio display represents the TG in use (2241) and (it is in dgid.db) the associated DG-ID (41).

To manage the connection to a room of the YSF network, use the following syntax:<br>
27:YSF#27003:ROOM-ITALY:ysfroomitaly.iw2gob.it:42000<br>

In particular:<br>
DG-ID:YSF#nnnnn:FREE DESCRIPTION:DNS/IP:PORT<br>
The room id, address and port are easily deduced from the YSF world registry. The description is displayed on the radio.

A latest software update enables the suffix where indicated in addition to the callsign. This feature is useful to connect a specific flow on reflectors like pYSF3 and make it FIXED. After having specified the room, it is necessary to enter # and the numeric identifier (from 01 to 99) which will complete the callsign (CALL-nn) used in the hs/rpt connection. If omitted, the link callsign will have no numeric suffixes.<br>
27:YSF#27003#27:ROOM-ITALY:ysfroomitaly.iw2gob.it:42000

info:<br>
if the dgid.db file is correctly compiled, you will see the confirmation in the gateway log, for example:<br>
Loaded 53 YSF Direct and 3 YSF Network DGID<br>

The ysfbmgateway.ini file contains the gateway configuration such as ports for connection with MMDVMHost, credentials for authentication to the BM master (same Callsign for auth and hs/rpt).

YSFBMGateway requires python 3.7 or higher. For a lean C4FM only installation it is recommended to use an empty raspbian distribution, compile MMDVMHost and add the gateway with the relative configurations. Nothing else is needed. Otherwise it can be added to the Pi-Star distribution with some simple configurations:<br>
https://www.grupporadiofirenze.net/2022/12/08/ysfbmgateway-connessione-a-bm-in-ysf-direct-protocol/
