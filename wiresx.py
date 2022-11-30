#   part of ysfbmgateway
#
#   based on 
#
#   Copyright (C) 2016,2017,2018,2019,2020 by Jonathan Naylor G4KLX
#

import ysfpayload
import crc
import ysffich
import time


DX_REQ    = [0x5D, 0x71, 0x5F]
CONN_REQ  = [0x5D, 0x23, 0x5F]
DISC_REQ  = [0x5D, 0x2A, 0x5F]
ALL_REQ   = [0x5D, 0x66, 0x5F]
CAT_REQ   = [0x5D, 0x67, 0x5F]

DX_RESP   = [0x5D, 0x51, 0x5F, 0x26]
CONN_RESP = [0x5D, 0x41, 0x5F, 0x26]
DISC_RESP = [0x5D, 0x41, 0x5F, 0x26]
ALL_RESP  = [0x5D, 0x46, 0x5F, 0x26]

DEFAULT_FICH = [0x20, 0x00, 0x01, 0x00, 0x00, 0x00]

NET_HEADER = 'YSFD                    ALL       '

seqn = 0
m_id = 0
m_name = '' 
m_txfrequency = 0 
m_rxfrequency = 0
m_callsign = ''
m_node = ''
m_csd1 = []
m_csd2 = []
m_csd3 = []
m_csd4 = []
wx_command = []

def process(data, source, DT, FI, FN, FT):
  global wx_command
 
  if (DT != 1):
    return 0
     
  if (FI != 1):
    return 0
  
  if (FN == 0):
    return 0
    
  if (FN == 1):
    wx_command = []
    valid = ysfpayload.readDataFRModeData2(data, wx_command)
    if (not valid):
      return 0
  else:
    valid = ysfpayload.readDataFRModeData1(data, wx_command) 
    if (not valid):
      return 0
    valid = ysfpayload.readDataFRModeData2(data, wx_command)      
    if (not valid):
      return 0
  # print(wx_command)    
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


def ReplyToWiresxDxReqPacket(conn, tg, q):
  global seqn
  ok = True
  data = bytearray(129)
 
  for i in range(128):
    data[i] = 0x20
  
  data[0] = seqn
  seqn = (seqn + 1) & 0xFF
  data[1:5] = DX_RESP 

  data[5:10] = str(m_id).encode()
  data[10:20] = m_node.ljust(10).encode()
  data[20:34] = str(m_name).ljust(14).encode()
  
  if not conn:
    data[34:35] = b'1'
    data[35:36] = b'2'
  else:   # connesso
    data[34:35] = b'1'
    data[35:36] = b'5'
    data[36:41] = str(tg).zfill(5).encode()
    data[41:57] = ('BM-' + str(tg)).ljust(16).encode()
    data[57:60] = '099'.encode()
   # data[60:70] = 'DSC10 '.ljust(10).encode()
    data[70:84] = 'BM YSF DIRECT'.ljust(14).encode()
  
  # frequency
  if ( m_txfrequency >=  m_rxfrequency):
    offset = m_txfrequency -  m_rxfrequency
    sign = '-'
  else:
    offset = m_rxfrequency -  m_txfrequency
    sign = '+'

  freqHz = int(m_txfrequency % 1000000)
  freqKHz = int((freqHz + 500) / 1000)
  
 # print(freqHz)
 # print(freqKHz)
 # print(offset % 1000000)
 # print(len(data))
  
  freqs = str(int(m_txfrequency / 1000000)).zfill(5) + '.' + str(freqKHz).zfill(3) + '000' + sign + str(int(offset / 1000000)).zfill(3) + '.' + str(int(offset % 1000000)).zfill(6)

  data[84:107] = freqs.encode()

  data[127] = 0x03
  #print(data)
  #print(len(data))
  data[128] = crc.addCRC(data, 128)
  
  #print(freqs)
  
  #print(data)

  #print(len(data))
  
  EncodeAndSendWiresxPacket(data, q)
  #print(data)
  #print(len(data))
 
  return ok  


def ReplyToWiresxConnReqPacket(conn, tg, q):
  global seqn
  ok = True
  data = bytearray(91)
 
  for i in range(90):
    data[i] = 0x20
  
  data[0] = seqn
  seqn = (seqn + 1) & 0xFF
  data[1:5] = CONN_RESP 
  data[5:10] = str(m_id).encode()
  data[10:20] = m_node.ljust(10).encode()
  data[20:34] = str(m_name).ljust(14).encode()
  
  data[34:35] = b'1'
  data[35:36] = b'5'

  data[36:41] = str(tg).zfill(5).encode()
  data[41:57] = ('TG' + str(tg)).ljust(16).encode()
  data[57:60] = '099'.encode()
  # data[60:70] = 'DSC10 '.ljust(10).encode()
  data[70:84] = 'BM YSF DIRECT'.ljust(14).encode()
  data[84:85] = b'0'
  data[85:86] = b'0'
  data[86:87] = b'0'
  data[87:88] = b'0'
  data[88:89] = b'0'

  data[89] = 0x03
  #print(data)
  #print(len(data))
  data[90] = crc.addCRC(data, 90)
  
  #print(data)
  
  EncodeAndSendWiresxPacket(data, q)
  
  return ok

