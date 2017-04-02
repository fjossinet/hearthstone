#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib, sys, re, math, io, datetime
from pymongo import MongoClient
import unicodedata
import commands
import fire

base_URL = "http://www.hearthstone-decks.com"
db = MongoClient()['hearthstone']

def get_cards():
    #f_droites = io.open("apostrophes_droites.csv", 'a', encoding='utf8')
    #f_curvees = io.open("apostrophes_curvees.csv", 'a', encoding='utf8')
    #f_both = io.open("apostrophes_both.csv", 'w', encoding='utf8')
    #we produce the empty bg for the images with 2 cards
    commands.getoutput("convert -size 291x400 xc:'#FFF2DB' website/images/templates/background.png")
    response = urllib.urlopen(base_URL+"/carte")
    content = str(response.read())
    soup = BeautifulSoup(content, 'html.parser')
    #first we get the last page index of cards from the first cards page
    div = soup.find('div', class_="pagination")
    cards_links = []
    for child in div.children:
        if child.name == 'a':
            cards_links.append(child)
    last_page = int(cards_links[-2].contents.pop())
    #now we iterate over each page to get the links for each page containing the card details
    total_card_recovered = 0
    for index in xrange(1, last_page+1):
        response = urllib.urlopen(base_URL+"/carte/%i"%index)
        content = str(response.read())
        soup = BeautifulSoup(content, 'html.parser')
        for c in soup.find_all('div', class_="carte_galerie_container"):
            #this div contains the link for each page containing the card details
            card_page_link = base_URL+c.contents[0]['href']
            print card_page_link
            if db['cards'].find_one({'Lien':card_page_link}):
                print "Already stored in the DB"
            else:
                response2 = urllib.urlopen(card_page_link)
                content2 = str(response2.read())
                soup2 = BeautifulSoup(content2, 'html.parser')
                card_description = {
                    'Lien': card_page_link
                }
                card_image_link = soup2.find('img', id="visuelcarte")['src']
                image_name = card_image_link.split('/')[-1].split('.jpg')[0].split('-')[0]
                #we download the image
                urllib.urlretrieve(card_image_link, "website/images/%s.jpg"%image_name)
                #we resize the image
                commands.getoutput('convert website/images/%s.jpg -resize 291x400 website/images/%s_resized.jpg'%(image_name, image_name.split('.jpg')[0]))
                commands.getoutput('rm website/images/%s.jpg'%image_name)
                commands.getoutput('mv website/images/%s_resized.jpg website/images/%s.jpg'%(image_name,image_name))
                #we produce the image with 2 cards
                commands.getoutput("convert website/images/{0}.jpg -fuzz 5% -transparent '#FFF2DB' -resize 95% website/images/resized.png".format(image_name))
                commands.getoutput("composite website/images/resized.png website/images/templates/background.png website/images/composite.png")
                commands.getoutput("composite -geometry  +10+20 website/images/resized.png website/images/composite.png website/images/%s_2.png"%image_name)
                card_description['Image'] = "%s.jpg"%image_name
                trs = soup2.find_all('tr')
                for tr in trs:
                    info = []
                    for td in tr.children:
                        for _child in td:
                            if not isinstance(_child, basestring): #the title of the information is like <strong>...</strong>
                                content = _child.contents
                                if len(content):
                                    if isinstance(content[0], basestring):
                                        info.append(content[0].strip())
                                    else:
                                        info.append('???')
                            elif isinstance(_child, basestring) and len(_child.strip()):
                                info.append(_child.strip())
                    if len(info) and info[0] != 'BBcode' and info[0] != '???':
                        key = unicodedata.normalize('NFKD', info.pop(0)).encode('ASCII', 'ignore') #to remove accents in the keys (easier to handler)
                        if key in [u'Vie', u'Attaque', u'Cout en mana', u'Cout en poussiere', u'Valeur en poussiere']:
                            card_description[key] = int(' '.join(info))
                        else:
                            value = ' '.join(info)
                            # if value.find(u"\u2019") != -1 and value.find(u"\u0027") != -1:
                            #     f_both.write(card_page_link)
                            #     f_both.write(u" ; ")
                            #     f_both.write(unicode(key, "utf-8"))
                            #     f_both.write(u" ; ")
                            #     f_both.write(value)
                            #     f_both.write(u'\n')
                            # elif value.find(u"\u0027") != -1:
                            #     f_droites.write(card_page_link)
                            #     f_droites.write(u" ; ")
                            #     f_droites.write(unicode(key, "utf-8"))
                            #     f_droites.write(u" ; ")
                            #     f_droites.write(value)
                            #     f_droites.write(u'\n')
                            # elif value.find(u"\u2019") != -1:
                            #     f_curvees.write(card_page_link)
                            #     f_curvees.write(u" ; ")
                            #     f_curvees.write(unicode(key, "utf-8"))
                            #     f_curvees.write(u" ; ")
                            #     f_curvees.write(value)
                            #     f_curvees.write(u'\n')
                            card_description[key] = value.replace(u"\u2019", u"\u0027") #some fields have curly single quotes (like Râle d’agonie). We replaced them with straight ones (like Râle d'agonie).
                card_description['Dans ma Collection'] = 0
                #we produce the images for the quizz
                db['cards'].insert(card_description)
                if card_description['Type'] == 'Sort':
                    commands.getoutput('composite -gravity center website/images/templates/masque_sort.png website/images/%s.jpg website/images/quizz/%s.jpg'%(image_name, image_name))
                elif card_description['Type'] == 'Serviteur':
                    commands.getoutput('composite -gravity center website/images/templates/masque_serviteur.png website/images/%s.jpg website/images/quizz/%s.jpg'%(image_name, image_name))
                elif card_description['Type'] == 'Arme':
                    commands.getoutput('composite -gravity center website/images/templates/masque_arme.png website/images/%s.jpg website/images/quizz/%s.jpg'%(image_name, image_name))
                total_card_recovered += 1
                print "%i cards recovered"%total_card_recovered

