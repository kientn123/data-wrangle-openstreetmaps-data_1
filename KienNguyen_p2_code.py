
# coding: utf-8

# In[9]:

# Author: Kien Nguyen
import xml.etree.ElementTree as ET
import pprint
import json
import re
import codecs

# Check to see if there is any non-5-digit format, and count the number of 5-digit format and the other
# 5 digig format
postal_re = re.compile(r'^[0-9]{5}$')

num_short_format = 0
num_long_format = 0
for _, elem in ET.iterparse('des-moines_iowa.osm'):
    if elem.tag == 'tag':
        if elem.attrib['k'] == 'addr:postcode':
            if not postal_re.match(elem.attrib['v']):
                num_long_format += 1
                print elem.attrib['v']
            else:
                num_short_format += 1
print 'done'
print num_long_format
print num_short_format


# In[8]:

# Explore Geographic Name Information System of Des Moines area
counties = set([])
ST_num = set([])
classes = set([])
st_alpha = set([])
county_num = set([])
for _, elem in ET.iterparse('des-moines_iowa.osm'):
    if elem.tag == 'tag':
        if elem.attrib['k'].startswith('gnis:'):
            if elem.attrib['k'] == 'gnis:County':
                counties.add(elem.attrib['v'])
            elif elem.attrib['k'] == 'gnis:ST_num':
                ST_num.add(elem.attrib['v'])
            elif elem.attrib['k'] == 'gnis:Class':
                classes.add(elem.attrib['v'])
            elif elem.attrib['k'] == 'gnis:ST_alpha':
                st_alpha.add(elem.attrib['v'])
            elif elem.attrib['k'] == 'gnis:County_num':
                county_num.add(elem.attrib['v'])
print counties
print ST_num
print classes
print st_alpha
print county_num
print 'done'


# In[9]:

# Check if any date is not in the format of "mm/dd/yyyy"
date_re = re.compile(r'^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$')

num_full_format = 0
num_short_format = 0
for _, elem in ET.iterparse('des-moines_iowa.osm'):
    if elem.tag == 'tag':
        if elem.attrib['k'] == 'gnis:created':
            if not date_re.match(elem.attrib['v']):
                num_short_format += 1
                print elem.attrib['v']
            else:
                num_full_format += 1
print 'done'
print num_full_format
print num_short_format


# In[12]:

# check to see if there are any abbreviated versions of street types
from collections import defaultdict

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons"]

def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])

    return street_types

print audit('des-moines_iowa.osm')
print 'done'


# In[23]:

# Convert xml into json data
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
postal_re = re.compile(r'^[0-9]{5}$')
date_re = re.compile(r'^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$')

# elements inside "created" of the json document
CREATED = ['version', 'changeset', 'timestamp', 'user', 'uid']
# used for correcting the street type
MAPPING = {'Pkwy': 'Parkway', 'Rd': 'Road', 'ST': 'Street', 'Ave': 'Avenue', 'St': 'Street', 'Dr': 'Drive',
           'Ct.': 'Court'}

# turn 9-digit postal code into 5-digit one
def fix_postal_code(code):
    if postal_re.match(code):
        return code
    else:
        return code[:5]

# turn date to consistent formate of mm/dd/yyyy
def fix_date_format(date):
    if date_re.match(date):
        return date
    else:
        month, day, year = map(int, date.split('/'))
        res = ''
        if month < 10:
            res += '0'
        res += str(month) + '/'
        if day < 10:
            res += '0'
        res += str(day) + '/' + str(year)
        return res

# Convert the abbreviated street type to the full verion
def update_name(name, mapping):

    m = street_type_re.search(name)
    if m and m.group() in mapping:
        m = m.group()
        name = name[:name.rfind(m)] + mapping[m]

    return name    
   
