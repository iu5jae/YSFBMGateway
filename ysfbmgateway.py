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

ver = '221119'

a_connesso = False
b_connesso = True
lock = False
t_lock = 0.0

a_tf = 0.0 # tempo trascorso da ultimo pacchetto
b_tf = 0.0

q_ab = queue.Queue() # coda pacchetti A -> B 
q_ba = queue.Queue() # coda pacchetti B -> A 

lock_a = threading.Lock()
lock_b = threading.Lock()
lock_a_time = threading.Lock()
lock_b_time = threading.Lock()
lock_conn_a = threading.Lock()
lock_conn_b = threading.Lock()
lock_dir = threading.Lock()
a_b_dir = False # direzione attiva A --> B
b_a_dir = False # direzione attiva B --> A
bufferSize = 2048

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


ack_period = 3.0
ack_tout = 30.0  
  
ack_time_a = ack_tout 
ack_time_b = ack_tout 


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



REM_PREF_B = 0
AUTH_A = 1

##log
logging.basicConfig(handlers=[RotatingFileHandler(log_file, maxBytes=log_maxBytes, backupCount=log_backupCount)], format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)


while (len(CALL_A) != 10):
	CALL_A += ' '

while (len(CALL_B) != 10):
	CALL_B += ' '
if (AUTH_A == 1):    
  MESSAGE_A = 'YSFL' + CALL_A # stringa connessione "A"
else:  
  MESSAGE_A = 'YSFP' + CALL_A # stringa connessione "A"

MESSAGE_B = 'YSFP' + CALL_B   # stringa connessione "B"

DISCONN_A = 'YSFU'  # stringa disconnessione "A"
DISCONN_B = 'YSFU'  # stringa disconnessione "B"

if (AUTH_A == 1):
  ACK_A =   '              '
else:  
  ACK_A = 'YSFPREFLECTOR '
#ACK_A =   'YSFPBM_2222  '


ACK_B = 'YSFPREFLECTOR '

#CALL_A = CALL_A.strip()
#CALL_B = CALL_B.strip()

keepalive_str_a = 'YSFP' + CALL_A
keepalive_str_b = 'YSFP' + CALL_B 


# socket connessione A
sock_a = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_a.settimeout(ack_tout + 10.0)

# socket connessione B
sock_b = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_b.setblocking(1)
sock_b.bind((UDP_IP_B, UDP_PORT_B_R))



TG=100*[0]
DGID = 0

def signal_handler(signal, frame):
  global run, a_connesso, b_connesso, arresto
  logging.info('Shutdown in progress ... ...')
  arresto = True
  time.sleep(0.5)
  if a_connesso:
    q_ba.put(str.encode(DISCONN_A))
    logging.info('Logout from BM server')
    time.sleep(1)
    a_connesso = False
    b_connesso = False
  if ((not a_connesso) and (not b_connesso)):
    run = False

def read_dgid_file(f):
  global TG
  error = False 
  try:
    file = open(f)
    TG_TMP = 100*[0]
    logging.info('Reload DG-ID/TG from File')
    for row in file:
      content = row.strip()
      # valid line (not a comment)
      if ((len(content) > 2) and (content[0] != '#')):
        c_split = content.split(':')
        if (len(c_split) == 2):
          try:
            dgid_int = int(c_split[0])
            tg_int = int(c_split[1])
          except:
            dgid_int = 0
            error = True
              # valid record    
          if ((dgid_int > 0 ) and (dgid_int < 100)):
            TG_TMP[dgid_int] = tg_int
    file.close() 
  except Exception as ex:
    error = True
  if not error:
    TG = TG_TMP.copy() 
  else:
    logging.info('Failed to load DG-ID from File ' + str(ex) )



def conn (sock, lato):
    global a_connesso, ACK_A, DGID, TG
  
    # Connection to BM YSF DIRECT
    if ((lato == 'A') and (AUTH_A == 1)):
      for i in range(100):
        if (TG[i] == OPTIONS_A):
          DGID = i
          break
          
      logging.info('conn: Try to connect to BM Server') 
      try:
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
              logging.info('BM Server Connected')
              lock_conn_a.acquire()
              a_connesso = True
              lock_conn_a.release()  
                        
              lock_a.acquire()
              ack_time_a = 0
              lock_a.release()


        

# invio dati a "A"
def send_a():
  while True:
    msg = q_ba.get()
    try: 
      sock_a.sendto(msg, (UDP_IP_A, UDP_PORT_A))
    except Exception as e:
      logging.error('send_a: Error sending data to BM Server ' + str(e))

# invio dati a "B" 
def send_b():
  while True:
    msg = q_ab.get()
    try: 
      sock_b.sendto(msg, (UDP_IP_B, UDP_PORT_B_S))
    except Exception as e:
      logging.error('send_b: Error sending data to MMDVMHost ' + str(e))

