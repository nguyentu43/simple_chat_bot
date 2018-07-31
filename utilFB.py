from underthesea import ner
from pyvi import ViTokenizer, ViPosTagger
import requests
import re
import unicodedata
import datetime
import amlich
import wikipedia
import random
from bs4 import BeautifulSoup
import feedparser
import pytz

wikipedia.set_lang("vi")

def get_name_by_id(id):
	token = 'your-api-facebook-app'
	r = requests.get('https://graph.facebook.com/v2.6/{0}?access_token={1}'.format(id, token))
	data = r.json()
	return data.get('last_name') + ' ' + data.get('first_name')

#https://gist.github.com/thuandt/3421905
def no_accent_vietnamese(s):
    s = re.sub(u'Đ', 'D', s)
    s = re.sub(u'đ', 'd', s)
    return unicodedata.normalize('NFKD', u"" + s).encode('ASCII', 'ignore').decode('ASCII')

def get_json_weather(city):
	url_api_weather = "http://api.openweathermap.org/data/2.5/weather?q={city}&appid=your-api&units=metric&lang=vi"
	city = no_accent_vietnamese(city)
	city = city.replace(" ", "")
	url = url_api_weather.replace("{city}", city)
	r = requests.get(url)
	return r.json()

def get_temp(st, track, data):

	url_img_weather = "http://openweathermap.org/img/w/"
	
	result = ner(st.title())

	for i in result:
		if i[3] == 'B-LOC':
			city = i[0]
			break

	if 'city' not in locals():
		return ({"text": "Cho em tỉnh thành phố đi"}, 1)

	json_data = get_json_weather(city)

	if json_data['cod'] == 200:
		res = u"Thời tiết ở " + city + "\n"
		res += u"Tình trạng: " + json_data['weather'][0]['description'] + "\n"
		res += u"Nhiệt độ trung bình: " + str(json_data['main']['temp']) + " độ C\n"
		res += u"Nhiệt độ cao nhất: " + str(json_data['main']['temp_max']) + " độ C\n"
		res += u"Nhiệt độ thấp nhất: " + str(json_data['main']['temp_min']) + " độ C\n"
		res += u"Độ ẩm: " + str(json_data['main']['humidity']) + "%"
		return ({"text": res}, 1)
	else:
		return { "text" :"Lỗi: " + json_data["message"]}

def get_datetime(st, track, data):
	dt = datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
	if (dt.isoweekday() + 1 == 8):
		w =  'CN'
	else:
		w = 'T' + str(dt.isoweekday() + 1)

	return {"text":"Thời gian: %s %s " % (w, datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%d/%m/%Y %H:%M"))}

def get_bmi(st, track, data):
	st = st.lower()

	try:
		if st.index("cm"):
			st = st.replace("cm", " cm")
	except ValueError:
		st = st.replace("m", " m")
	st = st.replace("kg", " kg")
	arr = []

	tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st))
	for i, j in enumerate(tagger[1]):
		if j == 'M':
			arr.append(float(tagger[0][i]))
		if j == 'Nu' and tagger[0][i] == 'cm':
			arr[0] = arr[0] / 100

	if(len(arr) < 2):
		return ({"text": "Cho em chỉ số về chiều cao (m) và cân nặng (kg)"}, 1)

	arr = sorted(arr)

	h = arr[0]
	w = arr[1]

	bmi = w / (h*h)

	if(bmi < 18.5):
		tt = "gầy"
	elif (bmi < 24.9):
		tt = "bình thường"
	elif (bmi < 29.9):
		tt = "hơi béo"
	elif (bmi < 34.9):
		tt = "béo phì cấp độ 1"
	elif (bmi < 39.9):
		tt = "béo phì cấp độ 2"
	else:
		tt = "béo phì cấp độ 3"

	return ({"text": "Chỉ số BMI của bạn là: %.2f.\nTình trạng hiện tại: %s" % (bmi, tt)}, 1)

def convert_lunar_day(st, track, data):
	val = fetch_data(st, 'DATE')

	if type(val) == type(()):
		return val
	if type(val) == type(False):
		return ({"text":"Hãy nhập ngày"}, 1)
	date = val

	lunar_date = amlich.S2L(date.day, date.month, date.year);

	list_can = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Quý']
	can = (lunar_date[2] + 6) % 10

	list_chi = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tỵ', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi']
	chi = (lunar_date[2] + 8) % 12

	return ({"text": "Ngày %s theo âm lịch %s/%s/%s (năm %s %s)" % (date.strftime("%d/%m/%Y"), lunar_date[0], lunar_date[1], lunar_date[2], list_can[can], list_chi[chi])}, 1)

