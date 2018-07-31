from chatbot import Chatbot
import util
import sys

chatbot = Chatbot()

if len(sys.argv) > 1 and sys.argv[1] == 'train':
	chatbot.create_and_train()
else:
	chatbot.load()
	str = input("Hỏi: ")
	while str != "":
		print("Trả lời: " + chatbot.response(str))
		str = input("Hỏi: ")
