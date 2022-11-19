#   part of ysf_bridge
#
#   based on 
#
#   Copyright (C) 2016,2017,2018,2019,2020 by Jonathan Naylor G4KLX
#
import ysfpayload
import crc


DX_REQ   = [0x5D, 0x71, 0x5F]
CONN_REQ  = [0x5D, 0x23, 0x5F]
DISC_REQ  = [0x5D, 0x2A, 0x5F]
ALL_REQ   = [0x5D, 0x66, 0x5F]
CAT_REQ   = [0x5D, 0x67, 0x5F]

DX_RESP   = [0x5D, 0x51, 0x5F, 0x26]
CONN_RESP = [0x5D, 0x41, 0x5F, 0x26]
DISC_RESP = [0x5D, 0x41, 0x5F, 0x26]
ALL_RESP  = [0x5D, 0x46, 0x5F, 0x26]

DEFAULT_FICH = [0x20, 0x00, 0x01, 0x00]

NET_HEADER = 'YSFD                    ALL      '

def process(data, source, DT, FI, FN, FT):
  wx_command = []
  if (DT != 1):
    print('ret 1')
    return 0
     
  if (FI != 1):
    print('ret 2')
    return 0
  
  if (FN == 0):
    print('ret 3')
    return 0
    
  if (FN == 1):
    valid = ysfpayload.readDataFRModeData2(data, wx_command)
    if (not valid):
      print('ret 4')
      return 0
  else:
    valid = ysfpayload.readDataFRModeData1(data, wx_command) 
    if (not valid):
      return 0
    valid = ysfpayload.readDataFRModeData2(data, wx_command)      
    if (not valid):
      print('ret 5')
      return 0
  print(wx_command)    
  if (FN == FT):
    valid = False
    cmd_len = (FN - 1) * 40 + 20
    i = cmd_len - 1
    while (wx_command[i] != 3):
     i = i-1
     
    if (wx_command[i] == 3):
      crc_a = crc.addCRC(wx_command, i+1)
      if (crc_a == wx_command[i+1]):
        valid = True
           
    if (not valid):
      print('ret 6')
      return 0
  
  
    if (wx_command[1:4] == DX_REQ):
      return 1
    
    if (wx_command[1:4] == ALL_REQ):
      return 2  
  
    if (wx_command[1:4] == CONN_REQ):
      return 3  
  
    if (wx_command[1:4] == DISC_REQ):
      return 4  
  
    if (wx_command[1:4] == CAT_REQ):
      return 5  
  
  return 0



if __name__ == '__main__':
  b0 = b'YSFDIU5JAE    IU5JAE    ALL       \x00\xd4q\xc9cM\x11[N%\xc0".\xd2J\x8b\xd0C%q9`\x11X\xa5\xb3}R9%H\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84'
  b1 = b'YSFDIU5JAE    IU5JAE    ALL       \x02\xd4q\xc9cM!\xabN\xcc\xbf\xe1\xbe\xd2=u\x91\xb3&u\xa3,\xd1Z;\x98\xf7\x929\xd0\x00\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84'
  b2 = b'YSFDIU5JAE    IU5JAE    ALL       \x04\xd4q\xc9cM!\xbb6]\x1c\xe1\xad\xddH\xfd\x91\x91\xb7\xe5],\xe1\xa8_n\xf7Q\x9a\x84W\xdf#c\xc9\xa0`\x7f\x1c\x83\xc3\xe3c\xc3\x16u?\x1c\x80\xdf\xa8Z\xbaK\xe9\x10\x14\xbe\x8aV\xda\xbaHOJ\x14\xbeuC\xf7\x7f\xb8"\x90\xf2\xc6|\xf2\x9d\xbf\xb8\x1f}c\x06=\xc3\x10\x84%\x1eM\xe8d=\xd2\xba\xb0e\x1e[Q-\x13s\xff\xf4\xfb\xd5\x89\x0e\x84\xd3s\xe1\x0e\xa8\xd5\x89%\x9b'
  b3 = b"YSFDIU5JAE    IU5JAE    ALL       \x07\xd4q\xc9cM\xd2\xfbN\xf9?c\xce\xd1z\x10\x9cs'\x07\x10\xeaQX$\xf8\xbe\x929\x88\xb8\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84"


  dt = []
  print(ysfpayload.readDataFRModeData2(b2[35:], dt))
  print(dt)
  print(process(b2[35:], 'iu5jae', 1, 1, 1, 1))

 
  
