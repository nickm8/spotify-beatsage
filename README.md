Build exe:
pyinstaller --onefile --icon=mapbuilder.ico --windowed mapbuilder.py

# How to run locally:
1. create a copy of env.json.example names env.json
2. Add a url that can handle spotify login flow and refreshing a token: https://developer.spotify.com/documentation/general/guides/authorization-guide/
3. run mapbuilder.py

# How to build locally
1. Get the app running locally
2. pyinstaller --onefile --icon=mapbuilder.ico --windowed mapbuilder.py
3. copy templates folder and env.json into dist folder and run .exe

# Edit beatsage build config
DIFFICULTIES: Hard,Expert,ExpertPlus,Normal