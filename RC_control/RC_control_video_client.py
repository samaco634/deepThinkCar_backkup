# This is client code to receive video frames over UDP
import cv2, socket
import numpy as np
import base64
from threading import Thread
import pygame 
import os 

'''
 Raspberry pi IP address to connect 
'''
PI_IP = '172.31.98.211'
TCP_PORT = 9998
UDP_PORT = 9999

class TcpThread(Thread):
    def __init__(self, ip, port):
        Thread.__init__(self)
        pygame.init()
        self.key="no key"
        self.font = pygame.font.SysFont("arial",30)  
        self.text1 = self.font.render("Remote Control deepThinkCar",True,(255,255,255)) 
        self.text2 = self.font.render("s: start car",True,(255,255,255))  
        self.text3 = self.font.render("SPACE: stop car",True,(255,255,255))
        self.text4 = self.font.render("LEFT: left turn",True,(255,255,255))  
        self.text5 = self.font.render("RIGHT: right turn",True,(255,255,255))  
        self.text6 = self.font.render("d: erase recored image",True,(255,255,255)) 
        self.text7 = self.font.render(self.key,True,(255,255,255))  
        self.running = True
        self.servo_angle = 90
        self.offset = -5
        self.ip = ip
        self.port = port
        self.record = False
        self.gamepads = []
        self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_address = (self.ip, self.port)
        self.tcp_client.connect(tcp_address) 
        print('Connectinng TCP at: ',tcp_address)
        self.screen = pygame.display.set_mode((640, 480))
        pygame.display.set_caption("TCP remocon")
        self.clock = pygame.time.Clock()
        for a in range(0, pygame.joystick.get_count()):
            print( pygame.joystick.get_count())
            self.gamepads.append(pygame.joystick.Joystick(a))
            self.gamepads[-1].init()
            print(self.gamepads[-1].get_name())

    def close_pygame_win(self):
        self.running = False

    def get_servo_angle(self):
        return self.servo_angle

    def get_record_status(self):
        return self.record
       
    def run(self):
        self.running = True
        while self.running:
            self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.tcp_client.close()
                    self.running = False
                if event.type == pygame.JOYBUTTONDOWN:
                    print(event.button)

                if event.type == pygame.JOYAXISMOTION:
                    x1 = int(self.gamepads[-1].get_axis(0)*100)
                    x2 = int(self.gamepads[-1].get_axis(1)*100)
                    x3 = int(self.gamepads[-1].get_axis(2)*100)
                    x4 = int(self.gamepads[-1].get_axis(3)*100)
                    x_all = 'a'+str(x1)+'b'+str(x2)+'c'+str(x3)+'d'+str(x4)+'e'
                    self.tcp_client.sendall(x_all.encode())
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]: # left
                    self.servo_angle -= 5
                    if self.servo_angle < 45:
                        self.servo_angle = 45
                    self.tcp_client.sendall(str(self.servo_angle+self.offset).encode())
                    self.key = 'left'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
                if keys[pygame.K_RIGHT]: # right
                    self.servo_angle += 5
                    if self.servo_angle > 135:
                        self.servo_angle = 135
                    self.tcp_client.sendall(str(self.servo_angle+self.offset).encode())
                    self.key = 'right'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
                if keys[pygame.K_UP]: # up
                    self.tcp_client.sendall('up'.encode())
                    self.key = 'up'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
                if keys[pygame.K_DOWN]: # down
                    self.tcp_client.sendall('down'.encode())
                    self.key = 'down'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
                if keys[pygame.K_s]: # s
                    self.record = True
                    self.tcp_client.sendall('start'.encode())
                    self.key = 'start'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
                if keys[pygame.K_d]: # d
                    try:
                        os.system("del C:\img\*.png")
                    except:
                        print("file error")
                    
                if keys[pygame.K_SPACE]: # Space
                    self.record = False
                    self.tcp_client.sendall('stop'.encode())
                    self.key = 'stop'
                    self.text7 = self.font.render(self.key,True,(255,255,255))  
            self.screen.fill((0,0,0))
            self.screen.blit(self.text1, (100, 50))
            self.screen.blit(self.text2, (100, 100))
            self.screen.blit(self.text3, (100, 150))
            self.screen.blit(self.text4, (100, 200))
            self.screen.blit(self.text5, (100, 250))
            self.screen.blit(self.text6, (100, 300))
            self.screen.blit(self.text7, (100, 350))
           
            pygame.display.update()
           
        print("client disconnected")
        self.tcp_client.close()

'''
Open UDP socket for video streaming  
'''
BUFF_SIZE = 65536
client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
message = b'Hello'
client_socket.sendto(message,(PI_IP, UDP_PORT))

'''
Start RC thread for remote control 
'''
tcp = TcpThread(PI_IP, TCP_PORT)
tcp.daemon = 1
tcp.start()

record = False
index = 0

# Make folder for labeling data
try:
	if not os.path.exists('C:\img'):
		os.makedirs('C:\img')
except OSError:
	pass

# Erase prior labeling data 
os.system("del C:\img\*.png")

while True:
    # Receiving video streaming from RPi server 
    packet,_ = client_socket.recvfrom(BUFF_SIZE)
    data = base64.b64decode(packet,' /')
    npdata = np.fromstring(data,dtype=np.uint8)
    # Decoding video streaming data 
    frame = cv2.imdecode(npdata,1)
    if tcp.get_record_status() == True:
        # Saving labeling data and steering angle 
        cv2.imwrite("C:\img\%s_%03d_%03d.png" % ("RC", index, tcp.get_servo_angle()), frame)
        index += 1
    cv2.imshow("RECEIVING VIDEO",frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        tcp.close_pygame_win()
        client_socket.close()
        record = False
        break
   
cv2.destroyAllWindows()
pygame.quit()


