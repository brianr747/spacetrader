from agent_based_macro import simulation as simulation

from agent_based_macro import base_simulation as base_simulation
from agent_based_macro import clientserver as clientserver


class MsgQuery(clientserver.ClientServerMsg):
    def ServerCommand(self, server, *args):
        """

        :param server: simulation.Simulation
        :return:
        """
        if len(self.args) > 0:
            if self.args[0] == 'entities':
                out = MsgQuery('entities', [f'{x.GID}: {x.Name} {x.Type}' for x in server.EntityList])
            if self.args[0] == 'locations':
                out = MsgQuery('locations',
                               [f'{server.GetEntity(x).GID}: {server.GetEntity(x).Name}' for x in server.Locations])
        else:
            out = MsgQuery('Uknown query', [])
        out.ClientID = self.ClientID
        server.QueueMessage(out)

    def ClientMessage(self, client, querytype, payload):
        if querytype == 'entities':
            client.EntityList = payload
            print(payload)
        if querytype == 'locations':
            client.LocationList = payload



class GameClient(simulation.Client):
    def __init__(self, simulation):
        super().__init__(simulation)
        self.IsPaused = None
        self.Time = None
        self.EntityList = []
        self.LocationList = []

class SpaceSimulation(base_simulation.BaseSimulation):
    def Setup(self):
        """
        Set up the galaxy.
        :return:
        """
        # Eventually, create Planet Entity's with more information like (x,y) position (x,y,z!)
        locations = ('Orth', 'Lave')
        for loc in locations:
            obj = base_simulation.Location(loc)
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






def build_sim():
    sim = SpaceSimulation()
    sim.TimeMode = 'realtime'
    sim.Setup()
    client = GameClient(simulation=sim)
    sim.ClientDict[client.ClientID] = client
    return sim, client