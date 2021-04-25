import os
import sys
from PySide2 import QtWidgets, QtGui
import flask
from flask import Flask, jsonify
from flask import request, redirect, url_for, render_template
from flask_cors import CORS, cross_origin
import webbrowser
import requests
import json
import threading
from os import path
import pathlib
import logging
from multiprocessing import Process
import time
import winreg
import sys
from winreg import KEY_WOW64_32KEY, OpenKey, KEY_READ, QueryValueEx, EnumKey
import psutil
import zipfile

# init logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

APPDATA = path.expandvars(r'%APPDATA%\MapBuilder')
CONFIGPATH = rf'{APPDATA}\config.json'

if not path.exists(APPDATA):
    os.makedirs(APPDATA)

ENVPATH = 'env.json'

if not os.path.isfile(ENVPATH):
    logging.info('no config file')
    sys.exit()

with open(ENVPATH) as f:
  data = json.load(f)

SPOTIFY_LINK_URL = data['SPOTIFY_LINK_URL']
SPOTIFY_TOKEN_URL = data['SPOTIFY_TOKEN_URL']
MODES = data['MODES']
EVENTS = data['EVENTS']
ENVIRONMENT = data['ENVIRONMENT']
DIFFICULTIES = data['DIFFICULTIES']
PORT = data['PORT']

UPDATE_SPOTIFY_ACTION = "Update Spotify Playlist"
LINK_SPOTIFY_ACTION = "Link Spotify"
TOOLTIP_NAME = 'Map Builder'
STOP_BUILDING_ACTION = 'Pause Building'
START_BUILDING_ACTION = 'Resume Building'

SPOTIFY_API_URL = "https://api.spotify.com"
BEATSAGE_BASEURL = "https://beatsage.com"
YOUTUBE_BASE_URL = 'https://www.youtube.com'

def get_config_data():
    if path.exists(CONFIGPATH):
        with open(CONFIGPATH) as f:
            return json.load(f)
    else:
        return None

