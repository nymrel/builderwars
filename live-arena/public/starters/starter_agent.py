#!/usr/bin/env python3
"""Dependency-free BuilderWars starter. Accepts raw move JSON or the local bridge prompt.
No network, file access, subprocesses or model calls. Edit choose_move to build your agent.
"""
import json
import sys

MAX_BYTES = 64000
MODEL = 'builderwars-starter-python-v1'
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

def read_request(text):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Move request exceeds 64KB')
    # bridge.py sends one fixed instruction line followed by one JSON data line.
    payload = text.strip() if text.lstrip().startswith('{') else text.rstrip().rsplit('\n', 1)[-1].strip()
    request = json.loads(payload)
    legal = request.get('legalMoves')
    if not isinstance(legal, list) or not 1 <= len(legal) <= 256 or any(not isinstance(m, str) or len(m) > 100 for m in legal):
        raise ValueError('A bounded nonempty legalMoves list is required')
    if request.get('turn') not in (0, 1):
        raise ValueError('turn must be 0 or 1')
    return request

def choose_move(request):
    legal = request['legalMoves']
    if request.get('game', {}).get('kind') == 'tictactoe':
        cells = request.get('position')
        if not isinstance(cells, list) or len(cells) != 9 or any(c not in ('', 'w', 'b') for c in cells):
            raise ValueError('Expected the standard tic-tac-toe board')
        own = 'w' if request['turn'] == 0 else 'b'
        for mark in (own, 'b' if own == 'w' else 'w'):
            for move in legal:
                if not move.isdigit() or not 0 <= int(move) < 9 or cells[int(move)]:
                    raise ValueError('Legal move contradicts the supplied board')
                next_cells = cells.copy(); next_cells[int(move)] = mark
                if any(all(next_cells[i] == mark for i in line) for line in LINES):
                    return move
        for move in ['4', '0', '2', '6', '8', '1', '3', '5', '7']:
            if move in legal:
                return move
    return legal[0]

def answer(request):
    move = choose_move(request)
    if move not in request['legalMoves']:
        raise ValueError('Agent returned a move outside the authoritative list')
    return {'move': move, 'comment': 'Starter: immediate win, immediate defense, then a fixed preference.', 'model': MODEL, 'tokens': None}

def check():
    request = {'game': {'kind':'tictactoe'}, 'position':['w','w','','b','b','','','',''], 'turn':0, 'legalMoves':['2','5','6','7','8']}
    assert answer(read_request(json.dumps(request)))['move'] == '2'
    assert answer(read_request('Play the supplied game. Data follows.\n' + json.dumps(request)))['move'] == '2'
    try:
        read_request('{"turn":0,"legalMoves":[]}')
        raise AssertionError('Malformed request was accepted')
    except ValueError:
        pass
    print(json.dumps({'checked':True,'model':MODEL,'providerCalls':0,'protocol':'raw JSON and local bridge prompt'}))

if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--check']:
            check()
        elif sys.argv[1:]:
            raise ValueError('Usage: python starter_agent.py [--check]')
        else:
            text = sys.stdin.read(MAX_BYTES + 1)
            print(json.dumps(answer(read_request(text))))
    except (ValueError, AssertionError, TypeError, KeyError) as error:
        print('Starter error: ' + str(error), file=sys.stderr)
        sys.exit(1)
