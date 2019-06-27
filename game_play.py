import _thread
from time import sleep
import chess
import util.logger as lg
from game.game import Game, GameState
import random
import subprocess

from util.xboardInterface import XBoardInterface
from main import create_and_run_agent


def playMatches(best_model, new_model, EPISODES, turns_until_high_noise, interface, memory=None, goes_first=0):
    # TODO: test and reimplement
    env = Game(0)
    scores = {}  # TODO Scores for each player
    points = {"best_players": [], "new_players": []}
    os.popen('cd ../tinyChessServer/')

    for e in range(EPISODES):
        print('====================')
        print('EPISODE %d OF %d', e + 1, EPISODES)
        print('====================')
        print(str(e + 1) + ' ', end='')

        server = subprocess.Popen(["node", "index.js"], cwd="../tinyChessServer", stdout=subprocess.PIPE)
        sleep(1)

        _thread.start_new_thread(create_and_run_agent, ("Agent 1", True, env, best_model))
        _thread.start_new_thread(create_and_run_agent, ("Agent 2", False, env, new_model))
        _thread.start_new_thread(create_and_run_agent, ("Agent 3", True, env, new_model))
        _thread.start_new_thread(create_and_run_agent, ("Agent 4", False, env, best_model))

    return (scores, memory, points)


def play_websocket_game(player, logger, interface, turns_with_high_noise, goes_first):
    while interface.color is None:
        sleep(0.01)
    env = Game(0)
    state = env.reset()
    turn = 0
    done = False

    while not done:
        # wait till game started
        while not interface.isMyTurn:
            sleep(0.01)

        # perform move of other player
        if (turn > 0 and interface.color == 'white') or interface.color == 'black':
            interface.logViaInterfaceType(f"[{player.name}] performing action of opponent {interface.lastMove}")
            mv = chess.Move.from_uci(interface.lastMove)
            mv.board_id = 0
            state, value, done, _ = env.step(mv)
            interface.lastMove = ''
            for move in interface.otherMoves:
                mv = chess.Move.from_uci(move)
                mv.board_id = 1
                state.push_action(mv)
            interface.otherMoves = []

        interface.logViaInterfaceType(f"[{player.name}] It's my turn!")

        turn += 1
        higher_noise = 1 if turn < turns_with_high_noise else 0

        # get action, edge_visited_rates, best_average_evaluation, next_state_evaluation
        action, _, _, _ = player.act(state, higher_noise)

        # send message
        lg.logger_model.info(f"move {action} was played by {player.name}")
        interface.sendAction(action)
        interface.isMyTurn = False

        # Do the action
        state, value, done, _ = env.step(action)

        # the value of the newState from the POV of the new playerTurn
        # i.e. -1 if the previous player played a winning move

    print(f"[{player.name}] Game finished!")