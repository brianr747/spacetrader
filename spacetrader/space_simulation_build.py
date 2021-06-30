
import ast

from agent_based_macro import simulation as simulation

from agent_based_macro import base_simulation as base_simulation
from agent_based_macro import clientserver as clientserver


class MsgQuery(clientserver.ClientServerMsg):
    def ServerCommand(self, server, *args):
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
                ent = server.GetEntity(int(args[1]))
                info = ent.GetRepresentation()
                out = MsgQuery('getinfo', info.__repr__())
            elif self.args[0] == 'entities':
                out = MsgQuery('entities', [f'{x.GID}: {x.Name} {x.Type}' for x in server.EntityList])
            elif self.args[0] == 'locations':
                out = MsgQuery('locations',
                               [f'{server.GetEntity(x).GID}:{server.GetEntity(x).Name}' for x in server.Locations])
            elif self.args[0] == 'getship':
                out = MsgQuery('getship', [f'{server.ShipGID}', ])
            elif self.args[0] == 'getspace':
                out = MsgQuery('getspace', [f'{server.NonLocationID}', ])
            elif self.args[0] == 'moveship':
                server.MoveShip(self.ClientID, int(args[1]), int(args[2]))
            else:
                out = MsgQuery('Unknown query', [])
        else:
            out = MsgQuery('Unknown query', [])
        if out is not None:
            out.ClientID = self.ClientID
            server.QueueMessage(out)

    def ClientMessage(self, client, querytype, payload):
        if querytype == 'getinfo':
            info = ast.literal_eval(payload)
            client.EntityInfo[info['GID']] = info
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

class GameClient(simulation.Client):
    """
    Basic client processing, that handles data management.

    Subclasses handle things like graphics and command processing. This way we can sub out the graphical
    interface easily without touching the data management core of the client.
    """
    def __init__(self, simulation):
        super().__init__(simulation)
        self.IsPaused = None
        self.Time = None
        self.EntityList = []
        self.LocationList = []
        self.PlanetDict = {}
        self.SelectedShipGID = None
        self.SelectedShipPlanet = None
        self.SpaceID = None
        self.EntityInfo = {}

    def ProcessingStep(self):
        # Do client side processing.
        if self.SelectedShipGID is not None:
            self.SendCommand(MsgQuery('getinfo', self.SelectedShipGID))
            if self.SelectedShipGID in self.EntityInfo:
                info = self.EntityInfo[self.SelectedShipGID]
                if not self.SelectedShipPlanet == info['Location']:
                    if not info['Location'] == self.SpaceID:
                        self.SendCommand(MsgQuery('getinfo', info['Location']))
                    self.SelectedShipPlanet = info['Location']
                else:
                    # Aleays query market info
                    if 'MarketList' in self.EntityInfo[self.SelectedShipPlanet]:
                        marketlist = self.EntityInfo[self.SelectedShipPlanet]["MarketList"]
                        for GID in marketlist:
                            self.SendCommand(MsgQuery('getinfo', GID))


class SpaceSimulation(base_simulation.BaseSimulation):
    def __init__(self):
        super().__init__()
        self.ShipGID = None

    def Setup(self):
        """
        Set up the galaxy.
        :return:
        """
        # Eventually, create Planet Entity's with more information like (x,y) position (x,y,z!)
        locations = (('Orth', (0.,0.)),
                     ('Lave', (1., 0.)))
        name_lookup = {}

        for loc, coords in locations:
            obj = base_simulation.Planet(loc, coords)
            # Temporarily store planet names for setup
            name_lookup[loc] = obj
            self.AddLocation(obj)
            num_workers = 80
            JG = base_simulation.JobGuarantee(obj.GID, self.CentralGovernmentID, job_guarantee_wage=100,
                                              num_workers=num_workers)
            self.AddEntity(JG)
            HH = base_simulation.HouseholdSector(obj.GID, money_balance=num_workers*10000,
                                                 target_money=num_workers*9900)
            self.AddHousehold(HH)
        commodities = ('Fud', 'Consumer Goods')
        for com in commodities:
            obj = simulation.Entity(com, 'commodity')
            self.AddCommodity(obj)
        self.GenerateMarkets()
        for loc_id in self.Locations:
            obj = simulation.Entity.GetEntity(loc_id)
            obj.Init()
            # Then, find the JobGuarantee object
            for ent_id in obj.EntityList:
                ent = simulation.Entity.GetEntity(ent_id)
                if ent.Type == 'JobGuarantee':
                    ent.FindEmployers()
        # Space is a "nonlocation": the ID to be used for anything (ships) that are not at a logical
        # location.
        space = base_simulation.Location('Space')
        self.AddLocation(space)
        self.NonLocationID = space.GID
        base_simulation.TravellingAgent.NoLocationID = space.GID
        # Add a ship
        orth = name_lookup["Orth"]
        # This looks strange, but we say that we start at Orth and are heading to Orth. Loter on,
        # may need to spawn ships in transit, so need the flexibility
        ship = base_simulation.TravellingAgent('ship', orth.Coordinates, orth.GID,
                                               travelling_to_ID=orth.GID)
        self.AddEntity(ship)
        # This is a bit of a hack
        self.ShipGID = ship.GID

    def MoveShip(self, clientID, shipID, locID):
        # Eventually, need to validate that the client has the right to move the ship
        ship = self.EntityList[shipID]
        ship.StartMoving(locID, self.Time)





def build_sim():
    sim = SpaceSimulation()
    sim.TimeMode = 'realtime'
    sim.Setup()

    return sim