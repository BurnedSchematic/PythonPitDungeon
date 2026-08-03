import pygame
import os
import paho.mqtt.client as mqtt
import random
import urllib.request
import threading
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox

pygame.init()#initialise graphics library
root = tk.Tk()
root.withdraw()

screen = pygame.display.set_mode((960,540))#set screen size to 1920x1080
clock = pygame.time.Clock()
global font
font = pygame.font.Font()
running = True

def do_nothing():
    pass

#define a button
class button():
    #create button by screen, text, function it performs, size, position, and various colors
    def __init__(self, screen, text, func = do_nothing, width = 200, height = 100, position = (None,None), textcolor = "black", buttoncolor = "white", highlightedcolor = "gray", pressedcolor = "darkgray", func_args = (), func_kwargs = None):
        if position[0] is None or position[1] is None:
            position = (screen.get_width()/2, screen.get_height()/2)
        self.screen = screen
        self.text = text
        self.func = func
        self.position = position
        self.textcolor = textcolor
        self.buttoncolor = buttoncolor
        self.highlightedcolor = highlightedcolor
        self.pressedcolor = pressedcolor
        self.width = width
        self.height = height
        self.rect = pygame.Rect(position[0]-width/2, position[1]-height/2, width, height)
        self.held = False
        self.func_args = func_args
        self.func_kwargs = func_kwargs if func_kwargs is not None else {}

    #show the button on screen
    def show(self, color = None):
        #if color wasn't set, use normal buttoncolor
        if color is None:
            color = self.buttoncolor
        #draw button
        pygame.draw.rect(self.screen, color, self.rect)
        #draw text on button
        textimg = pygame.font.Font(size=int(min([self.width,self.height])/2-len(self.text))).render(self.text,False,self.textcolor)
        screen.blit(textimg, (self.position[0]-textimg.get_width()/2, self.position[1]-textimg.get_height()/2))
    #check if pressed, do highlight and click colors, and perform function
    def getPressed(self):
        #if screen is focused, and mouse is hovering over the button
        if pygame.mouse.get_focused() and pygame.mouse.get_pos()[0] < self.position[0]+self.width/2 and pygame.mouse.get_pos()[0] > self.position[0]-self.width/2 and pygame.mouse.get_pos()[1] < self.position[1]+self.height/2 and pygame.mouse.get_pos()[1] > self.position[1]-self.height/2:
            #if the button is pressed, change to pressedcolor
            if pygame.mouse.get_pressed(num_buttons = 3)[0]:
                self.show(self.pressedcolor)
                self.held = True
            #if mouse is lifted, perform function
            elif self.held:
                self.func(*self.func_args, **self.func_kwargs)
                self.held = False
            #if button is not pressed, just change color to show hovering
            else:
                self.show(self.highlightedcolor)
        else:
            self.held = False
    def simulate(self):
        self.show()
        self.getPressed()
class sprite():
    def __init__(self, screen, imagepath, width = 100, height = 100, position = (None, None)):
        if position[0] is None or position[1] is None:
            position = (screen.get_width()/2, screen.get_height()/2)
        self.screen = screen
        self.imagepath = imagepath
        self.width = width
        self.height = height
        self.position = position
        self.rect = pygame.Rect(position[0]-width/2, position[1]-height/2, width, height)
        self.img = pygame.image.load(self.imagepath).convert_alpha()
    def show(self):
        self.img = pygame.transform.scale(self.img, (self.width, self.height))
        self.screen.blit(self.img, self.rect)
    def reloadImage(self):
        self.img = pygame.image.load(self.imagepath).convert_alpha()
