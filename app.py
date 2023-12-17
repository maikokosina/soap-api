#!venv/bin/python

import base64
import hashlib
from spyne import Application, rpc, ServiceBase, Integer, String
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.protocol.xml import XmlDocument
from spyne.server.wsgi import WsgiApplication
from pymongo import MongoClient
from bson.json_util import dumps

client_mongo = MongoClient("mongodb://127.0.0.1:27017")
db = client_mongo.archive
users = db.users
pages = db.pages
access = db.access
files = db.files

current_user = []

class Auth(ServiceBase):
	@rpc(String, String, _returns=String)
	def auth(ctx, user_name, key):
		passmd5 = hashlib.md5(key.encode('utf-8')).hexdigest()
		user_auth = users.find_one({"user_name": user_name, "password": passmd5.upper()})
		if user_auth is None:
			return 'Wrong username or password!'
		else:
			current_user.append(user_auth)
			return 'Success!'	
			
class GetPages(ServiceBase):
	@rpc(_returns=String)
	def get_pages(ctx):
		user_id = 0
		for user in current_user:
			user_id = user['user_id']
		
		if user_id == 0:
			return 'Invalid login'
		else:
			user_pages = []
			for access1 in access.find({"list": user_id, "privilege": "Read"},{ "_id": 0 }):
				user_pages.append(access1['page_id'])
			
			if user_pages == []:
				return 'No pages'
			
			pages_cursor = pages.find({"page_id": {"$in": user_pages}},{ "_id": 0 })
			pages_list = dumps(pages_cursor)
			return pages_list
		
class GetPage(ServiceBase):
	@rpc(Integer, _returns=String)
	def get_page(ctx, page_id):
		user_id = 0
		for user in current_user:
			user_id = user['user_id']
		
		if user_id == 0:
			return 'Invalid login'
		else:
			pages_cursor = pages.find({ },{ "_id": 0 })
			pages_list = list(pages_cursor)
	
			page = list(filter(lambda p: p['page_id'] == page_id, pages_list))
			if len(page) == 0:
				return 'This page does not exists!'
			
			if access.find_one({"page_id": page_id, "list": user_id, "privilege": "Read"},{ "_id": 0 }) is None:
				return 'Forbidden'
			
			return dumps(page)

application = Application([Auth, GetPages, GetPage],
			'spyne.lr3.archive.soap',
			in_protocol=HttpRpc(),
			out_protocol=XmlDocument())
			
wsgi_app = WsgiApplication (application)

if __name__ == '__main__':
	import logging
	from wsgiref.simple_server import make_server
	
	logging.basicConfig(level=logging.DEBUG)
	logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
	
	server = make_server('127.0.0.1', 8000, wsgi_app)
	
	print("listening to http://127.0.0.1:8000")
	print("wsdl is at: http://localhost:8000/?wsdl")
	
	server.serve_forever()
	
	app.run()	
