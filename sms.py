# -*- coding: utf-8 -*-

from messaging.sms import SmsDeliver
import datetime
import sys
import serial
import pickle
import gtk 
import webkit 
import tempfile
import os
import atexit
import thread
from cgi import escape

# ------ CONFIG

#ttypath = "/dev/rfcomm2"
ttypath = "/dev/ttyUSB2"
contact = """
    <ul id="contact">
        <li>SMS-szám: +36 20 264 7145</li>
        <!--<li>06202647145@sms.pgsm.hu</li>-->
    </ul>"""

datafile = "smsfal-%s" % (datetime.date.today())

# -----

class WebView(webkit.WebView):
    def __init__(self):
        webkit.WebView.__init__(self)
        self.connect_after("populate-popup", self.populate_popup)

    def populate_popup(self, view, menu):
        save = gtk.ImageMenuItem(gtk.STOCK_SAVE)
        save.connect('activate', save_log, view)
        menu.append(save)

        menu.show_all()
        return False

def save_log(menu_item, web_view):
    global do_save_log
    do_save_log = True

def humandate(d):
    dif = datetime.datetime.utcnow() - d
    if dif.seconds > 24 * 3600:
        return '%s UTC' % d
    elif dif.seconds > 3600:
        d = datetime.datetime.utcnow() - d
        return '%d óra %d perce' % (d.seconds/3600, d.seconds / 60 % 60)
    else:
        d = datetime.datetime.utcnow() - d
        if d.seconds < 60:
            return 'most'
        else:
            return '%d perce' % (d.seconds / 60)

def colorhash(number):
    try:
        number = int(number)
    except ValueError:
        num = 0
        for i in number:
            num = num * 11 + ord(i)
        number = num
            
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
            </div>""" % (colorhash(i[1]), humandate(i[0]), i[1][:-4]+"****", escape(i[2]))) + out
        if out == '':
            return render(outfile=outfile, empty='nincs üzenet')

    out = """<!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset=utf-8 />
            <title>SMS-fal</title>
            <style>
                .sender, .sent {font-size:.8em; color: #666; margin: 0 .5em;
                margin-bottom: -1.2em;padding: .1em;}
                .sender {float: left;}
                .sent {float: right;} 
                .msg {clear: both; margin: 0; padding: .5em;
                background-color:#fff;border-radius: 0 0 .3em .3em; padding-top: 1em;} 
                .item { margin:.5em;padding: .1em; border-radius: .3em; background-color: #ccc;} 
                body,div {margin:0; padding: 0;font-size: 1cm;}
                #contact {position: fixed; bottom:0; width: 100%; height:1em;
                text-align: center; background-color: #000; color: #fff;
                margin: 0; padding: .2em;}
                #contact li {display: inline;margin-right: 2em;}
            </style>
        </head>
        <body onload="setTimeout(\'location.reload()\', 5000)">
        """ + contact + out + "</body></html>"
    f = open(outfile, "wb")
    f.write(out)
    f.close()

def quit_event(self, *args):
    global quit
    quit = True
    gtk.main_quit()

def browsermain():
    view = WebView() 

    sw = gtk.ScrolledWindow() 
    sw.add(view) 

    win = gtk.Window(gtk.WINDOW_TOPLEVEL) 
    win.set_default_size(800, 420)
    win.add(sw) 
    win.show_all() 
    win.set_title("SMS-fal")
    win.set_decorated(False)
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

    log_count = 0
    while not quit:
        if do_save_log:
            log_count = log_count + 1
            logf = open("%s-%d-%d.log" % (datafile, os.getpid(), log_count), "w")
            for i in texts:
                logf.write("%s\t%s\t%s\n" % i)
            logf.close()
            do_save_log = False

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

do_save_log = False
quit = False

html = tempfile.mkstemp(".html")
atexit.register(os.unlink, html[1])
render(html[1], empty="betöltés...")

gtk.gdk.threads_init()
thread.start_new_thread(browsermain, ())

pollermain()