def rcv_a():
  global a_connesso, b_connesso, a_b_dir, b_a_dir, ack_time_a, a_tf, b_tf, lock, ACK_A, DGID,  dgid_prefix
  while True:
    if a_connesso:  
      try:
        msgFromServer = sock_a.recvfrom(bufferSize)
        #print(msgFromServer[0])        
        if ((len(msgFromServer[0]) == 16) and (msgFromServer[0][0:16] == str.encode('YSFACK' + ACK_A[4:14]))):
          logging.error('TG changed to ' + str(OPTIONS_A))
          #lock = False 
         # print('ricevuto ACK') 
        
        if ((len(msgFromServer[0]) == 16) and (msgFromServer[0][0:16] == str.encode('YSFNAK' + ACK_A[4:14]))):
          logging.error('TG changing rejected by BM Server ')  
          DGID = 0
        
        if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(ACK_A))):
          
          lock_a.acquire()
          ack_time_a = 0
          lock_a.release()
       
        if (msgFromServer[0][0:4] == b'YSFD'):
          #print(msgFromServer[0])
          if ysffich.decode(msgFromServer[0][40:]): 
            FI = ysffich.getFI()
            SQL = ysffich.getSQ()
            VOIP = ysffich.getVoIP()
            FN = ysffich.getFN()
            DT = ysffich.getDT()
            # print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
            # print(msgFromServer[0])
            # print('*****')
            if True:
              ysffich.setSQ(0)
              ysffich.setVoIP(False)
              bya_msg = bytearray(msgFromServer[0])   
              ysffich.encode(bya_msg)
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
                  ysffich.setFI(0)
                  ysffich.encode(bya_msg)
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


def rcv_b():
  global a_connesso, b_connesso, a_b_dir, b_a_dir, ack_time_b, a_tf, b_tf, OPTIONS_A, lock, TG, t_lock, DGID
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
          if ysffich.decode(msgFromServer[0][40:]): 
            FI = ysffich.getFI()
            SQL = ysffich.getSQ()
            VOIP = ysffich.getVoIP()
            FN = ysffich.getFN()
            DT = ysffich.getDT()
            #print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
            if ((SQL != 127) and (DT != 1)):              
              ysffich.setSQ(0)
              ysffich.setVoIP(False)
              bya_msg = bytearray(msgFromServer[0])   
              ysffich.encode(bya_msg)
              #print('a > b ' +  str(a_b_dir) + ' b > a ' + str(b_a_dir))
              if ((not a_b_dir) and (not b_a_dir) and (FI != 2)):  # header and bridge free
                if ((SQL != 0) and (TG[SQL] != OPTIONS_A) and (SQL < 100)):
                  # cambio TG
                  if (TG[SQL] != 0): 
                    OPTIONS_A = TG[SQL]
                    DGID = SQL
                    s_options = 'YSFO' + CALL_A.ljust(10) + 'group=' + str(OPTIONS_A)
                    q_ba.put(str.encode(s_options))                    
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
                  ysffich.setFI(0)
                  ysffich.encode(bya_msg)
                  # print('setto direzioni')
                  # print(bya_msg)
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = True
                  lock_dir.release()

              lock_a_time.acquire()
              a_tf = 0.0
              lock_a_time.release()
              if (a_connesso and b_connesso and b_a_dir and not lock):
             #   bya_msg[4:14] = str.encode(CALL_A.ljust(10))
                q_ba.put(bytes(bya_msg))    
            
   
              if (FI == 2):
                lock_dir.acquire()
                a_b_dir = False
                b_a_dir = False
                lock_dir.release()  
                lock = False
            else:
              #########################
              logging.info('W-X Command - SQL = ' + str(SQL) + ' DT = ' + str(DT))   
          else:
             logging.error('rcv_b: error decoding FICH')  
      except Exception as e:
        logging.error('rcv_b: ' + str(e))
    else:
      time.sleep(1.0)


# clock per gestione keepalive
def clock ():
 global ack_time_a, ack_time_b, ack_tout, a_tf, b_tf, a_b_dir, b_a_dir, lock, t_lock
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
     
     if lock:
       t_lock += 0.1
     
     if (t_lock > 5.0):
       lock = False
       logging.info('clock: Reset lock by timeout')
       t_lock = 0.0
      
     time.sleep(0.1)

# controllo connessioni
def check_conn():
  global a_connesso, b_connesso  
  while True:
    if (ack_time_a > ack_tout):
      logging.info('check_conn: BM Server connection Timeout')
      lock_conn_a.acquire()
      a_connesso = False
      lock_conn_a.release()
      conn (sock_a, 'A')    
    time.sleep(ack_tout/2.0)

# invio pacchetti keepalive
def keepalive():
  global ack_time_a, ack_time_b   
  ncnt = 0
  while True:
    ncnt += 1
    if (a_connesso and not arresto):
        q_ba.put(str.encode(keepalive_str_a))
                   
    time.sleep(ack_period)  


run = True
logging.info('YSFBMGateway Ver. ' + ver + ': started')
read_dgid_file(dgid_file)

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
t_rcv_a = threading.Thread(target = rcv_a)
t_rcv_a.daemon = True
t_rcv_b = threading.Thread(target = rcv_b)
t_rcv_b.daemon = True



t_clock.start() 
t_conn.start()
t_keep.start()
t_send_a.start()
t_send_b.start()
t_rcv_a.start()
t_rcv_b.start()



while run:
  time.sleep(3.0)
logging.info('ysfbmgateway properly stopped')

