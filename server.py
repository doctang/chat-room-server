# -*- coding: utf-8 -*-

import json
import os
import threading
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet import reactor
from twisted.python import log

mutex = threading.Lock()


class LiveServerProtocol(WebSocketServerProtocol):
    client_name = None

    def onConnect(self, request):
        log.msg('Client connecting: {0}'.format(request.peer))

    def onOpen(self):
        log.msg('WebSocket connection open.')

    def onMessage(self, payload, is_binary):
        log.msg('Text message received: {0}'.format(payload))
        with mutex:
            try:
                payload = json.loads(payload)
            except Exception as e:
                log.msg(e)
            else:
                t = payload.get('type')
                if t == 'login':
                    self.client_name = payload['client_name']
                    if len(user_online) == 5000:
                        self.sendMessage(json.dumps({'stat': 'MaxOnline'}), False)
                    elif self.client_name in user_online:
                        self.sendMessage(json.dumps({'stat': 'OtherLogin'}), False)
                    else:
                        payload['nick'] = self.client_name
                        room_id = payload['room_id']
                        if room_id in client_user:
                            client_user[room_id][self.client_name] = [self, payload]
                        else:
                            client_user[room_id] = {self.client_name: [self, payload]}
                        user_online.append(self.client_name)
                        log.msg('User login: %s' % len(user_online))
                        payload['roomid'] = payload['room_id']
                        send_msg = {'stat': 'OK', 'type': 'login',
                                    'Ulogin': payload, 'client_name': self.client_name,
                                    'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                    'client_list': [i[1] for i in client_user[room_id].values()]}

                        for key, value in client_user[room_id].items():
                            if value[0].state == 3:
                                value[0].sendMessage(json.dumps(send_msg), is_binary)
                            else:
                                client_user[room_id].pop(key)
                elif t == 'Msgsay':
                    flag = False
                    for key, value in client_user.items():
                        for h, i in value.items():
                            if h == self.client_name:
                                flag = True
                                send_msg = {'stat': 'OK', 'type': payload['type'],
                                            'UMsg': {'ChatId': i[1]['chatid'], 'ToChatId': payload['ToUser'],
                                                     'IsPersonal': payload['Personal'],
                                                     'Style': payload['Style'], 'Txt': payload['Msg']},
                                            'from_client_name': i[1]['nick'],
                                            'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}
                                for j in value.values():
                                    if j[0].state == 3:
                                        j[0].sendMessage(json.dumps(send_msg), is_binary)
                                    else:
                                        client_user[key].pop(h)
                                break
                        if flag:
                            break

    def onClose(self, was_clean, code, reason):
        log.msg('Websocket connection closed: {0}'.format(reason))
        with mutex:
            flag = False
            for key, value in client_user.items():
                for h, i in value.items():
                    if h == self.client_name:
                        flag = True
                        send_msg = {'from_client_name': {'chatid': i[1]['chatid'],
                                                         'nick': self.client_name},
                                    'type': 'logout', 'stat': 'OK'}
                        if self.client_name in user_online:
                            user_online.remove(self.client_name)
                        log.msg('User logout: %s' % len(user_online))
                        for j in value.values():
                            if j[0].state == 3:
                                j[0].sendMessage(json.dumps(send_msg), False)
                            elif self.client_name in client_user[key]:
                                client_user[key].pop(self.client_name)
                        break
                if flag:
                    break


if __name__ == '__main__':
    port = 9089
    logfile = open(os.path.join(os.path.expanduser('~'), 'live.log'), 'a')
    log.startLogging(logfile)
    user_online = []
    client_user = {}
    # import sys
    # log.startLogging(sys.stdout)
    factory = WebSocketServerFactory('ws://127.0.0.1:%s' % port)
    factory.protocol = LiveServerProtocol
    factory.setProtocolOptions(maxConnections=5000)
    reactor.listenTCP(port, factory)
    reactor.run()
    logfile.close()
