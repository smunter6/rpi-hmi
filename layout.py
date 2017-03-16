'''
Demo Layout for the Raspberry Pi Touchscreen HMI. This file is based on the example code provided by kivy.
This code is intended to be a proof of concept only.
'''

from time import time
from kivy.app import App
from os.path import dirname, join
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from pprint import pprint
from functools import partial
import gclib


class ShowcaseScreen(Screen):
    fullscreen = BooleanProperty(False)

    def add_widget(self, *args):
        if 'content' in self.ids:
            return self.ids.content.add_widget(*args)
        return super(ShowcaseScreen, self).add_widget(*args)

# The ShowcaseApp class is called at startup


class ShowcaseApp(App):
    current_title = StringProperty()
    current_title = 'Galil Motion Control'  # Set the title for the app
    time = NumericProperty(0)
    firstScreen = ObjectProperty()
    dmc = gclib.py()  # gclib object to communicate with Galil controllers
    controllerData = ""  # Store data returned by controller
    controllerConnected = 0

    # The build function is automatically called when the class is initialized.
    # This function will setup the UI update frequency and setup
    # the first screen
    def build(self):
        # Setup the UI to run clock update 30 times a second
        Clock.schedule_interval(self._update_clock, 1 / 30.)
        self.firstScreen = Builder.load_file(
            "accordian.kv")  # Setup the kv UI file at startup
        # Tell the UI to load the UI file
        self.root.ids.sm.switch_to(self.firstScreen)
        self.root.ids.avTitle.title = self.current_title + \
            ' - ' + self.dmc.GVersion()  # Update the title
        self.controllers = self.dmc.GAddresses()  # populate the controllers list
        self.populateControllers()  # Display available controllers to the UI

    # This function is called when a controller is selected on
    # the first page
    def selectController(self, value, *args):
        # Update the title to show the connected controller
        self.root.ids.avTitle.title = value + ' -d'
        print(value + ' -d')
        # Call GOpen with the IP Address selected
        self.dmc.GOpen(value.strip('()') + ' -d')
        # Open the Homing and Setup screen
        self.firstScreen.ids.homeSetup.collapse = False
        # Download initial settings
        self.dmc.GProgramDownload("""
#start
MO;         'Motor Off
'MT-2.5;    'Setup axis as stepper motor
SHA;        'Servo the motor
AC512000;   'Set Acceleration Rate
DC512000;   'Set Deceleration Rate
SPA=180000; 'Set Motor Speed
EN
        """)
        self.dmcCommand("XQ#start")  # Run the downloaded program

    # This function is executed when the slider is released.
    # It sends its position to the controller as a variable.
    # The program running on the controller will read that variable and perform the
    # Position Absolute move in Position Tracking mode.
    # This Position Tracking mode allows a new position to
    # be chosen before the previous one finishes.
    def sliderMove(self):
        if(self.controllerConnected == 1):
            self.dmcCommand(
                "PAA=" + str(int(self.firstScreen.ids['slider_PAA'].value)))

    # This function will perform error trapping on any GCommand calls.
    # It is intended to capture any gclib errors
    # and report the message to the title bar
    def dmcCommand(self, cmd):
        try:
            # Send command into the GCommand gclib API
            return self.dmc.GCommand(cmd)
        except gclib.GclibError as e:
            print(e)
            tc1 = ""
            # tc1 = self.dmc.GCommand('TC1')
            print(e, ': ' + cmd)
            # self.dmc.GClose()
            # Update title with error message
            self.root.ids.avTitle.title = str(e)
            # self.root.ids.sm.switch_to(self.firstScreen)
            raise  # allow the caller to handle the exception

    # This function will update the homing screen UI elements.
    # The function will ask for the Reported Position (RP) and Tell the state of the Switches (TS)
    # From this data the LED elements, text
    # elements and sliders can be updated.
    def updateHomingScreen(self):
        try:
            # Get Position and Switch info
            data = self.dmcCommand('MG{Z10.0} _RPA, _TSA')
            self.controllerData = data
            # Update the Position Text Element
            self.firstScreen.ids['TPA'].text = data.split()[0]
            # Update the Slider element
            self.firstScreen.ids['slider_TPA'].value = int(data.split()[0])
            # extract bit index 7 in _TSA that tells if the axis is moving
            if(int(data.split()[1]) & 128):
                self.firstScreen.ids['_BGA'].text = 'Axis Moving'
            else:
                self.firstScreen.ids['_BGA'].text = 'Idle'
            # extract bit index 2 in _TSA for the Reverse Limit Switch status
            if(int(data.split()[1]) & 4):
                self.firstScreen.ids['_RLA'].active = False
            else:
                self.firstScreen.ids['_RLA'].active = True
            # extract bit index 3 in _TSA for the Forward Limit Switch status
            if(int(data.split()[1]) & 8):
                self.firstScreen.ids['_FLA'].active = False
            else:
                self.firstScreen.ids['_FLA'].active = True
            # extract bit index 5 in _TSA for the Motor Off status
            if(int(data.split()[1]) & 32):
                self.firstScreen.ids['_MOA'].active = True
            else:
                self.firstScreen.ids['_MOA'].active = False
        except:
            #print(e)
            # do nothing

    # This function will update the Cut-to-length screen UI elements.
    # The function will ask for the Reported Position (RP) and a
    # variable called i
    def updateCutScreen(self):
        try:
            # Get Position and variable info
            data = self.dmcCommand('MG{Z10.0} _RPA, i')
            # Update the Position Text Element
            self.firstScreen.ids['cutPosition'].text = data.split()[0]
            # Update the Slider element
            self.firstScreen.ids['cutPositionSlider'].value = int(data.split()[
                                                                  0])
            # Update the counter element
            self.firstScreen.ids['currentCut'].text = data.split()[1]
            if(int(data.split()[1]) >= int(self.firstScreen.ids['numCuts'].text)):
                self.controllerConnected = 2
                self.firstScreen.ids['currentStatus'].text = "Completed."
        except:
            #print(e)
            # do nothing

    # This function will populate the UI with available controllers on the
    # network
    def populateControllers(self, *args):

        # the gclib API call will return all controllers with IP addresses
        self.controllers = self.dmc.GAddresses()
        if(len(self.controllers)):
            for key, value in self.controllers.items():
                print(" ", key, " \t| ", value)
                btn1 = Button(height=100,
                              text=value.split('Rev')[0],
                              background_color=[.6, 1.434, 2.151, 1],)
                # If controller is selected then pass info to the
                # selectController function
                btn1.bind(on_press=partial(self.selectController, key))

                box1 = BoxLayout(id=key, orientation='horizontal',
                                padding=[10, 10, 10, 10], height=100)
                box1.add_widget(btn1)
                box1.add_widget(Label(text=key))
                try:
                    box1.add_widget(Label(text='Rev' + value.split('Rev')[1]))
                except:
                    box1.add_widget(Label(text='Special'))
                self.firstScreen.ids['controllerBox'].add_widget(box1)
        else:
            self.firstScreen.ids['controllerBox'].add_widget(Label(
                height=100,
                size_hint=(.33, .15),
                text='No Controllers Found',
                font_size=14))
            btn2=Button(height = 100,
                          size_hint = (.33, .15),
                          text = 'Refresh',
                          background_color = [.6, 1.434, 2.151, 1],)
            btn2.bind(on_press = partial(self.populateControllers))
            self.firstScreen.ids['controllerBox'].add_widget(btn2)

    # This function is called when the cut-to-length application is started
    # It will download a simple proof of concept cut-to-length application code
    # that cycles the motor back and forth and toggles IO at the start and end
    # of the move
    def startCutToLength(self):
        self.dmc.GProgramDownload("""
j=10;len=12000
#cut
WT1000
i=0
PTA=0
SHA
PA0
BGA
AMA
#loop
'SB1
WT200
PAA=len
BGA
AMA
'CB1
WT200
PAA=0
BGA
AMA
i=i+1
JP#loop, i<j
        EN""")
        self.dmc.GSleep(100)
        # Set the number of cuts var on the controller
        self.dmcCommand('j=' + self.firstScreen.ids['numCuts'].text)
        # Set the length of cut var on the controller
        self.dmcCommand('len=' + self.firstScreen.ids['cutLen'].text)
        # run the downloaded program
        self.dmcCommand("XQ#cut")
        # update the var to tell the HMI which program is running on the
        # controller
        self.controllerConnected=2
        # Update the status text
        self.firstScreen.ids['currentStatus'].text="Running..."

    # This function is to stop the cut-to-length application
    def stopCutToLength(self):
        print('stop')
        self.dmcCommand("ST")
        self.firstScreen.ids['currentStatus'].text="Stopped"

    def startHomingandSetup(self):
        self.dmcCommand('PTA=1')
        self.controllerConnected=1

    # This is a simple function to increment or decrement the number of cuts
    # function is called from the accordian.kv UI file
    def addToCuts(self, count):
        value=int(self.firstScreen.ids['numCuts'].text) + count
        self.firstScreen.ids['numCuts'].text=str(value)

    # This function is called at 30Hz.
    # It will call the functions to update the selected screen
    def _update_clock(self, dt):
        self.time=time()
        if(self.firstScreen.ids.homeSetup.collapse == False):
            self.updateHomingScreen()
        if(self.firstScreen.ids.cutToLength.collapse == False):
            self.updateCutScreen()


if __name__ == '__main__':
    ShowcaseApp().run()
