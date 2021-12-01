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




import time
import math

import pygame
import spacetrader.space_simulation_build as simulation_build
import spacetrader.basic_client as basic_client
import agent_based_macro.clientserver

def main():
    sim = simulation_build.build_sim()
    sim.DayLength = 2.
    # Create the client
    client = basic_client.BasicClient(simulation=sim)
    # Ensure that the client DayLength is synced to the server. (Eventually, need to query.)
    client.DayLength = sim.DayLength
    sim.ClientDict[client.ClientID] = client
    pygame.init()
    screen = pygame.display.set_mode((960, 620))
    pygame.display.set_caption("Space Trader!")
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((0,0,0))
    client.SetScreen(screen)
    clock = pygame.time.Clock()
    client.send_command(agent_based_macro.clientserver.MsgTimeQuery())
    client.send_command(simulation_build.MsgQuery(query='entities'))
    client.send_command(simulation_build.MsgQuery(query='locations'))
    # One time queries to get the ship ID, the ID for space ("non-location"), commodities
    client.send_command(simulation_build.MsgQuery(query='getship'))
    client.send_command(simulation_build.MsgQuery(query='getspace'))
    client.send_command(simulation_build.MsgQuery(query='getcommodities'))
    font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
    # Paused is fixed text
    label_paused = font.render('Game Paused', True, (255, 255, 0))
    label_time = font.render('', True, (255,255,255))
    keepGoing = True
    frames_since_time = 0
    frames_since_time_query = 0
    frames_since_client_proc = 0
    proc_count = 0.
    while keepGoing:
        clock.tick(30)
        for event in pygame.event.get():
            was_processed = False
            if event.type == pygame.QUIT:
                keepGoing = False
                was_processed = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    if client.IsPaused:
                        client.send_command(agent_based_macro.clientserver.MsgUnpause())
                    else:
                        client.send_command(agent_based_macro.clientserver.MsgPause())
                    was_processed = True
                elif event.key == pygame.K_ESCAPE:
                    # Quick termination useful in debugging...
                    keepGoing = False
                    was_processed = True
            if not was_processed:
                client.ProcessEvent(event)
        frames_since_client_proc += 1
        if frames_since_client_proc >=3:
            client.ProcessingStep()
            frames_since_client_proc = 0
        frames_since_time += 1
        if frames_since_time >= 2:
            sim.increment_time()
            frames_since_time = 0
        frames_since_time_query += 1
        if frames_since_time_query >= 5:
            frames_since_time_query = 0
            client.send_command(agent_based_macro.clientserver.MsgTimeQuery())
            client.ProcessingStep()
        cnt = 0
        for i in range(0, 10):
            did_anything = sim.process()
            if not did_anything:
                break
            cnt += 1
        proc_count = .95 * proc_count + .05 * float(cnt)
        screen.blit(background, (0,0))
        client.DrawScreenState()
        label_prc = font.render(f'{int(proc_count)}', True, (200, 200, 200))
        screen.blit(label_prc, (5, 600))
        # This time state code should move to the client.
        if client.IsPaused:
            screen.blit(label_paused, (300, 10))
        if client.Time is not None:
            if client.IsPaused:
                # If paused, just render the time.
                label_time = font.render(f'Time: {client.Time:.2f}', True, (255,255, 0))
            else:
                # If not, estimate how far time has advanced by looking at the difference between
                # time.monotonic() and the last response time (filled in by the client message).
                # This way, we can have smooth client time flow without continuously bombarding with
                # time queries.
                # (Obviously, could just look at the simulation object, but want to be ready for
                # true client/server.
                time_estimate = client.Time + (time.monotonic() - client.LastResponseMonotonic)/client.DayLength
                label_time = font.render(f'Time: {time_estimate:.2f}', True, (255,255,255))
                screen.blit(label_time, (500, 10))
                width = 100*(time_estimate-math.floor(time_estimate))
                time_rect = pygame.Rect(500, 30, width, 5)
                pygame.draw.rect(screen, (0,0,255), time_rect)
                time_rect = pygame.Rect(500+width, 30, 100-width, 5)
                pygame.draw.rect(screen, (255, 255, 0), time_rect)
        pygame.display.flip()
    # cleanup - write the time series
    sim.shutdown()



