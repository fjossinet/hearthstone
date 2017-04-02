A project to manage a collection of hearthstone cards
=====================================================

This project is based on the website [Hearthstone Decks]("http://www.hearthstone-decks.com")

Dependencies: MongoDB, ImageMagick, Python >= 2.7

QuickStart on OSX:
------------------
Installation:
  * install [homebrew](https://brew.sh/index_fr.html)
  * from a terminal, type: brew update ; brew install mongodb ; brew install ImageMagick
  * install the [Anaconda Python Distribution](https://www.continuum.io)
  * from a terminal, type: conda install pymongo ; pip install fire

Running:
  * first you need to create the database. From the root directory, type: python crawl.py get_cards
  * then you need to install the website dependencies. From the "website" directory type: bower install
  * From the root directory, type: ./server.py
