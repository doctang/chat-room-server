# -*- coding:utf-8 -*-
import json
import os
import sys
import time

import MySQLdb
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet import reactor
from twisted.python import log


class LiveServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        log.msg('Client connecting: {0}'.format(request.peer))

    def onOpen(self):
        log.msg('WebSocket connection open.')

    def onMessage(self, payload, is_binary):
        log.msg('Text message received: {0}'.format(payload))
        try:
            payload = json.loads(payload)
        except Exception as e:
            log.msg(e)
        else:
            if 'type' in payload:
                if payload['type'] == 'login':
                    if len(user_online) == 5000:
                        self.sendMessage(json.dumps({'stat': 'MaxOnline'}), False)
                    elif payload['client_name'] in user_online:
                        self.sendMessage(json.dumps({'stat': 'OtherLogin'}), False)
                    else:
                        payload['nick'] = payload['client_name']
                        room_id = payload['room_id']
                        if room_id in client_user:
                            client_user[room_id][self.__hash__()] = [self, payload]
                        else:
                            client_user[room_id] = {self.__hash__(): [self, payload]}
                        user_online.append(payload['client_name'])
                        payload['roomid'] = payload['room_id']
                        send_msg = {'stat': 'OK', 'type': 'login',
                                    'Ulogin': payload, 'client_name': payload['client_name'],
                                    'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
                                    'client_list': [i[1] for i in client_user[room_id].values()]}
                        for i in client_user[room_id].values():
                            i[0].sendMessage(json.dumps(send_msg), is_binary)
                elif payload['type'] == 'Msgsay':
                    flag = False
                    for key, value in client_user.items():
                        for h, i in value.items():
                            if h == self.__hash__():
                                flag = True
                                send_msg = {'stat': 'OK', 'type': payload['type'],
                                            'UMsg': {'ChatId': i[1]['chatid'], 'ToChatId': payload['ToUser'],
                                                     'IsPersonal': payload['Personal'],
                                                     'Style': payload['Style'], 'Txt': payload['Msg']},
                                            'from_client_name': i[1]['nick'],
                                            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}
                                for j in value.values():
                                    j[0].sendMessage(json.dumps(send_msg), is_binary)
                                break
                        if flag:
                            break
                elif payload['type'] in ['pong', 'refresh']:
                    pass

    def onClose(self, wasClean, code, reason):
        flag = False
        for key, value in client_user.items():
            for h, i in value.items():
                if h == self.__hash__():
                    flag = True
                    send_msg = {'from_client_name': {'chatid': i[1]['chatid'],
                                                     'nick': i[1]['client_name']},
                                'type': 'logout', 'stat': 'OK'}
                    client_user.pop(key)
                    user_online.remove(i[1]['client_name'])
                    for j in value.values():
                        j[0].sendMessage(json.dumps(send_msg), False)
                    break
            if flag:
                break
        log.msg("WebSocket connection closed: {0}".format(reason))


if __name__ == "__main__":
    port = 9089
    logfile = open(os.path.join(os.path.expanduser("~"), "live.log"), "a")
    log.startLogging(logfile)
    user_online = []
    client_user = {}
    # log.startLogging(sys.stdout)
    factory = WebSocketServerFactory(u"ws://127.0.0.1:%s" % port)
    factory.protocol = LiveServerProtocol
    factory.setProtocolOptions(maxConnections=5000)
    reactor.listenTCP(port, factory)
    reactor.run()
    logfile.close()