def EncodeAndSendWiresxPacket(data, q):
 
  seqNo = 0
  
  length = len(data) 
  bt = 0
  
  if (length > 260):
    bt = 1
    bt += int((length - 260) / 259)
    length += bt
    
  if (length > 20):
    blocks = int((length - 20) / 40)
    if ((length % 40) > 0):
      blocks += 1
      length = blocks * 40 + 20
    else:
      length = 20

  if (length > len(data)):
    for i in range(length - len(data)):
      data.append(0x20)
     
  ft = WiresxCalcFt(length, 0)
  seqno = 0
  #print('BT = ' + str(bt) + ' - FT = ' + str(ft))
  
  # header frame
  buffer = bytearray(155)
  buffer[0:34] = NET_HEADER.encode()
  buffer[4:14] = m_callsign.encode()
  buffer[14:24] = m_node.encode()
  # sync
  buffer[34] = seqno
  seqno = seqno + 2
  buffer[35] = 0xD4
  buffer[36] = 0x71
  buffer[37] = 0xC9
  buffer[38] = 0x63
  buffer[39] = 0x4D
  ysffich.m_fich = DEFAULT_FICH   # load default FICH
  #print(ysffich.m_fich)
  ysffich.setFI(0)
  ysffich.setBT(bt)
  ysffich.setFT(ft)
  ysffich.encode(buffer)
  data_tmp = [0] * 120
  ysfpayload.writeHeader(data_tmp, m_csd1, m_csd2)
  buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
  q.put(buffer)
  #print(buffer) # header channel
  
  ysffich.setFI(1)    # CC
  offset = 0
  for bn in range(bt+1):
    for fn in range(ft+1):
      ysffich.setFT(ft)
      ysffich.setFN(fn)
      ysffich.setBT(bt) 
      ysffich.setBN(bn)
      ysffich.encode(buffer)
      buffer[34] = seqno
      seqno = seqno + 2
      if (fn == 0):
         data_tmp = [0] * 120
         ysfpayload.writeHeader(data_tmp, m_csd1, m_csd2)
         buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
      else:
        if (fn == 1):
          if (bn == 0):
            data_tmp = [0] * 120
            ysfpayload.writeHeader(data_tmp, m_csd3, data[offset:offset+20])
            buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
            offset = offset + 20
          else:
            temp = bytearray(20)
            temp[1:20] = data[offset:offset+19]
            data_tmp = [0] * 120
            ysfpayload.writeDataFRModeData2(temp, data_tmp)
            buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
        else:
         data_tmp = [0] * 120
         ysfpayload.writeHeader(data_tmp, data[offset:offset+20], data[offset+20:offset+40])
         offset = offset + 40
         buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]            
     
      q.put(buffer)         
      #print(buffer)
      time.sleep(0.07)
  
  # end frame
  ysffich.setFI(2)
  ysffich.setBT(bt)
  ysffich.setFT(ft)
  ysffich.encode(buffer)
  data_tmp = [0] * 120
  ysfpayload.writeHeader(data_tmp, m_csd1, m_csd2)
  buffer[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data_tmp[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
  buffer[34]  = seqno | 0x1
  q.put(buffer)
  #print(buffer)
  
  
  return


def ReplyToWiresxAllReqPacket(q):
  global seqn
  ok = True
  data = bytearray(1200)
  
  data[0] = seqn
  seqn = (seqn + 1) & 0xFF
  data[1:5] = ALL_RESP 
  data[5:6] = b'2'
  data[6:7] = b'1'
  
  data[7:12] = str(m_id).encode()
  data[12:22] = m_node.ljust(10).encode()
  
  total = 20
  n = 20
  
  data[22:28] = (str(n).zfill(3) + str(total).zfill(3)).encode()
  data[28] = 0x0D
  offset = 29
  for i in range(n):
    data[offset:offset+1] = b'5'
    data[offset+1:offset+6] = str(i+1).zfill(5).encode()
    data[offset+6:offset+22] = ('BM - ' + str(i+1).zfill(5)).encode()
    data[offset+22:offset+25] = b'099'
    data[offset+25:offset+35] = b'          '
    data[offset+35:offset+49] = b'DESCRIPTION   '
    data[offset+49] = 0x0D
    offset += 50
    # print(str(i) + ' -> ' + str(offset))
    
  data[offset] = 0x03
  data[offset+1] = crc.addCRC(data, offset+1) 
  
  data_1 = bytearray(1031)
  data_1 = data[0:1031]  
  EncodeAndSendWiresxPacket(data_1, q)
  
    
  return ok


def setInfo(name, tx_freq, rx_freq, callsign, node):
  global m_id, m_name, m_txfrequency, m_rxfrequency, m_callsign, m_node, m_csd1, m_csd2, m_csd3
  m_txfrequency = tx_freq
  m_rxfrequency = rx_freq
   
  if (len(name) > 14): 
    m_name = name[0:14]
  else:
    m_name = name.ljust(14)
  
  m_callsign = callsign.ljust(10)
  m_node = node.ljust(10)
     
     
  hash = 0 # 32 bit
  for i in range(len(name)):
    hash = (hash + ord(name[i])) & 0xFFFFFFFF
    hash = (hash + (hash << 10)) & 0xFFFFFFFF
    hash = (hash ^ (hash >> 6))  & 0xFFFFFFFF


  hash = (hash + (hash << 3)) & 0xFFFFFFFF
  hash = (hash ^ (hash >> 11)) & 0xFFFFFFFF
  hash = (hash + (hash << 15)) & 0xFFFFFFFF

  m_id = (hash % 100000)

 
  m_csd2 = 20*[' ']
  m_csd3 = 20*[' ']

  m_csd1 = ('**********' + m_node.ljust(10)).encode()
  m_csd2 = (m_callsign.ljust(10) + '          ').encode()
  m_csd3 = (str(m_id).zfill(5) + '          ' +  str(m_id).zfill(5)).encode() 

    

def WiresxCalcFt(length, offset):
  length -= offset
  if (length > 220):
    return 7
  if (length > 180):
    return 6
  if (length > 140):
    return 5
  if (length > 100):
    return 4
  if (length > 60):
    return 3
  if (length > 20):
    return 2
  return 1





if __name__ == '__main__':
  b0 = b'YSFDIU5JAE    IU5JAE    ALL       \x00\xd4q\xc9cM\x11[N%\xc0".\xd2J\x8b\xd0C%q9`\x11X\xa5\xb3}R9%H\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84'
  b1 = b'YSFDIU5JAE    IU5JAE    ALL       \x02\xd4q\xc9cM!\xabN\xcc\xbf\xe1\xbe\xd2=u\x91\xb3&u\xa3,\xd1Z;\x98\xf7\x929\xd0\x00\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84'
  b2 = b'YSFDIU5JAE    IU5JAE    ALL       \x04\xd4q\xc9cM!\xbb6]\x1c\xe1\xad\xddH\xfd\x91\x91\xb7\xe5],\xe1\xa8_n\xf7Q\x9a\x84W\xdf#c\xc9\xa0`\x7f\x1c\x83\xc3\xe3c\xc3\x16u?\x1c\x80\xdf\xa8Z\xbaK\xe9\x10\x14\xbe\x8aV\xda\xbaHOJ\x14\xbeuC\xf7\x7f\xb8"\x90\xf2\xc6|\xf2\x9d\xbf\xb8\x1f}c\x06=\xc3\x10\x84%\x1eM\xe8d=\xd2\xba\xb0e\x1e[Q-\x13s\xff\xf4\xfb\xd5\x89\x0e\x84\xd3s\xe1\x0e\xa8\xd5\x89%\x9b'
  # b3 = b"YSFDIU5JAE    IU5JAE    ALL       \x07\xd4q\xc9cM\xd2\xfbN\xf9?c\xce\xd1z\x10\x9cs'\x07\x10\xeaQX$\xf8\xbe\x929\x88\xb8\xf3\xecS\xd8\x1dS\x19\xfd\xb0\xf4\xc3S\xd8\x1f\xa0\x1f=\xb0\xb5\xa5\xf70:\x98&\xe1q\xb8,\xba\xb0:\x9d9\xe4\xb1\xad\xa2,\xfc9\xb9\x11\x9c\x88\xad\xa4\xc8\x1f\xb9\xb9\x1b\xf4f\x1a\xa3\x08>UC9\x9f\x8f\x1a\xa3\x0b\x19\x15\x039\x99\x11\x02\x9b\xc6=W\xf2\xa2\xe1\x83\xd3[\xc6;[\x15\xa2\xe1\x84"

  b3 = b'YSFDIU5JAE-41 IU5JAE    ALL       \x04\xd4q\xc9cM!\xbb<xc\xe1\xad\xd3\x01\x93\x91\x91\xb2\x96a,\xe1\xa0\xf4\x07\xf7Q\xa3\xa8\xa0\xdf#c\xc9\xa0`\x7f\x1c\x83\xf7\xf5\xb3\xc3\x16m&\xbc\x82\xdf\xa8Z\xbaK\xe9\x10\x14\xbe\x84j\xfc\nHIB\x0f\xbeuC\xf7\x7f\xb8"\x90\xf2\xc6}\xfe\x99\x90\xf8\x10\x7fk;=\xc3\x10\x84%\x1eM\xe8d}\xda\xb6tS\x9e[Z\xa5\x13s\xff\xf4\xfb\xd5\x89\x0e\x84\x04s\xe1?\x94\x80\xc9)\xb8'

  setInfo('Borgo a Mozzano', 433450000, 433450000, 'IU5JAE', 'IU5JAE')
  dt = []
  print(ysfpayload.readDataFRModeData2(b2[35:], dt))
  print(dt)
  print(process(b2[35:], 'iu5jae', 1, 1, 1, 1))
  ReplyToWiresxDxReqPacket(True, 'IU5JAE', 22251)
 
  
  
  # print(m_id)
  # print(m_name)