class player():
    def __init__(self, screen, imagepath, width = 100, height = 100, position = (None, None), rotation = 0, owner:str = "localhost"):
        if position[0] is None or position[1] is None:
            position = (screen.get_width()/2, screen.get_height()/2)
        if owner == "localhost":
            global public_ip
            owner = public_ip
        self.owner = owner
        self.screen = screen
        self.imagepath = imagepath
        self.width = width
        self.height = height
        self.position = position
        self.rotation = rotation
        self.img = pygame.image.load(self.imagepath).convert_alpha()
        self.rect = pygame.Rect(position[0]-width/2, position[1]-height/2, width, height)
    def show(self):
        self.rect = pygame.Rect(self.position[0]-self.width/2, self.position[1]-self.height/2, self.width, self.height)
        image = pygame.transform.scale(self.img, (self.width, self.height))
        image = pygame.transform.rotate(image, self.rotation)
        self.screen.blit(image, self.rect)
    def drag(self):
        global draggingSprite
        if self.rect.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed(num_buttons = 3)[0] and (draggingSprite == None or draggingSprite == self):
            self.position = pygame.mouse.get_pos()
            draggingSprite = self
        if draggingSprite == self and not pygame.mouse.get_pressed(num_buttons=3)[0]:
            draggingSprite = None
    def reloadImage(self):
        self.img = pygame.image.load(self.imagepath).convert_alpha()
    def simulate(self):
        self.drag()
        self.show()
class text():
    def __init__(self, screen, text, textcolor = "white", width = 200, height = 100, position = (None,None), size = None):
        if position[0] is None or position[1] is None:
            position = (screen.get_width()/2, screen.get_height()/2)
        if size is None:
            size=int(min([width,height])/2-len(text))
        self.screen = screen
        self.text = text
        self.textcolor = textcolor
        self.width = width
        self.height = height
        self.position = position
        self.size = size
        self.rect = pygame.Rect(position[0]-width/2, position[1]-height/2, width, height)
    def show(self):
        textimg = pygame.font.Font(size=self.size).render(self.text,False,self.textcolor)
        screen.blit(textimg, (self.position[0]-textimg.get_width()/2, self.position[1]-textimg.get_height()/2))
class tilemap():
    def __init__(self, screen, resolution = (500,500), columns = 10, rows = 10, bottom = None, left = None):
        if bottom is None:
            bottom = screen.get_height()-(resolution[1]/rows)/2
        if left is None:
            left = (resolution[0]/columns)/2
        
        self.screen = screen
        self.resolution = resolution
        self.width = resolution[0]
        self.height = resolution[1]
        self.tiles = [sprite(screen, "whitePanel.png", resolution[0]/columns, resolution[1]/rows, (left+x*resolution[0]/columns,bottom-y*resolution[1]/rows)) for x in range(columns) for y in range(rows)]
        self.bottom = bottom
        self.left = left
        self.columns = columns
        self.rows = rows
        self.position = (left+resolution[0]/2,bottom-resolution[1]/2)
        self.rect = pygame.Rect(left, bottom-self.height, self.width, self.height)
    def show(self):
        for tile in self.tiles[::-1]:
            tile.show()
    def addTile(self, x, y):
        global drawingelementtype
        if pygame.Rect(x,y,1,1).collidelist(self.tiles) != -1:
            tile = self.tiles[pygame.Rect(x,y,1,1).collidelist([t.rect for t in self.tiles])]
            self.tiles[pygame.Rect(x,y,1,1).collidelist(self.tiles)] = sprite(self.screen, drawingelementtype, tile.width, tile.height, tile.position)
    def loadMap(self, filepath = None):
        if filepath is None:
            filepath = simpledialog.askstring("Enter Map Name", "Enter Map File Name:")
        if filepath[-4:] != ".dat":
            filepath += ".dat"
        try:
            file = open(filepath)
            i = -1
            for path in file.read().split("\n"):
                if i == -1:
                    self.rows,self.columns = [int(x) for x in path.split(",")]
                    self.tiles = [sprite(screen, "whitePanel.png", self.resolution[0]/self.columns, self.resolution[1]/self.rows, (self.left+x*self.resolution[0]/self.columns,self.bottom-y*self.resolution[1]/self.rows)) for x in range(self.columns) for y in range(self.rows)]
                else:
                    self.tiles[i].imagepath = path
                    self.tiles[i].reloadImage()
                i+=1
            file.close()
        except FileNotFoundError:
            messagebox.showerror("File Not Found", "Please choose a real map file")
    def reinit(self):
        self.tiles = [sprite(screen, "whitePanel.png", self.resolution[0]/self.columns, self.resolution[1]/self.rows, (self.left+x*self.resolution[0]/self.columns,self.bottom-y*self.resolution[1]/self.rows)) for x in range(self.columns) for y in range(self.rows)]
        
