import subprocess
import os
import sys
import signal
import _thread
import numpy as np
import tensorflow as tf
from time import sleep

from agent import Agent
import config
import game_play
from game.game import Game
from self_play_training import self_play
import util.nn_interface as nni
from util import logger as lg
from util.xboardInterface import XBoardInterface

# intro_message =\
"""

                        __   __
           .,-;-;-,.   /'_\ /_'\ .,-;-;-,.
          _/_/_/_|_\_\) /    \ (/_/_|_\_\_\_
       '-<_><_><_><_>=/\     /\=<_><_><_><_>-'
         `/_/====/_/-'\_\   /_/'-\_\====\_\'

  _____             _             _____         _   _     
 |_   _|_ _ _ _  __| |___ _ __   |_   _|  _ _ _| |_| |___ 
   | |/ _` | ' \/ _` / -_) '  \    | || || | '_|  _| / -_)
   |_|\__,_|_||_\__,_\___|_|_|_|   |_| \_,_|_|  \__|_\___|

Jannis Blüml, Maximilian Otte, Florian Netzer, Magdalena Wache, Lars Wolf
License GPL v3.0                                                      
ASCII-Art: Joan Stark              
"""


def create_and_run_agent(name, env, model, graph, interfaceType="websocket", server_address=""):
    interface = XBoardInterface(name, interfaceType, server_address)
    agent1 = Agent(name, env.state_size, env.action_size, config.MCTS_SIMS, config.CPUCT, model, interface, graph)

    while not interface.gameStarted:
        sleep(0.1)

    game_play.play_websocket_game(agent1, lg.logger_main, interface, config.TURNS_WITH_HIGH_NOISE)


def main(agent_threads, start_server, server_address):

    # print(intro_message)
    # np.set_printoptions(suppress=True)

    env = Game(0)

    # tf.reset_default_graph()
    # if config.INITIAL_MODEL_PATH:
    print("Loading models")
    graphs = []
    for i in range(agent_threads):
        graphs.append(tf.Graph())
    models = []

    for graph in graphs:
        with graph.as_default():
            models.append(nni.load_nn(config.INITIAL_MODEL_PATH))

    print("Finished loading")

    # Add to agents if you want to have a random model #
    # print("loading")
    # model_rand = nni.load_nn("")
    # model_rand._make_predict_function()
    # graph = tf.Graph()
    # writer = tf.summary.FileWriter(logdir='logdir',
    #                               graph=tf.get_default_graph())
    # writer.flush()

    #### If we want to learn instead of playing (NOT FINISHED) ####
    if agent_threads == 0:
        new_best_model, version = self_play(env)
        nni.save_nn(f"run/models/{version}", new_best_model)

    #### If the server is running, create clients as threads and connect them to the websocket interface ####
    elif agent_threads != -1:
        if start_server:
            if agent_threads == 2:
                os.popen("cp ../tinyChessServer/config.json.sjengVsOur ../tinyChessServer/config.json", 'r', 1)
            if agent_threads == 4:
                os.popen("cp ../tinyChessServer/config.json.ourEngine4times ../tinyChessServer/config.json", 'r', 1)

            server = subprocess.Popen(["node", "index.js"], cwd="../tinyChessServer", stdout=subprocess.PIPE)

        else:
            for i in range(0, agent_threads):
                name = "TandemTurtle"
                if agent_threads > 1:
                    name = "Agent " + str(i)
                _thread.start_new_thread(create_and_run_agent, (name, env, models[i], graphs[i], "websocket", server_address))

        while True:
            sleep(10)

    elif agent_threads == -1:
        player = Agent("MisterTester", env.state_size, env.action_size, config.MCTS_SIMS, config.CPUCT, models[0], None)

        state = env.reset()

        action = player.act_nn(state, 0)
        print("You did it: ", action)

    else:
        raise NameError(f" Name: {mode} not existing")


if __name__ == "__main__":

    c = tf.ConfigProto()
    c.gpu_options.per_process_gpu_memory_fraction = 0.45

    agent_threads = config.GAME_AGENT_THREADS
    start_server = config.SERVER_AUTOSTART
    server_address = config.SERVER_ADDRESS
    game_id = config.GAMEID
    tournament_id = config.TOURNAMENTID

    mode = ''
    if len(sys.argv) == 4:
        mode = str(sys.argv[1])
        start_server = int(sys.argv[2])
        server_address = str(sys.argv[3])
    if len(sys.argv) == 6:
        mode = str(sys.argv[1])
        start_server = int(sys.argv[2])
        server_address = str(sys.argv[3])
        game_id = str(sys.argv[4])
        tournament_id = str(sys.argv[5])

    if mode == "auto-4":
        agent_threads = 4
    if mode == "2vsSjeng":
        agent_threads = 2
    if mode == "single_agent":
        agent_threads = 1
    if mode == "selfplay":
        agent_threads = 0
    if mode == "test_model":
        agent_threads = -1

    main(agent_threads, start_server, server_address)
