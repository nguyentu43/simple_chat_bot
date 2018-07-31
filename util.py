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

def get_temp(st, session, data):

	url_img_weather = "http://openweathermap.org/img/w/"
	
	result = ner(st.title())

	for i in result:
		if i[3] == 'B-LOC':
			city = i[0]
			break

	if 'city' not in locals():
		return ("Cho em tỉnh thành phố đi", 1)

	json_data = get_json_weather(city)

	if json_data['cod'] == 200:
		res = u"<strong>Thời tiết ở " + city + ".</strong><br/>"
		res += u"Tình trạng: " + json_data['weather'][0]['description'] + ".<img src='" + url_img_weather + json_data['weather'][0]['icon'] + ".png'/><br/>"
		res += u"Nhiệt độ trung bình: " + str(json_data['main']['temp']) + " độ C.<br/>"
		res += u"Nhiệt độ cao nhất: " + str(json_data['main']['temp_max']) + " độ C.<br/>"
		res += u"Nhiệt độ thấp nhất: " + str(json_data['main']['temp_min']) + " độ C.<br/>"
		res += u"Độ ẩm: " + str(json_data['main']['humidity']) + "%.<br/>"
		return (res, 1)
	else:
		return "<strong>Lỗi: " + json_data["message"] + "</strong>"

