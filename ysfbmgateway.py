#!/usr/bin/python3

#    ysfbmgateway
#
#    Created by Antonio Matraia (IU5JAE) on 15/11/2022.
#    Copyright 2020 Antonio Matraia (IU5JAE). All rights reserved.

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import time
import logging
import socket
import sys
import queue
import configparser
from logging.handlers import RotatingFileHandler
import signal
import ysffich
import ysfpayload
import hashlib
import wiresx

ver = '230225'

a_connesso = False
b_connesso = True
c_connesso = False

lock = False
t_lock = 0.0

a_tf = 0.0 # tempo trascorso da ultimo pacchetto
b_tf = 0.0
c_tf = 0.0

# A - YSF Direct (BM server)
# B - MMDVMHost
# C - YSF Network (Reflector)

q_ab = queue.Queue() # coda pacchetti A -> B 
q_ba = queue.Queue() # coda pacchetti B -> A 
q_bc = queue.Queue() # coda pacchetti B -> C 

mode = 1 # mode 1 > YSF Direct; 2 > YSF Net

lock_a = threading.Lock()
lock_b = threading.Lock()
lock_c = threading.Lock()
lock_a_time = threading.Lock()
lock_b_time = threading.Lock()
lock_c_time = threading.Lock()
lock_conn_a = threading.Lock()
lock_conn_b = threading.Lock()
lock_conn_c = threading.Lock()
lock_dir = threading.Lock()
a_b_dir = False # direzione attiva A --> B
b_a_dir = False # direzione attiva B --> A
b_c_dir = False # direzione attiva B --> C
c_b_dir = False # direzione attiva C --> B

bufferSize = 2048
wx_cmd = 0 
wx_t = 0

## config
config = configparser.ConfigParser()

if (len(sys.argv) != 2):
  print('Invalid Number of Arguments')
  logging.error('Invalid Number of Arguments')
  print('use: ysfbmgateway <configuration file>')
  logging.error('use: ysfbmgateway <configuration file>')
  sys.exit()
  
config_file = sys.argv[1].strip()
config.read(config_file)
log_file = config['General']['log_file'] 

dgid_file = config['General']['dgid_config'] 

try:
  log_maxBytes = int(config['General']['log_maxBytes'])
except:
  log_maxBytes = 1000000
try:    
  log_backupCount = int(config['General']['log_backupCount'])
except:
  log_backupCount = 10  
try:
   dgid_prefix = int(config['General']['dgid_prefix_enable'])
except:
   dgid_prefix = 0

try:
   time_to_home = float(config['BM']['time_to_home'])
except:
   time_to_home = 900.0

if (time_to_home < 60.0):
 time_to_home = 60.0

try:
   back_to_home = int(config['BM']['back_to_home'])
except:
   back_to_home = 0

try:
  RX_freq = int(config['Info']['RXFrequency'])
except:
  RX_freq = 435000000
  
try:
  TX_freq = int(config['Info']['TXFrequency'])
except:
  TX_freq = 435000000  
  
try:
  Pow = int(config['Info']['Power'])
except:
  Pow = 1
  
try:
  Lat = float(config['Info']['Latitude'])
except:
  Lat = 0.0  

try:
  Lon = float(config['Info']['Longitude'])
except:
  Lon = 0.0  

try:
  Height = int(config['Info']['Height'])
except:
  Height = 0

Name = config['Info']['Name']

Description =config['Info']['Description']


ack_period = 3.0
ack_tout = 30.0  
  
ack_time_a = ack_tout 
ack_time_b = ack_tout 
ack_time_c = ack_tout 

t_home_act = 0.0

# "BM" side
UDP_IP_A = config['BM']['address']
try:
  UDP_PORT_A = int(config['BM']['port'])
except:
  UDP_PORT_A = 42000
    
CALL_A = config['BM']['Callsign'] 

try:
  PASSWORD_A = bytes(config['BM']['password'].strip(), 'utf-8')
except:
  PASSWORD_A = bytes('', 'utf-8')
  
try:
  OPTIONS_A = int(config['BM']['options'])
except:
  OPTIONS_A = 0

if (OPTIONS_A > 0):
  HOME_TG = OPTIONS_A
else:
  HOME_TG = 0  


# "B" side
UDP_IP_B = config['General']['Address']
try:
  UDP_PORT_B_S = int(config['General']['RptPort'])
except:
  UDP_PORT_B_S = 3200

try:
  UDP_PORT_B_R = int(config['General']['LocalPort'])
except:
  UDP_PORT_B_R = 4200
  
CALL_B = config['General']['Callsign'] 

SUF_B = config['General']['Suffix'] 

##log
logging.basicConfig(handlers=[RotatingFileHandler(log_file, maxBytes=log_maxBytes, backupCount=log_backupCount)], format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)


while (len(CALL_A) != 10):
	CALL_A += ' '

while (len(CALL_B) != 10):
	CALL_B += ' '                            
    
    
