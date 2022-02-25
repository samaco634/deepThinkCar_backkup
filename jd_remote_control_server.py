# This is server code to send video frames over UDP
import cv2, imutils, socket
import numpy as np
import time
import base64
from threading import Thread
from jd_car_motor_l9110 import JdCarMotorL9110
from adafruit_servokit import ServoKit

'''
Raspberry pi IP address. Put your Raspberry pi IP address here.
Port number for remote control data
Port number for video streaming  
'''
PI_IP = '172.31.98.78'
TCP_PORT = 9998
VIDEO_PORT = 9999
OFFSET = 0

'''
TcpThread class for remote control through socket
'''
class TcpThread(Thread):
    def __init__(self, ip, port):
        Thread.__init__(self)
        # Setting TCP socket for remote control 
        self.ip = ip
        self.port = port
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_address = (self.ip, self.port)
        self.tcp_server.bind(tcp_address) 
        print('Listening TCP at: ',tcp_address)
       
    def run(self):
        while True:
            print('Waiting TCP connection... ')
            self.tcp_server.listen()
            self.conn, self.client_addr = self.tcp_server.accept()
            print('GOT TCP connection from ',self.client_addr)
            run = True
            while run:
                try:
                    # receive remote control data from client(PC)
                    data = self.conn.recv(40)
                    print("TCP received: ", data.decode())
                    # 'start': strat deepThinkCar 
                    if data.decode() == 'start':
                        motor.motor_move_forward(35)
                    # 'stop': stop deepThinkCar 
                    elif data.decode() == 'stop':
                        motor.motor_stop()
                    else:
                    # 'left' or 'right': turn front wheel
                        try:
                            angle = int(data.decode())
                            if angle > 30 and angle < 160:
                                servo.servo[0].angle = angle + OFFSET
                        except:
                            pass
                except:
                    print("TCP communication error")
                # Send ping data to check TCP socket
                # If we can not send ping data, disconnect UDP and TCP socket.

                try:
                    self.conn.sendall('ping'.encode())
                except:
                    print("client disconnected...")
                    self.conn.close()  # Disconnect TCP socket 
                    motor.motor_stop()
                    run = False
                    kill_udp()  # Disconnect UDP socket 
                
def kill_udp():
    global udp_run
    udp_run = False   

udp_run = True
BUFF_SIZE = 65536

# Strat TCP socket thread for remote control 
tcp = TcpThread(PI_IP, TCP_PORT)
tcp.daemon = 1
tcp.start()

# DC motor and servo control object 
motor = JdCarMotorL9110()
servo = ServoKit(channels=16)

while True:
    vid = cv2.VideoCapture(0) 
    # Setting UDP socket for video streaming (Rpi -> PC)
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
    host_name = socket.gethostname()
    socket_address = (PI_IP, VIDEO_PORT)
    server_socket.bind(socket_address)
    print('Listening at:',socket_address)

    print('Waiting UDP connection... ')
    msg,client_addr = server_socket.recvfrom(BUFF_SIZE)
    print('GOT connection from ',client_addr)
    
    udp_run = True
    while udp_run:
        # Getting image from camera 
        _,frame = vid.read()
        frame = imutils.resize(frame,width=400)
        # Encoding as JPEG 
        encoded,buffer = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
        message = base64.b64encode(buffer)
        try:
            # Sending to client 
            server_socket.sendto(message,client_addr)
        except:
            print("UDP communication error")
        cv2.imshow('TRANSMITTING VIDEO',frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    server_socket.close()
    cv2.destroyAllWindows()
    vid.release()
