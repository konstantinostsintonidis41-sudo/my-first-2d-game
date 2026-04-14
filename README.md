# 🎮 Epic Indie Platformer

A dynamic 2D platformer game built entirely in **Python** using the **Pygame** library. 
This project was created to practice object-oriented programming, game loops, and custom physics engines.

## ✨ Key Features
What makes this platformer stand out:
- **Custom Physics Engine:** Implements gravity, friction, momentum, and acceleration for smooth player movement.
- **Advanced Mechanics:** 
  - **Coyote Time:** Gives players a few split-seconds to jump even after walking off an edge, improving UX and game feel.
  - **Wall Jumping & Sliding:** Players can slide down walls and perform dynamic wall-jumps.
- **Smooth Camera Tracking:** The camera calculates the distance from the player and follows them smoothly across the level.
- **Level Entities:** Patrolling enemies, deadly lava hazards, bounce pads, and collectible coins for score tracking.
- **Parallax-like Background:** Infinite scrolling background relative to camera movement.

## 🚀 How to Run the Game

To play the game locally on your machine, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/konstantinostsintonidis41-sudo/my-first-2d-game.git
   Install Pygame:
Make sure you have Python installed, then run:
code pip install pygame
Run the game:
code python platformer.py
(Note: Ensure all image assets like bg.png, idle.png, etc., are in the same directory).
⌨️ Controls
[W], [UP Arrow], or [SPACE] : Jump (Press against a wall to Wall-Jump!)
[A],[D] or [Left/Right Arrows] : Move Left / Right
[R] : Restart (After reaching the final door or falling)
🛠️ Tech Stack
Language: Python 3.x
Library: Pygame
Architecture: Object-Oriented Programming (OOP)
Created by Konstantinos Tsintonidis - Student of Applied Informatics.