class scene():
    def __init__(self, screen, elements = [], backgroundcolor = "black"):
        self.screen = screen
        self.backgroundcolor = backgroundcolor
        self.elements = elements
        self.numelements = len(elements)
    def show(self):
        if len(self.elements) > self.numelements:
            self.elements.sort(key=lambda x:(x.position[1]+x.height/2))
            tlmp = next((x for x in scenes[sceneindex].elements if isinstance(x, tilemap)), None)
            if tlmp is not None:
                self.elements.remove(tlmp)
                self.elements.insert(0,tlmp)
        self.screen.fill(self.backgroundcolor)
        for element in self.elements:
            try:
                element.simulate()
            except:
                element.show()

#button functions
global TileInput, SpriteInput, server, public_ip
public_ip = str(urllib.request.urlopen('https://ident.me').read().decode('utf8'))
brokerAddress = "test.mosquitto.org"
server = str(random.randint(0,99999999))
topic = f'pythonpitdungeon/game/{server}'
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
TileInput = ""
SpriteInput = "KnightIcon.png"

def on_message(client, userdata, message):
    global scenes
    global sceneindex
    message = message.payload.decode("utf-8")
    if sceneindex == 1:#DM screen
        if message == 'Need_Player_Icon' or message == "Accepted":
            pass
        else:
            message = message.split(":")
            if message[1][-4:] == ".png":
                try:
                    scenes[sceneindex].elements.append(player(screen, message[1], owner=message[0]))
                except FileNotFoundError:
                    client.publish(topic, f"Need_Player_File:{message[0]}")
            elif len(message[1].split("=")) > 1:
                msg = message[1].split("=")
                name = msg[0]
                with open(name, "w") as file:
                    file.write(msg[1])
                scenes[sceneindex].elements.append(player(screen, name, owner=message[0]))
            foundPlayer = False
            for element in scenes[sceneindex].elements:
                if isinstance(element,player) and element.owner == message[0]:
                    if message[1] == "up":
                        element.position = (element.position[0],element.position[1]-10)
                    if message[1] == "right":
                        element.position = (element.position[0]+10,element.position[1])
                    if message[1] == "down":
                        element.position = (element.position[0],element.position[1]+10)
                    if message[1] == "left":
                        element.position = (element.position[0]-10,element.position[1])
                    client.publish(topic, "Accepted")
                    foundPlayer = True
                    break
            if not foundPlayer:
                client.publish(topic, f"Need_Player_Icon:{message[0]}")
    elif sceneindex == 2:#player screen
        if message == f"Need_Player_Icon:{public_ip}":
            for element in scenes[sceneindex].elements:
                if isinstance(element,player):
                    client.publish(topic, f'{public_ip}:{element.imagepath}')
                    break
        elif message == f"Need_Player_File:{public_ip}":
            for element in scenes[sceneindex].elements:
                if isinstance(element,player):
                    client.publish(topic, f'{public_ip}:{element.imagepath}={open(element.imagepath, "rb").read()}')
client.on_message = on_message
def askTileInput(title = "Enter file name"):
    global TileInput
    TileInput = simpledialog.askstring(title, title+":")
    if '.' not in TileInput:
        TileInput += ".png"
    if not os.path.isfile(TileInput):
        messagebox.showerror("File Not Found", "File Not Found.\nPlease enter a .png file in the current directory.")
        TileInput = ""