def cluster():
    from collections import Counter
    from random import randint
    WORD = re.compile(r'\S+')
    seed = "points de dégâts à un personnage"
    regx = re.compile(seed, re.IGNORECASE)
    card = db['cards'].find_one({
        'Description': regx
    })
    vector1 = WORD.findall(card['Description'])

    for _card in db['cards'].find({'Description': regx}):
        if card != _card:
            vector2 = WORD.findall(_card['Description'])
            if len(set(vector1).intersection(vector2)) > 2:
                print card['Nom'], " <-> ", _card['Nom']
                print card['Description'], " <-> ", _card['Description']

def get_decks(page="mois", score_cutoff = 5, drop = False):
    if drop:
        db.drop_collection('decks_%s'%page) #on erase les decks du mois stockés
    for card in db['cards'].find(): #on erase les données metagame des cartes
        db['cards'].update({'_id': card['_id']}, {"$unset":  {'Metagame_%s'%page: ""}})
    usages = {
        'Chasseur': {},
        'Chaman': {},
        'Druide': {},
        u'D\xe9moniste': {},
        'Guerrier': {},
        'Mage': {},
        'Paladin': {},
        u'Pr\xeatre': {},
        'Voleur': {},
    }
    response = urllib.urlopen(base_URL+"/deck?top=%s"%page)
    content = str(response.read())
    soup = BeautifulSoup(content, 'html.parser')
    #first we get the last page index of cards from the first cards page
    div = soup.find('div', class_="pagination")
    deck_links = []
    for child in div.children:
        if child.name == 'a':
            deck_links.append(child)
    last_page = int(deck_links[-2].contents.pop())
    deck_note = -1
    total_decks = {
        'Chasseur': 0,
        'Chaman': 0,
        'Druide': 0,
        u'D\xe9moniste': 0,
        'Guerrier': 0,
        'Mage': 0,
        'Paladin': 0,
        u'Pr\xeatre': 0,
        'Voleur': 0,
    }
    all_total_decks = 0
    for index in xrange(1, last_page+1):
        print "page de deck n", index
        response = urllib.urlopen(base_URL+"/deck/%i?top=%s"%(index,page))
        content = str(response.read())
        soup = BeautifulSoup(content, 'html.parser')
        for td in soup.find_all('td', class_="nom_deck"):
            deck_link = base_URL+td.find('a')['href']
            print deck_link
            if db['decks_%s'%page].find_one({'Lien':deck_link}):
                print "Already stored in the DB"
            else:
                response = urllib.urlopen(deck_link)
                content = str(response.read())
                soup = BeautifulSoup(content, 'html.parser')
                deck_title = soup.find('h1').text
                deck_class = soup.find('input', id="classe_nom")['value']
                deck_note = int(soup.find('span', class_="up_vert").text)-int(soup.find('span', class_="up_rouge").text)
                cards_in_deck = {}
                cards_in_my_collection = 0
                total_cards_in_deck = 0
                print deck_title, deck_note
                if deck_note >= score_cutoff:
                    for tr in soup.find_all('tr', class_="alt"):
                        td = tr.find('td', class_="zecha-popover")
                        if td:
                            image_link = "http://www.hearthstone-decks.com"+td.find('img', class_="zecha-popover-image")['src']
                            image_name = image_link.split('/')[-1].split('.jpg')[0]
                            my_card = db['cards'].find_one({'Image': "%s.jpg"%image_name})
                            if not my_card:
                                print "Card not in the database: ", image_link
                                sys.exit(0)
                            card_count = int(tr.find('td', class_="quantite").text)
                            total_cards_in_deck += card_count
                            cards_in_deck[my_card['Nom']] = card_count

                            copies = my_card.get('Dans ma Collection', 0)
                            if copies == card_count:
                                cards_in_my_collection += copies
                            elif card_count < copies:
                                cards_in_my_collection += card_count
                            elif copies < card_count:
                                cards_in_my_collection += copies
                    if len(cards_in_deck) > 0:
                        db['decks_%s'%page].insert({
                            'Nom': deck_title,
                            'Classe': deck_class,
                            'Note': deck_note,
                            'Lien': deck_link,
                            'Composition': cards_in_deck,
                            'Possedees': float("{0:.2f}".format(cards_in_my_collection/float(total_cards_in_deck)*100))
                        })
                        card_names = cards_in_deck.keys()
                        for i in range(0, len(card_names)):
                            if not usages[deck_class].has_key(card_names[i]):
                                usages[deck_class][card_names[i]] = 0
                            usages[deck_class][card_names[i]] = usages[deck_class][card_names[i]] +1
                        total_decks[deck_class] = total_decks[deck_class]+ 1
                        all_total_decks +=1
                else:
                    break
        if deck_note != -1 and deck_note < score_cutoff:
            break
    for card in db['cards'].find():
        metagame = {
            'Total_decks': all_total_decks,
            'Score_cutoff': score_cutoff
            }
        for classe_ in ['Chasseur', 'Chaman', 'Druide', u'D\xe9moniste','Guerrier','Mage','Paladin',u'Pr\xeatre','Voleur']:
            if usages[classe_].has_key(card['Nom']):
                metagame[classe_] = {'Presence':usages[classe_][card['Nom']], 'Total_decks': total_decks[classe_]}
            else:
                metagame[classe_] = {'Presence':0, 'Total_decks': total_decks[classe_]}
        db['cards'].update({'Nom': card['Nom']}, {"$set":  {'Metagame_%s'%page: metagame}})

