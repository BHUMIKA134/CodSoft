#!/usr/bin/env python3
"""
Rock-Paper-Scissors — Internship Project
Features:
- Tkinter GUI (buttons & labels)
- Randomized computer choice
- Game logic with win/lose/tie
- Score tracking across rounds
- Play again/reset functionality
"""

import tkinter as tk
from tkinter import messagebox
import random

# -----------------------------
# Main Game Class
# -----------------------------
class RockPaperScissors:
    def __init__(self, root):
        self.root = root
        self.root.title("Rock-Paper-Scissors Game")
        self.root.geometry("500x400")
        self.root.config(bg="#f5f5f5")

        # Scores
        self.user_score = 0
        self.computer_score = 0

        # Heading
        self.heading = tk.Label(
            root, text="Rock-Paper-Scissors",
            font=("Helvetica", 20, "bold"),
            bg="#f5f5f5", fg="#333"
        )
        self.heading.pack(pady=10)

        # Frame for buttons
        self.button_frame = tk.Frame(root, bg="#f5f5f5")
        self.button_frame.pack(pady=20)

        # Choices buttons
        self.rock_btn = tk.Button(
            self.button_frame, text="Rock 🪨", width=10,
            command=lambda: self.play("rock"),
            font=("Helvetica", 14), bg="#dfe6e9"
        )
        self.paper_btn = tk.Button(
            self.button_frame, text="Paper 📄", width=10,
            command=lambda: self.play("paper"),
            font=("Helvetica", 14), bg="#dfe6e9"
        )
        self.scissors_btn = tk.Button(
            self.button_frame, text="Scissors ✂️", width=10,
            command=lambda: self.play("scissors"),
            font=("Helvetica", 14), bg="#dfe6e9"
        )

        self.rock_btn.grid(row=0, column=0, padx=10)
        self.paper_btn.grid(row=0, column=1, padx=10)
        self.scissors_btn.grid(row=0, column=2, padx=10)

        # Result Display
        self.result_label = tk.Label(
            root, text="Make your choice!",
            font=("Helvetica", 16), bg="#f5f5f5", fg="#2d3436"
        )
        self.result_label.pack(pady=20)

        # Score Display
        self.score_label = tk.Label(
            root,
            text=f"User: {self.user_score}  |  Computer: {self.computer_score}",
            font=("Helvetica", 14), bg="#f5f5f5", fg="#0984e3"
        )
        self.score_label.pack(pady=10)

        # Reset Button
        self.reset_btn = tk.Button(
            root, text="Reset Game", command=self.reset_game,
            font=("Helvetica", 12), bg="#fab1a0"
        )
        self.reset_btn.pack(pady=15)

    # -----------------------------
    # Game Logic
    # -----------------------------
    def play(self, user_choice):
        choices = ["rock", "paper", "scissors"]
        computer_choice = random.choice(choices)

        # Determine result
        if user_choice == computer_choice:
            result = "It's a Tie!"
        elif (user_choice == "rock" and computer_choice == "scissors") or \
             (user_choice == "scissors" and computer_choice == "paper") or \
             (user_choice == "paper" and computer_choice == "rock"):
            result = "You Win! 🎉"
            self.user_score += 1
        else:
            result = "Computer Wins! 🤖"
            self.computer_score += 1

        # Update result display
        self.result_label.config(
            text=f"You: {user_choice.capitalize()} | Computer: {computer_choice.capitalize()}\n{result}"
        )

        # Update score display
        self.score_label.config(
            text=f"User: {self.user_score}  |  Computer: {self.computer_score}"
        )

    # -----------------------------
    # Reset Game
    # -----------------------------
    def reset_game(self):
        self.user_score = 0
        self.computer_score = 0
        self.result_label.config(text="Make your choice!")
        self.score_label.config(
            text=f"User: {self.user_score}  |  Computer: {self.computer_score}"
        )
        messagebox.showinfo("Game Reset", "Scores have been reset!")

# -----------------------------
# Run the App
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    game = RockPaperScissors(root)
    root.mainloop()