MESSAGE_A = 'YSFL' + CALL_A # stringa connessione "A"
MESSAGE_B = 'YSFP' + CALL_B   # stringa connessione "B"


DISCONN_B = 'YSFU'  # stringa disconnessione "B"

ACK_B = 'YSFPREFLECTOR '

keepalive_str_a = 'YSFP' + CALL_A
keepalive_str_b = 'YSFP' + CALL_B 

# socket for YSF Direct
sock_a = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_a.settimeout(ack_tout + 10.0)


# socket for YSF net
sock_c = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_c.settimeout(ack_tout + 10.0)


# socket for MMDVMHost connection
sock_b = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_b.setblocking(1)
sock_b.bind((UDP_IP_B, UDP_PORT_B_R))

MESSAGE_C = 'YSFP' + CALL_A # stringa connessione "C"
ACK_C = 'YSFPREFLECTOR '
DISCONN_C = 'YSFU'  # stringa disconnessione "C"


TG=100*[(0,0)]
DGID = 0
DENY = []
TG_DSC = {}


def signal_handler(signal, frame):
  global run, a_connesso, b_connesso, c_connesso, arresto
  logging.info('Shutdown in progress ...')
  arresto = True
  time.sleep(0.5)
  if a_connesso:
    q_ba.put(str.encode(DISCONN_A))
    logging.info('Logout from BM server')
    time.sleep(1)
    a_connesso = False
  if c_connesso:
    q_bc.put(str.encode(DISCONN_C))
    logging.info('Logout from YSF Reflector')
    time.sleep(1)
    c_connesso = False
  b_connesso = False
  if ((not a_connesso) and (not b_connesso) and (not c_connesso)):
    run = False

### not used ###
def get_ysf_info(f, id):
  file_ysf = open(f)
  info = []
  for row in file_ysf:
    content = row.strip()
    # valid line (not a comment)
    if ((len(content) > 2) and (content[0] != '#')):
      c_split = content.split(';')
      if (c_split[0] == str(id).zfill(5)):
        info = c_split
        break

  file_ysf.close()
  return info


def read_dgid_file(f):
  global TG, DENY, TG_DSC
  error = False 
  n_dir = 0
  n_ysf = 0
  try:
    file = open(f)
    TG_TMP = 100*[(0, 0)]
    DENY_TMP = []
    TG_DSC_TMP = {}
    logging.info('Load DG-ID/TG from File')
    for row in file:
      content = row.strip()
      # valid line (not a comment)
      if ((len(content) > 2) and (content[0] != '#')):
        c_split = content.split(':')
        if (len(c_split) >= 2):
          try:
            dgid_int = int(c_split[0])
            mod_s = c_split[1].split('#')
            if (len(mod_s) == 1):   
              tg_int = int(c_split[1])
              mode_tmp = 1
            if ((len(mod_s) == 2) and (mod_s[0].upper() == 'BM')):
              tg_int = int(mod_s[1])
              mode_tmp = 1
            if (((len(mod_s) == 2) or (len(mod_s) == 3)) and (mod_s[0].upper() == 'YSF')):
              tg_int = int(mod_s[1])
              mode_tmp = 2              
              if (len(mod_s) == 3):
                dgid_tmp = int(mod_s[2])
                if ((dgid_tmp < 0) or (dgid_tmp > 100)):
                  dgid_tmp = 0  
              else:
                dgid_tmp = 0  
          except:
            dgid_int = 0
            error = True
              # valid record    
          if ((dgid_int > 0 ) and (dgid_int < 100) and (tg_int > 0) and len(str(tg_int)) < 10):
            # TG_TMP[dgid_int] = (1, tg_int, )
            if ((len(str(tg_int)) > 5) or (mode_tmp == 2)):
              sep = '>'
            else: 
              sep = '/'  
            if (((len(c_split) == 3) and (mode_tmp == 1)) or (mode_tmp == 2)) :
              if (mode_tmp == 1):
                dsc = c_split[2].strip().upper()
              if (mode_tmp == 2):
                if (len(c_split[2].strip()) > 0):
                  dsc = c_split[2].strip().upper()
                else:
                  dsc = 'YSF#' + str(tg_int)  
              if (len(dsc) > 13):
                dsc = dsc[0:13]
              dsc = dsc + sep + str(dgid_int)
            else:
              dsc = 'TG-' + str(tg_int) + sep + str(dgid_int)
            
            if (mode_tmp == 1):
              n_dir += 1
              TG_TMP[dgid_int] = (1, tg_int, dsc)
              TG_DSC_TMP.update({tg_int:dsc})
            if (mode_tmp == 2):
              n_ysf += 1
              TG_TMP[dgid_int] = (2, tg_int, dsc, c_split[3], int(c_split[4]), dgid_tmp)
              TG_DSC_TMP.update({tg_int:dsc})
            
            
            
          if (dgid_int == -1): # TG not allowed
            DENY_TMP.insert(len(DENY_TMP), tg_int)                
    file.close()
    # print(TG_TMP)
    # print(TG_DSC_TMP)
     
  except Exception as ex:
    error = True
    logging.info('Failed to load DG-ID from File ' + str(ex) )
  if not error:
    TG = TG_TMP.copy() 
    DENY = DENY_TMP.copy()
    TG_DSC = TG_DSC_TMP.copy()
    logging.info('Loaded ' + str(n_dir) + ' YSF Direct and ' + str(n_ysf) + ' YSF Network DGID')


