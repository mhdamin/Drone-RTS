# This code is adopted from https://learn.droneblocks.io/p/tello-drone-programming-with-python/
# Import the necessary modules
import socket
import threading
import time
import PySimpleGUI as sg

class Tello():


    def __init__(self):
        IP_DRONE = '192.168.0.1'
        PORT_DRONE = 8889
        IP_PC = ''
        PORT_PC = 9000

        # IP and port of Tello
        self.tello_address = (IP_DRONE, PORT_DRONE)

        # IP and port of local computer
        self.local_address = (IP_PC, PORT_PC)

        # Create a UDP connection that we'll send the command to
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the local address and port
        self.sock.bind(self.local_address)

        # Create and start a listening thread that runs in the background
        # This utilizes our receive functions and will continuously monitor for incoming messages
        self.receiveThread = threading.Thread(target=self.receive)
        self.receiveThread.daemon = True
        self.receiveThread.start()

    # Send the message to Tello and allow for a delay in seconds
    def send(self, message, delay):
        # Try to send the message otherwise print the exception
        try:
            self.sock.sendto(message.encode(), self.tello_address)
            print("Sending message: " + message)
        except Exception as e:
            print("Error sending: " + str(e))

        # Delay for a user-defined period of time
        time.sleep(delay)

    # Receive the message from Tello
    def receive(self):
        # Continuously loop and listen for incoming messages
        while True:
            # Try to receive the message otherwise print the exception
            try:
                response, ip_address = self.sock.recvfrom(128)
                print("Received message: " + response.decode(encoding='utf-8'))
            except Exception as e:
                # If there's an error close the socket and break out of the loop
                self.sock.close()
                print("Error receiving: " + str(e))
            break

    def edit_connection(self):

        layout = [
            [sg.Text('IP Address of Tello', size=(20, 1)), sg.InputText(key='-IP_DRONE-')],
            [sg.Text('Port of Tello', size=(20, 1)), sg.InputText(key='-PORT_DRONE-')],
            [sg.Text('IP Address of Local PC', size=(20, 1)), sg.InputText(key='-IP_PC-')],
            [sg.Text('Port of Local PC', size=(20, 1)), sg.InputText(key='-PORT_PC-')],
            [sg.Button('Submit'), sg.Button('Cancel')]]

        window = sg.Window('Edit Connection Setup', layout)
        event, values = window.read(close=True)

        if event == 'Submit':
            print('Drone IP:', values['-IP_DRONE-'], '\nDrone PORT:', values['-PORT_DRONE-'], '\nPC IP:',
                  values['-IP_PC-'], '\nPC PORT:', values['-PORT_PC-'])
        else:
            print('User cancelled')

    edit_connection()