def update_config_data(data):
    # expects data to be the existing config data plus the updated values
    with open(CONFIGPATH, 'w+') as f:
        json.dump(data, f)

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """
    CREATE A SYSTEM TRAY ICON CLASS AND ADD MENU
    """
    def __init__(self, icon, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        self.setToolTip(TOOLTIP_NAME)
        self.actions = []
        self.menu = QtWidgets.QMenu(parent)
        self.callback_thread()
        self.builder_running = False
        # self.setIcon(QtGui.QIcon("sync.png"))

        update_playlist_action = self.menu.addAction(UPDATE_SPOTIFY_ACTION)
        update_playlist_action.triggered.connect(self.playlist_page)
        self.actions.append(update_playlist_action)

        stop_building_action = self.menu.addAction(STOP_BUILDING_ACTION)
        stop_building_action.triggered.connect(self.stop_builder)
        self.actions.append(stop_building_action)
        stop_building_action.setEnabled(False)

        start_building_action = self.menu.addAction(START_BUILDING_ACTION)
        start_building_action.triggered.connect(self.start_builder)
        self.actions.append(start_building_action)
        start_building_action.setEnabled(False)

        link_spotify_action = self.menu.addAction(LINK_SPOTIFY_ACTION)
        link_spotify_action.triggered.connect(self.init_spotify)
        self.actions.append(link_spotify_action)

        exit_ = self.menu.addAction("Exit")
        exit_.triggered.connect(self.exit)
        # exit_.triggered.connect(lambda: sys.exit())

        data = get_config_data()
        if (data):
            if 'refresh_token' in data and data['refresh_token']:
                self.refresh_token = data['refresh_token']
                link_spotify_action.setEnabled(False)
            if 'playlist_id' in data and 'playlist_name' in data:
                self.playlist_id = data['playlist_id']
                self.playlist_name = data['playlist_name']
            
            if hasattr(self, 'refresh_token') and hasattr(self, 'playlist_id'):
                self.start_builder()
                self.enable_action(STOP_BUILDING_ACTION)
                # pause_building_action.setEnabled(True)

        else:
            update_playlist_action.setEnabled(False)

        self.menu.addSeparator()
        self.setContextMenu(self.menu)
        self.activated.connect(self.onTrayIconActivated)
    
    def spotify_auth_token(self, refresh_token):
        try:
            headers = {}
            headers['Authorization'] = refresh_token
            response = requests.request("GET", SPOTIFY_TOKEN_URL, headers=headers)
            response.raise_for_status()
            body = json.loads(response.text)
            access_token = body['access_token']
            # TODO use expires_in
            # expires_in = body['expires_in']
            return f'Bearer {access_token}'
        except Exception as e:
            print(e)
            self.refresh_token = None
            self.stop_builder()
            self.enable_action(LINK_SPOTIFY_ACTION)
            self.disable_action(UPDATE_SPOTIFY_ACTION)
            update_config_data({})

    def spotify_playlists(self, token):
        url = f'{SPOTIFY_API_URL}/v1/me/playlists'
        headers = {
            'Authorization': token
        }
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status()
        playlists = json.loads(response.text)['items']
        playlist_ids = []
        for playlist in playlists:
            playlist_ids.append((playlist['id'],playlist['name']))
        return playlist_ids

    def onTrayIconActivated(self, reason):
        """
        This function will trigger function on click or double click
        :param reason:
        :return:
        """
        if reason == self.DoubleClick:
            self.open_notepad()
        # if reason == self.Trigger:
        #     self.open_notepad()

    def init_spotify(self):
        response = requests.request("POST", SPOTIFY_LINK_URL)
        linkUrl = json.loads(response.text)

        webbrowser.open(linkUrl)
        # @app.route('/callback', methods=['GET'])
        # def spotify_callback():
            # self.spotifyToken = ""
            # return ""

    def playlist_page(self):
        webbrowser.open(f'http://localhost:{PORT}/playlist')

    def callback_thread(self):
        def callback(self):
            app = Flask(__name__)
            # cors = CORS(app)
            app.config['CORS_HEADERS'] = 'Content-Type'

            def shutdown_server():
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    raise RuntimeError('Not running with the Werkzeug Server')
                func()

            @app.route('/shutdown', methods=['POST'])
            def shutdown():
                shutdown_server()
                return 'Server shutting down...'

            @app.route('/callback', methods=['GET'])
            def spotify_callback():
                refresh_token = request.args.get('refresh_token')

                config_json = {
                    "refresh_token": refresh_token
                }

                with open(CONFIGPATH, 'w+') as f:
                    json.dump(config_json, f)
                
                self.refresh_token = refresh_token

                self.disable_action(LINK_SPOTIFY_ACTION)
                self.enable_action(UPDATE_SPOTIFY_ACTION)

                self.get_playlists()

                return redirect(url_for('playlist'))

            @app.route('/playlist')
            def playlist():
                return render_template("index.html")

            @app.route('/success')
            def success():
                # TODO kill thread
                if hasattr(self, 'refresh_token'):
                    self.start_builder()
                return 'Map builder setup successfully'
            
            @app.route('/playlists', methods=['GET', 'POST'])
            def playlists():
                if flask.request.method == 'GET':
                    playlistsArray = []
                    for playlist_id, playlist_name in self.get_playlists():
                        playlistObj = {}
                        playlistObj['playlist_id'] = playlist_id
                        playlistObj['playlist_name'] = playlist_name
                        playlistsArray.append(playlistObj)

                    return jsonify(playlistsArray)
                else:
                    playlist_id = request.args.get('playlist_id')
                    playlist_name = request.args.get('playlist_name')
                    self.update_playlist(playlist_id, playlist_name)
                    return redirect(url_for('success')) 

            app.run(host='localhost', port=PORT)

        callbackThread = threading.Thread(kwargs={'self':self}, target = callback)
        callbackThread.start()
        # self.callback = callbackThread
    
    def update_playlist(self, playlist_id, playlist_name):
        self.playlist_id = playlist_id
        self.playlist_name = playlist_name
        data = get_config_data()
        data['playlist_id'] = playlist_id
        data['playlist_name'] = playlist_name
        update_config_data(data)

    def get_playlists(self):
        if hasattr(self, 'playlists'):
            playlists = self.spotify_playlists(self.spotify_auth_token(self.refresh_token))
            return playlists
        if hasattr(self, 'refresh_token'):
            playlists = self.spotify_playlists(self.spotify_auth_token(self.refresh_token))
            self.playlists = playlists
            return playlists

    def disable_action(self, action):
        action = list(filter (lambda x: x.text() == action, self.actions))
        if len(action) > 0:
            action[0].setEnabled(False)

    def enable_action(self, action):
        action = list(filter (lambda x: x.text() == action, self.actions))
        if len(action) > 0:
            action[0].setEnabled(True)
    
    def start_builder(self):
        if self.builder_running == False and hasattr(self, 'refresh_token'):
            self.builder_running = True
            self.map_builder_thread()
            self.disable_action(START_BUILDING_ACTION)
            self.enable_action(STOP_BUILDING_ACTION)

    def stop_builder(self):
        if self.builder_running == True:
            self.builder_running = False
            # not running means we should allow users to try
        if hasattr(self, 'refresh_token'):
            self.enable_action(START_BUILDING_ACTION)
        else:
            self.disable_action(START_BUILDING_ACTION)
        self.disable_action(STOP_BUILDING_ACTION)

    def map_builder_thread(self):
        def map_builder(self):
            while self.builder_running:
                token = self.spotify_auth_token(self.refresh_token)

                headers = {'Authorization': token}
                url = SPOTIFY_API_URL + "/v1/playlists/"+self.playlist_id+"/tracks"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                tracks = json.loads(response.text)['items']

                if(len(tracks) > 0):
                    # get first trackId in playlist
                    trackId = tracks[0]['track']['id']
                    uri = tracks[0]['track']['uri']
                    logging.info(uri)
                    # TODO add option to save track to a backup playlist
                    self.build_map(trackId)

                    body = ({
                        "tracks": [
                            {
                                "uri": uri
                            }
                        ]
                    })

                    url = f'{SPOTIFY_API_URL}/v1/playlists/{self.playlist_id}/tracks'
                    response = requests.delete(url, headers=headers, json=body)
                    response.raise_for_status()
                    
                    # if(SAVEPLAYLISTID):
                        # url = f"{SPOTIFY_API_URL}/v1/playlists/{SAVEPLAYLISTID}/tracks?uris=spotify:track:{trackId}"
                        # response = requests.post(url, headers=headers)
                    time.sleep(5)
                else:
                    for x in range(5):
                        time.sleep(1)
                        if not self.builder_running:
                            break

        builderThread = threading.Thread(kwargs={'self':self}, target = map_builder)
        builderThread.start()
        # self.builder = builderThread

    def build_map(self, trackId):
        def thread():
            try:
                print('starting: build_map')
                token = self.spotify_auth_token(self.refresh_token)

                headers = {'Authorization': token}
                url = f'{SPOTIFY_API_URL}/v1/tracks/{trackId}'
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                track = json.loads(response.text)

                artistName = ''
                artists = track['artists']
                for artist in artists:
                    artistName = artistName + ', ' + artist['name']

                artistName = artistName.replace(', ', '', 1)

                trackName = track['name']
                image_url = track['album']['images'][1]['url']
                print ("trackName: " + trackName)
                print ("image_url: " + image_url)

                # TODO ability to exclude tracks based on trackName being in blacklist

                url = f'{YOUTUBE_BASE_URL}/results?search_query={trackName} {artistName}'

                headers_yt = {}

                response = requests.request("GET", url, headers=headers_yt)
                response.raise_for_status()
                responseBody = response.text

                find = 'watch?v='
                start_index = responseBody.index(find)
                youtube_id = responseBody[start_index:start_index+19]

                youtube_url = f'{YOUTUBE_BASE_URL}/{youtube_id}'
                logging.info("youtube_url: " + youtube_url)

                url = BEATSAGE_BASEURL+"/beatsaber_custom_level_create"

                payload = {
                    'youtube_url': youtube_url,
                    'cover_art': '',
                    'audio_metadata_title': trackName,
                    'audio_metadata_artist': artistName,
                    'difficulties': DIFFICULTIES,
                    'modes': MODES,
                    'events': EVENTS,
                    'environment': ENVIRONMENT,
                    'system_tag': 'v2'
                }
                files = [

                ]
                headers_beatsage = {
                    'authority': 'beatsage.com',
                    'dnt': '1',
                    'accept': '*/*',
                    'origin': BEATSAGE_BASEURL,
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-dest': 'empty',
                    'referer': BEATSAGE_BASEURL,
                    'accept-language': 'en-US,en;q=0.9'
                }

                response = requests.request("POST", url, headers=headers_beatsage, data = payload, files = files)
                response.raise_for_status()
                map_id = json.loads(response.text)['id']

                url = BEATSAGE_BASEURL+"/beatsaber_custom_level_heartbeat/"+map_id

                status = "PENDING"
                while( status != "DONE"):
                    time.sleep(1)
                    response = requests.request("GET", url, headers=headers_beatsage)
                    status = json.loads(response.text)['status']

                url = BEATSAGE_BASEURL+"/beatsaber_custom_level_download/"+map_id

                chunk_size=128
                map_name = "map"+"_"+map_id+"_"+trackId
                save_path = APPDATA + "\\" + map_name
                save_path_full = save_path+".zip"
                response = requests.request("GET", url, headers=headers_beatsage)
                response.raise_for_status()
                with open(save_path_full, 'wb') as fd:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        fd.write(chunk)

                logging.info("zip saved")

                ###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~####
                #zip file is downloaded
                #extract to maps folder in local steam directory
                ###~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~####

                aKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Valve", access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                val = ''

                for i in range(1024):
                    try:
                        asubkey_name=EnumKey(aKey,i)
                        asubkey=OpenKey(aKey,asubkey_name)
                        val=QueryValueEx(asubkey, "InstallPath")
                        break
                    except EnvironmentError:
                        break

                directory_to_extract_to=val[0]+"\\steamapps\\common\\Beat Saber\\Beat Saber_Data\\CustomLevels\\"+map_name
                logging.info("steam folder: " + directory_to_extract_to)
                image_path=directory_to_extract_to+"\\cover.jpg"

                with zipfile.ZipFile(save_path_full, 'r') as zip_ref:
                    zip_ref.extractall(directory_to_extract_to)

                logging.info("zip extracted")

                response = requests.request("GET", image_url, headers=headers_beatsage)
                response.raise_for_status()
                with open(image_path, 'wb') as fd:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        fd.write(chunk)

                logging.info("cover image updated")
                # cleanup zip file
                os.remove(save_path_full)

                info_path = f'{directory_to_extract_to}\Info.dat'
                print(info_path)
                
                with open(info_path) as f:
                    info = json.load(f)
                
                info['_songSubName'] = ''
                info['_levelAuthorName'] = trackId

                if '_editors' in info['_customData'] and 'beatsage' in info['_customData']['_editors']:
                    info['_customData']['_editors']['_lastEditedBy'] = 'beatmix'
                    info['_customData']['_editors']['beatmix'] = info['_customData']['_editors']['beatsage']
                    del info['_customData']['_editors']['beatsage']

                with open(info_path, 'w') as f:
                    f.write(json.dumps(info))
                logging.info("info updated")

            except Exception as e:
                logging.info(e)
                # TODO add a way for the user to see that a song has failed to create
                if(trackName):
                    print ("error processing track: " + trackName)

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()  
    
    def exit(self):
        self.stop_builder()
        requests.request("POST", f'http://localhost:{PORT}/shutdown')
        sys.exit()

def main():
    for proc in psutil.process_iter():
        if proc.name() is sys.argv[0]:
            sys.exit()
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    tray_icon = SystemTrayIcon(QtGui.QIcon("static/images/beatsaber.png"), w)
    tray_icon.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()