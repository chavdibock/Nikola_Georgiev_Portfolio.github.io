import urllib

import urllib.parse
import urllib.request
import json
import os
# Tries to open the url with the params through the method specified

key = os.getenv("API_KEY")
function = "search"
ontology = "ticker"
terms = "sscore,smean,sdispersion"
dates = "datetime+eq+recent"
sort = "sscore+desc,smean+desc,sdispersion+desc"
method = "POST"
parms = {"api_key": key, "function": function}
urlParameters = "api_key=" + key + "&function=search"
url = "https://api.socialmarketanalytics.com/api/search?subject=TSLA&ontology=" + ontology + "&items=" + terms + "&dates=" + dates + "&sort" + sort + "?api_key"
values = {'api_key': key,
          'function': function}

data = urllib.parse.urlencode(values)
data = data.encode('utf-8')  # data should be bytes
req = urllib.request.Request(url, data)
response = urllib.request.urlopen(req)
content = response.read()
json_data = json.loads(content.decode("utf-8"))
print(json_data)