def conn (sock, lato):
    global a_connesso, ACK_A, DGID, TG, UDP_IP_A_N, DISCONN_A
    global c_connesso, ACK_C, UDP_IP_C_N, DISCONN_C 
  
    # Connection to BM YSF DIRECT
    if (lato == 'A'):
      for i in range(100):
        if (TG[i][1] == OPTIONS_A):
          DGID = i
          break
          
      logging.info('conn: Try to connect to BM Server') 
      try:
        sock.connect((UDP_IP_A, UDP_PORT_A))
        sock.sendto(str.encode(MESSAGE_A), (UDP_IP_A, UDP_PORT_A))
        # print(str.encode(MESSAGE_A))
        msgFromServer = sock.recvfrom(bufferSize)
        # print(msgFromServer[0])
        sock_err = False
      except Exception as e:
        logging.error('conn: Error sending connection request to BM Server ' + str(e))
        sock_err = True
      if (not sock_err):  
        msg = msgFromServer[0][0:16]
        # print(msg)
        if ((len(msg) == 16) and (msg[0:6] == b'YSFACK')):
          ACK_A = 'YSFP' + msg[6:16].decode("utf-8") 
          DISCONN_A = 'YSFU' + msg[6:16].decode("utf-8") 
          key = msgFromServer[0][16:20]
          s_auth = bytes('YSFK' + CALL_A.ljust(10), 'utf-8') + hashlib.sha256(key + PASSWORD_A).digest() 
          
          try:
            sock.sendto(s_auth, (UDP_IP_A, UDP_PORT_A))
           # print(s_auth)
            msgFromServer = sock.recvfrom(bufferSize)
            # print(msgFromServer[0])
          except Exception as e:
            logging.error('conn: Error sending authentication to BM Server ' + str(e))
            sock_err = True
          # print(str.encode('YSFACK' + ACK_A[4:14]))
          if ((not sock_err) and (len(msg) == 16) and (msg[0:16] == str.encode('YSFACK' + ACK_A[4:14]))): 
            s_options = 'YSFO' + CALL_A.ljust(10) + 'group=' + str(OPTIONS_A)
            try:
              sock.sendto(str.encode(s_options), (UDP_IP_A, UDP_PORT_A))
              msgFromServer = sock.recvfrom(bufferSize)
            except Exception as e:
              logging.error('conn: Error sending options to BM Server ' + str(e))
              sock_err = True
           
            
            if ((not sock_err) and (len(msg) == 16) and (msg[0:16] == str.encode('YSFACK' + ACK_A[4:14]))):
              logging.info('BM Server Connected on TG ' + str(OPTIONS_A))
              lock_conn_a.acquire()
              UDP_IP_A_N = socket.gethostbyname(UDP_IP_A)
              a_connesso = True
              lock_conn_a.release()  
                        
              lock_a.acquire()
              ack_time_a = 0
              lock_a.release()


    if (lato == 'C'):
      logging.info('conn: try to connecto YSF Reflector') 
      try:
        UDP_IP_C_N = socket.gethostbyname(UDP_IP_C)
        sock.connect((UDP_IP_C, UDP_PORT_C))
        sock.sendto(str.encode(MESSAGE_C), (UDP_IP_C, UDP_PORT_C))
#        msgFromServer = sock.recvfrom(bufferSize)
        sock_err = False
      except Exception as e:
        logging.error('conn: Error connecting YSF Reflector ' + str(e))
        sock_err = True
       

# invio dati a "A"
def send_a():
  while True:
    msg = q_ba.get()
    try: 
      sock_a.sendto(msg, (UDP_IP_A, UDP_PORT_A))
    except Exception as e:
      logging.error('send_a: Error sending data to BM Server: ' + str(e))
      
      
# invio dati a "C"
def send_c():
  while True:
    msg = q_bc.get()
    try: 
      sock_c.sendto(msg, (UDP_IP_C, UDP_PORT_C))
    except Exception as e:
      logging.error('send_c: Error sending data to YSF Network: ' + str(e))


# invio dati a "B" 
def send_b():
  global mode
  while True:
    msg = q_ab.get()
    try: 
      sock_b.sendto(msg, (UDP_IP_B, UDP_PORT_B_S))
    except Exception as e:
      logging.error('send_b: Error sending data to MMDVMHost: ' + str(e))

