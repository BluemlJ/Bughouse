"""
This file contains the game rules.
It gives the logic behind moving from one game state to another, given a chosen action. For example, given the intial board and the move g1f3, the "takeAction" method return a new game state, with the move played.
You can replace the game.py file with any game file that conforms to the same API and the algorithm will in principal, learn strategy through self play, based on the rules you have given it.
"""
import copy

import chess
import numpy as np
import logging
from chess.variant import BughouseBoards, SingleBughouseBoard


# board_number  0 for left 1 for right board
class Game:
    def __init__(self, board_number):
        """

        :param board_number: 0 for left 1 for right board
        """
        self.board_number = board_number
        self.currentPlayer = 1
        boards = BughouseBoards()
        self.gameState = GameState(boards, self.board_number, self.currentPlayer)
        self.actionSpace = np.zeros(135)

        self.name = 'bughouse'

        self.action_size = len(self.actionSpace)
        self.state_size = len(self.gameState.binary)

        """
        TODO Do we need this stuff?
        self.pieces = {'1':'X', '0': '-', '-1':'O'}
        self.grid_shape = (6,7)
        self.input_shape = (2,6,7)
        """

    def reset(self):
        self.currentPlayer = 1
        boards = BughouseBoards()
        self.gameState = GameState(boards, self.board_number, self.currentPlayer)
        return self.gameState

    def step(self, action):
        next_state, value, done = self.gameState.take_action(action)
        self.gameState = next_state
        self.currentPlayer = -self.currentPlayer
        info = None
        return ((next_state, value, done, info))


class GameState:
    """
    The gamestate consists out of both Bughouse Boards.
    The board number decides on which board the engine is playing
    Moves/actions are passed as numpy arrays.

    TODO:
    -id does not include whether kings/rooks moved
    -functions to update partner board
    -Do we really need the representation as numpy arrays for the actions?
    """

    def __init__(self, boards, board_number, player_turn):
        """
        :param boards: BughouseBoards
        :param board_number: 0 for left 1 for right board
        :param player_turn: 1 white -1 black
        """
        self.boards = boards
        self.board_number = board_number

        self.board = boards.boards[board_number]

        if board_number == 1:
            self.partner_board = boards.boards[0]
        else:
            self.partner_board = boards.boards[1]

        self.playerTurn = player_turn

        self.binary = self._binary()
        self.id = self._convert_state_to_id()
        self.allowedActions = self._allowed_actions()
        self.isEndGame = self._check_for_end()
        self.value = self._get_value()

    def _allowed_actions(self):
        allowed = [move_as_array(m) for m in list(self.board.legal_moves)]
        return allowed

    def _binary(self):
        """
        :return: The game state as a binary numpy array including both boards and pockets
        """
        b1 = board_to_array(self.board).flatten()
        b2 = board_to_array(self.partner_board).flatten()
        pockets1 = [pocket_to_array(p) for p in self.board.pockets]
        pockets2 = [pocket_to_array(p) for p in self.partner_board.pockets]

        return np.concatenate([b1,pockets1[0],pockets1[1],b2,pockets2[0],pockets2[1]])


    def _convert_state_to_id(self):
        s = self.boards.__str__()
        return "".join(s.split())

    def _check_for_end(self):
        if self.boards.is_game_over():
            return 1
        return 0

    def _get_value(self):
        """
        :return: (state, currentPlayerPoints, opponentPlayerPoints)
        """
        result = self.boards.result()
        if result == "1/2-1/2":
            return (0, 0.5, 0.5)
        elif result == "0-1":
            if self.playerTurn == 1:
                return (-1, -1, 1)
            else:
                return (1, 1, -1)
        elif result == "1-0":
            if self.playerTurn == -1:
                return (-1, -1, 1)
            else:
                return (1, 1, -1)

        return (0, 0, 0)

    def check_if_legal(self, action):
        """
        Check if move at current game state is correct and for current player playable
        :param action: action as np array
        :return: True if legal, raise Exception otherwise
        """
        is_legal_move = np.any([(action == el).all() for el in self._allowed_actions()])
        if not is_legal_move:
            # TODO make Exception as concrete as possible, maybe own class
            print("allowed actions ", [array_as_move(el) for el in self._allowed_actions()])
            print("action itself: ", action)
            raise Exception(f"Illegal Move: {array_as_move(action)} {action} Legal Moves: ",
                            [array_as_move(el) for el in self._allowed_actions()])
        return True

    def take_action(self, action):
        """
        creates a new gamestate by copying this state and making a move
        :param action:  action as np array
        :return: newState, value, done
        """

        # Checks if move is correct
        self.check_if_legal(action)

        new_boards = BughouseBoards()
        left = new_boards[0]
        right = new_boards[1]
        for move in self.boards.boards[0].move_stack:
            left.push(move)
        for move in self.boards.boards[1].move_stack:
            right.push(move)

        new_board = new_boards.boards[self.board_number]
        move = array_as_move(action)
        new_board.push(move)

        newState = GameState(new_boards, self.board_number, -self.playerTurn)

        value = 0
        done = 0

        if newState.isEndGame:
            value = newState.value[0]
            done = 1

        return (newState, value, done)

    def render(self, logger):
        logger.info(self.boards.__str__())
        logger.info('--------------')


"""
Helper functions to convert python-chess representations to numpy arrays.
"""


def move_as_array(move, color=chess.WHITE):
    """
    Converts a python-chess move to a numpy array. The color is relevant for drops.
    :param move: a python-chess move
    :param color: chess.WHITE / 1 or chess.BLACK / 0
    :return: a numpy array (135,)
    """
    move_array = np.zeros(
        128 + 6 + 1)  # first 64 from square second 64 to_ square + 6 for the drop piece + 1 for colour
    move_array[move.from_square] = 1
    move_array[64 + move.to_square] = 1
    if move.drop:
        move_array[127 + move.drop] = 1

    if color:
        move_array[-1] = 1

    return move_array


def array_as_move(action):
    """
    Converts a numpy array to a python-chess move.
    :param action: move as a numpy array (135,)  see move_as_array
    :return: python-chess move
    """
    fromSquare = np.argmax(action[0:64])
    toSquare = np.argmax(action[64:128])
    if np.max(action[128:-1]) > 0:  # move is a drop
        color = action[-1]
        piece = chess.Piece(np.argmax(action[128:-1]) + 1, color)
        return chess.Move.from_uci(piece.symbol() + "@" + chess.SQUARE_NAMES[toSquare])
    else:
        return chess.Move(fromSquare, toSquare, None)


def board_to_array(board):
    """
    Converts a single board without pockets to a binary numpy array
    The size should be:
    number of squares * number of possible figures * number of colors = 8*8*6*2
    :param board: single chess board

    TODO
    Can/should this be smaller?
    """
    array = np.zeros((64, 6, 2))
    for field,piece in board.piece_map().items():
        p_type = piece.piece_type - 1
        color = 1 if piece.color else 0
        array[field][p_type][color] = 1

    return array


def pocket_to_array(pocket):
    """
    Converts a pocket of a SingleBughouseBoard to a numpy array (6,).
    """
    d = dict(pocket.pieces)
    array = np.zeros(6)
    for piece, count in d.items():
        array[piece - 1] = count
    return array
