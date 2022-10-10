import argparse
import asyncio
import json
from datetime import datetime

from logger import logger


"""Archive of messages"""
HISTORY = []

"""Last visit of user"""
USER_HISTORY = {}

"""Users with their transport options"""
USERS = {}


class ChatServer(asyncio.Protocol):
    """TCP-server"""

    def __init__(self, connections):
        self.transport = None
        self.connections = connections
        self.user = None
        self.peername = ''

    def connection_made(self, transport):
        self.connections += [transport]
        self.peername = transport.get_extra_info('sockname')
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        if isinstance(exc, ConnectionResetError):
            self.connections.remove(self.transport)
        else:
            logger.info(exc)
        err = '{} disconnected ({}:{})'.format(self.user, *self.peername)
        message = self.make_msg(err, '[Server]', 'servermsg')
        print(err)
        time_now = datetime.now()
        USER_HISTORY[self.user] = time_now
        for connection in connections:
            connection.write(message)

    def data_received(self, data: bytes) -> None:
        if data:
            if not self.user:
                self.user = data.decode()
                USERS[self.user] = self.transport
                msg = '{} connected ({}:{})'.format(self.user, *self.peername)
                print(msg)
                message = self.make_msg(msg, '[Server]', 'servermsg')
                for connection in connections:
                    connection.write(message)
            else:
                message = data.decode()
                if message[0] == '/':
                    self.run_command(message)
                else:
                    self.check_msg(data)

    def run_command(self, message: str):
        """Method to work with user command start with /"""
        context = message.split(' ')
        if context[0] == '/w':
            try:
                command, user, *text = context
                txt = ' '.join(text)
                print('{} {} {}: {}'.format(self.user, command, user, txt))
                msg = self.make_msg(txt, self.user, 'whisper')
                address = USERS.get(user)
                address.write(msg)
            except ValueError:
                msg = self.make_msg(
                    'Unacceptable message', '[Server]', 'servermsg')
                address = USERS.get(self.user)
                address.write(msg)

    def check_msg(self, data):
        """Method to work with usual message"""
        message = data.decode()
        print("{}: {}".format(self.user, message))
        msg = self.make_msg(message, self.user)
        for connection in self.connections:
            connection.write(msg)

    def make_msg(self, message, author, *event):
        """
        Method to make dict object
        {
            "content": "some message",
            "author": "some author or server",
            "timestamp": datetime.now(),
            "event": message or servermsg or whisper,
        }
        """
        msg = dict()
        msg['content'] = message
        msg['author'] = author
        time_now = datetime.now()
        msg["timestamp"] = "{hour}:{minute}:{sec}".format(
            hour=str(time_now.hour).zfill(2),
            minute=str(time_now.minute).zfill(2),
            sec=str(time_now.second).zfill(2)
        )
        if event:
            msg["event"] = event[0]
        else:
            msg["event"] = "message"
        HISTORY.append(msg)
        return self.send_msg(msg)

    def send_msg(self, message):
        """Method to make encoded json from dict message"""
        return json.dumps(message).encode()


if __name__ == "__main__":
    logger.info('Start app')
    parser = argparse.ArgumentParser(description="Server settings")
    parser.add_argument("--addr", default="127.0.0.1", type=str)
    parser.add_argument("--port", default=5000, type=int)
    args = vars(parser.parse_args())

    connections = []
    loop = asyncio.get_event_loop()
    coro = loop.create_server(
        lambda: ChatServer(connections),
        args["addr"],
        args["port"]
    )
    server = loop.run_until_complete(coro)

    logger.info('Serving on {}:{}'.format(*server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
    logger.info('Close app')
