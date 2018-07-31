import json
import numpy as np
import pickle
import random
from model import Model
import util
import utilFB
from pyvi import ViTokenizer, ViPosTagger
import datetime
from pymongo import MongoClient
client = MongoClient('mongo-host', 'port')
db = client.chatbot
db.authenticate('user', 'pass')
collection = db.users

POS_TAG = ['F', 'L'] #M: số, F: dấu câu, L: định lượng
REPLACE = {'M': '100', 'Np': 'Việt_Nam'}
STOP_WORDS = []
SKIP_WORDS = ['Hi', 'Hello', 'Goodbye', 'Bye', 'Thank']

DATA_FILE = "data.json"

SAVE_FILE = "training_data"

class Chatbot:
	def __init__(self):
		self.documents = []
		self.classes = []
		self.words = []
		self.train_x = []
		self.train_y = []
		self.model = 0

		with open(DATA_FILE, encoding="utf-8") as data:
			self.json_data = json.load(data)

	def create_and_train(self):

		for key, value in self.json_data.items():

			if 'patterns' not in value:
				continue

			for pattern in value['patterns']:
				tagger = ViPosTagger.postagging(ViTokenizer.tokenize(pattern))
				w = []
				for i, j in enumerate(tagger[1]):
					if j in REPLACE:
						tagger[0][i] = REPLACE[j]
					if j not in POS_TAG and tagger[0][i] not in STOP_WORDS:
						w.append(tagger[0][i])
				self.words.extend(w)

				self.documents.append((w, key))

			self.classes.append(key)

		self.words = sorted(list(set(self.words)))

		training = []

		for doc in self.documents:
			st_out = [0] * len(self.words)

			for w in doc[0]:
				st_out[self.words.index(w)] = doc[0].count(w)

			class_out = [0]*len(self.classes)
			class_out[self.classes.index(doc[1])] = 1

			training.append([st_out, class_out])

		random.shuffle(training)
		training = np.array(training)
		self.train_x = list(training[:,0])
		self.train_y = list(training[:,1])

		pickle.dump({"documents": self.documents, "classes": self.classes, "words": self.words}, open(SAVE_FILE, "wb"))

		self.model = Model()
		self.model.train(self.train_x, self.train_y)

	def load(self):
		data = pickle.load(open(SAVE_FILE, "rb"))
		self.documents = data['documents']
		self.classes = data['classes']
		self.words = data['words']
		self.model = Model()
		self.model.load()

	def convert_st_to_bow(self, st):
		bow = [0] * len(self.words)
		tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st))

		if not (len(tagger[1]) == 1 and tagger[1][0] == 'Np' and tagger[0][0] not in SKIP_WORDS):
			tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st.lower()))

		for i, j in enumerate(tagger[1]):
			if j in REPLACE:
				tagger[0][i] = REPLACE[tagger[1][i]]
			if tagger[0][i] in self.words:
				bow[self.words.index(tagger[0][i])] = tagger[0].count(tagger[0][i])
		return np.array(bow)

	def response(self, st, session):

		ERR_THRESHOLD = 0.25

		st = st.strip()

		bow = self.convert_st_to_bow(st)
		result = self.model.predict(bow)
		result = list(result[0])

		key_class = "khong_biet"

		if(max(result) > ERR_THRESHOLD):
			classes_index = result.index(max(result))
			key_class = self.classes[classes_index]

		value = self.json_data[key_class]

		if value['type'] == 1:
			response = random.choice(value['responses'])

		if value['type'] == 2:
			getattr(util, 'remove_params')(st, session, value)
			val = getattr(util, value['action'])(st, session, value)
			if type(val) == type(()):
				if val[1] == 1:
					session['intent'] = key_class
					response = val[0]
			else:
				session.pop('intent', None)
				response = val

		if value['type'] == 3:
			if 'intent' in session and session.get('intent') == value['intent']:
				val = getattr(util, "save_data_session")(st, session, value, self.json_data[value['intent']])
				if val != type(()):
					val = getattr(util, self.json_data[session.get('intent')]["action"])(st, session, self.json_data[value['intent']])
				if type(val) == type(()):
					if val[1] == 1:
						response = val[0]
				else:
					session.pop('intent', None)
					response = val

		if value['type'] == 4:
			if 'intent' in session and session.get('intent') in value['intents']:
				val = getattr(util, self.json_data[session.get('intent')]["action"])(st, session, self.json_data[session.get('intent')])
				if type(val) == type(()):
					if val[1] == 1:
						response = val[0]
				else:
					session.pop('intent', None)
					response = val

		if 'response' not in locals():
			response = random.choice(self.json_data['khong_biet']['responses'])
			session.pop('intent', None)

		print(session)

		return response.replace("{name}", session['name'])

	def responseFB(self, sender, st):

		track = collection.find_one({"sender_id": sender})

		if (track == None):
			sender_name = utilFB.get_name_by_id(sender)
			collection.insert_one({"sender_id": sender, "name": sender_name})
			track = collection.find_one({"sender_id": sender})
		else:
			sender_name = track["name"]

		ERR_THRESHOLD = 0.25

		st = st.strip()

		bow = self.convert_st_to_bow(st)
		result = self.model.predict(bow)
		result = list(result[0])

		key_class = "khong_biet"

		if(max(result) > ERR_THRESHOLD):
			classes_index = result.index(max(result))
			key_class = self.classes[classes_index]

		value = self.json_data[key_class]

		if value['type'] == 1:
			response = {"text": random.choice(value['responses'])}

		if value['type'] == 2:
			getattr(utilFB, 'remove_params')(st, track, value)
			val = getattr(utilFB, value['action'])(st, track, value)
			if type(val) == type(()):
				if val[1] == 1:
					track['intent'] = key_class
					response = val[0]
			else:
				if track.get('intent'):
					del track['intent']
				response = val

		if value['type'] == 3:
			if 'intent' in track and track.get('intent') == value['intent']:
				val = getattr(utilFB, "save_data_track")(st, track, value, self.json_data[value['intent']])
				if val != type(()):
					val = getattr(utilFB, self.json_data[track.get('intent')]["action"])(st, track, self.json_data[value['intent']])
				if type(val) == type(()):
					if val[1] == 1:
						response = val[0]
				else:
					if track.get('intent'):
						del track['intent']
					response = val

		if value['type'] == 4:
			if 'intent' in track and track.get('intent') in value['intents']:
				val = getattr(utilFB, self.json_data[track.get('intent')]["action"])(st, track, self.json_data[track.get('intent')])
				if type(val) == type(()):
					if val[1] == 1:
						response = val[0]
				else:
					if track.get('intent'):
						del track['intent']
					response = val

		if 'response' not in locals():
			response = {"text": random.choice(self.json_data['khong_biet']['responses'])}
			if track.get('intent'):
				del track['intent']

		track["last_time"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

		collection.find_one_and_replace({"sender_id": sender}, track)

		print(track)

		if response.get('text') != None:
			response['text'] = response['text'].replace("{name}", sender_name)

		return json.dumps({ 'recipient': { 'id': sender }, 'message': response })
