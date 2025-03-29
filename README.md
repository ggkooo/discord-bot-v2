# Discord Bot V2

This is a Discord bot for managing a store called Spectre Store. The bot provides various functionalities such as ticket creation, automatic messaging, and user notifications.

## Features

- **Ticket System**: Users can create tickets for support, purchases, or media creator inquiries.
- **Automatic Messaging**: Automatically send product messages at specified intervals.
- **User Notifications**: Notify when a user joins or leaves the server, and when messages are edited or deleted.
- **Transcript Saving**: Save transcripts of ticket channels, including messages, embeds, and attachments.

## Requirements

- Python 3.8+
- MongoDB
- Discord Bot Token

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/ggkooo/discord-bot-v2.git
    cd discord-bot-v2
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install package_name
    ```

4. Create a `.env` file in the root directory and add your Discord bot token and MongoDB URI:
    ```dotenv
    DISCORD_TOKEN=your_discord_token
    MONGO_URI=your_mongodb_uri
    ```

## Usage

1. Run the bot:
    ```sh
    python main.py
    ```

2. The bot will be online and ready to use in your Discord server.

## Commands

- `!clear`: Clear the last 100 messages in the channel (Admin only).
- `!ban <member> [reason]`: Ban a member from the server (Admin only).
- `!ticket`: Create a ticket embed for support, purchases, or media creator inquiries (Admin only).
- `!auto_msg <name> <interval>`: Start automatic messaging for a product (Admin only).
- `!all_auto_msg <interval>`: Start automatic messaging for all products (Admin only).
- `!stop_auto_msg`: Stop all automatic messaging tasks (Admin only).

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - Python library for Discord API
- [pymongo](https://github.com/mongodb/mongo-python-driver) - Python driver for MongoDB
- [dotenv](https://github.com/theskumar/python-dotenv) - Python library to manage environment variables

## Contact

For any questions or issues, please open an issue on the GitHub repository or contact the maintainer at giordanoberwig@proton.me.