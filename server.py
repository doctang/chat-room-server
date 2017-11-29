# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet import reactor
from twisted.python import log

online_user = dict()


class LiveServerProtocol(WebSocketServerProtocol):
    client_name = None

    def onConnect(self, request):
        pass

    def onOpen(self):
        pass

    def onMessage(self, payload, is_binary):
        try:
            payload = json.loads(payload)
        except Exception as e:
            log.msg(e)
        else:
            t = payload.get('type')
            if t == 'login':
                if len(online_user) == 10000:
                    self.sendMessage(json.dumps({'stat': 'MaxOnline'}), False)
                # elif payload['client_name'] in online_user \
                #         and online_user[payload['client_name']][1].state == self.STATE_OPEN:
                #     self.sendMessage(json.dumps({'stat': 'OtherLogin'}), False)
                else:
                    self.client_name = payload['client_name']
                    payload['nick'] = self.client_name
                    room_id = payload['room_id']
                    payload['roomid'] = room_id
                    online_user[self.client_name] = [room_id, self, payload]
                    send_msg = {'stat': 'OK', 'type': 'login', 'Ulogin': payload, 'client_name': self.client_name,
                                'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                'client_list': [i[2] for i in online_user.values() if i[0] == room_id]}

                    for k, v in [i for i in online_user.items() if i[1][0] == room_id]:
                        if v[1].state == self.STATE_OPEN:
                            v[1].sendMessage(json.dumps(send_msg), is_binary)
            elif t == 'Msgsay':
                value = online_user.get(self.client_name)
                if value:
                    send_msg = {'stat': 'OK', 'type': payload['type'],
                                'UMsg': {'ChatId': value[2]['chatid'], 'ToChatId': payload['ToUser'],
                                         'IsPersonal': payload['Personal'], 'Style': payload['Style'],
                                         'Txt': payload['Msg']},
                                'from_client_name': value[2]['nick'],
                                'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}
                    for k, v in [i for i in online_user.items() if i[1][0] == value[0]]:
                        if v[1].state == self.STATE_OPEN:
                            v[1].sendMessage(json.dumps(send_msg), is_binary)

    def onClose(self, was_clean, code, reason):
        value = online_user.get(self.client_name)
        if value:
            send_msg = {'from_client_name': {'chatid': value[2]['chatid'], 'nick': value[2]['nick']},
                        'type': 'logout', 'stat': 'OK'}
            for k, v in [i for i in online_user.items() if i[1][0] == value[0]]:
                if v[1].state == self.STATE_OPEN:
                    v[1].sendMessage(json.dumps(send_msg), False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-p', dest='port', type=int)
    port = p.parse_args(sys.argv[1:]).port or 9089
    f = open(os.path.join(os.path.expanduser('~'), 'live-%d.log' % port), 'a')
    log.startLogging(f)
    factory = WebSocketServerFactory('ws://127.0.0.1:%s' % port)
    factory.protocol = LiveServerProtocol
    factory.setProtocolOptions(maxConnections=10000)
    reactor.listenTCP(port, factory)
    reactor.run()
    f.close()
