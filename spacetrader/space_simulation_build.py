
import ast
import time

import agent_based_macro.base_simulation_agents
import agent_based_macro.entity
from agent_based_macro import simulation as simulation

from agent_based_macro import base_simulation as base_simulation
from agent_based_macro import clientserver as clientserver


class MsgQuery(clientserver.ClientServerMsg):
    def server_command(self, server, *args):
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
        if len(self.args) > 0:
            if self.args[0] == 'getinfo':
                ent = server.get_entity(int(args[1]))
                info = ent.get_representation()
                out = MsgQuery('getinfo', info.__repr__())
            elif self.args[0] == 'entities':
                out = MsgQuery('entities', [f'{x.GID}: {x.Name} {x.Type}' for x in server.EntityList])
            elif self.args[0] == 'locations':
                out = MsgQuery('locations',
                               [f'{server.get_entity(x).GID}:{server.get_entity(x).Name}' for x in server.Locations])
            elif self.args[0] == 'getship':
                out = MsgQuery('getship', [f'{server.ShipGID}', ])
            elif self.args[0] == 'getspace':
                out = MsgQuery('getspace', [f'{server.NonLocationID}', ])
            elif self.args[0] == 'getcommodities':
                commodities = []
                for ent in server.EntityList:
                    if ent.Type == 'commodity':
                        commodities.append((ent.GID, ent.Name))
                out = MsgQuery('getcommodities', commodities)
            elif self.args[0] == 'moveship':
                server.MoveShip(self.ClientID, int(args[1]), int(args[2]))
            else:
                out = MsgQuery('Unknown query', [])
        else:
            out = MsgQuery('Unknown query', [])
        if out is not None:
            out.ClientID = self.ClientID
            server.queue_message(out)

    def client_message(self, client, querytype, payload):
        if querytype == 'getinfo':
            info = ast.literal_eval(payload)
            client.EntityInfo[info['GID']] = info
            try:
                client.PendingQueries.remove(info['GID'])
            except KeyError:
                pass
        if querytype == 'entities':
            client.EntityList = payload
            print(payload)
        if querytype == 'locations':
            client.LocationList = payload
            for info in client.LocationList:
                GID, name = info.split(':')
                client.PlanetDict[int(GID)] = name
        if querytype == 'getship':
            client.SelectedShipGID = int(payload[0])
            print('Ship GID:', client.SelectedShipGID)
        if querytype == 'getspace':
            client.SpaceID = int(payload[0])
            print('Space ID: ', client.SpaceID)
        if querytype == 'getcommodities':
            client.CommodityDict = {}
            for GID, name in payload:
                client.CommodityDict[name] = GID
            print(client.CommodityDict)

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
        self.send_command(MsgQuery('getinfo', GID))
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
        self.open_log('transactions', 'transactions.txt')

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
                                                                        travelling_to_id=orth.GID, speed=1.)
        self.add_entity(ship)
        # This is a bit of a hack
        self.ShipGID = ship.GID

    def MoveShip(self, clientID, shipID, locID):
        # Eventually, need to validate that the client has the right to move the ship
        ship = self.EntityList[shipID]
        ship.start_moving(locID, self.Time)


def build_sim():
    sim = SpaceSimulation()
    sim.TimeMode = 'realtime'
    sim.Setup()

    return sim