def mine_decks():
    for classe_ in ['Chasseur', 'Chaman', 'Druide', u'D\xe9moniste','Guerrier','Mage','Paladin',u'Pr\xeatre','Voleur']:
        print "\n################ %s ##################\n"%classe_
        for page in ['semaine', 'mois']:
            query = {}
            print "--- Statistiques %s -----\n"%page
            total_decks = 0
            all_total_decks = 0
            import numpy as np
            utilisations = []
            for card in db['cards'].find(query):
                if not card.has_key('Metagame_%s'%page):
                    #print "Pas trouvée dans le metagame", card['Nom']
                    pass
                else:
                    metagame = card['Metagame_%s'%page]
                    all_total_decks = metagame['Total_decks']
                    utilisations.append(metagame[classe_]['Presence'])
                    total_decks = card['Metagame_%s'%page][classe_]['Total_decks']
            print "All Total decks: %i"%all_total_decks
            print "%s Total decks: %i (%0.2f%% of All)\n"%(classe_, total_decks, total_decks/float(all_total_decks)*100)
            a = np.array(utilisations)
            p = np.percentile(a, 90)
            best=[]
            for card in db['cards'].find(query):
                if card.has_key('Metagame_%s'%page):
                    presence = card['Metagame_%s'%page][classe_]['Presence']
                    if presence > p:
                        presence_percent = presence/float(card['Metagame_%s'%page][classe_]['Total_decks'])*100
                        best.append((classe_, card['Rarete'], card['Nom'], presence_percent))
            best = sorted(best, key=lambda b: (b[0], -b[3]))
            for b in best:
                print "%s :"%b[2], "%.2f%% des decks"%b[3], "(%s)"%b[1]
            print ""

#helper function to curate the db
def fix_database():
    for card in db['cards'].find():
        db['cards'].update({'_id': card['_id']}, {"$set":  {'Dans ma Collection': int(card['Dans ma Collection'])}})

#function to test the batch production of images with 2 cards
def images():
    commands.getoutput("convert -size 291x400 xc:'#FFF2DB' website/images/templates/background.png")
    from os import listdir
    for f in listdir('website/images/'):
        if f.endswith('.jpg'):
            commands.getoutput("convert website/images/{0} -fuzz 5% -transparent '#FFF2DB' -resize 95% website/images/resized.png".format(f))
            commands.getoutput("composite website/images/resized.png website/images/templates/background.png website/images/composite.png")
            commands.getoutput("composite -geometry +10+20 website/images/resized.png website/images/composite.png website/images/%s_2.png"%f.split('.jpg')[0])

if __name__ == '__main__':
    fire.Fire()
    #get_cards()
    #cluster()
    #drop = True
    #get_decks(page="semaine", score_cutoff = 1, drop = drop)
    #get_decks(page="mois", score_cutoff = 5, drop = drop)
    #get_decks(page="total", score_cutoff = 10, drop = drop)
    #mine_decks()
    #fix_database()
