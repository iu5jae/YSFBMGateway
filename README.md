# YSFBMGateway
Experimental gateway for using YSF Direct on BM servers.

Antonio IU5JAE's YSFBMGateway works in conjunction with G4KLX's MMDVMHost software. It allows C4FM hotspots and repeaters to connect directly to the Brandmeister Master Server that has the YSF Direct protocol active, logging in with the Callsign and Password set in BM self-care.

Gateway features:

- sending of the default TG at login, also used for the back to home function after a certain amount of time, if enabled;
- sending of TG change (up to 5 digits) via DTMF tones in Wires-X mode;
- sending the change of any TG through the use of DG-IDs, useful for TGs greater than 5 digits;
- possibility to set the prefix for displaying the DG-ID in use (e.g. nn/Callsign);
- TG block management, useful for the sysop that doesn't want to allow access to a TG.

The gateway reads a file called dgid.db which contains the management of the blocked TGs and the DG-IDs associated with the TGs, and relative description. This is the syntax:

DG-ID(-1 to block):TG:DESCR(up to 13chars)

If present, the description is displayed on the radio, otherwise only the TG.

-1:222:IT NATIONAL
22:22292:ITALY MULTIP
41:2241:
55:222555:CLS GRF

For this example: impossible to send TG 222, TG 22292 and 2241 can also be called via DG-ID. TG 222555 can only be sent via DG-ID (greater than 5 digits).
Compiling a dgid.db file can be useful for creating a usage standard.

The ysfbmgateway.ini file contains the gateway configuration such as ports for connection with MMDVMHost, credentials for authentication to the BM master.

YSFBMGateway requires python 3.7 or higher and some libraries installable via PIP.
