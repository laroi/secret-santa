import yaml
import re
import random
import smtplib
import datetime
import pytz
import time
import socket
import sys
import getopt
import os
import json
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from encrypt import AESCipher;
help_message = '''
To use, fill out config.yml with your own participants. You can also specify
DONT-PAIR so that people don't get assigned their significant other.

You'll also need to specify your mail server settings. An example is provided
for routing mail through gmail.

For more information, see README.
'''
iv = 'This is an IV456'

REQRD = (
    'SMTP_SERVER',
    'SMTP_PORT',
    'USERNAME',
    'PASSWORD',
    'TIMEZONE',
    'PARTICIPANTS',
    'DONT-PAIR',
    'FROM',
    'SUBJECT',
    'MESSAGE',
)

HEADER = """Date: {date}
Content-Type: text/html; charset=UTF-8"
"""

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yml')
participant_file = os.path.join(os.path.dirname(__file__), 'participants.json')

class Person:
    def __init__(self, name, email, cubicle, invalid_matches):
        self.name = name
        self.email = email
	self.cubicle = cubicle
        self.invalid_matches = invalid_matches

    def __str__(self):
        return "%s <%s> - %s" % (self.name, self.email, self.cubicle)

class Pair:
    def __init__(self, giver, reciever):
        self.giver = giver
        self.reciever = reciever

    def __str__(self):
        if (hasattr(self, 'key')):
            return "%s (%d)---> %s (%d) key is %s" % (self.giver.name, self.giver.cubicle, self.reciever.name, self.reciever.cubicle, self.key)
        else:
            return "%s (%d)---> %s (%d)" % (self.giver.name, self.giver.cubicle, self.reciever.name, self.reciever.cubicle)
'''
class Mailer:
	def __init__(self, mail_smtp, mail_from, mail_password):
		print mail_smtp
		self.server = smtplib.SMTP(mail_smtp, '587')
                print 'Hey !!! Mailer ' + str(mail_smtp) + ' is Initialized with ' + str(mail_from)
		self.server.starttls()
		self.server.login(mail_from, mail_password)
	def sendMail(self, sub, frm, recipient, body):
		msg = MIMEMultipart('alternative')
		msg['Subject'] = sub
		msg['From'] = frm
		msg['To'] = recipient
		bdy = MIMEText(body, 'html')
		msg.attach(bdy)
                print 'Sending mail to '+ str(recipient)
		#self.server.sendmail(frm, recipient, msg.as_string())
	def kill(self):
		self.server.quit()
		print 'Bye bye ! Quitting Mailer ....'
'''

def parse_yaml(yaml_path=CONFIG_PATH):
    return yaml.load(open(yaml_path))

def choose_reciever(giver, recievers):
    choice = random.choice(recievers)
    if choice.name in giver.invalid_matches or giver.name == choice.name or giver.cubicle == choice.cubicle:
	print 'same cubicle',  giver, choice
        if len(recievers) is 1:
            raise Exception('Only one reciever left, try again')
        return choose_reciever(giver, recievers)
    else:
        return choice

def create_pairs(g, r):
    givers = g[:]
    recievers = r[:]
    pairs = []
#   print 'Giver \n'
#    for p in givers : print p
#    print '\n Rec \n'
#    for p in recievers: print p

    for giver in givers:
        try:
	    mod_rec = list(filter(lambda x: x.cubicle != giver.cubicle, recievers))
	    #mod_rec = recievers
#	    print 'modified'
            for p in mod_rec : print p
            reciever = choose_reciever(giver, mod_rec)
#	    print 'Choosen', reciever
#	    print 'Recievers Left '
            for p in recievers: print p
            recievers.remove(reciever)
            pairs.append(Pair(giver, reciever))
        except Exception as e:
	    return create_pairs(g, r)
    return pairs


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "shc", ["send", "help", "doencrypt"])
        except getopt.error, msg:
            raise Usage(msg)

        # option processing
        doencrypt = False
        send = False
        print opts
        for option, value in opts:
            if option in ("-s", "--send"):
                send = True
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-e", "--doencrypt"):
                doencrypt = True

        config = parse_yaml()
        for key in REQRD:
            if key not in config.keys():
                raise Exception(
                    'Required parameter %s not in yaml config file!' % (key,))

        participants = json.loads(open(participant_file).read())
        dont_pair = config['DONT-PAIR']
	if dont_pair == None:
		dont_pair = []
        if len(participants) < 2:
            raise Exception('Not enough participants specified.')

        givers = []

        for person in participants:
            name, email, cubicle = person['name'], person['email'], person['cubicle']
            name = name.strip()
            invalid_matches = []
            for pair in dont_pair:
                names = [n.strip() for n in pair.split(',')]
                if name in names:
                    # is part of this pair
                    for member in names:
                        if name != member:
                            invalid_matches.append(member)
            person = Person(name, email, cubicle, invalid_matches)
            givers.append(person)

        random.shuffle(givers)
        recievers = givers[:]
        pairs = create_pairs(givers, recievers)
        if doencrypt:
            for pair in pairs:
                key = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
                pair.key = key
                cipher = AESCipher(key, iv)
                pair.reciever.hash = cipher.encrypt(pair.reciever.name)
                print pair;

        if not send:
            print """
Test pairings:

%s

To send out emails with new pairings,
call with the --send argument:

    $ python secret_santa.py --send

            """ % ("\n".join([str(p) for p in pairs]))

        if send:
	    server = smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT'])
            server.starttls()
	    server.login(config['USERNAME'], config['PASSWORD'])
#	    mail_obj = Mailer(config['SMTP_SERVER'], config['USERNAME'], config['PASSWORD'])
        for pair in pairs:
            zone = pytz.timezone(config['TIMEZONE'])
            now = zone.localize(datetime.datetime.now())
            date = now.strftime('%a, %d %b %Y %T %Z') # Sun, 21 Dec 2008 06:25:23 +0000
            message_id = '<%s@%s>' % (str(time.time())+str(random.random()), socket.gethostname())
            frm = config['FROM']
            to = pair.giver.email
            #subject = config['SUBJECT'].format(santa=pair.giver.name, santee=pair.reciever.name)
            subject = 'Your Secret Santa'
            body = (config['MESSAGE']).format(
#                date=date,
#                message_id=message_id,
#                frm=frm,
#                to=to,
#                subject=subject,
                santa=pair.giver.name,
                santee=pair.reciever.hash,
            )
            if send:
                if (to == 'arpitha.hn@mobinius.com'):
                    print body
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = 'Secret Santa'
                    msg['From'] = frm
                    msg['To'] = to
                    part2 = MIMEText(body, 'html')
                    msg.attach(part2)
                    result = server.sendmail(frm, [to], msg.as_string())
                    print "Emailed %s <%s> with key %s" % (pair.giver.name, to, pair.key)

        if send:
            #mail_obj.kill()
	    server.quit()

    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())
