import asyncio
import os
import uuid

import aiohttp.web
from jinja2 import Environment, PackageLoader, select_autoescape

from .room import Room, RoomStatus


class NinjutsuApp(object):
    def __init__(self):
        self._jinja = Environment(
            loader=PackageLoader("ninjutsu"),
            autoescape=select_autoescape(),
        )
        self._webapp = self._create_webapp()
        self._ws = {}
        self._rooms = {}
        self._loop = asyncio.get_event_loop()

    def run(self):
        port = int(os.environ.get("PORT", 8080))
        aiohttp.web.run_app(self._webapp, port=port)

    def _create_webapp(self):
        webapp = aiohttp.web.Application()
        webapp.add_routes(
            [
                aiohttp.web.get("/", self._handle_get_home),
                aiohttp.web.post("/", self._handle_new_room),
                aiohttp.web.get(r"/room/{room_id}", self._handle_get_room, name="room"),
                aiohttp.web.get(r"/room/{room_id}/ws", self._handle_room_ws),
                aiohttp.web.static("/static", os.path.join("ninjutsu", "static")),
            ]
        )
        return webapp

    async def _handle_static_file(self, request):
        pass

    async def _handle_get_home(self, request):
        return aiohttp.web.Response(
            text=self._jinja.get_template("home.html").render(),
            content_type="text/html",
        )

    async def _handle_new_room(self, request):
        location = request.app.router["room"].url_for(room_id=str(uuid.uuid4()))
        raise aiohttp.web.HTTPFound(location=location)

    async def _handle_get_room(self, request):
        room_id = request.match_info["room_id"]
        try:
            room_uuid = str(uuid.UUID(room_id))
        except Exception:
            raise aiohttp.web.HTTPNotFound()

        return aiohttp.web.Response(
            text=self._jinja.get_template("room.html").render(room_uuid=room_uuid),
            content_type="text/html",
        )

    async def _handle_room_ws(self, request):
        room_id = request.match_info["room_id"]
        try:
            room_uuid = str(uuid.UUID(room_id))
        except Exception:
            raise aiohttp.web.HTTPNotFound()

        # Is there a room object for this uuid?
        if room_uuid not in self._rooms:
            room = Room(id=room_uuid)
            room.subscribe(self._room_subscriber)
            self._rooms[room_uuid] = room
        else:
            room = self._rooms[room_uuid]

        # New player
        player = room.new_player()

        # Create websocket for the new player
        ws = aiohttp.web.WebSocketResponse()
        self._ws[player] = ws
        await ws.prepare(request)

        # Welcome player!
        await ws.send_str("WELCOME {}".format(player.id))

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                elif msg.data == "RESET":
                    room.reset()
                elif msg.data.startswith("VOTE"):
                    try:
                        value = int(msg.data.split()[1])
                    except Exception as e:
                        print(e)
                        continue
                    room.vote(player, value)
                else:
                    await ws.send_str(msg.data + "/answer")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("ws connection closed with exception %s" % ws.exception())

        print("websocket connection closed")
        room.remove_player(player)
        del self._ws[player]

        # Was this the last player?
        # Clean up garbage
        if len(room.get_players()) == 0:
            room.unsubscribe(self._room_subscriber)
            del self._rooms[room_uuid]

        return ws

    def _room_subscriber(self, room, event, **kwargs):
        print(room, event, kwargs)
        if event == "vote_placed":
            asyncio.create_task(
                self._send_str_to_room(room, self._create_message_vote_placed(**kwargs))
            )
        asyncio.create_task(
            self._send_str_to_room(room, self._create_message_room_state(room))
        )

    def _create_message_vote_placed(self, player, vote):
        return "VOTE {}".format(player.id)

    def _create_message_room_state(self, room):
        if room.status == RoomStatus.PROGRESS:
            return "ROOM_STATE PROGRESS {}".format(
                " ".join(
                    [
                        "{}:{}".format(player.id, vote is not None)
                        for player, vote in room.get_votes()
                    ]
                )
            )

        elif room.status == RoomStatus.RESULT:
            return "ROOM_STATE RESULT {}".format(
                " ".join(
                    [
                        "{}:{}".format(player.id, vote)
                        for player, vote in room.get_votes()
                    ]
                )
            )

    async def _send_str_to_room(self, room, message):
        players = room.get_players()
        for player in players:
            if player in self._ws:
                try:
                    await self._ws[player].send_str(message)
                except Exception as e:
                    print(e)
                    await self._ws[player].close()
