# Dependencies
from flask import Flask, render_template, url_for, request, redirect
from datetime import datetime, timedelta
import requests, hashlib, time, os
import xml.etree.ElementTree as ET

#Datetime-Unix Converters:
current_datetime = datetime.now()
def datetime_to_unix(dt):
	unixtime = time.mktime(dt.timetuple())
	return int(unixtime)
def unix_to_datetime(unix):
	return datetime.fromtimestamp(unix)

# Flask Init
app = Flask(__name__)

#Lastfm API Globals
apiUrl = "http://ws.audioscrobbler.com/2.0/"
apiKey = os.environ.get('apikey')
sharedSecret = os.environ.get('sharedsecret')
period = 'overall'
limit = 30

#Request, Decode & Parse
def rdp(user, passMethod):
    method = f'user.{passMethod}'
    query = f'{apiUrl}?method={method}&user={user}&period={period}&limit={limit}&api_key={apiKey}'
    r = requests.get(query)
    decoded = r.content.decode("utf-8")
    root = ET.fromstring(decoded)
    return root

#User class
class _User:
	instances = []
	def __init__(self,username,playcount,registeredUnix):
		__class__.instances.clear()
		self.__class__.instances.append(self)
		self.username = username
		self.playcount = int(playcount)
		self.registeredUnix = registeredUnix
		self.registeredDT = unix_to_datetime(int(registeredUnix)).date()
		self.DTdelta = (current_datetime.date() - self.registeredDT).days

#Scrobble Class - Super of Artist, Album & Track Class
class Scrobble:
    def __init__(self,artistName,playCount):
        self.artistName = artistName
        self.playCount = playCount
    def get_artistNames(self):
        return self.artistName
    def get_playCounts(self):
        return self.playCount

#Artist Class
class _Artist(Scrobble):
    instances = []
    def __init__(self,artistName,playCount,img):
        self.__class__.instances.append(self)
        self.artistName = artistName
        self.playCount = playCount
        self.img = img

#Album Class
class _Album(Scrobble):
    instances = []
    def __init__(self,artistName,playCount,albumName,img):
        self.__class__.instances.append(self)
        super().__init__(artistName, playCount)
        self.albumName = albumName
        self.img = img
    def get_albumNames(self):
        return self.albumName

#Track Class
class _Track(Scrobble):
    instances = []
    def __init__(self,artistName,playCount,trackName):
        self.__class__.instances.append(self)
        super().__init__(artistName, playCount)
        self.trackName = trackName
    def get_trackNames(self):
        return self.trackName

#Create Objs
def createUser(root):
    _User(root[0][0].text,root[0][11].text,root[0][14].text)

def createArts(root):
    numTop = 10
    for i in range(numTop):
        _Artist(root[0][i][0].text, root[0][i][1].text, root[0][i][6].text)

def createAlbs(root):
    numTop = 10
    for i in range(numTop):
        _Album(root[0][i][4][0].text, root[0][i][1].text, root[0][i][0].text, root[0][i][6].text)

def createTrax(root):
    numTop = 10
    for i in range(numTop):
        _Track(root[0][i][6][0].text, root[0][i][2].text, root[0][i][0].text)

# Index:
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        username = request.form['content']
        try:
            clear()
            createUser(rdp(username, 'getinfo'))
            createAlbs(rdp(username,'gettopalbums'))
            createArts(rdp(username, 'gettopartists'))
            createTrax(rdp(username, 'gettoptracks'))
            art_bar_labels= list(map(_Artist.get_artistNames,_Artist.instances))
            art_bar_values= list(map(_Artist.get_playCounts,_Artist.instances))
            alb_bar_labels= list(map(_Album.get_albumNames,_Album.instances))
            alb_bar_values= list(map(_Album.get_playCounts,_Album.instances))
            alb_bar_bys= list(map(_Album.get_artistNames,_Album.instances))
            trax_bar_labels= list(map(_Track.get_trackNames,_Track.instances))
            trax_bar_values= list(map(_Track.get_playCounts,_Track.instances))
            trax_bar_bys= list(map(_Track.get_artistNames,_Track.instances))
            return render_template('index.html', albObjs=_Album.instances, artObjs=_Artist.instances, traxObjs=_Track.instances, USER=_User.instances,
            ARTtitle='Top Artists', ARTmax=_Artist.instances[0].playCount, ARTlabels=art_bar_labels, ARTvalues=art_bar_values,
            ALBtitle='Top Albums', ALBmax=_Album.instances[0].playCount, ALBlabels=alb_bar_labels, ALBvalues=alb_bar_values, ALBbys=alb_bar_bys,
            TRXtitle='Top Tracks', TRXmax=_Track.instances[0].playCount, TRXlabels=trax_bar_labels, TRXvalues=trax_bar_values, TRAXbys=trax_bar_bys)
        except ConnectionError:
            return "No Internet Connection Detected, Please check your internet connection and try again..."
        except (KeyError, TypeError) as e:
            return str(e)
        except (ValueError, NameError) as e:
            return str(e)
        except Exception as e:
            return str(e)
    else:
        return render_template('index.html')

