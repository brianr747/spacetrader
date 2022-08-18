"""
Code for drawing stuff


Copyright 2021 Brian Romanchuk

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
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
        self.SelectedCommodity = None
        self.SelectedBid = 10000
        self.SelectedAsk = 0
        self.OrderSize = 1


    def set_screen(self, screen):
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
                self.send_command(space_simulation_build.MsgQuery(query='moveship', ship_id=self.SelectedShipGID,
                                                                  target=target))
            if event.key == pygame.K_b:
                if self.PlanetDict[self.SelectedShipPlanet] == 'Space':
                    return
                if self.SelectedCommodity is None:
                    return
                if self.SelectedAsk is None:
                    return
                price = self.SelectedAsk
                amount = self.OrderSize
                self.send_command(space_simulation_build.MsgQuery(query='ship_buy',
                                                                  ship_id=self.SelectedShipGID,
                                                                  planet_id=self.SelectedShipPlanet,
                                                                  commodity_id=self.SelectedCommodity,
                                                                  price=price, amount=amount))
            if event.key == pygame.K_s:
                if self.PlanetDict[self.SelectedShipPlanet] == 'Space':
                    return
                if self.SelectedCommodity is None:
                    return
                if self.SelectedBid is None:
                    return
                price = self.SelectedBid
                amount = self.OrderSize
                self.send_command(space_simulation_build.MsgQuery(query='ship_sell', ship_id=self.SelectedShipGID,
                                                                  planet_id=self.SelectedShipPlanet,
                                                                  commodity_id=self.SelectedCommodity,
                                                                  price=price, amount=amount))
            if event.key == pygame.K_PERIOD:
                if self.OrderSize == 1:
                    self.OrderSize = 10
                else:
                    self.OrderSize = 1
            if event.key == pygame.K_2:
                self.Mode = 'Entities'
            if event.key == pygame.K_1:
                self.Mode = 'DrawPlanets'
            if event.key == pygame.K_3:
                self.Mode = 'MarketScreen'


    def draw_screen_state(self):
        if self.Mode == 'DrawPlanets':
            self.draw_screen_planets()
        elif self.Mode == 'Entities':
            self.draw_screen_entities()
        elif self.Mode == 'MarketScreen':
            self.draw_market_screen()
        else:
            raise ValueError(f'Unknown client mode: {self.Mode}')

    def draw_screen_planets(self):
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
            money = f'Ship Cash ${self.EntityInfo[self.SelectedShipGID]["Money"]}'
            inventory = self.EntityInfo[self.SelectedShipGID]["Inventory"]
            money_msg = self.planet_font.render(money, True, (240, 240, 240))
            self.Screen.blit(money_msg, (800, 20))
            inventory_msg = self.planet_font.render('Inventory', True, (240, 240, 240))
            self.Screen.blit(inventory_msg, (800, 40))
            pos = 40
            for row in inventory:
                pos += 18
                txt = f'{self.CommodityDict[row[0]]:15} {row[1]:4}'
                inventory_msg = self.planet_font.render(txt, True, (240, 240, 240))
                self.Screen.blit(inventory_msg, (800, pos))
            pos += 18
            size_msg = self.planet_font.render(f'Trade Size = x{self.OrderSize}', True, (128, 128, 255))
            self.Screen.blit(size_msg, (800, pos))
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
            self.SelectedCommodity = fud_ID
            if fud_ID in self.MarketLookup[loc_ID]:
                market_ID = self.MarketLookup[loc_ID][fud_ID]
                ent = self.EntityInfo[market_ID]
                txt = f'Last ${ent["LastPrice"]}'
                last_time = ent["LastTime"]
                if last_time is None:
                    is_recent = False
                else:
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
                # Fill in the bid/ask members
                self.SelectedBid = ent["BidPrice"]
                self.SelectedAsk = ent['AskPrice']
                self.Screen.blit(market_msg, (screen_x, screen_y + 40))
                txt = f'({ent["BidSize"]}/{ent["AskSize"]})'
                market_msg = self.planet_font.render(txt, True, (240, 240, 240))
                self.Screen.blit(market_msg, (screen_x, screen_y + 60))
        if self.planet_font is None:
            self.planet_font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        for GID, name in self.PlanetDict.items():
            if GID not in self.EntityInfo:
                self.send_command(space_simulation_build.MsgQuery(query='getinfo', GID=GID))
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

    def draw_screen_entities(self):
        num_entities = len(self.EntityList)
        msg = self.planet_font.render(f'Num Entities {num_entities}', True, (240, 240, 0))
        self.Screen.blit(msg, (20, 10))
        y = 30
        for i in range(0,num_entities):
            info = self.EntityList[i].split(' ')
            if info[2] == 'agent':
                gid = int(info[0])
                txt = self.EntityList[i]
                try:
                    entity_info = self.EntityInfo[gid]
                    txt += " "+ repr(entity_info)
                except KeyError:
                    pass
                msg = self.planet_font.render(txt, True, (220, 220, 220))
                self.Screen.blit(msg, (20, y))
                y += 20

    def draw_market_screen(self):
        msg = self.planet_font.render(f'Market Orders', True, (240, 240, 0))
        self.Screen.blit(msg, (20, 10))
        loc_ID = None
        try:
            loc_ID = self.EntityInfo[self.SelectedShipGID]['Location']
            loc_name = self.PlanetDict[int(loc_ID)]
            # Draw Landed Location at top
            self.Screen.blit(self.text_bitmaps[loc_name], (100, 30))
        except KeyError:
            # Cannot do much
            return
        if loc_ID in self.MarketLookup:
            # Eventually, need to change target commodity
            fud_ID = self.CommodityDict['Fud']
            self.SelectedCommodity = fud_ID
            line_height = 18
            if fud_ID in self.MarketLookup[loc_ID]:
                market_ID = self.MarketLookup[loc_ID][fud_ID]
                ent = self.EntityInfo[market_ID]
                keyz = list(ent.keys())
                keyz.sort()
                pos = 60
                for k in keyz:
                    if k in ('BuyQueue', 'SellQueue'):
                        continue
                    txt = f'{k} = {ent[k]}'
                    msg = self.planet_font.render(txt, True, (220, 220, 200))
                    self.Screen.blit(msg, (100, pos))
                    pos += line_height
                pos = 60
                txt = 'Sell Orders'
                msg = self.planet_font.render(txt, True, (220, 220, 200))
                self.Screen.blit(msg, (300, pos))
                pos += line_height
                if len(ent['SellQueue']) == 0:
                    txt = '---'
                    msg = self.planet_font.render(txt, True, (220, 220, 200))
                    self.Screen.blit(msg, (300, pos))
                    pos += line_height
                else:
                    queue = ent['SellQueue']
                    N = min(10, len(queue))
                    if N > 10:
                        txt = '+ More Orders'
                        msg = self.planet_font.render(txt, True, (220, 220, 200))
                        self.Screen.blit(msg, (300, pos))
                        pos += line_height
                    for i in range(N, 0, -1):
                        x = queue[i-1]
                        txt = f'{x[1]} @ {x[0]}   ({x[2]})'
                        msg = self.planet_font.render(txt, True, (220, 220, 200))
                        self.Screen.blit(msg, (300, pos))
                        pos += line_height
                pos += 10
                txt = 'Buy Orders'
                msg = self.planet_font.render(txt, True, (220, 220, 200))
                self.Screen.blit(msg, (300, pos))
                pos += line_height
                queue = ent['BuyQueue']
                N = len(queue)
                if N == 0:
                    txt = '---'
                    msg = self.planet_font.render(txt, True, (220, 220, 200))
                    self.Screen.blit(msg, (300, pos))
                    pos += line_height
                else:
                    for x in queue[0:min(N,10)]:
                        txt = f'{x[1]} @ {x[0]}   ({x[2]})'
                        msg = self.planet_font.render(txt, True, (220, 220, 200))
                        self.Screen.blit(msg, (300, pos))
                        pos += line_height
                    if N > 10:
                        txt = '+ More Orders'
                        msg = self.planet_font.render(txt, True, (220, 220, 200))
                        self.Screen.blit(msg, (300, pos))
                        pos += line_height








