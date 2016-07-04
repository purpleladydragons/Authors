import nltk
import pickle
import json
import re
import unicodedata as ud
import string
from bs4 import BeautifulSoup, SoupStrainer
from urllib2 import urlopen

start_url = "https://en.wikipedia.org/wiki/Ernest_Hemingway"
# TODO enable non-english names while still not allowing other crap
name_regex = re.compile(r"^[A-Za-z ,.'-]+$", re.U)
job_regex = re.compile('[^a-zA-Z]')

def get_all_authors():
    authors = set()
    base_url = "https://en.wikipedia.org/wiki/List_of_authors_by_name:_"
    for letter in string.ascii_uppercase:
        url = base_url + letter
        html = urlopen(url).read()

        count = 0
        # go thru every link on the page
        for link in BeautifulSoup(html, parse_only=SoupStrainer('a', href=True)).find_all("a", href=True):
            if link.has_attr('href'):
                if 'title' in link.attrs:
                    # check if the link is a list of things
                    if link.attrs['title'][0:7] == "List of":
                        # we're okay with all the letter lists because those come before
                        # our list of authors. problem is, the pages aren't consistent on 
                        # which letters they include, so if you do 24 as your threshold,
                        # you hit Z on a lot of them and get no authors
                        # so i actually don't know if 25 works for every page,
                        # or if it cuts off some, TODO i guess
                        if count > 25:
                            break
                        else:
                            count += 1
                    # if it's not a list, check if it matches basic english name stuff
                    elif name_regex.match(link.attrs['title']):
                        authors.add(link.attrs['title'])

    return authors

# TODO super fucking janky right now lol
def determine_occupation(text):
    try:
        start = min(text.index(" was "), text.index(" is "))
    except ValueError:
        try:
            start = text.index(" was ")
        except ValueError:
            try:
                start = text.index(" is ")
            except ValueError:
                return "NA"
    phrase = text[start:end]

    end = text[start:].index(".") + start

    print nltk.pos_tag(nltk.word_tokenize(phrase))

    words = phrase.split()
    job_raw = words[3]
    job = job_regex.sub('', job_raw)

    return job

class Author:
    def __init__(self, name, occupation, connections):
        self.name = name
        self.occupation = occupation
        self.connections = connections

def build_network(start_url, authors, network={}):

    base_url = "https://en.wikipedia.org"

    count = 0

    queue = [start_url]
    while queue:

        url = queue.pop()
        html = urlopen(url).read()

        page = BeautifulSoup(html)
        author = page.find("h1", {"id":"firstHeading"}).get_text()
        occupation = determine_occupation(page.find("div", {"id":"mw-content-text"}).find("p").get_text())

        if author not in network:
            network[author] = Author(author, occupation, [])
        else:
            continue

        print "Building", author, "was", occupation
        print "Queue Size:", len(queue)

        for link in BeautifulSoup(html, parse_only=SoupStrainer('a', href=True)).find_all("a", href=True):
            if link.has_attr('href'):
                if 'title' in link.attrs:
                    if link.attrs['title'] in authors:
                        if link.attrs['title'] not in network:
                            # set a limit for how many nodes we can add to network b/c computing time etc
                            if count < 600:
                                queue.append(base_url + link.attrs['href'])
                                count += 1

                        network[author].connections.append(link.attrs['title'])

    return network

all_authors = get_all_authors()

print "Done making authors set"

network = build_network(start_url, all_authors)

pickle.dump(network, open("network.p", "w"))

nodes_for_links = {}
links = []
nodes = []

for i, key in enumerate(network.keys()):
    author = network[key]
    nodes.append({"name":author.name, "size": len(author.connections), "occupation":author.occupation})
    nodes_for_links[author.name] = i

for i, key in enumerate(network.keys()):
    author = network[key]
    for link in author.connections:
        try:
            links.append({"source": nodes_for_links[author.name], "target": nodes_for_links[link]})
        except KeyError:
            pass

print len(nodes), "nodes"
json_data = {"nodes":nodes, "links":links}

with open("graph.json", "w") as f:
    f.write(json.dumps(json_data))
