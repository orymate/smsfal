# -*- coding: utf-8 -*-

from messaging.sms import SmsDeliver
from datetime import date
import sys
import serial
import pickle
import gtk 
import webkit 
import tempfile
import os
from cgi import escape


#ttypath = "/dev/rfcomm2"
ttypath = "/dev/ttyUSB2"
contact = """
    <ul id="contact">
        <li>SMS-szám: +36 20 264 7145</li>
        <!--<li>06202647145@sms.pgsm.hu</li>-->
    </ul>"""

datafile = "smsfal-%s" % (date.today())

def smsremove(tty, msgid):
    try:
        cmd = 'AT+CMGD=%d\r' % msgid
        tty.write(cmd)
        tty.readlines()
    except ValueError:
        print "Not an integer msgid: " + msgid

def smslist(tty):
    tty.write('AT+CMGF=0\r')
    tty.readlines()

    tty.write('AT+CMGL=1\r')
    out = tty.readlines()
    ret = []
    toremove = []
    lastid = None
    for i in out:
        if i.startswith('OK'):
            break
        elif i.strip() == '' or i.startswith("AT"):
            continue
        elif i.startswith('+CMGL:'):
            params = i[7:].split(",")
            lastid = int(params[0])
        else:
            try:
                ret.append(SmsDeliver(i.rstrip()))
                smsremove(tty, lastid)
            except ValueError:
                print "Can't parse: " + i.rstrip()
    return ret

def render(texts, outfile):
    out = ''
    for i in texts:
        
        out = ("""
        <div class="item"> 
            <div class="sent">%s</div>
            <div class="sender">%s</div>
            <p class="msg">%s</p>
        </div>""" % (i[0], i[1], escape(i[2]))) + out

    if out == '':
        out = '<div class="item"><p>(nincs üzenet)</p></div>'

    out = """<!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset=utf-8 />
            <title>SMS-fal</title>
            <style>
                .sender, .sent {font-size:.8em; color: #666;}
                .sender {float: left;}
                .sent {float: right;} 
                .msg {clear: both; margin: .2em 0 0;} 
                .item { margin:.5em;padding:.5em; border-radius: .5em; background-color: #ccc;} 
                body,div {margin:0; padding: 0;font-size: 1cm;}
                #contact {position: fixed; bottom:0; width: 100%; height:1em;
                background-color: #000; color: #fff;}
                #contact li {display: inline;margin-right: 2em;}
            </style>
        </head>
        <body onload="setTimeout(\'location.reload()\', 5000)">
        """ + contact + out + "</body></html>"
    f = open(outfile, "wb")
    f.write(out)
    f.close()

def browsermain():
    view = webkit.WebView() 

    sw = gtk.ScrolledWindow() 
    sw.add(view) 

    win = gtk.Window(gtk.WINDOW_TOPLEVEL) 
    win.add(sw) 
    win.show_all() 
    win.set_title("SMS-fal")
    win.maximize()

    view.open("file://%s" % html[1])
    gtk.main()


def pollermain():
    tty = serial.Serial(ttypath, timeout=1)

    texts = []
    try:
        f = open(datafile, 'rb')
        texts = pickle.load(f)
        f.close()
        render(texts, html[1])
    except IOError:
        pass


    while True:
        new = smslist(tty)
        for i in new:
            texts.append((i.data['date'], i.data['number'], i.data['text']))
        texts = sorted(texts, key=lambda t: t[0])
        if len(new):
            try:
                f = open(datafile, 'wb')
                pickle.dump(texts, f)
                f.close()
            except:
                f = open(datafile + '~', 'wb')
                pickle.dump(texts, f)
                f.close()

            render(texts, html[1])

    tty.close()

html = tempfile.mkstemp(".html")
render([('', '', 'betöltés...')], html[1])

if os.fork() == 0:
    browsermain()
else:
    pollermain()

