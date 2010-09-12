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
import signal
from cgi import escape


#ttypath = "/dev/rfcomm2"
ttypath = "/dev/ttyUSB2"
contact = """
    <ul id="contact">
        <li>SMS-szám: +36 20 264 45</li>
        <!--<li>062026445@sms.pgsm.hu</li>-->
    </ul>"""

datafile = "smsfal-%s" % (date.today())



def colorhash(number):
    number = int(number)
    c = (60, (number % 1747) % 101, (number % 1847) % 101)
    return "hsl(%d, %d%%, %d%%)" % c

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
    tty.write('AT+CMGL\r')
    out = tty.readlines()
    ret = []
    toremove = []
    lastid = None
    for i in out:
        if i.startswith('OK'):
            lastid = None
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

def render(outfile, texts=None, empty=False):
    out = ''
    if empty != False:
        out = """<div class="item empty">
            <p class="msg">%s</p>
        </div>""" % (empty)
    else:
        for i in texts:
            out = ("""
            <div class="item" style="background-color: %s;"> 
                <div class="sent">%s</div>
                <div class="sender">%s</div>
                <p class="msg">%s</p>
            </div>""" % (colorhash(i[1]), i[0], i[1], escape(i[2]))) + out
        if out == '':
            return render(outfile=outfile, empty='nincs üzenet')

    out = """<!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset=utf-8 />
            <title>SMS-fal</title>
            <style>
                .sender, .sent {font-size:.8em; color: #666;}
                .sender {float: left;}
                .sent {float: right;} 
                .msg {clear: both; margin: 0; padding: .5em; background-color:#fff;border-radius: .5em; } 
                .item { margin:.5em;padding: .1em; border-radius: .5em; background-color: #ccc;} 
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

def quit_event(self, *args):
    os.kill(other, signal.SIGTERM)
    gtk.main_quit()

def browsermain():
    view = webkit.WebView() 

    sw = gtk.ScrolledWindow() 
    sw.add(view) 

    win = gtk.Window(gtk.WINDOW_TOPLEVEL) 
    win.add(sw) 
    win.show_all() 
    win.set_title("SMS-fal")
    win.maximize()
    win.connect("delete-event", quit_event)

    view.open("file://%s" % html[1])
    gtk.main()


def pollermain():
    tty = serial.Serial(ttypath, timeout=1)

    texts = []
    try:
        f = open(datafile, 'rb')
        texts = pickle.load(f)
        f.close()
    except IOError:
        f = open(datafile, 'wb')
        pickle.dump([], f)
        f.close()

    render(html[1], texts)


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

            render(html[1], texts=texts)

    tty.close()

html = tempfile.mkstemp(".html")
render(html[1], empty="betöltés...")

other = os.getpid()
pid = os.fork()
if pid == 0:
    pollermain()
else:
    other = pid
    browsermain()
