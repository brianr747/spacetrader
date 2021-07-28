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
        self.MarketLookup = {}


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
                self.send_command(space_simulation_build.MsgQuery('moveship', self.SelectedShipGID, target))


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
        loc_ID = None
        try:
            loc_ID = self.EntityInfo[self.SelectedShipGID]['Location']
            loc_name = self.PlanetDict[int(loc_ID)]
            # Draw Landed Location at top
            self.Screen.blit(self.text_bitmaps[loc_name], (100, 10))
        except KeyError:
            pass
        # Make sure we have market information
        # Fill in self.MarketLookup for loc_ID if we have all the entity information in
        # the planet's MarketList
        # Add a bunch of defensive checks in case the Entity information is not yet filled in.
        if (not loc_ID in self.MarketLookup) and (loc_ID is not None) and (loc_ID in self.EntityInfo) \
                and ('MarketList' in self.EntityInfo[loc_ID]):
            have_all_info = True
            for GID in self.EntityInfo[loc_ID]['MarketList']:
                if GID not in self.EntityInfo:
                    self.QueryInfo(GID)
                    have_all_info = False
            if have_all_info:
                looker_upper = dict()
                for GID in self.EntityInfo[loc_ID]['MarketList']:
                    looker_upper[self.EntityInfo[GID]["CommodityID"]] = GID
                self.MarketLookup[loc_ID] = looker_upper
        if loc_ID in self.MarketLookup:
            # Eventually, need to change target commodity
            fud_ID = self.CommodityDict['Fud']
            if fud_ID in self.MarketLookup[loc_ID]:
                market_ID = self.MarketLookup[loc_ID][fud_ID]
                ent = self.EntityInfo[market_ID]
                txt = f'Last ${ent["LastPrice"]}'
                last_time = ent["LastTime"]
                is_recent = abs(last_time - self.Time) < .02
                coordinates = self.EntityInfo[loc_ID]['Coordinates']
                screen_x = int(mid_point[0] + coordinates[0] * x_scale) + 50
                screen_y = int(mid_point[1] + coordinates[1] * y_scale) - 30
                if is_recent:
                    market_msg = self.planet_font.render(txt, True, (255, 255, 0))
                else:
                    market_msg = self.planet_font.render(txt, True, (240, 240, 240))
                self.Screen.blit(market_msg, (screen_x, screen_y))
                txt = 'Bid/Ask'
                market_msg = self.planet_font.render(txt, True, (240, 240, 240))
                self.Screen.blit(market_msg, (screen_x, screen_y + 20))
                txt = f'{ent["BidPrice"]}/{ent["AskPrice"]}'
                market_msg = self.planet_font.render(txt, True, (240, 240, 240))
                self.Screen.blit(market_msg, (screen_x, screen_y + 40))
        if self.planet_font is None:
            self.planet_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        for GID, name in self.PlanetDict.items():
            if GID not in self.EntityInfo:
                self.send_command(space_simulation_build.MsgQuery('getinfo', GID))
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