def askSpriteInput(title = "Enter file name"):
    global SpriteInput
    global scenes
    global sceneindex
    SpriteInput = simpledialog.askstring(title, title+":")
    if '.' not in SpriteInput:
        SpriteInput += ".png"
    if not os.path.isfile(SpriteInput) and SpriteInput[-3:] == "png":
        messagebox.showerror("File Not Found", "File Not Found.\nPlease enter a .png file in the current directory.")
        SpriteInput = "KnightIcon.png"
    if sceneindex == 2:
        for element in scenes[sceneindex].elements:
            if isinstance(element,player):
                element.imagepath=SpriteInput
                element.reloadImage()
                client.publish(topic, f'{public_ip}:{element.imagepath}')
def increment_scene(num = 1):
    global sceneindex
    global scenes
    if(sceneindex < len(scenes)-num):
        sceneindex+=num
def decrement_scene(num = 1):
    global sceneindex
    global client
    if(sceneindex > num-1):
        sceneindex -= num
    client.loop_stop()
    client.disconnect()
def changeSpritetype(filepath):
    global drawingelementtype
    global drawtype
    drawtype = "sprite"
    drawingelementtype = filepath
def changeTiletype(filepath):
    global drawingelementtype
    global drawtype
    drawtype = "tile"
    drawingelementtype = filepath
def saveMap(map:tilemap):
    file = open(simpledialog.askstring("Name your map", "Save map as:")+".dat","w")
    file.write(f'{map.rows},{map.columns}')
    for tile in map.tiles:
        file.write("\n"+tile.imagepath)
    file.close()
def emptydrawtype():
    global drawtype
    drawtype = "none"
def sendCommand(command:str):
    global scenes
    global sceneindex
    global public_ip
    global client
    client.publish(topic, f'{public_ip}:{command}')
def connectToServer(texttochange:text = text(pygame.Surface((1,1)),"")):
    global server
    global client
    global topic
    server = simpledialog.askstring("Connect", "Enter DM's Game Code")
    texttochange.text=server
    topic = f'pythonpitdungeon/game/{server}'
    client.connect(brokerAddress, 1883, 60)
    client.subscribe(topic)
    client.loop_start()
    '''
    networking_thread = threading.Thread(target=client.loop_forever)
    networking_thread.start()
    '''
def hostGame():
    global scenes
    global sceneindex
    global screen
    global client
    client.connect(brokerAddress, 1883, 60)

    client.subscribe(topic)
    networking_thread = threading.Thread(target=client.loop_forever)
    networking_thread.start()
map = tilemap(screen, (550,500), 11)
serverconnecttextplayer = text(screen, server, position = (screen.get_width()/2,50))
def shrinkMap():
    global map
    map.columns += 1
    map.rows += 1
    map.reinit()
def growMap():
    global map
    map.columns -= 1
    map.rows -= 1
    map.reinit()
scenes = [scene(screen, [#Main menu (index 0)
        button(screen, "DM", increment_scene, position=(int(screen.get_width()/3), int(screen.get_height()/2))),
        button(screen, "Player", increment_scene, func_args=(2,), position=(int((2*screen.get_width())/3),int(screen.get_height()/2)))
        ]),
            scene(screen, [#DM screen (index 1)
        text(screen,server,position=(screen.get_width()/2,25)),
        button(screen, "Import Tile", askTileInput, position=(screen.get_width()-100,50)),
        button(screen, "Import Token", askSpriteInput, position=(screen.get_width()-300,50)),
        button(screen, "Back", decrement_scene, 100, 50, (50,25)),
        button(screen, "Save Map", saveMap, 100, 50, (150,25), func_args=(map,)),
        button(screen, "Load Map", map.loadMap, 100, 50, (250,25)),
        button(screen, "Cursor(shift)", emptydrawtype, 100, 50, (350,25)),
        button(screen,"Host Game", hostGame, 100, 50, (screen.get_width()-50,screen.get_height()-25)),
        button(screen, "-", shrinkMap, 50, 50, (screen.get_width()-126,screen.get_height()-25)),
        button(screen, "+", growMap, 50, 50, (screen.get_width()-177,screen.get_height()-25)),
        map
        ]),
            scene(screen, [#player screen (index 2)
        button(screen, "Back", decrement_scene, 100, 50, (50,25), func_args=(2,)),
        button(screen, "^", sendCommand, 100, position = (screen.get_width()/2,screen.get_height()/3),func_args=("up",)),
        button(screen, ">", sendCommand, 100, position = ((screen.get_width()*2)/3,screen.get_height()/2),func_args=("right",)),
        button(screen, "v", sendCommand, 100, position = (screen.get_width()/2,(screen.get_height()*2)/3),func_args=("down",)),
        button(screen, "<", sendCommand, 100, position = (screen.get_width()/3,screen.get_height()/2),func_args=("left",)),
        player(screen, SpriteInput),
        button(screen, "Change Icon", askSpriteInput, 100, 50, (150,25)),
        serverconnecttextplayer,
        button(screen, "Connect",connectToServer,100,50,(screen.get_width()-50,25),func_args=(serverconnecttextplayer,))
        ])
        ]