def convert_solar_day(st, track, data):
	
	val = fetch_data(st, 'DATE')

	if type(val) == type(()):
		return val
	if type(val) == type(False):
		return ({"text":"Hãy nhập ngày"}, 1)
	date = val

	leap_year = 0

	if (date.year % 19 in [3, 6, 9, 11, 14, 17]):
		leap_year = 1

	solar_date = amlich.L2S(date.day, date.month, date.year , leap_year);
	return ({"text": "Ngày %s theo dương lịch %s/%s/%s" % (date.strftime("%d/%m/%Y"), solar_date[0], solar_date[1], solar_date[2])}, 1)

def get_wiki(st, track, data):

	keyword = st[: st.rfind("là") - 1]

	try:
		page = wikipedia.page(keyword)
		title = page.title
		summary = page.summary

		image = 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png'
		if len(page.images) > 0:
			image = random.choice(page.images)
		url = page.url


		item = {
				"title": title, 
				"content": summary,
				"img": image, 
				"url": url, 
				"buttons": [("Xem chi tiết", "url")]
		}

		return get_template([item])
	except wikipedia.exceptions.PageError:
		return ({"text": 'Not Found'}, 0)
	return ({"text": 'Not Found'}, 0)

def remove_params(st, track, data):
	if 'params' in data:
		for key, value in data['params'].items():
			if key[0] != '_' and key in track:
				del track[key]

def build_query(st, track, data):

	if 'options' in data:

		if 'params' in data:

			for key, value in data['params'].items():

				if key not in track and 'intent' in track:
					if value == 'QUIZ':
						return (get_quick_replies(data['question'][key], data['options'][key]), 1)
					else:
						return ({"text":data['question'][key]}, 1)

				if value == 'QUIZ':
					for i, j in enumerate(data['options'][key]):
						if st.lower().find(j.lower()) >= 0:
							track[key] = j.lower()
							break

				if value == 'QUIZ' and key not in track:
					return (get_quick_replies(data['question'][key], data['options'][key]), 1)

			return eval(data['x_action'])(st, track, data)
		else:
			return (get_quick_replies(data['question'], data['options']), 1)

	else:
		return (get_template_button(random.choice(data['responses'], ["Gợi ý khác"])), 1)

def get_suggest_skin(st, track, data):
	return (get_template_button(random.choice(data['responses'][track['skin']]), ["Gợi ý khác"]), 1)

def get_info_boi(st, track, data):
	url_boi = "http://tuvi.xemtuong.net/boi/boi_bai/index.php"
	r = requests.post(url_boi, data={"lan": "1"})
	r = requests.post(url_boi, data={"lan": "2", "boibai": "Submit"})
	soup = BeautifulSoup(r.text, 'html.parser')
	kq1 = str(soup.find(attrs={"name":"ketqua1"})["value"])
	r = requests.post(url_boi, data={"lan": "3", "boibai": "Submit", "ketqua1": kq1})

	soup = BeautifulSoup(r.text, 'html.parser')
	kq2 = str(soup.find(attrs={"name":"ketqua2"})["value"])
	r = requests.post(url_boi, data={"lan": "4", "boibai": "Submit", "ketqua1": kq1, "ketqua2": kq2})

	soup = BeautifulSoup(r.text, 'html.parser')
	kq3 = str(soup.find(attrs={"name":"ketqua3"})["value"])
	r = requests.post(url_boi, data={"lan": "5", "boibai": "Submit", "ketqua1": kq1, "ketqua2": kq2, "ketqua3": kq3})

	soup = BeautifulSoup(r.text, 'html.parser')
	content = soup.find_all("table")[1].get_text()
	content = "Bạn rút được 3 lá bài: " + content
	content = content.replace("Lời Giải Đoán", "\nLời Giải Đoán")
	content += '\nTheo xemtuong.net'
	return {"text": content}

