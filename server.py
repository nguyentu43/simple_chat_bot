from chatbot import Chatbot
import util
import sys
import json
import traceback
import requests

chatbot = Chatbot()
chatbot.load()

from flask import Flask, render_template, request, jsonify, session, redirect
app = Flask(__name__)
app.secret_key = 'mychatbot'

token = 'your-api-facebook-app'

@app.route('/', methods=['GET', 'POST'])
def index():
	if 'name' in session:
		return redirect('/chat')
	if request.method == 'POST':
		print(request.data)
		session['name'] = request.values.get('name')
		session['gender'] = request.values.get('gender')
		if request.values.get('t2s') == 'on':
			session['t2s'] = 1
		else:
			session['t2s'] = 0
		return redirect('/chat')
	return render_template('index.html')
@app.route('/privacy-policy')
def privacy_policy():
	return render_template('privacypolicy.html')

@app.route('/chat')
def chat():
	if 'name' not in session:
		return redirect('/')
	return render_template('chat.html', gender=session['gender'], t2s=session['t2s'])

@app.route('/response', methods=['POST'])
def response():
	content = request.get_json()
	res = chatbot.response(content['txt'], session)
	return jsonify({"txt": res})

@app.route('/out')
def out():
	session.clear()
	return redirect('/')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
	if request.method == 'POST':
		send = ""
		try:
			params = {
				'access_token': token
			}

			headers = {
				'Content-Type': 'application/json'
			}

			data = request.get_json()

			print(data)

			data = data['entry'][0]['messaging'][0]
			sender = data['sender']['id']

			requests.post('https://graph.facebook.com/v2.6/me/messages/', params=params, headers=headers, data=json.dumps({ 'recipient': { 'id': sender }, "sender_action": "mark_seen"}))
			requests.post('https://graph.facebook.com/v2.6/me/messages/', params=params, headers=headers, data=json.dumps({ 'recipient': { 'id': sender }, "sender_action": "typing_on"}))

			if data.get('message') != None:
				if data['message'].get("text") != None:
					text = data['message']['text']
					send = chatbot.responseFB(sender, text)
				else:
					send = json.dumps({ 'recipient': { 'id': sender }, "message": {"text": "Like"}})
			else:
				text = data['postback']['title']
				send = chatbot.responseFB(sender, text)
			
		except Exception as e:
			print(e)
			send = json.dumps({ 'recipient': { 'id': sender }, 'message': {"text": "Đã xảy ra lỗi. Vui lòng thử lại sau"}})
		
		requests.post('https://graph.facebook.com/v2.6/me/messages/', params=params, headers=headers, data=json.dumps({ 'recipient': { 'id': sender }, "sender_action": "typing_off"}))
		requests.post('https://graph.facebook.com/v2.6/me/messages/', params=params, headers=headers, data=send)

	elif request.method == 'GET':
		if request.args.get('hub.verify_token') == 'token-facebook':
			return request.args.get('hub.challenge')
	return jsonify({'ok': '1'})
if __name__ == "__main__":
	app.run()