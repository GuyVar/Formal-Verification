import subprocess
import math

# Function to run nuXmv with a given model file and save the output
def run_nuxmv(model_filename):
    nuxmv_process = subprocess.Popen(["nuXmv", model_filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    output_filename = model_filename.split(".")[0] + ".out"

    stdout, _ = nuxmv_process.communicate()

    # Save output to file
    with open(output_filename, "w") as f:
        f.write(stdout)
    print(f"Output saved to {output_filename}")

    return output_filename

# Function to parse Sokoban board from XSB format
def parse_board(board_str):
    lines = board_str.split('\n')
    board = [list(line.strip()) for line in lines if line.strip()]
    return board

# Function to generate SMV model for Sokoban board
def generate_smv_model(board):
    n = len(board) #row
    m = len(board[0]) #coloum

    print(f'm {m} n {n}')
    
    smv_model = f"MODULE main\n"
    smv_model += f"VAR\n"
    
    
    
    # Define variables for each position on the board
    for i in range(n):
        for j in range(m):
            if board[i][j] != '#':
                smv_model += f"    pos_{i}_{j} : 1..3;\n"  # 1: empty, 2: box, 3: keeper

    #smv_model += f"    x_keeper : 0..{m-1};\n"  
    #smv_model += f"    y_keeper : 0..{n-1};\n"  
    smv_model += f"    steps_counter : 0..60;\n"

    # Initial state constraints
    # 1: empty (floor or goal), 2: box (on goal or not), 3: keeper (on goal or not)

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
        return  0 <= x < m and 0 <= y < n and board[y][x] != '#' and board[y][x] != '$' and board[y][x] != '*'


    # (x,y) keaper location

    #math.sqrt((nx-x_keeper)**2 + (ny-y_keeper)**2) == 1
    true_list = []
    true_list.append(f"       TRUE:\n")    
    for y in range(n):
        for x in range(m):

            if valid_for_keeper(x,y):

                for dx, dy in directions:
                    nx, ny = x + dx, y + dy
                    if valid_coords(nx, ny):
                        print(nx, ny)
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
                            #for i in range(n):
                            #    for j in range(m):
                            #        if not (i == y and j == x) and not (i == ny and j == nx) and valid_coords(j, i) and not (i == nny and j == nnx):
                            #            transitions.append(f"       & next(pos_{i}_{j}) = pos_{i}_{j} \n")   
                            #transitions.append(';')

            if valid_coords(x, y):
                true_list.append(f"       (next(pos_{y}_{x}) = pos_{y}_{x})&")

    #true_list[-1] = true_list[-1][:-1]
    true_list.append(f"       (next(steps_counter) = steps_counter);")
    #true_list[-1] += ';'
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

    print('done 1')
    # Write SMV model to a temporary file
    model_filename = "sokoban_board4.smv"
    with open(model_filename, "w") as f:
        f.write(smv_model)

    print('done 2')

    # Run nuXmv to check for winning condition
    output_filename = run_nuxmv(model_filename)

    # Parse nuXmv output to check if winnable and extract solution
    with open(output_filename, "r") as f:
        output_str = f.read()

    if "is true" in output_str:
        print("Board is not winnable!")
        # Extract and print winning solution (LURD format)
        # Add solution extraction logic here based on nuXmv_output
    else:
        print("Board is winnable.")

    print('done 3')

# Example Sokoban board in XSB format


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


# Solve Sokoban board
solve_sokoban(board_xsb)