sceneindex = 0

imports = []
drawingelementtype = "whitePanel.png"

th = 150
sh = 150
tilebuttonheight = 100
tilebuttonwidth = 100
drawtype = "none"
spritepressed = False
draggingSprite = None

while running:
    #Check if window is closed
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEWHEEL:
            for element in scenes[sceneindex].elements:
                if isinstance(element,player):
                    if element.rect.collidepoint(pygame.mouse.get_pos()):
                        if pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]:
                            element.rotation += event.y
                        else:
                            element.width += event.y
                            element.height += event.y
                            element.rotation += event.x
    #wipe everything
    screen.fill("black")
    scenes[sceneindex].show()
    if sceneindex == 1:
        if TileInput not in imports and TileInput != "":
            imports.append(TileInput)
            scenes[sceneindex].elements.append(sprite(screen,TileInput,height=tilebuttonheight,width=tilebuttonheight,position=(screen.get_width()-tilebuttonheight/2, th)))
            scenes[sceneindex].elements.append(button(screen, TileInput[:-4],changeTiletype,height=tilebuttonheight,width=tilebuttonwidth,position=(screen.get_width()-tilebuttonheight-tilebuttonwidth/2,th),func_args = (TileInput,)))
            th += tilebuttonheight
        if SpriteInput not in imports:
            imports.append(SpriteInput)
            scenes[sceneindex].elements.append(sprite(screen,SpriteInput,height=tilebuttonheight,width=tilebuttonheight,position=(screen.get_width()-tilebuttonwidth*2-tilebuttonheight/2, sh)))
            scenes[sceneindex].elements.append(button(screen, SpriteInput[:-4],changeSpritetype,height=tilebuttonheight,width=tilebuttonwidth,position=(screen.get_width()-tilebuttonwidth*2-tilebuttonheight-tilebuttonwidth/2,sh),func_args = (SpriteInput,)))
            sh += tilebuttonheight
        if pygame.mouse.get_pressed(num_buttons=3)[0]:
            try:
                if drawtype == 'tile':
                    next((x for x in scenes[sceneindex].elements if isinstance(x, tilemap)), None).addTile(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
                elif drawtype == 'sprite' and next((x for x in scenes[sceneindex].elements if isinstance(x, tilemap)), None).rect.collidepoint(pygame.mouse.get_pos()):
                    spritepressed = True
            except:
                pass
        elif spritepressed:
            scenes[sceneindex].elements.append(player(screen,drawingelementtype,position = pygame.mouse.get_pos()))
            spritepressed = False
        if pygame.mouse.get_pressed(num_buttons=3)[2]:
            for element in scenes[sceneindex].elements:
                if isinstance(element,player):
                    if element.rect.collidepoint(pygame.mouse.get_pos()):
                        scenes[sceneindex].elements.remove(element)
        if pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]:
            drawtype = 'none'
    
    pygame.display.flip()

client.loop_stop()
client.disconnect()