def get_info_bao(st, track, data):

	bao = { 
			"vietnamnet": {"rss":"http://vietnamnet.vn/rss/giai-tri.rss", "img": "https://upload.wikimedia.org/wikipedia/vi/2/22/Vietnamnet-Logo.png"}, 
			"vnexpress":{"rss":"https://vnexpress.net/rss/giai-tri.rss", "img": "https://scdn.vnecdn.net/vnexpress/restruct/i/v56/logo_default.jpg"},
			"tinhte.vn":{"rss":"https://tinhte.vn/rss", "img": "http://hanoilab.com.vn/toy/public/files/tinhte.jpg"}, 
			"dân trí":{"rss": "http://dantri.com.vn/giai-tri.rss", "img": "https://upload.wikimedia.org/wikipedia/commons/e/e9/Dan-tri.png"}
	}

	loai = track['bao']
	feed = feedparser.parse(bao[loai]['rss'])
	item = random.choice(feed['items'])
	image = None
	soup = BeautifulSoup(item['summary'], 'html.parser')
	try:
		image = soup.find('img')['src']
	except TypeError:
		image = bao[loai]['img']
	summary = soup.get_text()

	obj = {
		"title": item['title'], 
		"content": summary, 
		"img": image, 
		"url": item['link'], 
		"buttons": [("Xem chi tiết", "url"), ("Xem tin khác", "text")]
	}

	return (get_template([obj]), 1)

def save_data_track(st, track, data, data_intent):
	
	for key, value in data['params'].items():
		if key in track:
			continue
		if value == 'QUIZ':
			for i, j in enumerate(data_intent['options'][key]):
				if st.lower().find(j) >= 0:
					track[key] = j
					break
			if key not in track:
				return False

		fetch = fetch_data(st, value)

		if fetch == False:
			return ({"text": "Bạn nhập thông tin không đúng"}, 1)
		else:
		 track[key] = fetch
	return True

def fetch_data(st, t):
	tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st))
	for i, j in enumerate(tagger[1]):
		if j == 'Np' and t == 'NAME':
			return tagger[0][i]
		if j == 'M':
			if t == 'NUMBER':
				return tagger[0][i]
			if t == 'DATE':
				str_date = tagger[0][i]
				try:		
					return datetime.datetime.strptime(str_date, "%d/%m/%Y")
				except ValueError:
					return ({"text": "Bạn chưa nhập đúng định dạng ngày theo ngày/tháng/năm hoặc ngày nhập không hợp lệ"}, 1)
	return False

def get_story(st, track, data):
	r = requests.get('http://luudiachiweb.com/gettruyen.asp')
	soup = BeautifulSoup(r.text, 'html.parser')
	soup.find('p').decompose()
	content = soup.get_text()
	content += "\nNguồn: Truyện cười luudiachiweb.com"

	return (get_template_button(content, ["Xem truyện khác"]), 1)

def get_kqxs(st, track, data):

	tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st.title()))

	if tagger[1][-1] == 'Np':
		p = tagger[0][-1]

	url = 'http://xskt.com.vn/rss-feed/'

	rss = {
		'Bắc': 'mien-bac-xsmb.rss',
		'Nam': 'mien-nam-xsmn.rss',
		'Trung': 'mien-trung-xsmt.rss',
		'Bình_Định': 'binh-dinh-xsbdi.rss',
		'Đắc_Lắk': 'dac-lac-xsdlk.rss',
		'Đà Nẵng': 'da-nang-xsdng.rss',
		'Đắc_Nông': 'dac-nong-xsdno.rss',
		'TP.HCM' :'tp-hcm-xshcm.rss',
		'Sài_Gòn' :'tp-hcm-xshcm.rss',
		'Hcm' :'tp-hcm-xshcm.rss',
		'Quảng_Ngãi': 'quang-ngai-xsqng.rss',
		'Quảng_Nam': 'quang-nam-xsqnm.rss'
	}

	try:
		link = url + rss[p]
	except KeyError:
		p = no_accent_vietnamese(p.lower().replace("_", " "))
		vt = ""
		for i in p.split():
			vt += i[0]
		link = url + p.replace(" ", "-") + ("-xs{0}.rss").format(vt)

	feed = feedparser.parse(link)

	content = ""

	if len(feed['items']) == 0:
		feed = feedparser.parse(url + rss['Bắc'])

	for item in feed['items']:
		content += item['title'] + "\n"
		content += item['summary'].replace("[", "\n[").replace("8:", "\n8:") + "\n\n"

	return {"text": content}

