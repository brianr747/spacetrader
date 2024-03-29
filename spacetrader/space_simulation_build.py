"""

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
import ast
import time

import agent_based_macro.base_simulation_agents
import agent_based_macro.entity
from agent_based_macro import simulation as simulation

from agent_based_macro import base_simulation as base_simulation
from agent_based_macro import clientserver as clientserver


class MsgQuery(clientserver.ClientServerMsg):
    def server_command(self, server, **kwargs):
        """
        This class implements the protocol for passing messages between client and server. Both the client and
        server use this class, so that everything is mirrored in one place.

        Since I am not yet using an actual client-server framework, this methodology looks silly and is inefficent.
        However, if I jumble the client and server code together, so way to disentangle them later.

        At the time of writing (2021-04-14), the protocol is too simple: I just have nested if's based on parsing
        the text of the message. This will be replaced with a more elegant solution that is less spaghetti-like,
        but since there are so few message types, there is no need to over-design it yet.

        It will also need a way for Entity objects to mirror their state between clients and server, but once again,
        I want to do the simplest version until it is absolutely necessary to go for the more complex code solution.

        :param server: simulation.Simulation
        :return:
        """
        out = None
        if 'query' in kwargs:
            if kwargs['query'] == 'getinfo':
                ent = server.get_entity(kwargs['GID'])
                info = ent.get_representation()
                out = MsgQuery(query='getinfo', response=info.__repr__())
            elif kwargs['query'] == 'entities':
                out = MsgQuery(query='entities', response=[f'{x.GID}: {x.Name} {x.Type}' for x in server.EntityList])
            elif kwargs['query'] == 'locations':
                out = MsgQuery(query='locations',
                               response=[f'{server.get_entity(x).GID}:{server.get_entity(x).Name}' for x in server.Locations])
            elif kwargs['query'] == 'getship':
                out = MsgQuery(query='getship', response=[f'{server.ShipGID}', ])
            elif kwargs['query'] == 'getspace':
                out = MsgQuery(query='getspace', response=[f'{server.NonLocationID}', ])
            elif kwargs['query'] == 'getcommodities':
                commodities = []
                for ent in server.EntityList:
                    if ent.Type == 'commodity':
                        commodities.append((ent.GID, ent.Name))
                out = MsgQuery(query='getcommodities', response=commodities)
            elif kwargs['query'] == 'moveship':
                server.MoveShip(self.ClientID, shipID=int(kwargs['ship_id']),
                                locID=int(kwargs['target']))
            elif kwargs['query'] == 'ship_buy':
                server.ship_buy(self.ClientID, int(kwargs['ship_id']), int(kwargs['planet_id']),
                                int(kwargs['commodity_id']), int(kwargs['price']), int(kwargs['amount']))
            elif kwargs['query'] == 'ship_sell':
                server.ship_sell(self.ClientID,int(kwargs['ship_id']), int(kwargs['planet_id']),
                                 int(kwargs['commodity_id']), int(kwargs['price']), int(kwargs['amount']))
            else:
                out = MsgQuery(query='Unknown query', response=kwargs)
        else:
            out = MsgQuery(query='Unknown query')
        if out is not None:
            out.ClientID = self.ClientID
            server.queue_message(out)

    def client_message(self, client, **kwargs):
        querytype = kwargs['query']
        payload = kwargs['response']
        if  querytype == 'getinfo':
            info = ast.literal_eval(payload)
            client.EntityInfo[info['GID']] = info
            try:
                client.PendingQueries.remove(info['GID'])
            except KeyError:
                pass
        elif querytype == 'entities':
            client.EntityList = payload
            print(payload)
        elif querytype == 'locations':
            client.LocationList = payload
            for info in client.LocationList:
                GID, name = info.split(':')
                client.PlanetDict[int(GID)] = name
        elif querytype == 'getship':
            client.SelectedShipGID = int(payload[0])
            print('Ship GID:', client.SelectedShipGID)
        elif querytype == 'getspace':
            client.SpaceID = int(payload[0])
            print('Space ID: ', client.SpaceID)
        elif querytype == 'getcommodities':
            client.CommodityDict = {}
            for GID, name in payload:
                client.CommodityDict[name] = GID
                client.CommodityDict[GID] = name
            print(client.CommodityDict)
        else:
            raise ValueError(f'Unknown message: {querytype} {payload}')

class GameClient(simulation.Client):
    """
    Basic client processing, that handles data management.

    Subclasses handle things like graphics and command processing. This way we can sub out the graphical
    interface easily without touching the data management core of the client.
    """
    def __init__(self, simulation):
        super().__init__(simulation)
        self.IsPaused = None
        self.EntityList = []
        self.LocationList = []
        self.PlanetDict = {}
        self.SelectedShipGID = None
        self.SelectedShipPlanet = None
        self.SpaceID = None
        self.EntityInfo = {}
        self.CommodityDict = {}
        self.PendingQueries = set()
        # Number of seconds per game day. Value copied from server.



    def QueryInfo(self, GID):
        """
        "Safe" Entity query call. Does nothing if a query is pending.
        :param GID: int
        :return:
        """
        if GID in self.PendingQueries:
            return
        self.send_command(MsgQuery(query='getinfo', GID=GID))
        self.PendingQueries.add(GID)


    def ProcessingStep(self):
        # Do client side processing.
        if self.SelectedShipGID is not None:
            self.QueryInfo(self.SelectedShipGID)
            if self.SelectedShipGID in self.EntityInfo:
                info = self.EntityInfo[self.SelectedShipGID]
                if not self.SelectedShipPlanet == info['Location']:
                    if not info['Location'] == self.SpaceID:
                        self.QueryInfo(info['Location'])
                    self.SelectedShipPlanet = info['Location']
                else:
                    # Aleays query market info
                    if 'MarketList' in self.EntityInfo[self.SelectedShipPlanet]:
                        marketlist = self.EntityInfo[self.SelectedShipPlanet]["MarketList"]
                        for GID in marketlist:
                            self.QueryInfo(GID)


class SpaceSimulation(base_simulation.BaseSimulation):
    def __init__(self):
        super().__init__()
        self.ShipGID = None
        self.SeriesFileName = 'series.txt'

    def Setup(self):
        """
        Set up the galaxy.
        :return:
        """
        commodities = ('Fud', 'Consumer Goods')
        for com in commodities:
            obj = agent_based_macro.entity.Entity(com, 'commodity')
            self.add_commodity(obj)
        # Eventually, create Planet Entity's with more information like (x,y) position (x,y,z!)
        locations = (
            ('Orth', (0.,0.), (1.2,), 2),
            ('Mors', (1., 0.), (1.1,), 2),
                     )
        name_lookup = {}
        # Log of all transactions. If we do not open the log, log messages are not processed.
        log_transactions = False
        if log_transactions:
            self.open_log('transactions', 'transactions.txt')
        else:
            # Clear out transactions.txt if we are not logging so we don't get confused by an out of date log
            f = open('transactions.txt', 'w')
            f.close()
        for loc, coords, productivity, num_producers in locations:
            obj = base_simulation.Planet(loc, coords)
            # Temporarily store planet names for setup
            name_lookup[loc] = obj
            self.add_location(obj)
            num_workers = 80
            JG = agent_based_macro.base_simulation_agents.JobGuarantee(obj.GID, self.CentralGovernmentID, job_guarantee_wage=100,
                                                                       num_workers=num_workers)
            fud_id = self.get_commodity_by_name('Fud')
            JG.ProductivityMultiplier = 0.8
            if len(productivity) > 1:
                raise NotImplementedError('Need to fix initial stocking of the JG inventory')
            # Add one day's production to inventory, as otherwise, households will buy up everything...
            JG.Inventory[fud_id].add_inventory(productivity[0]*num_workers, 0.)
            self.add_entity(JG)
            # Add a lookup for the JG by planet GID
            self.JGLookup[obj.GID] = JG
            JG.register_series('production')
            JG.register_series('emergency')
            JG.register_series('unemployment')
            money_balance = num_workers*1000
            HH = base_simulation.HouseholdSector(obj.GID, money_balance=money_balance,
                                                 target_money=int(money_balance*.99))
            HH.register_series('DailyBid')
            HH.register_series('MarketOrder')
            HH.register_series('TargetMoney')
            HH.register_series('Money')
            HH.register_series('DailyEarnings')
            self.add_household(HH)
            # Assign the productivity
            for prod, commodity_name in zip(productivity, ('Fud',)):
                commod = self.get_commodity_by_name(commodity_name)
                obj.ProductivityDict[commod] = prod
            for i in range(0, num_producers):
                producer = agent_based_macro.base_simulation_agents.ProducerLabour(f'producer{i}', 10000., location_id=obj.GID,
                                                                                   commodity_id=fud_id)
                if i == 0:
                    producer.register_series('money')
                    producer.register_series('wage_payment')
                self.add_entity(producer)
        self.generate_markets()
        for loc_id in self.Locations:
            obj = agent_based_macro.entity.Entity.get_entity(loc_id)
            obj.initialise()
            # Then, find the JobGuarantee object
            for ent_id in obj.EntityList:
                ent = agent_based_macro.entity.Entity.get_entity(ent_id)
                if ent.Type == 'JobGuarantee':
                    ent.find_employers()
        # Space is a "nonlocation": the ID to be used for anything (ships) that are not at a logical
        # location.
        space = base_simulation.Location('Space')
        self.add_location(space)
        self.NonLocationID = space.GID
        agent_based_macro.base_simulation_agents.TravellingAgent.NoLocationID = space.GID
        # Add a ship
        orth = name_lookup["Orth"]
        # This looks strange, but we say that we start at Orth and are heading to Orth. Loter on,
        # may need to spawn ships in transit, so need the flexibility
        ship = agent_based_macro.base_simulation_agents.TravellingAgent('ship', orth.Coordinates, orth.GID,
                                                                        money_balance=2000,
                                                                        travelling_to_id=orth.GID, speed=1.)
        self.add_entity(ship)
        # This is a bit of a hack
        self.ShipGID = ship.GID
        self.PlayerGID.add(ship.GID)

    def MoveShip(self, clientID, shipID, locID):
        # Eventually, need to validate that the client has the right to move the ship
        ship = self.EntityList[shipID]
        ship.start_moving(locID, self.Time)


    def ship_buy(self, client_ID, ship_ID, planet_id, commodity_id, price, amount):
        ent = self.get_entity(ship_ID)
        # Force an update of location
        ent.get_coordinates(self.Time)
        if not ent.LocationID == planet_id:
            raise ValueError('invalid order')
        event = simulation.Event(ship_ID, ent.event_buy, self.Time, None, commodity_id=commodity_id,
                                       price=price, amount=amount)
        simulation.queue_event(event)

    def ship_sell(self, client_ID, ship_ID, planet_id, commodity_id, price, amount):
        ent = self.get_entity(ship_ID)
        # Force an update of location
        ent.get_coordinates(self.Time)
        if not ent.LocationID == planet_id:
            raise ValueError('invalid order')
        event = simulation.Event(ship_ID, ent.event_sell, self.Time, None, commodity_id=commodity_id,
                                       price=price, amount=amount)
        simulation.queue_event(event)

    def event_send_invalid_action(self, *args):
        print('Bad callback', args)


def build_sim():
    sim = SpaceSimulation()
    sim.TimeMode = 'realtime'
    sim.Setup()

    return sim