def rcv_a():
  global a_connesso, b_connesso, a_b_dir, b_a_dir, ack_time_a, a_tf, b_tf, lock, ACK_A, DGID, dgid_prefix, wx_cmd
  while True:
    if a_connesso:  
      try:
        msgFromServer = sock_a.recvfrom(bufferSize)
        if ((msgFromServer[1][0] == UDP_IP_A_N) and (msgFromServer[1][1] == UDP_PORT_A)):
          # print(msgFromServer)        
          if True:
            if ((len(msgFromServer[0]) == 16) and (msgFromServer[0][0:16] == str.encode('YSFACK' + ACK_A[4:14]))):
              logging.error('TG changed to ' + str(OPTIONS_A))
              if (wx_cmd == 3):
                wx_cmd = 30
             # lock = False 
             # print('ricevuto ACK') 
        
            if ((len(msgFromServer[0]) == 16) and (msgFromServer[0][0:16] == str.encode('YSFNAK' + ACK_A[4:14]))):
              logging.error('TG changing rejected by BM Server ')  
              DGID = 0
        
          if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(ACK_A))):
          
            lock_a.acquire()
            ack_time_a = 0
            lock_a.release()
       
          if ((msgFromServer[0][0:4] == b'YSFD') and (mode == 1)):
            #print(msgFromServer[0])
            fich_a = ysffich.decode(msgFromServer[0][40:])
            if fich_a: 
              FI = ysffich.getFI(fich_a)
              SQL = ysffich.getSQ(fich_a)
              VOIP = ysffich.getVoIP(fich_a)
              FN = ysffich.getFN(fich_a)
              DT = ysffich.getDT(fich_a)
              # print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
              # print(msgFromServer[0])
              # print('*****')
              if True:
                ysffich.setSQ(0,fich_a)
                ysffich.setVoIP(False, fich_a)
                bya_msg = bytearray(msgFromServer[0])   
                ysffich.encode(bya_msg, fich_a)
                if ((not a_b_dir) and (not b_a_dir) and (FI != 2)):  # new stream and bridge free            
                  if (FI == 0):  # valid HC
                    lock_dir.acquire()
                    a_b_dir = True
                    b_a_dir = False
                    lock_dir.release()
                  else: # HC missing  
                    logging.error('rcv_a: add missing HC at ' + bya_msg[4:14].decode() + ' from ' + bya_msg[14:24].decode() + ' to ' + bya_msg[24:34].decode())
                    # print(bya_msg)
                    data = [0] * 120
                    csd1 = [0] * 20
                    csd2 = [0] * 20
                    csd1 = (bya_msg[24:34] + bya_msg[14:24])  # destination/source
                    csd2 = ('          ' + '          ').encode()  # downlink/uplink
                    try:
                      ysfpayload.writeHeader(data, csd1, csd2)
                      bya_msg[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
                    except Exception as e:
                      logging.error('rcv_a: error writing missing HC ' + str(e))
                    # print('setto direzioni')
                    ysffich.setFI(0, fich_a)
                    ysffich.encode(bya_msg, fich_a)
                    # print(bya_msg)
                    lock_dir.acquire()
                    a_b_dir = True
                    b_a_dir = False
                    lock_dir.release()
                                    
                lock_b_time.acquire()
                b_tf = 0.0
                lock_b_time.release()
                if (a_connesso and b_connesso and a_b_dir and not lock):
                 # bya_msg[4:14] = str.encode(CALL_B.ljust(10))
                  if ((dgid_prefix > 0) and (DGID > 0)):
                    if (FI == 0): 
                      data_p = bya_msg[35:]
                      if (ysfpayload.processheaderdata(bya_msg[35:])):
                        csd1 = ((ysfpayload.m_dest).ljust(10) + (str(DGID) + '/' + str(bya_msg[14:24], 'utf-8').strip()).ljust(10)).encode()
                        csd2 = (ysfpayload.m_downlink.ljust(10) + ysfpayload.m_uplink.ljust(10)).encode()
                        ysfpayload.writeHeader(data_p, csd1, csd2)
                        data_mod = bytearray(155)
                        data_mod[:35] = bya_msg[:35]
                        data_mod[35:] = data_p  
                        q_ab.put(bytes(data_mod))
                    else:
                      if ((FN == 1) and (DT == 2)):
                        data_p = bya_msg[35:]
                        src = (str(DGID) + '/' + str(bya_msg[14:24], 'utf-8').strip()).ljust(10).encode()
                        ysfpayload.writeVDMmode2Data(data_p, src)
                        data_mod = bytearray(155)
                        data_mod[:35] = bya_msg[:35]
                        data_mod[35:] = data_p  
                        q_ab.put(bytes(data_mod))
                      else:
                        q_ab.put(bytes(bya_msg))    
                  else:
                    q_ab.put(bytes(bya_msg))    
       
                if (FI == 2):
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = False
                  lock_dir.release()  
            else:
              logging.error('rcv_a: error decoding FICH')  
      except Exception as e:
        logging.error('rcv_a: ' + str(e))
        
    else:
      time.sleep(1.0)   

def rcv_c():
  global c_connesso, b_connesso, c_b_dir, b_c_dir, ack_time_c, c_tf, b_tf, lock, ACK_C, DGID, dgid_prefix
  global mode
  while True:
    if True:  
      try:
        msgFromServer = sock_c.recvfrom(bufferSize)
        if ((msgFromServer[1][0] == UDP_IP_C_N) and (msgFromServer[1][1] == UDP_PORT_C)):
          # print(msgFromServer)        
          
          if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(ACK_C))):
            if not c_connesso:
              logging.info('rcv_c: YSF Reflector connected')
              c_connesso = True
            lock_c.acquire()
            ack_time_c = 0
            lock_c.release()
       
          if ((msgFromServer[0][0:4] == b'YSFD') and (mode == 2) and c_connesso):
            # print(msgFromServer[0])
            fich_c = ysffich.decode(msgFromServer[0][40:])
            if fich_c: 
              FI = ysffich.getFI(fich_c)
              SQL = ysffich.getSQ(fich_c)
              VOIP = ysffich.getVoIP(fich_c)
              FN = ysffich.getFN(fich_c)
              DT = ysffich.getDT(fich_c)
              # print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
              # print(msgFromServer[0])
              # print('*****')
              if True:
                ysffich.setSQ(0,fich_c)
                ysffich.setVoIP(False, fich_c)
                bya_msg = bytearray(msgFromServer[0])   
                ysffich.encode(bya_msg, fich_c)
                if ((not c_b_dir) and (not b_c_dir) and (FI != 2)):  # new stream and bridge free            
                  if (FI == 0):  # valid HC
                    lock_dir.acquire()
                    c_b_dir = True
                    b_c_dir = False
                    lock_dir.release()
                  else: # HC missing  
                    logging.error('rcv_c: add missing HC at ' + bya_msg[4:14].decode() + ' from ' + bya_msg[14:24].decode() + ' to ' + bya_msg[24:34].decode())
                    # print(bya_msg)
                    data = [0] * 120
                    csd1 = [0] * 20
                    csd2 = [0] * 20
                    csd1 = (bya_msg[24:34] + bya_msg[14:24])  # destination/source
                    csd2 = ('          ' + '          ').encode()  # downlink/uplink
                    try:
                      ysfpayload.writeHeader(data, csd1, csd2)
                      bya_msg[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
                    except Exception as e:
                      logging.error('rcv_a: error writing missing HC ' + str(e))
                    # print('setto direzioni')
                    ysffich.setFI(0, fich_c)
                    ysffich.encode(bya_msg, fich_c)
                    # print(bya_msg)
                    lock_dir.acquire()
                    c_b_dir = True
                    b_c_dir = False
                    lock_dir.release()
                                    
                lock_c_time.acquire()
                c_tf = 0.0
                lock_c_time.release()
                if (c_connesso and b_connesso and c_b_dir and not lock):
                 # bya_msg[4:14] = str.encode(CALL_B.ljust(10))
                  if ((dgid_prefix > 0) and (DGID > 0)):
                    if (FI == 0): 
                      data_p = bya_msg[35:]
                      if (ysfpayload.processheaderdata(bya_msg[35:])):
                        csd1 = ((ysfpayload.m_dest).ljust(10) + (str(DGID) + '/' + str(bya_msg[14:24], 'utf-8').replace('-','/').split('/')[0].strip()).ljust(10)).encode()
                        csd2 = (ysfpayload.m_downlink.ljust(10) + ysfpayload.m_uplink.ljust(10)).encode()
                        ysfpayload.writeHeader(data_p, csd1, csd2)
                        data_mod = bytearray(155)
                        data_mod[:35] = bya_msg[:35]
                        data_mod[35:] = data_p  
                        q_ab.put(bytes(data_mod))
                    else:
                      if ((FN == 1) and (DT == 2)):
                        data_p = bya_msg[35:]
                        src = (str(DGID) + '/' + str(bya_msg[14:24], 'utf-8').replace('-','/').split('/')[0].strip()).ljust(10).encode()
                        ysfpayload.writeVDMmode2Data(data_p, src)
                        data_mod = bytearray(155)
                        data_mod[:35] = bya_msg[:35]
                        data_mod[35:] = data_p  
                        q_ab.put(bytes(data_mod))
                      else:
                        q_ab.put(bytes(bya_msg))    
                  else:
                    q_ab.put(bytes(bya_msg))    
       
                if (FI == 2):
                  lock_dir.acquire()
                  c_b_dir = False
                  b_c_dir = False
                  lock_dir.release()  
            else:
              logging.error('rcv_c: error decoding FICH')  
      except Exception as e:
        if c_connesso:
          logging.error('rcv_c: ' + str(e))
        pass
        
    else:
      time.sleep(1.0)   




def rcv_b():
  global a_connesso, b_connesso, c_connesso, a_b_dir, b_a_dir, ack_time_a, ack_time_b, a_tf, b_tf, OPTIONS_A, lock, TG, t_lock, DGID, t_home_act, wx_cmd, wx_t, wx_start
  global UDP_IP_A, UDP_PORT_A, sock_a, mode, UDP_IP_C, UDP_PORT_C, MESSAGE_C
  ch_gw = False
  gw_suf = 0
  while True:
    if True:
      try:
        msgFromServer = sock_b.recvfrom(bufferSize)
        #print(msgFromServer[0]) 
        if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(MESSAGE_B))):
          q_ab.put(str.encode(ACK_B)) 
         
          lock_b.acquire()
          ack_time_b = 0
          lock_b.release()
          
          
        if (msgFromServer[0][0:4] == b'YSFD'):  
          if ch_gw:
            msg_bya = bytearray(msgFromServer[0])   
            msg_bya[4:14] = str.encode((CALL_A[0:7].strip()+ '-' + str(gw_suf)).ljust(10))
            msg_rcv = bytes(msg_bya)    
          else:
             msg_rcv = msgFromServer[0]
            
          t_home_act = 0.0
          fich_b = ysffich.decode(msg_rcv[40:])
          if fich_b: 
            FI = ysffich.getFI(fich_b)
            SQL = ysffich.getSQ(fich_b)
            VOIP = ysffich.getVoIP(fich_b)
            FN = ysffich.getFN(fich_b)
            FT = ysffich.getFT(fich_b)
            DT = ysffich.getDT(fich_b)
            #print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
            if ((SQL != 127) and (DT != 1)):              
              ysffich.setSQ(0, fich_b)
              ysffich.setVoIP(False, fich_b)
              bya_msg = bytearray(msg_rcv)   
              ysffich.encode(bya_msg, fich_b)
              #print('a > b ' +  str(a_b_dir) + ' b > a ' + str(b_a_dir))
              if ((not a_b_dir) and (not b_a_dir) and (FI != 2)):  # header and bridge free
                if ((SQL != 0) and (TG[SQL][1] != OPTIONS_A) and (SQL < 100)):
                  # cambio TG                    
                  if (TG[SQL][1] != 0): 
                    OPTIONS_A = TG[SQL][1]
                    DGID = SQL
                    if (TG[SQL][0] != mode):  # Devo cambiare modo
                      if (TG[SQL][0] == 1): # Direct 
                        mode = 1
                        q_bc.put(str.encode(DISCONN_C )) 
                        ch_gw = False
                        gw_suf = 0
                        c_connesso = False
                        logging.error('rcv_b: Set Network to YSF Direct')
                    
                      if (TG[SQL][0] == 2): # YSF Net 
                        mode = 2
                        logging.error('rcv_b: Change Network to YSF')
                    
                    
                    if (mode == 1):
                      s_options = 'YSFO' + CALL_A.ljust(10) + 'group=' + str(OPTIONS_A)
                      q_ba.put(str.encode(s_options))                    
                    
                    if (mode == 2):
                      ack_time_c = 0.0
                      # set reflector IP and PORT 
                      if c_connesso:
                        q_bc.put(str.encode(DISCONN_C )) 
                        c_connesso = False  
                        time.sleep(1.0)
                      UDP_IP_C = TG[SQL][3] 
                      UDP_PORT_C = TG[SQL][4]
                      if (TG[SQL][5] > 0):
                        MESSAGE_C = 'YSFP' + (CALL_A[0:7].strip()+ '-' + str(TG[SQL][5]).zfill(2)).ljust(10)
                        ch_gw = True
                        gw_suf = TG[SQL][5]
                      else:
                        MESSAGE_C = ('YSFP' + CALL_A).ljust(10)
                        ch_gw = False  
                        gw_suf = 0
                      conn (sock_c, 'C') 
                      logging.error('rcv_b: Set Network to YSF Net at YSF#' + str(TG[SQL][1]) + ' with DGID ' + str(SQL) + ' and callsign ' + MESSAGE_C[4:].strip())
                    
                    lock = True
                    t_lock = 0.0
                  
                if (FI == 0):
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = True
                  lock_dir.release()
                else:
                  logging.error('rcv_b: add missing HC at ' + bya_msg[4:14].decode() + ' from ' + bya_msg[14:24].decode() + ' to ' + bya_msg[24:34].decode())
                  # print(bya_msg)
                  data = [0] * 120
                  csd1 = [0] * 20
                  csd2 = [0] * 20
                  csd1 = (bya_msg[24:34] + bya_msg[14:24])  # destination/source
                  csd2 = ('          ' + '          ').encode()  # downlink/uplink
                  try:
                    ysfpayload.writeHeader(data, csd1, csd2)
                    bya_msg[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
                  except Exception as e:
                    logging.error('rcv_b: error writing missing HC ' + str(e))
                  ysffich.setFI(0, fich_b)
                  ysffich.encode(bya_msg, fich_b)
                  # print('setto direzioni')
                  # print(bya_msg)
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = True
                  lock_dir.release()

              if (SQL != 0):
                ysffich.setSQL(0, fich_b)
                ysffich.encode(bya_msg, fich_b)

              lock_a_time.acquire()
              a_tf = 0.0
              lock_a_time.release()
              if (a_connesso and b_connesso and b_a_dir and not lock):
             #   bya_msg[4:14] = str.encode(CALL_A.ljust(10))
                if (mode == 1):
                  q_ba.put(bytes(bya_msg))    
                if (mode == 2):
                  q_bc.put(bytes(bya_msg))  
   
              if (FI == 2):
                lock_dir.acquire()
                a_b_dir = False
                b_a_dir = False
                lock_dir.release()  
                lock = False
            else:
              #########################
              # logging.info('rcv_b: W-X Command - SQL = ' + str(SQL) + ' DT = ' + str(DT) + ' FI = ' + str(FI) + ' FN = ' + str(FN) + ' FT = ' + str(FT))  
              try:
                cmd = wiresx.process(msg_rcv[35:], CALL_B, DT, FI, FN, FT) 
              except Exception as e:
                logging.error('rcv_b: wires-x process command: ' + str(e))
              if (cmd == 1):
                logging.info('rcv_b: Received Wires-x DX_REQ Command')
                wx_cmd = 1
                wx_t = 0.0
                
                
              if (cmd == 2):
                logging.info('rcv_b: Received Wires-x ALL_REQ Command')
                wx_cmd = 2
                wx_start = 0
                if ((chr(wiresx.wx_command[5]) == '0') and (chr(wiresx.wx_command[6]) == '1')): # ALL without search
                  s_start = ''
                  for i in wiresx.wx_command[7:10]:
                    s_start+=chr(i)
                  try:
                    wx_start = int(s_start)
                  except:
                    wx_start = 0
                  
                  if (wx_start > 0):
                   wx_start -= 1
                        
                # print(wiresx.wx_command)
                wx_t = 0.0
                
                
              if (cmd == 3):
                logging.info('rcv_b: Received Wires-x CON_REQ Command')
                if (mode == 2):
                  mode = 1
                  q_bc.put(str.encode(DISCONN_C )) 
                  c_connesso = False
                  logging.error('rcv_b: Set Network to YSF Direct')
                tg_s = ''
                for i in wiresx.wx_command[5:10]:
                  tg_s+=chr(i)
                try:
                  tg_i = int(tg_s)
                except:
                  tg_i = 0
                if ((tg_i > 1) and (not (tg_i in DENY))):
                  logging.info('rcv_b: Received Wires-x Request for change TG to '+ str(tg_i))
                  OPTIONS_A = tg_i
                  dg_tmp = 0
                  for i in range(100):
                    if (TG[i][1] == OPTIONS_A):
                      dg_tmp = i
                      break
                  
                  if (dg_tmp != 0):
                    DGID = dg_tmp
                  else:
                    DGID = 0
                  
                  s_options = 'YSFO' + CALL_A.ljust(10) + 'group=' + str(OPTIONS_A)
                  q_ba.put(str.encode(s_options))                    
                  lock = True
                  t_lock = 0.0  
                  
                      
                  wx_cmd = 3
                  wx_t = 0.0 
                    
                
              if (cmd == 4):
                logging.info('rcv_b: Received Wires-x DIS_REQ Command')
                
              if (cmd == 5):
                logging.info('rcv_b: Received Wires-x CAT_REQ Command')
                              
          else:
             logging.error('rcv_b: error decoding FICH')  
      except Exception as e:
        logging.error('rcv_b: ' + str(e))
    else:
      time.sleep(1.0)


# clock per gestione keepalive
def clock ():
 global ack_time_a, ack_time_b, ack_time_c, ack_tout, a_tf, b_tf, c_tf, a_b_dir, b_a_dir, b_c_dir, lock, t_lock, t_home_act 
 global OPTIONS_A, DGID, wx_cmd, wx_t, wx_start, mode, c_connesso
 t = ack_tout * 1.1
 while 1:
     if (a_tf < 5.0):
       lock_a_time.acquire()
       a_tf += 0.1
       lock_a_time.release()  
       
     if ((a_tf > 2.0) and (b_a_dir == True)):
       lock_dir.acquire()
       b_a_dir = False
       lock_dir.release()  
       lock = False  
       
     if (c_tf < 5.0):
       lock_c_time.acquire()
       c_tf += 0.1
       lock_c_time.release()    
     
     if ((c_tf > 2.0) and (b_c_dir == True)):
       lock_dir.acquire()
       b_c_dir = False
       lock_dir.release()  
       lock = False  
         
     if (b_tf < 5.0):
       lock_b_time.acquire()
       b_tf += 0.1
       lock_b_time.release()
       
     if ((b_tf > 2.0) and (a_b_dir == True)):
         lock_dir.acquire()
         a_b_dir = False
         lock_dir.release()   
         
     if (ack_time_a < t):   
       lock_a.acquire()
       ack_time_a +=0.1
       lock_a.release()
       
     if (ack_time_b < t):     
       lock_b.acquire()
       ack_time_b +=0.1
       lock_b.release()
     
     if (ack_time_c < t):   
       lock_c.acquire()
       ack_time_c +=0.1
       lock_c.release()
     
     if lock:
       t_lock += 0.1
     
     if (t_lock > 7.0):
       lock = False
       # logging.info('clock: Reset lock by timeout')
       t_lock = 0.0
     
     if (((HOME_TG > 0) and (HOME_TG != OPTIONS_A) and (back_to_home > 0)) or (mode == 2)): # not at home (home is always YSF Direct)
       t_home_act += 0.1
     
     if ((t_home_act > time_to_home) and not a_b_dir and not b_a_dir and not b_c_dir and not c_b_dir and ((OPTIONS_A != HOME_TG) or (mode == 2)) and (back_to_home > 0)):  # back to home
       OPTIONS_A = HOME_TG
       DGID = HOME_DGID
       logging.info('clock: Back To Home at ' + str(OPTIONS_A))
       if (mode == 2):
         mode = 1
         q_bc.put(str.encode(DISCONN_C )) 
         c_connesso = False
         logging.error('rcv_b: Set Network to YSF Direct')
         time.sleep(1.0)
       s_options = 'YSFO' + CALL_A.ljust(10) + 'group=' + str(OPTIONS_A)
       q_ba.put(str.encode(s_options))
       
       wiresx.ReplyToWiresxConnReqPacket(a_connesso, OPTIONS_A, q_ab, TG_DSC)
       t_home_act = 0.0                      
     
     if (wx_cmd > 0):
       wx_t += 0.1
     
     if (wx_t > 1.0):
       wx_t = 0.0
       if (wx_cmd == 1):
         wx_cmd = 0
         wiresx.ReplyToWiresxDxReqPacket(a_connesso, OPTIONS_A, q_ab, TG_DSC)
         
       if (wx_cmd == 2):
         wx_cmd = 0
         wiresx.ReplyToWiresxAllReqPacket(q_ab, TG_DG_DICT, wx_start, TG_DSC)  
         
       if (wx_cmd == 30):   # wx_cmd == 3 with BM ACK
         wx_cmd = 0
         wiresx.ReplyToWiresxConnReqPacket(a_connesso, OPTIONS_A, q_ab, TG_DSC) 
         
      
     time.sleep(0.1)

# controllo connessioni
def check_conn():
  global a_connesso, b_connesso, c_connesso  
  while True:
    if (ack_time_a > ack_tout):
      logging.info('check_conn: BM Server connection Timeout')
      lock_conn_a.acquire()
      a_connesso = False
      lock_conn_a.release()
      conn (sock_a, 'A')    
      
    if (ack_time_c > ack_tout) and (mode == 2):
      logging.info('check_conn: YSF Network connection Timeout')
      lock_conn_c.acquire()
      c_connesso = False
      lock_conn_c.release()
      conn (sock_c, 'C')    
      
    time.sleep(ack_tout/2.0)

# invio pacchetti keepalive
def keepalive():
  global ack_time_a, ack_time_b, ack_time_c   
  while True:
    if (a_connesso and not arresto):
        q_ba.put(str.encode(keepalive_str_a))
    
    if (c_connesso and not arresto):
        q_bc.put(str.encode(MESSAGE_C))
    
                   
    time.sleep(ack_period)  


run = True
logging.info('YSFBMGateway Ver. ' + ver + ': started')
read_dgid_file(dgid_file)

TG_DG_DICT = {}
for i in range(100):
  if (TG[i][1] > 0):
    TG_DG_DICT.update({i:TG[i]})

for i in range(100):
  if (TG[i][1] == OPTIONS_A):
    HOME_DGID = i
    break
nd_tmp = CALL_B.strip() + '-' + SUF_B.strip()
if (len(nd_tmp) > 10):
  nd_tmp = CALL_B


wiresx.setInfo(Name, TX_freq, RX_freq, CALL_B, nd_tmp.ljust(10))

arresto = False
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

t_clock = threading.Thread(target = clock)
t_clock.daemon = True
t_conn = threading.Thread(target = check_conn)
t_conn.daemon = True
t_keep = threading.Thread(target = keepalive)
t_keep.daemon = True
t_send_a = threading.Thread(target = send_a)
t_send_a.daemon = True
t_send_b = threading.Thread(target = send_b)
t_send_b.daemon = True
t_send_c = threading.Thread(target = send_c)
t_send_c.daemon = True
t_rcv_a = threading.Thread(target = rcv_a)
t_rcv_a.daemon = True
t_rcv_b = threading.Thread(target = rcv_b)
t_rcv_b.daemon = True
t_rcv_c = threading.Thread(target = rcv_c)
t_rcv_c.daemon = True


t_clock.start() 
t_conn.start()
t_keep.start()
t_send_a.start()
t_send_b.start()
t_send_c.start()
t_rcv_a.start()
t_rcv_b.start()
t_rcv_c.start()


while run:
  time.sleep(3.0)
logging.info('ysfbmgateway properly stopped')

