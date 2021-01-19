import socket
import threading
import time
import numpy as np
import libh264decoder


class Tello:
    """Wrapper class to interact with the Tello drone."""

    def __init__(self, local_ip, local_port, imperial=False, command_timeout=.3, tello_ip='192.168.10.1',
                 tello_port=8889):
        """
        Binds to the local IP/port and puts the Tello into command mode.

        :param local_ip (str): Local IP address to bind.
        :param local_port (int): Local port to bind.
        :param imperial (bool): If True, speed is MPH and distance is feet.
                             If False, speed is KPH and distance is meters.
        :param command_timeout (int|float): Number of seconds to wait for a response to a command.
        :param tello_ip (str): Tello IP.
        :param tello_port (int): Tello port.
        """
        self.is_running = False
        self.preplan_pause = False
        self.abort_flag = False
        self.decoder = libh264decoder.H264Decoder()
        self.command_timeout = command_timeout
        self.imperial = imperial
        self.response = None
        self.frame = None  # numpy array BGR -- current camera output frame
        self.is_freeze = False  # freeze current camera output
        self.last_frame = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for sending cmd
        self.socket_video = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for receiving video stream
        self.tello_address = (tello_ip, tello_port)
        self.local_video_port = 11111  # port for receiving video stream
        self.last_height = 0
        self.socket.bind((local_ip, local_port))

        # thread for receiving cmd ack
        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = True

        self.receive_thread.start()

        # to receive video -- send cmd: command, streamon
        self.socket.sendto(b'command', self.tello_address)
        print('sent: command')
        self.socket.sendto(b'streamon', self.tello_address)
        print('sent: streamon')

        self.socket_video.bind((local_ip, self.local_video_port))

        # thread for receiving video
        self.receive_video_thread = threading.Thread(target=self._receive_video_thread)
        self.receive_video_thread.daemon = True

        self.receive_video_thread.start()

    def __del__(self):
        """Closes the local socket."""

        self.socket.close()
        self.socket_video.close()

    def read(self):
        """Return the last frame from camera."""
        if self.is_freeze:
            return self.last_frame
        else:
            return self.frame

    def video_freeze(self, is_freeze=True):
        """Pause video output -- set is_freeze to True"""
        self.is_freeze = is_freeze
        if is_freeze:
            self.last_frame = self.frame

    def _receive_thread(self):
        """Listen to responses from the Tello.

        Runs as a thread, sets self.response to whatever the Tello last returned.

        """
        while True:
            try:
                self.response, ip = self.socket.recvfrom(3000)
                # print(self.response)
            except socket.error as exc:
                print("Caught exception socket.error : %s" % exc)

    def _receive_video_thread(self):
        """
        Listens for video streaming (raw h264) from the Tello.

        Runs as a thread, sets self.frame to the most recent frame Tello captured.

        """
        packet_data = ""
        while True:
            try:
                res_string, ip = self.socket_video.recvfrom(2048)
                packet_data += res_string
                # end of frame
                if len(res_string) != 1460:
                    for frame in self._h264_decode(packet_data):
                        self.frame = frame
                    packet_data = ""

            except socket.error as exc:
                print("Caught exception socket.error : %s" % exc)

    def _h264_decode(self, packet_data):
        """
        decode raw h264 format data from Tello
        
        :param packet_data: raw h264 data array
       
        :return: a list of decoded frame
        """
        res_frame_list = []
        frames = self.decoder.decode(packet_data)
        for framedata in frames:
            (frame, w, h, ls) = framedata
            if frame is not None:
                # print 'frame size %i bytes, w %i, h %i, linesize %i' % (len(frame), w, h, ls)

                frame = np.fromstring(frame, dtype=np.ubyte, count=len(frame), sep='')
                frame = (frame.reshape((h, ls / 3, 3)))
                frame = frame[:, :w, :]
                res_frame_list.append(frame)

        return res_frame_list

    def send_command(self, command, delay):
        """
        Send a command to the Tello and wait for a response.

        :param command: Command to send.
        :return (str): Response from Tello.

        """

        print(">> send cmd: {}".format(command))
        self.abort_flag = False
        timer = threading.Timer(self.command_timeout, self.set_abort_flag)

        self.socket.sendto(command.encode('utf-8'), self.tello_address)

        timer.start()
        while self.response is None:
            if self.abort_flag is True:
                break
        timer.cancel()

        if self.response is None:
            response = 'none_response'
        else:
            response = self.response.decode('utf-8')

        self.response = None

        time.sleep(delay)

        return response

    def send_command_preplan(self, command, delay):
        """
        Send a command to the Tello and wait for a response.

        :param command: Command to send.
        :return (str): Response from Tello.

        """
        while self.preplan_pause is True:
            time.sleep(1)
        else:
            pass

        print(">> send cmd: {}".format(command))
        self.abort_flag = False
        timer = threading.Timer(self.command_timeout, self.set_abort_flag)

        self.socket.sendto(command.encode('utf-8'), self.tello_address)

        timer.start()
        while self.response is None:
            if self.abort_flag is True:
                break
        timer.cancel()

        if self.response is None:
            response = 'none_response'
        else:
            response = self.response.decode('utf-8')

        self.response = None

        time.sleep(delay)

        return response

    def set_abort_flag(self):
        """
        Sets self.abort_flag to True.

        Used by the timer in Tello.send_command() to indicate to that a response
        
        timeout has occurred.

        """

        self.abort_flag = True

    def takeoff(self):
        """
        Initiates take-off.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.send_command('takeoff', 0)

    def set_speed(self, speed):
        """
        Sets speed.

        This method expects KPH or MPH. The Tello API expects speeds from
        1 to 100 centimeters/second.

        Metric: .1 to 3.6 KPH
        Imperial: .1 to 2.2 MPH

        Args:
            speed (int|float): Speed.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        speed = float(speed)

        if self.imperial is True:
            speed = int(round(speed * 44.704))
        else:
            speed = int(round(speed * 27.7778))

        return self.send_command('speed %s' % speed, 0)

    def rotate_cw(self, degrees):
        """
        Rotates clockwise.

        Args:
            degrees (int): Degrees to rotate, 1 to 360.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.send_command('cw %s' % degrees, 0)

    def rotate_ccw(self, degrees):
        """
        Rotates counter-clockwise.

        Args:
            degrees (int): Degrees to rotate, 1 to 360.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """
        return self.send_command('ccw %s' % degrees, 0)

    def flip(self, direction):
        """
        Flips.

        Args:
            direction (str): Direction to flip, 'l', 'r', 'f', 'b'.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.send_command('flip %s' % direction, 0)

    def get_response(self):
        """
        Returns response of tello.

        Returns:
            int: response of tello.

        """
        response = self.response
        return response

    def get_height(self):
        """Returns height(dm) of tello.

        Returns:
            int: Height(dm) of tello.

        """
        height = self.send_command('height?', 0)
        height = str(height)
        height = filter(str.isdigit, height)
        try:
            height = int(height)
            self.last_height = height
        except:
            height = self.last_height
            pass
        return height

    def get_battery(self):
        """Returns percent battery life remaining.

        Returns:
            int: Percent battery life remaining.

        """

        battery = self.send_command('battery?', 0)

        try:
            battery = int(battery)
        except:
            pass

        return battery

    def get_flight_time(self):
        """Returns the number of seconds elapsed during flight.

        Returns:
            int: Seconds elapsed during flight.

        """

        flight_time = self.send_command('time?', 0)

        try:
            flight_time = int(flight_time)
        except:
            pass

        return flight_time

    def get_speed(self):
        """Returns the current speed.

        Returns:
            int: Current speed in KPH or MPH.

        """

        speed = self.send_command('speed?', 0)

        try:
            speed = float(speed)

            if self.imperial is True:
                speed = round((speed / 44.704), 1)
            else:
                speed = round((speed / 27.7778), 1)
        except:
            pass

        return speed

    def start_pre_plan(self):

        self.is_running = True

        while self.is_running == True:
            # Not sure if this will run or not in realtime, doctor's/arina's
            # example code would be the backup to replace this.

            # Travel to/from starting checkpoint 0 from/to the charging base
            frombase = ["forward", 50, "ccw", 150]
            tobase = ["ccw", 150, "forward", 50]

            # Flight path to Checkpoint 1 to 5 and back to Checkpoint 0 sequentially
            checkpoint = [[1, "cw", 90, "forward", 100], [2, "ccw", 90, "forward", 80], [3, "ccw", 90, "forward", 40],
                          [4, "ccw", 90, "forward", 40], [5, "cw", 90, "forward", 60], [0, "ccw", 90, "forward", 40]]

            # Put Tello into command mode

            Tello.send_command_preplan(self, "command", 3)

            # Send the takeoff command
            Tello.send_command_preplan(self, "takeoff", 3)

            print("\n")

            # Start at checkpoint 1 and print destination
            while self.preplan_pause is True:
                time.sleep(1)
            else:
                print("From the charging base to the starting checkpoint of sweep pattern.\n")

            Tello.send_command_preplan(self, frombase[0] + " " + str(frombase[1]), 4)
            Tello.send_command_preplan(self, frombase[2] + " " + str(frombase[3]), 4)

            while self.preplan_pause is True:
                time.sleep(1)
            else:
                print("Current location: Checkpoint 0 " + "\n")


            # Billy's flight path
            for i in range(len(checkpoint)):
                if i == len(checkpoint) - 1:
                    while self.preplan_pause is True:
                        time.sleep(1)
                    else:
                        print("Returning to Checkpoint 0. \n")

                Tello.send_command_preplan(self, checkpoint[i][1] + " " + str(checkpoint[i][2]), 4)
                Tello.send_command_preplan(self, checkpoint[i][3] + " " + str(checkpoint[i][4]), 4)

                while self.preplan_pause is True:
                    time.sleep(1)
                else:
                    print("Arrived at current location: Checkpoint " + str(checkpoint[i][0]) + "\n")

                time.sleep(4)

            # Reach back at Checkpoint 0
            while self.preplan_pause is True:
                time.sleep(1)
            else:
                print("Complete sweep. Return to charging base.\n")
            Tello.send_command_preplan(self, tobase[0] + " " + str(tobase[1]), 4)
            Tello.send_command_preplan(self, tobase[2] + " " + str(tobase[3]), 4)

            # Turn to original direction before land
            while self.preplan_pause is True:
                time.sleep(1)
            else:
                print("Turn to original direction before land.\n")
            Tello.send_command_preplan(self, "cw 180", 4)

            # Land
            Tello.send_command_preplan(self, "land", 3)
            print("Drone has successfully landed.\n")
            self.is_running = False
            # Close the socket
            # self.socket.close()

    def interruptDrone(self):
        """
        Interrupt drone from moving and enable user to move using keyboard
        """
        return self.send_command('interruptDrone', 0)

    def resumeDrone(self):
        """
        Resume drone operation based on the last location it stopped.
        Reversed the whole movement during interruption and start
        from the start of interruption.
        """
        self.preplan_pause = False
        print("Pre-plan route has been resumed!")
        return self.send_command('resumeDrone', 0)

    def emergency(self):
        """Stop all motors immediately.
        """
        return self.send_command('emergency', 0)

    def land(self):
        """Initiates landing.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.send_command('land', 0)

    def move(self, direction, distance):
        """Moves in a direction for a distance.

        This method expects meters or feet. The Tello API expects distances
        from 20 to 500 centimeters.

        Metric: .02 to 5 meters
        Imperial: .7 to 16.4 feet

        Args:
            direction (str): Direction to move, 'forward', 'back', 'right' or 'left'.
            distance (int|float): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        distance = float(distance)

        if self.imperial is True:
            distance = int(round(distance * 30.48))
        else:
            distance = int(round(distance * 100))

        return self.send_command('%s %s' % (direction, distance), 0)

    def move_backward(self, distance):
        """Moves backward for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.move('back', distance)

    def move_down(self, distance):
        """Moves down for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.move('down', distance)

    def move_forward(self, distance):
        """Moves forward for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """
        return self.move('forward', distance)

    def move_left(self, distance):
        """Moves left for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """
        return self.move('left', distance)

    def move_right(self, distance):
        """Moves right for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        """
        return self.move('right', distance)

    def move_up(self, distance):
        """Moves up for a distance.

        See comments for Tello.move().

        Args:
            distance (int): Distance to move.

        Returns:
            str: Response from Tello, 'OK' or 'FALSE'.

        """

        return self.move('up', distance)
