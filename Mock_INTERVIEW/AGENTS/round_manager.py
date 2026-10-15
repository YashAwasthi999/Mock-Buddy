AVAILBLE_ROUNDS = {
    "1": {"name": "HR", "num_questions": 5},
    "2": {"name": "Technical", "num_questions": 5},
    "3": {"name": "Managerial", "num_questions": 5},
    "4": {"name": "General", "num_questions": 5}
}


def select_round() -> dict | None:
    """Ask the user to select an interview round."""
    print("\nSelect an Interview Round: ")
    for key, round_info in AVAILBLE_ROUNDS.items():
        print(f"{key}. {round_info['name']}")

    while True:
        choice = input("Enter the number of the round you want to take: ")
        if choice in AVAILBLE_ROUNDS:
            return AVAILBLE_ROUNDS[choice]
        else:
           print("Invalid choice. Please enter a valid number.")
