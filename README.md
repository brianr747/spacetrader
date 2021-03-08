# spacetrader
Space Trader Game using agent_based_macro model.

This is supposed to evolve into a space-trading game. 

Still have not closed the economy loop, so it does not do much.

**Version 0.1 Plan**

In case anyone is excited about a sophisticated economic simulation, it will take patience.
At present, the program works. However, the gameplay current consists of ... pausing and
unpausing the simulation.

The objective for "Version 0.1" is to create a closed, simplified economy. It will
consist of:

- 2-D map with two planets that happen to look remarkably like colored circles.
- A spaceship (that looks like a square) that flies between the two planets.
- It can buy and sell food (the only commodity) at the planets. 

OK, that won't win any awards for gameplay.

However, once that is accomplished, a lot of core functionality is there under the hood.

- Agents are sending buy/sell orders to the markets.
- Closed economy loop, with a household sector, farms, and a central galactic 
government running a Job Guarantee.
  
- Messaging system between the game client and the simulation engine.
- Model agent event and behavioural logic loop working, although behaviour will be the 
minimum required to create a closed economy loop. (Closing the economy means that
  there are sources and sinks for all the commodities and money, and the economy
  will evolve to something resembling a steady state without requiring intervention.)

That is a non-trivial amount of work, but of course, it's almost entirely invisible.

Once completed, the economic simulation would be the bare bones minimum one that could
get transferred back to the "agent_based_macro" project, which could then be used
to develop more "serious" simulations.

Will add more documentation if it works...

(I will look into adding a open source license if this thing is viable.)

(c) 2021 Brian Romanchuk