def get_datetime(st, session, data):
	dt = datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
	if (dt.isoweekday() + 1 == 8):
		w =  'CN'
	else:
		w = 'T' + str(dt.isoweekday() + 1)

	return ("Thời gian: %s %s " % (w, datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%d/%m/%Y %H:%M")))

def get_bmi(st, session, data):
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
		return ("Cho em chỉ số về chiều cao (m) và cân nặng (kg)", 1)

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

	return ("Chỉ số BMI của bạn là: %.2f.<br/>Tình trạng hiện tại: %s" % (bmi, tt), 1)

def convert_lunar_day(st, session, data):
	val = fetch_data(st, 'DATE')

	if type(val) == type(()):
		return val
	if type(val) == type(False):
		return ("Hãy nhập ngày", 1)
	date = val

	lunar_date = amlich.S2L(date.day, date.month, date.year);

	list_can = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Quý']
	can = (lunar_date[2] + 6) % 10

	list_chi = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tỵ', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi']
	chi = (lunar_date[2] + 8) % 12

	return ("Ngày %s theo âm lịch %s/%s/%s (năm %s %s)" % (date.strftime("%d/%m/%Y"), lunar_date[0], lunar_date[1], lunar_date[2], list_can[can], list_chi[chi]), 1)

def convert_solar_day(st, session, data):
	
	val = fetch_data(st, 'DATE')
	if type(val) == type(()):
		return val
	if type(val) == type(False):
		return ("Hãy nhập ngày", 1)
	date = val

	leap_year = 0

	if (date.year % 19 in [3, 6, 9, 11, 14, 17]):
		leap_year = 1

	solar_date = amlich.L2S(date.day, date.month, date.year , leap_year);
	return ("Ngày %s theo dương lịch %s/%s/%s" % (date.strftime("%d/%m/%Y"), solar_date[0], solar_date[1], solar_date[2]), 1)

def get_wiki(st, session, data):
	
	keyword = st[: st.rfind("là") - 1]

	try:
		page = wikipedia.page(keyword)
		html = page.summary

		if len(page.images) > 0:
			html += '<br/><img src="' + random.choice(page.images) +'" style="margin-top: 5px" class="h-25 w-25 img-thumbnail" alt="hinh" />'

		html += '<br/><a target="_blank" class="btn btn-outline-primary btn-sm" style="margin-top: 5px" href="' + page.url + '" role="button">Xem chi tiết trên Wikipedia</a>'

		return html
	except Exception:
		return ('Not Found' , 0)
	return ('Not Found', 0)

def build_question_html(question, options=None):
	html = '<div class="alert alert-info" role="alert">%s</div>' % question

	if options == None:
		return html

	type_button = ['primary', 'warning', 'info',  'danger', 'success']
	for i, j in enumerate(options):
		html += '<a target="_blank" class="btn btn-%s btn-select" role="button" style="margin-left: 5px">%s</a>' % (type_button[i % len(type_button)], j)
	return html

def remove_params(st, session, data):
	if 'params' in data:
		for key, value in data['params'].items():
			if key[0] != '_' and key in session:
				session.pop(key, None)

def build_query(st, session, data):

	if 'options' in data:

		if 'params' in data:

			for key, value in data['params'].items():

				if key not in session and 'intent' in session:
					if value == 'QUIZ':
						return (build_question_html(data['question'][key], data['options'][key]), 1)
					else:
						return (build_question_html(data['question'][key]), 1)

				if value == 'QUIZ':
					for i, j in enumerate(data['options'][key]):
						if st.lower().find(j.lower()) >= 0:
							session[key] = j.lower()
							break

				if value == 'QUIZ' and key not in session:
					return (build_question_html(data['question'][key], data['options'][key]), 1)

			return eval(data['x_action'])(st, session, data)
		else:
			return (build_question_html(data['question'], data['options']), 1)

	else:
		return (random.choice(data['responses']), 1)

def get_suggest_skin(st, session, data):
	return (random.choice(data['responses'][session['skin']]), 1)

def get_info_boi(st, session, data):
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
	html = re.sub("(\\r|\\n|\\xa0)", "", soup.find_all("table")[1].get_text())

	html = "Bạn rút được 3 lá: " + html
	html = html.replace("Lời Giải Đoán", "<br/><br/><h4 class='text-primary text-center'>-Lời Giải Đoán-</h4>")
	html = html.replace("Bổn Mạng:", "<br/><strong>Bổn Mạng:</strong>")
	html = html.replace("Tài Lộc:", "<br/><br/><strong>Tài Lộc:</strong>")
	html = html.replace("Gia Đạo:", "<br/><br/><strong>Gia Đạo:</strong>")

	html = html + "<br/><br/>"

	html += '<img src="http://phongthuy.xemtuong.net/boi/boi_bai/img/b%s.jpg" class="img-thumbnail" alt="Responsive image">' % kq1
	html += '<img src="http://phongthuy.xemtuong.net/boi/boi_bai/img/b%s.jpg" class="img-thumbnail" alt="Responsive image">' % kq2
	html += '<img src="http://phongthuy.xemtuong.net/boi/boi_bai/img/b%s.jpg" class="img-thumbnail" alt="Responsive image">' % kq3

	html += '<br/><i>Theo xemtuong.net</i>'
	return html

def get_info_bao(st, session, data):

	url = { "vietnamnet":"http://vietnamnet.vn/rss/giai-tri.rss", "vnexpress":"https://vnexpress.net/rss/giai-tri.rss", "tinhte.vn":"https://tinhte.vn/rss", "dân trí":"http://dantri.com.vn/giai-tri.rss"}

	loai = session['bao']

	feed = feedparser.parse(url[loai])

	card = '<div class="card"><div class="card-block"><h5 class="card-title">%s.</h5><hr/><p class="card-text">%s</p><div class="btn-group" role="group"><a target="_blank" href="%s" class="btn btn-primary">Xem chi tiết</a><button type="button" class="btn btn-default btn-select">Xem tin khác</button></div></div></div>'

	item = random.choice(feed['items'])

	html = card % (item['title'], item['summary'], item['link'])

	return (html, 1)

def save_data_session(st, session, data, data_intent):
	
	for key, value in data['params'].items():
		if key in session:
			continue
		if value == 'QUIZ':
			for i, j in enumerate(data_intent['options'][key]):
				if st.lower().find(j) >= 0:
					session[key] = j
					break
			if key not in session:
				return False

		fetch = fetch_data(st, value)

		if fetch == False:
			return ("Bạn nhập thông tin không đúng", 1)
		else:
			session[key] = fetch
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
					return ("Bạn chưa nhập đúng định dạng ngày theo ngày/tháng/năm hoặc ngày nhập không hợp lệ", 1)
	return False

def get_story(st, session, data):
	r = requests.get('http://luudiachiweb.com/gettruyen.asp')
	soup = BeautifulSoup(r.text, 'html.parser')
	soup.find('p').decompose()

	return (str(soup) + "<br/><b style='font-size: 10px'>Nguồn: Truyện cười luudiachiweb.com</b>", 1)

def get_kqxs(st, session, data):

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
		content += "<div><strong>" + item['title'] + "</strong></div>"
		content += "<div>" + item['summary'].replace("[", "<br/>[").replace("8:", " 8:") + "</div>"

	return content

def get_quan_an(st, session, data):

	if session.get("page") == None:
		session["page"] = 0

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

		session["loc"] = quan

		keyword = ""

		tagger = ViPosTagger.postagging(ViTokenizer.tokenize(st))
		for i, j in enumerate(tagger[0]):
			if j.lower() not in ('quán', 'ngon', 'ăn', 'ở', 'quận', 'huyện') and tagger[1][i] not in ('M', 'V', 'Np'):
				keyword += j.replace("_", " ") + " "

		if keyword != "":
			session["keyword"] = keyword
	else:
		session["page"] += 1

	if (session.get("keyword") != None):
		result = search_ddan(tenmon=session["keyword"], quan=session["loc"], p=session["page"])
	else:
		result = search_ddan(quan=session["loc"], p=session["page"])

	if result == False:
		return "Không còn quán nào khác"
	return (result, 1)

def search_ddan(tenmon=None, thanhpho=217, quan="", gia=5000, p=""):

	if (tenmon != None):
		url = 'http://diadiemanuong.com/Search?q={0}&province={1}&district={2}&minPrice=0&maxPrice={3}&p={4}'.format(tenmon, thanhpho, quan, gia*1000, p)
	else:
		url = 'http://diadiemanuong.com/tim-kiem?sort=[Place].[Priority] DESC, [Place].[AvgRating] DESC, [Place].[CreateDate] DESC&province={0}&district={1}&minPrice=0&maxPrice={2}&p={3}'.format(thanhpho, quan, gia*1000, p)

	r = requests.get(url)
	soup = BeautifulSoup(r.text, 'html.parser')

	list_items = soup.find_all(attrs={"class": "list-item"})

	if len(list_items) == 0:
		return False

	content = "<div class='card-columns'>"

	for item in list_items:
		url = 'http://diadiemanuong.com' + item['href']
		title = item.h3.get_text()
		img = item.img['src']
		review = item.find(attrs={"class": "star"})['data-star-value']
		address = item.find(attrs={"class": "address"}).get_text()

		card = '<div class="card"><img class="card-img-top" alt="Card image" src={0}><div class="card-body"><h5 class="card-title">{1}</h5><p class="card-text">Đánh giá: {2}/5 ⭐<br/>Địa chỉ: {3}</p><a target="_blank" href="{4}" class="btn btn-primary">Xem chi tiết</a></div></div>'.format(img, title, review, address, url)
		content += card

	return content + "</div>"

