
import pygame
import spacetrader.space_simulation_build as simulation_build
import agent_based_macro.clientserver

def main():
    sim, client = simulation_build.build_sim()

    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Space Trader!!LOL!!")
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((0,0,0))
    clock = pygame.time.Clock()
    client.SendCommand(agent_based_macro.clientserver.MsgTimeQuery())
    client.SendCommand(simulation_build.MsgQuery('entities'))
    client.SendCommand(simulation_build.MsgQuery('locations'))
    client.SendCommand(simulation_build.MsgQuery('getship'))
    font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
    # Paused is fixed text
    label_paused = font.render('Game Paused', True, (255, 255, 0))
    last_time = client.Time
    label_time = font.render('', True, (255,255,255))
    keepGoing = True
    frames_since_time = 0
    frames_since_time_query = 0
    while keepGoing:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keepGoing = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    if client.IsPaused:
                        client.SendCommand(agent_based_macro.clientserver.MsgUnpause())
                    else:
                        client.SendCommand(agent_based_macro.clientserver.MsgPause())
                elif event.key == pygame.K_ESCAPE:
                    # Quick termination useful in debugging...
                    keepGoing = False
        # Allow up to 5 processing steps within a loop <?>
        frames_since_time += 1
        if frames_since_time >= 5:
            sim.IncrementTime()
            frames_since_time = 0
        frames_since_time_query += 1
        if frames_since_time_query >= 11:
            client.SendCommand(agent_based_macro.clientserver.MsgTimeQuery())
        for i in range(0,5):
            did_anything = sim.Process()
            if not did_anything:
                break
        screen.blit(background, (0,0))
        if client.IsPaused:
            screen.blit(label_paused, (300, 10))
        if not client.Time == last_time:
            label_time = font.render(f'{client.Time:.2f}', True, (255,255,255))
        screen.blit(label_time, (500, 10))
        for i in range(0, len(client.LocationList)):
            label = font.render(client.LocationList[i], True, (0, 255, 0))
            screen.blit(label, (20, 100+ (50*i)))
        pygame.display.flip()



