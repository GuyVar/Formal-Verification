import subprocess
import math
import time

def run_nuxmv(model_filename):
    nuxmv_process = subprocess.Popen(["nuXmv", model_filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    output_filename = model_filename.split(".")[0] + ".out"
    stdout, _ = nuxmv_process.communicate()

    with open(output_filename, "w") as f:
        f.write(stdout)
    return output_filename

def parse_board(board_str):
    lines = board_str.split('\n')
    board = [list(line.strip()) for line in lines if line.strip()]
    return board

def generate_smv_model(board, box_coords, goal_coords, steps_limit):
    n = len(board)
    m = len(board[0])

    smv_model = f"MODULE main\nVAR\n"

    for i in range(n):
        for j in range(m):
            if board[i][j] != '#':
                smv_model += f"    pos_{i}_{j} : 1..3;\n"
    smv_model += f"    steps_counter : 0..{steps_limit};\n"

    smv_model += f"INIT\n"
    init_state = []
    for i in range(n):
        for j in range(m):
            if board[i][j] == '_':
                init_state.append(f"pos_{i}_{j} = 1")
            elif board[i][j] == '$' and i == box_coords[0] and j == box_coords[1] :
                init_state.append(f"pos_{i}_{j} = 2")
            elif board[i][j] == '@':
                init_state.append(f"pos_{i}_{j} = 3")
            elif board[i][j] == '.':
                init_state.append(f"pos_{i}_{j} = 1")
            elif board[i][j] == '*' and i == box_coords[0] and j == box_coords[1] :
                init_state.append(f"pos_{i}_{j} = 2")
            elif board[i][j] == '+':
                init_state.append(f"pos_{i}_{j} = 3")

    smv_model += " & ".join(init_state) 
    smv_model += f" & steps_counter = 0\n"

    smv_model += f"TRANS\n   case\n"
    transitions = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def valid_coords(x, y):
        return 0 <= x < m and 0 <= y < n and board[y][x] != '#'
    
    def valid_for_keeper(x, y):
        return  0 <= x < m and 0 <= y < n and board[y][x] != '#' and board[y][x] != '$' and board[y][x] != '*'

    true_list = []
    true_list.append(f"       TRUE:\n")    
    for y in range(n):
        for x in range(m):
            if valid_for_keeper(x, y):
                for dx, dy in directions:
                    nx, ny = x + dx, y + dy
                    if valid_coords(nx, ny):
                        transitions.append(f"    (steps_counter < {steps_limit} & pos_{y}_{x} = 3 & pos_{ny}_{nx} = 1):\n")
                        transitions.append(f"       next(pos_{y}_{x}) = 1 &\n       next(pos_{ny}_{nx}) = 3 &\n       next(steps_counter) = steps_counter + 1 \n")
                        for i in range(n):
                            for j in range(m):
                                if not (i == y and j == x) and not (i == ny and j == nx) and valid_coords(j, i):
                                    transitions.append(f"       & next(pos_{i}_{j}) = pos_{i}_{j} \n")   
                        transitions.append(';')
                        if valid_for_keeper(x + 2 * dx, y + 2 * dy):
                            nnx, nny = x + 2 * dx, y + 2 * dy
                            transitions.append(f"    (steps_counter < {steps_limit} & pos_{y}_{x} = 3 & pos_{ny}_{nx} = 2 & pos_{nny}_{nnx} = 1):\n")
                            transitions.append(f"       (next(pos_{y}_{x}) = 1 &\n       next(pos_{ny}_{nx}) = 3 &\n       next(pos_{nny}_{nnx}) = 2 &\n       next(steps_counter) = steps_counter + 1);\n") 

            if valid_coords(x, y):
                true_list.append(f"       (next(pos_{y}_{x}) = pos_{y}_{x})&")

    true_list.append(f"       (next(steps_counter) = steps_counter);")
    smv_model += "".join(transitions) + "\n"
    smv_model += " \n ".join(true_list) + "\n"
    smv_model += "   esac;\n"

    smv_model += f"LTLSPEC\n   ! (F (pos_{goal_coords[0]}_{goal_coords[1]} = 2));\n"

    return smv_model

def solve_sokoban_iteratively(board_str):
    board = parse_board(board_str)
    boxes = [(i, j) for i in range(len(board)) for j in range(len(board[0])) if board[i][j] in ['$', '*']]
    goals = [(i, j) for i in range(len(board)) for j in range(len(board[0])) if board[i][j] in ['.', '*', '+']]
    
    steps_limit = 60  # You can adjust this limit as needed
    total_iterations = 0
    start_time = time.time()
    final_results = 0

    for box, goal in zip(boxes, goals):
        smv_model = generate_smv_model(board, box, goal, steps_limit)
        model_filename = "sokoban_temp_Board4.smv"
        with open(model_filename, "w") as f:
            f.write(smv_model)

        iteration_start_time = time.time()
        output_filename = run_nuxmv(model_filename)
        iteration_end_time = time.time()
        total_iterations += 1

        with open(output_filename, "r") as f:
            output_str = f.read()

        if "is true" in output_str:
            print(f"Iteration {total_iterations}: Box at {box} to Goal at {goal} - Not Winnable!")
            final_results += 1

        else:
            print(f"Iteration {total_iterations}: Box at {box} to Goal at {goal} - Winnable!")
            final_results += 0

        print(f"Iteration {total_iterations} Runtime: {iteration_end_time - iteration_start_time:.2f} seconds")

    if final_results > 0:
        print('Not Winnable')
    
    else:  print('Winnable!!!')


    end_time = time.time()
    print(f"Total Iterations: {total_iterations}")
    print(f"Total Runtime: {end_time - start_time:.2f} seconds")

# Example Sokoban board in XSB format

'''
board_xsb = """\
#########
####.####
####$####
####_####
#.$_@_$.#
####_####
####$####
####.####
#########
"""
'''

'''
board_xsb = """\
#####
#@$.#
#####
"""
'''


board_xsb = """\
#########
#@______#
#_______#
#_____..#
#____#$$#
#____#__#
#____#__#
#########
"""


# Solve Sokoban board iteratively
solve_sokoban_iteratively(board_xsb)
