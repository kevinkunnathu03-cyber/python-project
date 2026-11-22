
board = [" "] * 9
player = "X"

while True:

    print("\n", board[0], "|", board[1], "|", board[2])
    print("---+---+---")
    print("", board[3], "|", board[4], "|", board[5])
    print("---+---+---")
    print("", board[6], "|", board[7], "|", board[8])

    pos = int(input("Player " + player + " enter position (1-9): "))

    if pos < 1 or pos > 9:
        print("Invalid position!")
        continue

    if board[pos - 1] != " ":
        print("Position already taken!")
        continue

    board[pos - 1] = player

    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]

    won = False

    for w in wins:
        if board[w[0]] == board[w[1]] == board[w[2]] != " ":
            won = True
            break

    if won:
        print("Player", player, "wins!")
        break

    if " " not in board:
        print("Game Draw!")
        break

    if player == "X":
        player = "O"
    else:
        player = "X"

print("Game Over!")
