#!/usr/bin/env python
#-*- coding: utf-8 -*-
#pylint: disable=
"""
File       : MongoIO.py
Author     : Valentin Kuznetsov <vkuznet AT gmail dot com>
Description: WMArchive Mongo storage client
"""

# futures
from __future__ import print_function, division

# system modules
import itertools

# Mongo modules
from pymongo import MongoClient
from pymongo.errors import InvalidDocument, InvalidOperation, DuplicateKeyError
from pymongo.son_manipulator import SONManipulator
from bson.son import SON

# WMArchive modules
from WMArchive.Storage.BaseIO import Storage
from WMArchive.Utils.Regexp import PAT_UID
from WMArchive.Utils.Exceptions import WriteError, ReadError

class WMASONManipulator(SONManipulator):
    """WMArchive MongoDB SON manipulator"""
    def __init__(self):
        SONManipulator.__init__(self)

    def transform_incoming(self, son, collection):
        "Manipulate an incoming SON object"
        if  self.will_copy():
            return SON(son)
        return son

    def transform_outgoing(self, son, collection):
        "Manipulate an outgoing SON object"
        if  self.will_copy():
            return SON(son)
        if  isinstance(son, dict) and '_id' in son:
            del son['_id']
        return son

class MongoStorage(Storage):
    "Storage based on MongoDB back-end"
    def __init__(self, uri, dbname='fwjr', collname='db', chunk_size=1000):
        "ctor with mongo uri: mongodb://host:port"
        Storage.__init__(self, uri)
        self.client = MongoClient(uri, w=1)
        self.mdb = self.client[dbname]
        self.mdb.add_son_manipulator(WMASONManipulator())
        self.collname = collname
        self.coll = self.mdb[collname]
        self.jobs = self.mdb['jobs'] # separate collection for job results
        self.log(self.coll)
        self.chunk_size = chunk_size

    def sconvert(self, spec, fields):
        "convert input spec/fields into ones suitable for MognoDB QL"
        return spec, fields

    def write(self, data, safe=None):
        "Write API, return ids of stored documents"
        if  not isinstance(data, list):
            data = [data] # ensure that we got list of data
        coll = self.coll
        if  isinstance(data[0], dict) and data[0].get('dtype', None) == 'job':
            coll = self.jobs
        wmaids = self.getids(data)
        total = 0
        try:
            # we use generator and itertools to slice specific chunk of data
            # for MongoDB bulk insertion
            gen = (r for r in data)
            while True:
                nres = coll.insert(itertools.islice(gen, self.chunk_size))
                if  not nres:
                    break
                total += len(nres)
        except InvalidDocument as exp:
            self.log('WARNING InvalidDocument: %s' % str(exp))
        except InvalidOperation as exp:
            self.log('WARNING InvalidOperation: %s' % str(exp))
        except DuplicateKeyError as exp:
            pass
        except Exception as exp:
            raise WriteError(str(exp))
        if  total != len(wmaids):
            err = 'Unable to insert all records, given (%s) != inserted (%s)' \
                    % (len(wmaids), total)
            raise WriteError(msg)
        return wmaids

    def read(self, spec, fields=None):
        "Read API, it reads data from MongoDB storage for provided spec."
        try:
            gen = self.find(spec, fields)
            docs = [r for r in gen]
            return docs
        except Exception as exp:
            raise ReadError(str(exp))

    def find(self, spec, fields):
        """
        Find records in MongoDB storage for provided spec, returns generator
        over MongoDB collection
        """
        if  not spec:
            spec = {}
        if  isinstance(spec, list):
            spec = {'wmaid': {'$in': spec}}
            return self.jobs.find(spec)
        elif  PAT_UID.match(str(spec)):
            spec = {'wmaid': spec}
            return self.jobs.find(spec)
        if  fields:
            return self.coll.find(spec, fields)
        return self.coll.find(spec)

    def update(self, ids, spec):
        "Update documents with given set of document ids and update spec"
        doc_query = {'wmaid' : {'$in': ids}}
        return self.coll.update(doc_query, spec, multi=True)

    def remove(self, spec=None):
        "Remove documents from MongoDB for given spec"
        if  not spec:
            spec = {}
        return self.coll.remove(spec)

    def dropdb(self, dbname):
        "Remove given database from MongoDB"
        return self.client.drop_database(dbname)

    def stats(self):
        "Return statistics about MongoDB"
        return self.mdb.command("collstats", self.collname)

    def jobsids(self):
        "Return jobs ids"
        out = []
        for row in self.jobs.find():
            if  'wmaid' in row:
                out.append({'wmaid':row['wmaid']})
        return out
