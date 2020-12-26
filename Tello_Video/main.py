import tello
from tello_control_ui import TelloUI


def main():
    drone = tello.Tello('', 8889)
    vplayer = TelloUI(drone, "./img/")

    # start the Tkinter mainloop
    vplayer.root.geometry("350x250+300+300")
    vplayer.root.mainloop()


if __name__ == "__main__":
    main()