# Convert a xml node into a json document
def shape_element(element):
    node = {}
    if element.tag == 'node' or element.tag == 'way':
        node['id'] = element.attrib['id']
        node['type'] = element.tag
        node['created'] = {}
        for elem in CREATED:
            node['created'][elem] = element.attrib[elem]
        if element.tag == 'node':
            node['pos'] = [float(element.attrib['lat']), float(element.attrib['lon'])]
        else:
            node['node_refs'] = []
            for nd in element.iter('nd'):
                node['node_refs'].append(nd.attrib['ref'])
        node['address'] = {}
        node['gnis'] = {}
        for tag in element.iter('tag'):
            if lower.match(tag.attrib['k']):
                node[tag.attrib['k']] = tag.attrib['v']
            elif lower_colon.match(tag.attrib['k']):
                if tag.attrib['k'].startswith('addr'):
                    key = tag.attrib['k'][tag.attrib['k'].find(':')+1:]
                    if key == 'postcode':
                        # add correctly formatted postal code
                        node['address'][key] = fix_postal_code(tag.attrib['v'])
                    elif key == 'street':
                        # add full version of street type
                        node['address'][key] = update_name(tag.attrib['v'], MAPPING)
                    else:
                        node['address'][key] = tag.attrib['v']
                elif tag.attrib['k'].startswith('gnis'):
                    key = tag.attrib['k'][tag.attrib['k'].find(':')+1:]
                    if key == 'created':
                        # add correctly formatted date
                        node['gnis'][key] = fix_date_format(tag.attrib['v'])
                    else:
                        node['gnis'][key] = tag.attrib['v']
        if node['address'] == {}:
            node.pop('address', None)
        if node['gnis'] == {}:
            node.pop('gnis', None)
        return node
    else:
        return None
    

def process_map(file_in):
    # Write date to a json file for manual inspection purposes
    # Return a list of json object
    file_out = '{0}.json'.format(file_in)
    data = []
    with codecs.open(file_out, 'w') as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                fo.write(json.dumps(el) + '\n')
    return data

des_moines_data = process_map('des-moines_iowa.osm')   
print 'done'


# In[26]:

# Connect and add json data to mongodb
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client.iowa
for node in des_moines_data:
    db.desMoines.insert(node)
print db.desMoines.find_one()
print 'done'


# In[36]:

# Most popular postal codes
res = db.desMoines.aggregate([{'$match': {'address.postcode': {'$exists': 1}}},
                              {'$group': {'_id': '$address.postcode', 'count': {'$sum': 1}}},
                              {'$sort': {'count': -1}},
                              {'$limit': 5}])

pprint.pprint(list(res))


# In[42]:

# Number of documents / data points
print db.desMoines.find().count()


# In[43]:

# Number of nodes
print db.desMoines.find({'type': 'node'}).count()


# In[45]:

# Number of ways
print db.desMoines.find({'type': 'way'}).count()


# In[49]:

# Number of unique users
print len(db.desMoines.distinct('created.user'))


# In[37]:

# Number of users who make only one contribution
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client.iowa
res = db.desMoines.aggregate([{'$group': {'_id': '$created.user',
                                          'count': {'$sum': 1}}},
                              {'$group': {'_id': '$count',
                                          'num_users': {'$sum': 1}}},
                              {'$match': {'_id': 1}}])
pprint.pprint(list(res))


# In[50]:

# Number of shops
print db.desMoines.find({'shop': {'$exists': 1}}).count()


# In[51]:

# Number of nodes with amenity as cafe
print db.desMoines.find({'amenity': 'cafe'}).count()


# In[53]:

# Top one contributing user
res = db.desMoines.aggregate([{'$group': {'_id': '$created.user',
                                          'count': {'$sum': 1}}},
                              {'$sort': {'count': -1}},
                              {'$limit': 1}])
pprint.pprint(list(res))


# In[55]:

# Combined top ten user contributions
res = db.desMoines.aggregate([{'$group': {'_id': '$created.user',
                                          'count': {'$sum': 1}}},
                              {'$sort': {'count': -1}},
                              {'$limit': 10},
                              {'$group': {'_id': 'sum10',
                                          'sum': {'$sum': '$count'}}}])
pprint.pprint(list(res))


# In[38]:

# Most popular amenities
res = db.desMoines.aggregate([{"$match": {"amenity": {"$exists": 1}}},
                              {"$group": {"_id": "$amenity",
                                          "count": {"$sum": 1}}},
                              {"$sort": {"count": -1}},
                              {"$limit": 10}])

pprint.pprint(list(res))


# In[39]:

# Most popular religions
res = db.desMoines.aggregate([{"$match": {"religion": {"$exists": 1}}},
                              {"$group": {"_id": "$religion",
                                          "count": {"$sum": 1}}},
                              {"$sort": {"count": -1}},
                              {"$limit": 3}])
pprint.pprint(list(res))


# In[41]:

# Most popular highway types
res = db.desMoines.aggregate([{"$match": {"highway": {"$exists": 1}}},
                              {"$group": {"_id": "$highway",
                                          "count": {"$sum": 1}}},
                              {"$sort": {"count": -1}},
                              {"$limit": 3}])
pprint.pprint(list(res))

