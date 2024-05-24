import subprocess
import time
import math

# Function to run nuXmv with a given model file and save the output
def run_nuxmv(model_filename, engine):

    if engine == "bdd":
        commands = "go\ncheck_ltlspec\nquit\n"
    elif engine == "sat":
        commands = "go_bmc\ncheck_ltlspec_bmc -k 30\nquit\n"
    else:
        raise ValueError("Unsupported solver specified")
    #commands = f"set {engine}\nread_model {model_filename}\ngo\ncheck_ltlspec\nquit\n"


    nuxmv_process = subprocess.Popen(["nuXmv", "-int", model_filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    start_time = time.time()
    stdout, stderr = nuxmv_process.communicate(commands)
    end_time = time.time()

    output_filename = model_filename.split(".")[0] + f"_{engine}.out"

    # Save output to file
    with open(output_filename, "w") as f:
        f.write(stdout)
    print(f"Output saved to {output_filename}")

    return end_time - start_time, output_filename

# Function to parse Sokoban board from XSB format
def parse_board(board_str):
    lines = board_str.split('\n')
    board = [list(line.strip()) for line in lines if line.strip()]
    return board

# Function to generate SMV model for Sokoban board
def generate_smv_model(board):
    n = len(board)  # number of rows
    m = len(board[0])  # number of columns

    smv_model = f"MODULE main\nVAR\n"

    # Define variables for each position on the board
    for i in range(n):
        for j in range(m):
            if board[i][j] != '#':
                smv_model += f"    pos_{i}_{j} : 1..3;\n"  # 1: empty, 2: box, 3: keeper

    smv_model += f"    steps_counter : 0..60;\n"

    # Initial state constraints
    smv_model += f"INIT\n"
    init_state = []

    for i in range(n):
        for j in range(m):
            if board[i][j] == '_':
                init_state.append(f"pos_{i}_{j} = 1")
            elif board[i][j] == '$':
                init_state.append(f"pos_{i}_{j} = 2")
            elif board[i][j] == '@':
                init_state.append(f"pos_{i}_{j} = 3")
            elif board[i][j] == '.':
                init_state.append(f"pos_{i}_{j} = 1")
            elif board[i][j] == '*':
                init_state.append(f"pos_{i}_{j} = 2")
            elif board[i][j] == '+':
                init_state.append(f"pos_{i}_{j} = 3")

    smv_model += " & ".join(init_state) 
    smv_model += f" & steps_counter = 0\n"

    # Generate transitions
    smv_model += f"TRANS\n"
    smv_model += f"   case\n"
    transitions = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def valid_coords(x, y):
        return 0 <= x < m and 0 <= y < n and board[y][x] != '#'
    
    def valid_for_keeper(x, y):
        return 0 <= x < m and 0 <= y < n and board[y][x] != '#' and board[y][x] != '$' and board[y][x] != '*'

    true_list = []
    true_list.append(f"       TRUE:\n")    
    for y in range(n):
        for x in range(m):
            if valid_for_keeper(x, y):
                for dx, dy in directions:
                    nx, ny = x + dx, y + dy
                    if valid_coords(nx, ny):
                        # Player move
                        transitions.append(f"    (steps_counter < 60 & pos_{y}_{x} = 3 & pos_{ny}_{nx} = 1):\n")
                        transitions.append(f"       next(pos_{y}_{x}) = 1 &\n       next(pos_{ny}_{nx}) = 3 &\n       next(steps_counter) = steps_counter + 1 \n")
                        for i in range(n):
                            for j in range(m):
                                if not (i == y and j == x) and not (i == ny and j == nx) and valid_coords(j, i):
                                    transitions.append(f"       & next(pos_{i}_{j}) = pos_{i}_{j} \n")   
                        transitions.append(';')
                        # Box push
                        if valid_for_keeper(x + 2 * dx, y + 2 * dy):
                            nnx, nny = x + 2 * dx, y + 2 * dy
                            transitions.append(f"    (steps_counter < 60 & pos_{y}_{x} = 3 & pos_{ny}_{nx} = 2 & pos_{nny}_{nnx} = 1):\n")
                            transitions.append(f"       (next(pos_{y}_{x}) = 1 &\n       next(pos_{ny}_{nx}) = 3 &\n       next(pos_{nny}_{nnx}) = 2 &\n       next(steps_counter) = steps_counter + 1);\n") 

            if valid_coords(x, y):
                true_list.append(f"       (next(pos_{y}_{x}) = pos_{y}_{x})&")

    true_list.append(f"       (next(steps_counter) = steps_counter);")
    smv_model += "".join(transitions) + "\n"
    smv_model += " \n ".join(true_list) + "\n"
    smv_model += "   esac;\n"

    # Define winning condition (all boxes on goals)
    smv_model += f"LTLSPEC\n   ! (F ("
    goals = [(i, j) for i in range(n) for j in range(m) if board[i][j] == '.']
    for idx, (i, j) in enumerate(goals):
        if idx > 0:
            smv_model += " & "
        smv_model += f"(pos_{i}_{j} = 2)"
    smv_model += "));\n"

    return smv_model

# Function to solve Sokoban using nuXmv and return the solution
def solve_sokoban(board_str):
    board = parse_board(board_str)
    smv_model = generate_smv_model(board)

    # Write SMV model to a temporary file
    model_filename = "sokoban2.smv"
    with open(model_filename, "w") as f:
        f.write(smv_model)

    # Run nuXmv to check for winning condition using BDD
    bdd_time, bdd_output_filename = run_nuxmv(model_filename, "bdd")
    #bdd_time, bdd_output_filename = 10, 'sokoban2_bdd.out'


    # Run nuXmv to check for winning condition using SAT
    sat_time, sat_output_filename = run_nuxmv(model_filename, "sat")

    # Parse nuXmv output to check if winnable and extract solution
    with open(bdd_output_filename, "r") as f:
        bdd_output_str = f.read()

    with open(sat_output_filename, "r") as f:
        sat_output_str = f.read()

    print("BDD Solver Output:")
    if "is true" in bdd_output_str:
        print("Board is not winnable with BDD solver!")
    else:
        print("Board is winnable with BDD solver.")
    
    print(f"BDD Solver Time: {bdd_time:.2f} seconds")

    print("SAT Solver Output:")
    if "is false" in sat_output_str:
        print("Board is winnable with SAT solver!")
    else:
        print("Board is not winnable with SAT solver.")
    
    print(f"SAT Solver Time: {sat_time:.2f} seconds")

    print("Performance Comparison:")
    if bdd_time < sat_time:
        print("BDD solver is more efficient.")
    else:
        print("SAT solver is more efficient.")

# Example Sokoban board in XSB format



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
board_xsb = """\
#####
#@$.#
#####
"""


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

'''


# Solve Sokoban board
solve_sokoban(board_xsb)