def get_quan_an(st, track, data):

	if track.get("page") == None:
		track["page"] = 0

		quan = ""

		num = fetch_data(st, "NUMBER")

		if(num != False):
			quan = num
		else:
			tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st.title()))
			if tagger[1][-1] in ('Np'):
				quan = tagger[0][-1].replace("_", " ")

		map_quan = {"1":"1","Gò Vấp":"2","2":"4","3":"5","4":"6","5":"7","6":"8","7":"9","8":"10","9":"11","10":"12","11":"13","12":"14","Bình Thạnh":"15","Tân Bình":"16","Phú Nhuận":"17","Bình Tân":"18","Tân Phú":"19","Thủ Đức":"693","Củ Chi":"694","Hóc Môn":"695","Bình Chánh":"696","Cần Giờ":"698","Nhà Bè":"699"}

		try:
			quan = map_quan[quan]
		except Exception:
			quan = ""

		track["loc"] = quan

		keyword = ""

		tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st))
		for i, j in enumerate(tagger[0]):
			if j.lower() not in ('quán', 'ngon', 'ăn', 'ở', 'quận', 'huyện') and tagger[1][i] not in ('M', 'V', 'Np'):
				keyword += j.replace("_", " ") + " "

		if keyword != "":
			track["keyword"] = keyword

	else:
		track["page"] +=1

	if (track.get("keyword") != None):
		result = search_ddan(tenmon=track["keyword"], quan=track["loc"], p=track["page"])
	else:
		result = search_ddan(quan=track["loc"], p=track["page"])

	if len(result) == 0:
		return {"text": "Không còn quán nào khác"}

	list_items = []

	for item in result:

		list_items.append({
			"title": item['title'],
			"content": "Đánh giá: " + item["review"] + "/5 ⭐\n" + "Địa chỉ: " + item["address"],
			"img": item["img"],
			"url": item["url"],
			"buttons": [("Xem chi tiết", "url")]
		})

	return (get_template(list_items), 1)


def search_ddan(tenmon=None, thanhpho=217, quan="", gia=5000, p=""):

	if (tenmon != None):
		url = 'http://diadiemanuong.com/Search?q={0}&province={1}&district={2}&minPrice=0&maxPrice={3}&p={4}'.format(tenmon, thanhpho, quan, gia*1000, p)
	else:
		url = 'http://diadiemanuong.com/tim-kiem?sort=[Place].[Priority] DESC, [Place].[AvgRating] DESC, [Place].[CreateDate] DESC&province={0}&district={1}&minPrice=0&maxPrice={2}&p={3}'.format(thanhpho, quan, gia*1000, p)

	r = requests.get(url)
	soup = BeautifulSoup(r.text, 'html.parser')

	list_items = soup.find_all(attrs={"class": "list-item"})

	quan_an = []

	for item in list_items:
		url = item['href']
		title = item.h3.get_text()
		img = item.img['src']
		review = item.find(attrs={"class": "star"})['data-star-value']
		address = item.find(attrs={"class": "address"}).get_text()

		quan_an.append({
			"url": 'http://diadiemanuong.com' + url,
			"title": title,
			"img": img,
			"review": review,
			"address": address
		})

	return quan_an

def get_template(list_items):

	elements = []

	for item in list_items:

		list_button = []

		for b, t in item['buttons']:
			if t == 'url':
				list_button.append({
						"type": "web_url",
						"url": item['url'],
						"title": b
				})
			elif t == 'text':
				list_button.append({
						"type": "postback",
						"title": b,
						"payload": "<ANSWER>"
			})

		elements.append({
				"title": item['title'],
				"image_url": item['img'],
				"subtitle": item['content'],
				"default_action": {
					"type": "web_url",
					"url": item['url']
				},
			"buttons": list_button
		})

	obj = {
		"attachment": {
			"type": "template",
			"payload": {
				"template_type":"generic",
				"elements": elements
			}
		}
	}

	return obj

def get_template_button(content, buttons):
	list_button = []

	for b in buttons:
		list_button.append({
			"type": "postback",
			"title": b,
			"payload": "<ANSWER>"
		})

	obj = {
		"attachment": {
			"type": "template",
			"payload": {
				"template_type":"button",
				"text": content,
				"buttons": list_button
			}
		}
	}

	return obj

def get_quick_replies(quiz, buttons):
	list_button = []

	for b in buttons:
		list_button.append({
				"content_type": "text",
				"title": b,
				"payload": "<ANSWER>"
			})

	return {
		"text": quiz,
		"quick_replies": list_button
	}
