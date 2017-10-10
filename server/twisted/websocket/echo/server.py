# -*- coding:utf-8 -*-
import sys
import os
import time
import json

import MySQLdb
from twisted.internet import reactor
from twisted.python import log

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory


class LiveServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        log.msg('Client connecting: {0}'.format(request.peer))

    def onOpen(self):
        log.msg('WebSocket connection open.')

    def onMessage(self, payload, is_binary):
        log.msg('Text message received: {0}'.format(payload))
        send_msg = {}
        try:
            payload = json.loads(payload)
        except Exception as e:
            log.msg(e)
        else:
            if 'type' in payload:
                if payload['type'] == 'login':
                    if len(user_online) == 5000:
                        send_msg = {'stat': 'MaxOnline'}
                    elif payload['client_name'] in user_online:
                        send_msg = {'stat': 'OtherLogin'}
                    else:
                        payload['nick'] = payload['client_name']
                        room_id = payload['room_id']
                        if room_id in client_user:
                            client_user[room_id]['client_list'].append(payload)
                            client_user[room_id]['client_id'].append({self.__hash__(), self})
                        else:
                            client_user[room_id] = {'client_id': [[self.__hash__(), self]], 'client_list': [payload]}
                        user_online.append(payload['client_name'])
                        payload['roomid'] = payload['room_id']
                        send_msg = {'stat': 'OK', 'type': 'login',
                                    'Ulogin': payload, 'client_name': payload['client_name'],
                                    'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
                                    'client_list': client_user[room_id]['client_list']}
                elif payload['type'] == 'Msgsay':
                    time.sleep(5)
                    try:
                        db = MySQLdb.connect(host='10.206.79.43', db='zhibo_com', user='root', passwd='123456',
                                             charset='utf8')
                        cursor = db.cursor()
                        sql = 'select * from chat_chatlog where msgid="%s"' % payload['Msg'].split('_')[0]
                        cursor.execute(sql)
                        chat_log = cursor.fetchone()
                        cursor.close()
                    except Exception as e:
                        log.msg(e)
                    else:
                        if chat_log:
                            cursor = db.cursor()
                            cursor.execute('select * from chat_config where rid="%s"' % str(chat_log[1]))
                            room_id = cursor.fetchone()
                            print room_id[0]
                            send_msg = {'stat': 'OK', 'type': payload['type'],
                                        'UMsg': {'ChatId': str(chat_log[3]), 'ToChatId': str(chat_log[4]),
                                                 'IsPersonal': payload['Personal'],
                                                 'Style': payload['Style'], 'Txt': payload['Msg']},
                                        'from_client_name': chat_log[5],
                                        'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}
                    finally:
                        db.close()
                elif payload['type'] in ['pong', 'refresh']:
                    pass
            if send_msg:
                self.sendMessage(json.dumps(send_msg), is_binary)

    def onClose(self, wasClean, code, reason):
        room_id = None
        for key, value in client_user.items():
            log.msg(value)
            for i, item in enumerate(value['client_id']):
                print item
                if item[0] == self.__hash__():
                    room_id = key
                    client_user[key]['client_id'].pop(i)
        if room_id:
            for client in client_user[room_id]['client_list']:
                if client['room_id'] == room_id:
                    user_online.remove(client['client_name'])
                    send_msg = {'chatid': client['chatid'], 'nick': client['client_name']}
            if send_msg:
                for s in client_user[room_id]['client_id']:
                    s[1].sendMessage({'from_client_name': send_msg})
        log.msg("WebSocket connection closed: {0}".format(reason))


if __name__ == "__main__":
    port = 9089
    # logfile = open(os.path.join(os.path.expanduser("~"), "live.log"), "a")
    # log.startLogging(logfile)
    user_online = []
    client_user = {}
    client_list = []
    log.startLogging(sys.stdout)
    factory = WebSocketServerFactory(u"ws://127.0.0.1:%s" % port)
    factory.protocol = LiveServerProtocol
    factory.setProtocolOptions(maxConnections=5001)
    reactor.listenTCP(port, factory)
    reactor.run()
    # logfile.close()
