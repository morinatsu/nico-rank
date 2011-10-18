# -*- coding: utf-8 -*-
import simplejson
from google.appengine.ext import db
import datetime
import logging


class GaeJson(simplejson.JSONEncoder):
    def default(self, obj):
        """ JSON Encoder for Model class of Google App Engine

            gaejson.encode(model) : encode model to JSON format
        """

        # db.Modelは辞書に
        if isinstance(obj, db.Model):
            properties = obj.properties().items()
            output = {}
            for field, value in properties:
                output[field] = getattr(obj, field)
            return output

        # db.QglQueryはリストに
        elif isinstance(obj, db.GqlQuery):
            return list(obj)

        # dateは文字列に
        elif isinstance(obj, datetime.date):
            return str(obj)

        return simplejson.JSONEncoder.default(self, obj)
