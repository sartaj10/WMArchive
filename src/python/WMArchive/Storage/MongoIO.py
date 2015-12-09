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

# WMArchive modules
from WMArchive.Storage.BaseIO import Storage
from WMArchive.Utils.Utils import tstamp

class MongoStorage(Storage):
    "Storage based on MongoDB back-end"
    def __init__(self, uri):
        Storage.__init__(self, uri)
        self.client = MongoClient(self.uri)
        self.coll = self.client['fwjr']['db']
        self.chunk_size = 100

    def write(self, data):
        "MongoIO write API"
        inserted = 0
        try:
            while True:
                nres = self.coll.insert(itertools.islice(data, self.chunk_size))
                if  nres and isinstance(nres, list):
                    inserted += len(nres)
                else:
                    break
        except InvalidDocument as exp:
            print(tstamp('WMA WARNING'), 'InvalidDocument during injection', str(exp))
        except InvalidOperation as exp:
            print(tstamp('WMA WARNING'), 'InvalidOperation during injection', str(exp))
        except DuplicateKeyError as exp:
            print(tstamp('WMA WARNING'), 'DuplicateKeyError during injection', str(exp))
        except Exception as exp:
            print(tstamp('WMA WARNING'), 'Uncaught exception', str(exp))

    def read(self, query=None):
        "MongoIO read API"
        pass
