import argparse
import asyncio
import json
from sys import stdout

from colorama import Fore, Style


class Client(asyncio.Protocol):
    """TCP-client"""

    def __init__(self, loop, user):
        self.user = user
        self.is_active = False
        self.loop = loop
        self.last_message = ''

    def connection_made(self, transport) -> None:
        self.sockname = transport.get_extra_info('sockname')
        self.transport = transport
        self.transport.write(self.user.encode())
        self.is_active = True

    def connection_lost(self, exc) -> None:
        self.is_active = False
        self.loop.stop()

    def data_received(self, data: bytes) -> None:
        if data:
            message = json.loads(data.decode())
            self.process_message(message)

    def process_message(self, message):
        """Method to colour input data"""
        try:
            if message['event'] == 'whisper':
                content = (Fore.MAGENTA
                           + ('{timestamp} | {author}: {content}')
                           .format(**message))
                print(Style.RESET_ALL)
            elif message['event'] == 'message':
                content = (Fore.LIGHTYELLOW_EX
                           + ('{timestamp} | {author}: {content}')
                           .format(**message))
                print(Style.RESET_ALL)
            elif message['event'] == 'servermsg':
                content = (Fore.CYAN
                           + ('{timestamp} | {author} {content}')
                           .format(**message))
                print(Style.RESET_ALL)
            self.output(content.strip() + '\n')
        except KeyError:
            print('Malformed message')

    def send(self, data):
        """Send method"""
        if data and self.user:
            command = data.split(' ')
            if command[0] == '/w':
                self.transport.write(data.encode())
            else:
                self.last_message = (('{author}: {content}').
                                     format(author=self.user, content=data))
                self.transport.write(data.encode())

    async def getmsgs(self, loop):
        self.output = self.stdoutput
        self.output("Connected to {0}:{1}\n".format(*self.sockname))
        while True:
            msg = await loop.run_in_executor(
                None,
                input,
                "{}: ".format(self.user)
            )
            self.send(msg)

    def stdoutput(self, data):
        if self.last_message.strip() == data.strip():
            return
        else:
            stdout.write(data.strip() + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client settings")
    parser.add_argument("--user", default='user', type=str)
    parser.add_argument("--addr", default="127.0.0.1", type=str)
    parser.add_argument("--port", default=5000, type=int)
    args = vars(parser.parse_args())

    loop = asyncio.get_event_loop()
    userClient = Client(loop, args["user"])
    coro = loop.create_connection(
        lambda: userClient,
        args["addr"],
        args["port"]
    )
    server = loop.run_until_complete(coro)

    asyncio.ensure_future(userClient.getmsgs(loop))

    loop.run_forever()
    loop.close()
