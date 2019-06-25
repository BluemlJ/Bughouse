from time import sleep
import chess
import util.logger as lg
from game.game import Game, GameState
import random


def playMatches(player1, player2, EPISODES, turns_until_tau0, memory=None, goes_first=0):
    # TODO: test and reimplement
    env = Game(0)
    scores = {player1.name: 0, "drawn": 0, player2.name: 0}
    sp_scores = {'sp': 0, "drawn": 0, 'nsp': 0}
    points = {player1.name: [], player2.name: []}

    for e in range(EPISODES):
        print('====================')
        print('EPISODE %d OF %d', e + 1, EPISODES)
        print('====================')
        print(str(e + 1) + ' ', end='')

        state = env.reset()

        done = 0
        turn = 0
        player1.mcts = None
        player2.mcts = None

        if goes_first == 0:
            player1Starts = random.randint(0, 1) * 2 - 1
        else:
            player1Starts = goes_first

        if player1Starts == 1:
            players = {1: {"agent": player1, "name": player1.name}, -1: {"agent": player2, "name": player2.name}
                       }
        else:
            players = {1: {"agent": player2, "name": player2.name}, -1: {"agent": player1, "name": player1.name}
                       }

        while done == 0:
            turn = turn + 1

            # Run the MCTS algo and return an action
            if turn < turns_until_tau0:
                action, pi, MCTS_value, NN_value = players[state.playerTurn]['agent'].act(state, 1)
            else:
                action, pi, MCTS_value, NN_value = players[state.playerTurn]['agent'].act(state, 0)

            if memory != None:
                print('action: %d', action)
                print('MCTS perceived value for %s: %f', state.pieces[str(state.playerTurn)],
                            MCTS_value, 2)
                print('NN perceived value for %s: %f', state.pieces[str(state.playerTurn)], NN_value, 2)
                print('====================')

                # Commit the move to memory
                memory.commit_stmemory(env.identities, state, pi)

            # Do the action
            state, value, done, _ = env.step(
                action)  # the value of the newState from the POV of the new playerTurn i.e. -1 if the previous player played a winning move

            if done == 1:
                if memory != None:
                    # If the game is finished, assign the values correctly to the game moves
                    for move in memory.stmemory:
                        if move['playerTurn'] == state.playerTurn:
                            move['value'] = value
                        else:
                            move['value'] = -value

                    memory.commit_ltmemory()

                if value == 1:
                    scores[players[state.playerTurn]['name']] = scores[players[state.playerTurn]['name']] + 1
                    if state.playerTurn == 1:
                        sp_scores['sp'] = sp_scores['sp'] + 1
                    else:
                        sp_scores['nsp'] = sp_scores['nsp'] + 1

                elif value == -1:
                    scores[players[-state.playerTurn]['name']] = scores[players[-state.playerTurn]['name']] + 1

                    if state.playerTurn == 1:
                        sp_scores['nsp'] = sp_scores['nsp'] + 1
                    else:
                        sp_scores['sp'] = sp_scores['sp'] + 1

                else:
                    scores['drawn'] = scores['drawn'] + 1
                    sp_scores['drawn'] = sp_scores['drawn'] + 1

                pts = state.score
                points[players[state.playerTurn]['name']].append(pts[0])
                points[players[-state.playerTurn]['name']].append(pts[1])

    return (scores, memory, points, sp_scores)


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
