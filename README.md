# CS50-Reader

CS50-Reader is a web-based RSS reader, inspired by the defunct Google Reader. The backend is written in Python using Flask/SQLite; and the front end is written in Javascript using Bootstrap and jQuery. Although the basis for this project was my final project for CS50, as I've continued to work on it I decided that it should have it's own repo. There have been significant logic changes since the CS50 version. ;)

## Features

- **Subscribe to feeds**: Easily add feeds to your subscriptions.
- **View articles by read/unread status**: View your articles by read/unread status.

## Installation

To get started with CS50-Reader, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/vivaceuk/CS50-Reader.git
   cd CS50-Reader
2. **Install the Dependencies**:
   ```bash
   pip install -r requirements.txt
3. **Run the Application**:
   ```bash
   flask --app cs50reader run --debug
