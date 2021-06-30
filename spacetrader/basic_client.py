"""
Code for drawing stuff
"""

import pygame
import spacetrader.space_simulation_build as space_simulation_build


class BasicClient(space_simulation_build.GameClient):
    def __init__(self, simulation):
        super().__init__(simulation)
        self.text_bitmaps = {}
        self.planet_font = None
        self.Screen = None
        self.ScreenSize = (0,0)
        self.Mode = 'DrawPlanets'

    def SetScreen(self, screen):
        self.ScreenSize = screen.get_size()
        self.Screen = screen

    def ProcessEvent(self, event):
        """
        Processing
        :param event: pygame.Event
        :return:
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                ship_loc = self.EntityInfo[self.SelectedShipGID]["TravellingTo"]
                # Figure out which planet to fly to
                target = None
                for GID in self.PlanetDict.keys():
                    if (not(ship_loc) == GID) and (not self.PlanetDict[GID] == 'Space'):
                        target = GID
                self.SendCommand(space_simulation_build.MsgQuery('moveship', self.SelectedShipGID, target))


    def DrawScreenState(self):
        screen_size = self.ScreenSize
        mid_point = (screen_size[0]/2, screen_size[1]/2)
        x_scale = 200
        y_scale = 200
        try:
            coordinates = self.EntityInfo[self.SelectedShipGID]['Coordinates']
            screen_x = int(mid_point[0] + coordinates[0] * x_scale)
            screen_y = int(mid_point[1] + coordinates[1] * y_scale)
            l = 60
            ship_rect = pygame.Rect(screen_x - l/2, screen_y - l/2, l, l)
            pygame.draw.rect(self.Screen, (0,0,255), ship_rect)
        except KeyError:
            pass
        try:
            loc_ID = self.EntityInfo[self.SelectedShipGID]['Location']
            loc_name = self.PlanetDict[int(loc_ID)]
            # Draw Landed Location at top
            self.Screen.blit(self.text_bitmaps[loc_name], (100, 10))
        except KeyError:
            pass
        if self.planet_font is None:
            self.planet_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        for GID, name in self.PlanetDict.items():
            if GID not in self.EntityInfo:
                self.SendCommand(space_simulation_build.MsgQuery('getinfo', GID))
                # In order to avoid spamming this getinfo() request, stick an empty entry in the EntityInfo
                self.EntityInfo[GID] = {}
            else:
                try:
                    coordinates = self.EntityInfo[GID]['Coordinates']
                except:
                    continue
                screen_x = int(mid_point[0] + coordinates[0] * x_scale)
                screen_y = int(mid_point[1] + coordinates[1] * y_scale)
                pygame.draw.circle(self.Screen, color=(0,255,0), center=(screen_x, screen_y), radius=30)
                if name not in self.text_bitmaps:
                    self.text_bitmaps[name] = self.planet_font.render(name, False, (240, 240, 240))
                self.Screen.blit(self.text_bitmaps[name], (screen_x, screen_y))


