# Role Invite Bot

Role Invite Bot is a Discord bot that manages role invites and provides various commands to manage messages in a server.

## Features

- Create, update, and revoke role invites
- Automatically assign roles based on invite usage
- Clear messages in a channel based on various criteria (e.g., containing specific words, from bots, etc.)
- Nuke entire channels

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/role-invite-bot.git
    cd role-invite-bot
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up your environment variables:
    ```sh
    cp .env.example .env
    # Edit the .env file to include your Discord bot token and other necessary configurations
    ```

5. Run the bot:
    ```sh
    python rampage.py
    ```

## Usage

### Role Invite Commands

- **Create a Role Invite**: `!rinv create <role> [channel] [duration] [max_uses]`
- **Update a Role Invite**: `!rinv update <invite_id> <uses>`
- **Revoke a Role Invite**: `!rinv revoke <invite_id>`
- **List Role Invites**: `!rinv list`
- **Set Default Role**: `!rinv setdefault <role>`

### Clear Commands

- **Nuke a Channel**: `/clear nuke`
- **Delete Messages**: `/clear default <amount>`
- **Delete Bot Messages**: `/clear bot <amount>`
- **Delete Messages from a Member**: `/clear member <user> <amount>`
- **Delete Messages Containing a Word**: `/clear contains <word> <amount>`
- **Delete Messages Starting with a Word**: `/clear startswith <word> <amount>`
- **Delete Messages with Attachments**: `/clear attachment <amount>`
- **Delete Messages with Embeds**: `/clear embeds <amount>`
- **Delete Messages with Mentions**: `/clear mentions <amount>`

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.