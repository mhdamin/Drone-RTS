import PySimpleGUI as sg

"""
  Simple Form
  Use this design pattern to show a form one time to a user that is "submitted"
"""

def edit_connection():

    layout = [
          [sg.Text('IP Address of Tello', size=(20, 1)), sg.InputText(key='-IP_DRONE-')],
          [sg.Text('Port of Tello', size=(20, 1)), sg.InputText(key='-PORT_DRONE-')],
          [sg.Text('IP Address of Local PC', size=(20, 1)), sg.InputText(key='-IP_PC-')],
          [sg.Text('Port of Local PC', size=(20, 1)), sg.InputText(key='-PORT_PC-')],
          [sg.Button('Submit'), sg.Button('Cancel')]]

    window = sg.Window('Edit Connection Setup', layout)
    event, values = window.read(close=True)

    if event == 'Submit':
        print('Drone IP:', values['-IP_DRONE-'], '\nDrone PORT:', values['-PORT_DRONE-'], '\nPC IP:', values['-IP_PC-'], '\nPC PORT:', values['-PORT_PC-'])
    else:
        print('User cancelled')

edit_connection()