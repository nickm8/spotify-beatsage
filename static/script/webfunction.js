console.log("script loaded");

// **** Add to playlist ****

var api_URL = "http://localhost:4200"

var payload;
function addSong(playlist_id,playlist_name){
    //console.log(uri);
    //console.log(destination);
    if(playlist_id){
        // NYE playlist specified
        payload = "?playlist_id="+playlist_id+"&playlist_name="+playlist_name
        // sending payload to playlist NYE
        $.ajax({
            url: api_URL+'/playlists'+payload
            , type: 'POST'
            , success: function(mixreply) {clearSong(); console.log(mixreply);}
            , error: function(mixerror) {console.log('error'); console.log(mixerror);}
        });
    }
    else{
        // failed add
        console.log("no destination or uri specified")
    }
}

// **** Hides the song title after it is added to a playlist ****
function clearSong(){
    document.getElementById('song-prefix').innerHTML = "Playlist Confirmed";
    document.getElementById('selected-song').innerHTML = "Playlist can be updated at any time";
    document.getElementById('selected-song').value = null;
}

// **** function to search for a song and then return a list of them into buttons ****
var arrSongList;
function search(searchValue){
    var resultList; // returned search
    var songCounter = 0; // counter so that it limits to 10 results
    var searchURL = api_URL+'/playlists'; // search url for ajax
    var songTitle; // concat of song name and artist name
    var uriURL; // url for URI adding
    if(searchValue.indexOf("spotify:track:") === -1){
        // if statement to catch non-URI based adds to playlist
        $.ajax({
            url: searchURL
            , type: 'GET'
            , success: function(mixreply) {
                if($.isEmptyObject(mixreply)){
                    // this is a search that returned no results
                    document.getElementById("search-results").innerHTML = "<div style='padding:9px 0px 2px 0;'>No Results Found</div>"
                    activeSearch(true);
                }else{
                    // this is a search that does return results
                    arrSongList = mixreply;
                    _.each(arrSongList, function(objSong){
                        if(songCounter <= 99){
                            // creating song title
                            //songTitle = objSong.name+' - '+objSong.artists;
                            if(songCounter === 0){
                                // if no buttons, set as first in list
                                resultList = '<button onclick="selectSong('+'&quot;'+objSong.playlist_id+'&quot;,&quot;'+objSong.playlist_name+'&quot;);">'+objSong.playlist_name+'</button>'
                            }else{
                                // if buttons, then combines to existing ones
                                resultList += '<button onclick="selectSong('+'&quot;'+objSong.playlist_id+'&quot;,&quot;'+objSong.playlist_name+'&quot;);">'+objSong.playlist_name+'</button>'
                            }
                            songCounter++;
                        }
                    });
                    // populating search dropdown with results
                    document.getElementById("search-results").innerHTML = resultList;
                    activeSearch(true);
                }

            }
            , error: function(mixerror) {console.log('Searching returned an error'); console.log(mixerror);}
        });
    }else{
        // triggering URI search and add
        uriURL = 'trackDetails?uri='+searchValue;
        $.ajax({
            url: uriURL
            , type: 'GET'
            , success: function(x) {
                songTitle = x.name+' - '+x.artists;
                selectSong(searchValue, songTitle)
            }
            , error: function(mixerror) {console.log('error'); console.log(mixerror);}
        });

    }
}

// **** search input functionality ****

// this will unfocus and hide keyboard after pressing enter
document.getElementById('search-form').addEventListener('keyup',function(e){
    if (e.which === 13) this.blur();
});

// this will unfocus and hide keybioard and clicking search button
document.getElementById('search-value').addEventListener('keyup',function(e){
    if (e.which === 13) this.blur();
});

// this makes pressing enter click the search button
document.getElementById("search-value").addEventListener("keyup", function(event) {
    event.preventDefault();
    if (event.keyCode === 13) {
        document.getElementById("search-button").click();
    }
});


// **** this hides and shows the search dropdown based on given boolean parameter ****
function activeSearch(blnActive){
    if(blnActive === true){
        document.getElementById("search-results").style.display = "block";
    }else{
        document.getElementById("search-results").style.display = "none";
    }
}

// **** select a song from the list and adds it to the currently selected section to be added to playlist ****
function selectSong(playlist_id, playlist_name){
    document.getElementById('song-prefix').innerHTML = "Currently Selected Playlist:";
    document.getElementById('selected-song').innerHTML = "<b>"+playlist_name+"</b>";
    document.getElementById('selected-song').value = playlist_id;
    document.getElementById('selected-song').name = playlist_name;
    activeSearch(false);
    highlightSong(true);
    //console.log("preparing to add: "+uri)
}


// **** after selecting the song, this will highlight it for 600ms to indicate it has been queued to add. ****
function highlightSong(blnHighlight){
    if(blnHighlight === true){
        document.getElementById('search-entry').style.backgroundColor = "#FF3F18";
        setTimeout(function(){
            highlightSong(false);
        }, 600);
    }else if(blnHighlight === false){
        document.getElementById('search-entry').style.backgroundColor = "#000";
    }
}
