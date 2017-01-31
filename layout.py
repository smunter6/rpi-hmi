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

#The ShowcaseApp class is called at startup
class ShowcaseApp(App):
    current_title = StringProperty()
    current_title = 'Galil Motion Control'#Set the title for the app
    time = NumericProperty(0)
    firstScreen = ObjectProperty()
    dmc=gclib.py()#gclib object to communicate with Galil controllers
    controllerData = ""#Store data returned by controller
    controllerConnected = 0

    #The build function is automatically called when the class is initialized.
    #This function will setup the UI update frequency and setup the first screen
    def build(self):
        Clock.schedule_interval(self._update_clock, 1 / 10.)#Setup the UI to run clock update 10 times a second
        self.firstScreen = Builder.load_file("accordian.kv")#Setup the kv UI file at startup
        self.root.ids.sm.switch_to(self.firstScreen)#Tell the UI to load the UI file
        self.root.ids.avTitle.title = self.current_title +' - ' + self.dmc.GVersion()#Update the title
        self.controllers=self.dmc.GAddresses()#populate the controllers list
        self.populateControllers()#Display available controllers to the UI
    
    #This function is called when a controller is selected on the first page
    def selectController(self, value, *args):
        self.firstScreen.ids.homeSetup.collapse = False#Open the Homing and Setup screen
        self.root.ids.avTitle.title = value + ' -d'#Update the title to show the connected controller
        print(value +' -d')
        self.dmc.GOpen(value.strip('()') +' -d')#Call GOpen with the IP Address selected
        self.controllerConnected = 1
        #Download slider program
        self.dmc.GProgramDownload("""
#slider
MO;         'Motor Off
'MT-2.5;    'Setup axis as stepper motor
SHA;        'Servo the motor
AC512000;   'Set Acceleration Rate
DC512000;   'Set Deceleration Rate
SPA=180000; 'Set Motor Speed
pa=_RPA;    'Record current position
PTA=1;      'Setup Position Tracking Mode
#loop;      'Start of loop
PAA=pa;     'Update absolute position based on variable sent from HMI
WT100;      'Setup 100ms scan loop
JP#loop;    'Jump to loop
EN
""")
        self.dmcCommand("XQ#slider")#Run the downloaded program

    #This function is executed when the slider is released. 
    #It sends its position to the controller as a variable. 
    #The program running on the controller will read that variable and perform the 
    #Position Absolute move in Position Tracking mode. 
    #This Position Tracking mode allows a new position to be chosen before the previous one finishes.
    def sliderMove(self):
        if(self.controllerConnected == 1):
            self.dmcCommand("pa="+str(int(self.firstScreen.ids['slider_PAA'].value)))

    #This function will perform error trapping on any GCommand calls.
    #It is intended to capture any gclib errors and report the message to the title bar
    def dmcCommand(self, cmd):
        try:
            rc = self.dmc.GCommand(cmd)#Send command into the GCommand gclib API
        except Exception as e:
            print (e)
            tc1 = self.dmc.GCommand('TC1')
            print (tc1)
            self.root.ids.avTitle.title = tc1#Update title with error message

    #This function will update the homing screen UI elements.
    #The function will ask for the Reported Position (RP) and Tell the state of the Switches (TS)
    #From this data the LED elements, text elements and sliders can be updated.
    def updateHomingScreen(self):
        data = self.dmc.GCommand('MG{Z10.0} _RPA, _TSA')#Get Position and Switch info
        self.controllerData = data
        self.firstScreen.ids['TPA'].text = data.split()[0]#Update the Position Text Element
        self.firstScreen.ids['slider_TPA'].value = int(data.split()[0])#Update the Slider element
        if(int(data.split()[1])&128):#extract bit index 7 in _TSA that tells if the axis is moving
            self.firstScreen.ids['_BGA'].text = 'Axis Moving'
        else:
            self.firstScreen.ids['_BGA'].text = 'Idle'
        if(int(data.split()[1])&4):#extract bit index 2 in _TSA for the Reverse Limit Switch status
            self.firstScreen.ids['_RLA'].active = False
        else:
            self.firstScreen.ids['_RLA'].active = True
        if(int(data.split()[1])&8):#extract bit index 3 in _TSA for the Forward Limit Switch status
            self.firstScreen.ids['_FLA'].active = False
        else:
            self.firstScreen.ids['_FLA'].active = True
        if(int(data.split()[1])&32):#extract bit index 5 in _TSA for the Motor Off status
            self.firstScreen.ids['_MOA'].active = True
        else:
            self.firstScreen.ids['_MOA'].active = False

    #This function will update the Cut-to-length screen UI elements.
    #The function will ask for the Reported Position (RP) and a variable called i
    def updateCutScreen(self):
        data = self.dmc.GCommand('MG{Z10.0} _RPA, i')#Get Position and variable info
        self.firstScreen.ids['cutPosition'].text = data.split()[0]#Update the Position Text Element
        self.firstScreen.ids['cutPositionSlider'].value = int(data.split()[0])#Update the Slider element
        self.firstScreen.ids['currentCut'].text = data.split()[1]#Update the counter element
        if(int(data.split()[1])>= int(self.firstScreen.ids['numCuts'].text)):
            self.controllerConnected = 2
            self.firstScreen.ids['currentStatus'].text = "Completed."

    #This function will populate the UI is available controllers on the network
    def populateControllers(self, *args):
        self.firstScreen.ids['row1'].clear_widgets()
        self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='[b]Click to Select Controller[/b]',
                                                      markup= True,
                                                      font_size= 14))
        self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='[b]Address[/b]',
                                                      markup= True,
                                                      font_size= 14))
        self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='[b]Revision[/b]',
                                                      markup= True,
                                                      font_size= 14))
        self.controllers=self.dmc.GAddresses()#the gclib API call will return all controllers with IP addresses
        if(len(self.controllers)):
            for key, value in self.controllers.items():
                print (" ", key, " \t| ", value)
                btn1 = Button(  height= 100, 
                                  size_hint=(.33, .15),
                                  text=value.split('Rev')[0],
                                  background_color= [.6, 1.434, 2.151, 1],
                                  )
                btn1.bind(on_press=partial(self.selectController, key))#If controller is selected then pass info to the selectController function

                self.firstScreen.ids['row1'].add_widget(btn1)
                self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text=key))
                try:
                    self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='Rev'+value.split('Rev')[1]))
                except:
                    self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='Special'))
        else:
            self.firstScreen.ids['row1'].add_widget(Label(height= 100, 
                                                      size_hint=(.33, .15),
                                                      text='No Contollers Found',
                                                      font_size= 14))
            btn2 = Button(  height= 100, 
                            size_hint=(.33, .15),
                            text='Refresh',
                            background_color= [.6, 1.434, 2.151, 1],
                            )
            btn2.bind(on_press=partial(self.populateControllers))
            self.firstScreen.ids['row1'].add_widget(btn2)


    #This function is called when the cut-to-length application is started
    #It will download a simple proof of concept cut-to-length application code the cycles the motor
    #back and forth and toggles IO at that start and end of the move.
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
SB1
WT200
PAA=len
BGA
AMA
CB1
WT200
PAA=0
BGA
AMA
i=i+1
JP#loop, i<j
EN""")
        self.dmc.GSleep(100)
        self.dmcCommand('j='+self.firstScreen.ids['numCuts'].text)#Set the number of cuts variable on the controller
        self.dmcCommand('len='+self.firstScreen.ids['cutLen'].text)#Set the length of cut variable on the controller
        #rc = self.dmc.GCommand("XQ#cut")
        self.dmcCommand("XQ#cut")#Run the downloaded program
        self.controllerConnected = 2#update the variable to tell the UI which screen to update
        self.firstScreen.ids['currentStatus'].text = "Running..."#Update the status text

    #This function is to stop the cut-to-length application
    #TODO: Send the ST command to the controller to stop the application
    def stopCutToLength(self):
        print ('stop')
        self.firstScreen.ids['currentStatus'].text = "Stopped"

    #This is a simple function to increment or decrement the number of cuts
    #function is called from the accordian.kv UI file
    def addToCuts(self, count):
        value = int(self.firstScreen.ids['numCuts'].text) + count
        self.firstScreen.ids['numCuts'].text = str(value)
        
    #This function is called at 10Hz.
    #It will call the functions to update the selected screen 
    def _update_clock(self, dt):
        self.time = time()
        if(self.controllerConnected == 1):
            self.updateHomingScreen()
        elif(self.controllerConnected == 2):
            self.updateCutScreen()
            

if __name__ == '__main__':
    ShowcaseApp().run()