# Clear Objects:
@app.route('/clear')
def clear():
    for album in _Album.instances:
        del album
    _Album.instances.clear()
    for artist in _Artist.instances:
        del artist
    _Artist.instances.clear()
    for track in _Track.instances:
        del track
    _Track.instances.clear()
    return redirect('/')

# Import All Scrobbles
def get_root(query):
	r = requests.get(query)
	decoded = r.content.decode("utf-8")
	return ET.fromstring(decoded)

listOfUts =[]
# queue = Queue()

def return_uts(unixEnd):
	user = _User.instances[0].username
	method = 'user.getrecenttracks'
	limit = 1000
	totalScrobbles = _User.instances[0].playcount
	try:
		if unixEnd == None:
			query = f'{apiUrl}?method={method}&user={user}&limit={limit}&api_key={apiKey}'
		else:
			query = f'{apiUrl}?method={method}&user={user}&to={unixEnd}&limit={limit}&api_key={apiKey}'
		root = get_root(query)
		try:
			assert root[0][0].attrib['nowplaying'] != 'true'
			for i in range(limit):
				listOfUts.append(root[0][i][10].attrib['uts'])
		except (AssertionError, KeyError):
			for i in range(limit):
				try:
					listOfUts.append(root[0][i+1][10].attrib['uts'])
				except IndexError:
					pass
		lastVal = listOfUts[-1] #the earliest timestamp from this batch of 1000
		#queue.put("{:.2%}".format(len(listOfUts)/totalScrobbles))
		# THREAD: return lastVal, len(listOfUts), "{:.2%}".format(len(listOfUts)/totalScrobbles)
		if len(listOfUts) < totalScrobbles:
			return_uts(lastVal)
	except IndexError:
		lastRemaining = totalScrobbles - len(listOfUts)
		query = f'{apiUrl}?method={method}&user={user}&to={unixEnd}&limit={lastRemaining}&api_key={apiKey}'
		root = get_root(query)
		for i in range(lastRemaining):
			listOfUts.append(root[0][i][10].attrib['uts'])
		lastVal = listOfUts[-1] #the earliest timestamp of all time (in theory)
		# THREAD END: return lastVal, len(listOfUts), "{:.2%}".format(len(listOfUts)/totalScrobbles)
	except ConnectionError:
		return "No Internet, Please Check Your Connection And Try Again"

# Import All Scrobbles:
# @app.route('/imports')
# def imports():
# 	thread1 = threading.Thread(target=return_uts,args=(None))
# 	thread1.start()
# 	work = queue.get()
# 	return work
# 	# return_uts(None)
# 	return render_template('toppanel.html', paneltype=3, listOfUts=listOfUts)

# Top Panels:
@app.route('/toppanel/<int:type>') # 0-art, 1-alb, 2-trx
def top_panel(type):
	if type == 0:
		art_bar_labels= list(map(_Artist.get_artistNames,_Artist.instances))
		art_bar_values= list(map(_Artist.get_playCounts,_Artist.instances))
		return render_template('toppanel.html', paneltype=type, artObjs=_Artist.instances, ARTmax=_Artist.instances[0].playCount, ARTlabels=art_bar_labels, ARTvalues=art_bar_values)
	elif type == 1:
		alb_bar_labels= list(map(_Album.get_albumNames,_Album.instances))
		alb_bar_values= list(map(_Album.get_playCounts,_Album.instances))
		alb_bar_bys= list(map(_Album.get_artistNames,_Album.instances))
		return render_template('toppanel.html', paneltype=type, albObjs=_Album.instances, ALBmax=_Album.instances[0].playCount, ALBlabels=alb_bar_labels, ALBvalues=alb_bar_values, ALBbys=alb_bar_bys)
	elif type == 2:
		trax_bar_labels= list(map(_Track.get_trackNames,_Track.instances))
		trax_bar_values= list(map(_Track.get_playCounts,_Track.instances))
		trax_bar_bys= list(map(_Track.get_artistNames,_Track.instances))
		return render_template('toppanel.html', paneltype=type, traxObjs=_Track.instances, TRXmax=_Track.instances[0].playCount, TRXlabels=trax_bar_labels, TRXvalues=trax_bar_values, TRAXbys=trax_bar_bys)

#Flask RUN:
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=7000, debug=True, threaded=True)
