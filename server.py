#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ujson, sys, os, re, json, subprocess, time
from random import randint

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from pymongo import MongoClient
from bson.objectid import ObjectId
import webbrowser

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'website')
pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'website/pages')

app = None
mongodb = None
db = None

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

class CardHandler(tornado.web.RequestHandler):
    def get(self):
        card = db['cards'].find_one({'Nom':self.get_argument("nom", "???")})
        card['_id'] = str(card['_id'])
        self.render('card.html', card = card)

class QuizzHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('quizz.html')

class DuelsHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('duels.html')

class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def open(self, *args):
        print "New client connected"

    def on_message(self, message):
        message = ujson.loads(message)
        query = {}
        try:
            if message['header'] == 'get decks list':
                decks = []
                decks_db = None
                if message['type'] == "Top semaine":
                    decks_db ="decks_semaine"
                elif message['type'] == "Top mois":
                    decks_db = "decks_mois"
                elif message['type'] == "Top total":
                    decks_db = "decks_total"
                elif message['type'] == "Mes decks":
                    decks_db = "mes_decks"

                query = {}
                if message.has_key('Classe'):
                    if message['Classe'] == 'Non-Neutre':
                        query['Classe'] = { '$ne': 'Neutre' }
                    else:
                        query['Classe'] = message['Classe']

                for deck in db[decks_db].find(query).sort([('Note', -1)]):
                    decks.append({'Nom':deck['Nom'], 'Lien':deck['Lien'], 'Possedees':deck['Possedees']})

                answer = {
                    'header': 'got decks list',
                    'type': message['type'],
                    'decks': decks
                }
                self.write_message(answer)

            elif message['header'] == 'search':
                deck_composition = None
                if message.has_key('Deck-type') and message.has_key('Deck-name'):
                    if message['Deck-type'] == "Top semaine":
                        decks_db ="decks_semaine"
                    elif message['Deck-type'] == "Top mois":
                        decks_db ="decks_mois"
                    elif message['Deck-type'] == "Top total":
                        decks_db ="decks_total"
                    elif message['Deck-type'] == "Mes decks":
                        decks_db ="mes_decks"
                    deck_composition = db[decks_db].find_one({'Nom': message['Deck-name']})['Composition']
                    query = {'Nom':{'$in': deck_composition.keys()}}
                if message['Tri'] == 'Attaque' or message['Tri'] == 'Vie':
                    query['Type'] = 'Serviteur'
                if len(message['Nom'].strip()):
                    regx = re.compile(message['Nom'].strip(), re.IGNORECASE)
                    query['Nom'] = regx
                if len(message['Description'].strip()):
                    regx = re.compile(message['Description'].strip(), re.IGNORECASE)
                    query['Description'] = regx
                if len(message[u'Attaque'].strip()):
                    if message[u'Attaque'].strip().startswith('>='):
                        query['Attaque'] = {'$gte': int(message[u'Attaque'].strip().split('>=')[-1])}
                    elif message[u'Attaque'].strip().startswith('>'):
                        query['Attaque'] = {'$gt': int(message[u'Attaque'].strip().split('>')[-1])}
                    elif message[u'Attaque'].strip().startswith('<='):
                        query['Attaque'] = {'$lte': int(message[u'Attaque'].strip().split('<=')[-1])}
                    elif message[u'Attaque'].strip().startswith('<'):
                        query['Attaque'] = {'$lt': int(message[u'Attaque'].strip().split('<')[-1])}
                    else:
                        query['Attaque'] = int(message[u'Attaque'].strip())
                if len(message[u'Vie'].strip()):
                    if message[u'Vie'].strip().startswith('>='):
                        query['Vie'] = {'$gte': int(message[u'Vie'].strip().split('>=')[-1])}
                    elif message[u'Vie'].strip().startswith('>'):
                        query['Vie'] = {'$gt': int(message[u'Vie'].strip().split('>')[-1])}
                    elif message[u'Vie'].strip().startswith('<='):
                        query['Vie'] = {'$lte': int(message[u'Vie'].strip().split('<=')[-1])}
                    elif message[u'Vie'].strip().startswith('<'):
                        query['Vie'] = {'$lt': int(message[u'Vie'].strip().split('<')[-1])}
                    else:
                        query['Vie'] = int(message[u'Vie'].strip())
                if len(message[u'Cout en mana'].strip()):
                    if message[u'Cout en mana'].strip().startswith('>='):
                        query['Cout en mana'] = {'$gte': int(message[u'Cout en mana'].strip().split('>=')[-1])}
                    elif message[u'Cout en mana'].strip().startswith('>'):
                        query['Cout en mana'] = {'$gt': int(message[u'Cout en mana'].strip().split('>')[-1])}
                    elif message[u'Cout en mana'].strip().startswith('<='):
                        query['Cout en mana'] = {'$lte': int(message[u'Cout en mana'].strip().split('<=')[-1])}
                    elif message[u'Cout en mana'].strip().startswith('<'):
                        query['Cout en mana'] = {'$lt': int(message[u'Cout en mana'].strip().split('<')[-1])}
                    else:
                        query['Cout en mana'] = int(message[u'Cout en mana'].strip())
                if message.has_key('Rarete'):
                    query['Rarete'] = message['Rarete']
                if message.has_key('Type'):
                    query['Type'] = message['Type']
                if message.has_key('Race'):
                    query['Race'] = message['Race']
                if message.has_key('Classe'):
                    if message['Classe'] == 'Non-Neutre':
                        query['Classe'] = { '$ne': 'Neutre' }
                    else:
                        query['Classe'] = message['Classe']
                if message.has_key('Possedee'):
                    if message['Possedee']:
                        query['Dans ma Collection'] = {'$gt':0}
                    else:
                        query['Dans ma Collection'] = {'$in':[0]}
                cards = []
                possedees = 0
                for card in db['cards'].find(query).sort([(message['Tri'], message['Ordre']), ('Classe', message['Ordre']), ('Nom', message['Ordre'])]):
                    del card['_id']
                    if int(card['Dans ma Collection']) != 0:
                        possedees += 1
                    if deck_composition: #if we recovered cards from a deck list, we add the number of cards
                        if deck_composition.has_key(card['Nom']):
                            card['Quantite'] = deck_composition[card['Nom']]
                    cards.append(card)

                answer = { 'header': 'cards found',
                        'cards':cards,
                        'possedees': possedees
                        }
                self.write_message(answer)

            elif message['header'] == 'new quizz':
                total = db['cards'].count()
                card = db['cards'].find()[randint(0,total-1)]
                questions = None
                if card['Type'] == 'Serviteur':
                    #questions = ['Nom', 'Attaque', 'Vie', 'Cout en mana', 'Image&Nom', 'Image&Description']
                    questions = ['Nom', 'Image&Nom', 'Image&Description']
                    if card['Description'] != "":
                        questions.append('Description')
                elif card['Type'] == 'Sort':
                    #questions = ['Nom', 'Cout en mana', 'Image&Nom', 'Image&Description']
                    questions = ['Nom', 'Image&Nom', 'Image&Description']
                    if card['Description'] != "":
                        questions.append('Description')
                elif card['Type'] == 'Arme':
                    #questions = ['Nom', 'Cout en mana', 'Image&Nom', 'Image&Description']
                    questions = ['Nom', 'Image&Nom', 'Image&Description']
                    if card['Description'] != "":
                        questions.append('Description')
                index = randint(0,len(questions)-1)
                question = questions[index]
                image = card['Image']
                answer = { 'header': 'new quizz',
                            'Image':image,
                            '_id': str(card['_id']),
                            'question': question
                        }
                self.find_propositions(answer, card)
                self.write_message(answer)

            elif message['header'] == 'send answer':
                card = db['cards'].find_one({'_id': ObjectId(message['_id'])})
                answer = { 'header': 'got answer',
                        'Image':card['Image']
                        }
                guest = db['users'].find_one({'name': 'guest'})
                question = message['question']
                if question.split('&')[0] == 'Description' and message['answer'] == "[Aucune description]":
                    message['answer'] = ""
                if db['cards'].find_one({'_id': ObjectId(message['_id']), question.split('&')[0]: message['answer']}):
                    if question == "Image&Nom" or question == "Image&Description": #If we succeed to the question with the 4 images, second question...
                        image = card['Image']
                        answer = { 'header': 'new quizz',
                                    'Image':image,
                                    '_id': str(card['_id'])
                                }
                        if question == 'Image&Nom':
                            answer['question'] = 'Description'
                        else:
                            answer['question'] = 'Nom'
                        self.find_propositions(answer, card)
                    else: #if the quizz was not about the 4 images, we have the point
                        answer['point'] = 1
                        if message['current_score']+1 > guest['best_score']:
                            db['users'].update({'_id':guest['_id']}, {"$set":  {'best_score': message['current_score']+1}})
                else: #we failed
                    answer['point'] = 0
                answer['best_score'] = db['users'].find_one({'name': 'guest'})['best_score']
                self.write_message(answer)
            elif message['header'] == 'dans ma collection':
                card = db['cards'].find_one({'_id': ObjectId(message['_id'])})
                db['cards'].update({'_id': card['_id']}, {"$set":  {'Dans ma Collection': int(message['copies'])}})
            elif message['header'] == 'estimate next turn':
                cards = []
                _ids = []
                decks = []
                for deck in db[message['deck-type']].find({'Classe': message['classe']}):
                    not_good_deck = False
                    for card_played in message['cards-played']:
                        if not card_played in deck['Composition'].keys():
                            not_good_deck = True
                            break
                    if not_good_deck:
                        continue
                    decks.append([deck['Nom'], deck['Lien']])
                    for card_name, card_count in deck['Composition'].iteritems():
                        card = db['cards'].find_one({'Nom':card_name, 'Cout en mana': {'$lte': int(message['mana'])}})
                        if not card and message['piece']:
                                card = db['cards'].find_one({'Nom':card_name, 'Cout en mana': {'$lte': int(message['mana'])+1}})
                        if card and card['_id'] not in _ids:
                            _ids.append(card['_id'])
                            del card['_id']
                            cards.append(card)
                answer = { 'header': 'cards found',
                        'cards': sorted(cards, key=lambda x: (x['Cout en mana'], x['Type'])),
                        'decks': decks
                        }
                self.write_message(answer)
        except Exception, e:
            import traceback
            print(traceback.format_exc())

    def on_close(self):
        print "Client disconnected"

    def find_propositions(self, answer, card):
        if answer['question'] == 'Cout en mana':
            propositions = [card['Cout en mana']]
            for _ in range(2):
                n = randint(0,10)
                while n in propositions:
                    n = randint(0,10)
                propositions.append(n)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
        elif answer['question'] == 'Attaque':
            propositions = [card['Attaque']]
            for _ in range(2):
                n = randint(0,10)
                while n in propositions:
                    n = randint(0,10)
                propositions.append(n)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
        elif answer['question'] == 'Vie':
            propositions = [card['Vie']]
            for _ in range(2):
                n = randint(0,10)
                while n in propositions:
                    n = randint(0,10)
                propositions.append(n)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
        elif answer['question'] == 'Nom':
            propositions = [card['Nom']]
            total = db['cards'].find({'Type': card['Type']}).count()
            for _ in range(4):
                nom = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Nom']
                while nom in propositions:
                    nom = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Nom']
                propositions.append(nom)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
        elif answer['question'] == 'Description':
            if card['Description'] == "":
                propositions = ["[Aucune description]"]
            else:
                propositions = [card['Description']]
            total = db['cards'].find({'Type': card['Type']}).count()
            for _ in range(4):
                description = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Description']
                while description in propositions:
                    description = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Description']
                    if description == "":
                        description = "[Aucune description]"
                propositions.append(description)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
        elif answer['question'] == 'Image&Nom':
            image = card['Image']
            propositions = [image]
            total = db['cards'].find({'Type': card['Type']}).count()
            for _ in range(10):
                image = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Image']
                while image in propositions:
                    image = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Image']
                propositions.append(image)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
            answer['Nom'] = card['Nom']
        elif answer['question'] == 'Image&Description':
            image = card['Image']
            propositions = [image]
            total = db['cards'].find({'Type': card['Type']}).count()
            for _ in range(10):
                _card = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]
                image = _card['Image']
                while image in propositions or _card['Description'] == card['Description']: #we don't want twice the same description
                    image = db['cards'].find({'Type': card['Type']})[randint(0,total-1)]['Image']
                propositions.append(image)
            from random import shuffle
            shuffle(propositions)
            answer['propositions'] = propositions
            if card['Description'] == "":
                answer['Description'] = "[Aucune description]"
            else:
                answer['Description'] = card['Description']

class Application(tornado.web.Application):
    def __init__(self):

        handlers = [
            (r'/', IndexHandler),
            (r'/card', CardHandler),
            (r'/quizz', QuizzHandler),
            (r'/duels', DuelsHandler),
            (r'/websocket', WebSocketHandler),
        ]

        settings = {
            'template_path': pages_dir,
            'static_path': static_dir,
            'debug': True
        }

        tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == '__main__':
    webserver_port = 8080
    mongodb = None
    subprocess.Popen(['mongod', '-dbpath', '/Users/fjossinet/Development_projects/hearthstone/db'])

    while not mongodb:
        time.sleep(2)
        try :
            mongodb = MongoClient()
            db = mongodb['hearthstone']
            if not db['users'].find_one({'name': 'guest'}):
                db['users'].insert({
                    'name':'guest',
                    'best_score': 0
                })
        except Exception, e:
            print e
            print '\033[91mI cannot connect to Mongodb\033[0m'

    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(webserver_port)
    print "\033[92mYour webserver is now accessible \033[0m"

    webbrowser.open("http://localhost:%i"%webserver_port)

    main_loop = tornado.ioloop.IOLoop.instance()
    main_loop.start()
