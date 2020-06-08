#requirements
import csv
import numpy
import nltk
from nltk.corpus import stopwords
from nltk.collocations import *
from web_monitoring import internetarchive
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import caffeine
import re
import fnmatch

default_stopwords = set(nltk.corpus.stopwords.words('english'))
all_stopwords = default_stopwords


#ancillary count functions
def count(term, visible_text): # this function counts single word terms from the decoded HTML
    term = term.lower()  # normalize so as to make result case insensitive
    tally = 0
    for section in visible_text:
    	##bigram here. instead of section.split, bigram the section
        for token in section.split():
            token = re.sub(r'[^\w\s]','',token)#remove punctuation
            tally += int(term == token.lower()) # instead of in do ==
    #print(term, tally)
    return tally

def two_count (term, visible_text): #this function counts phrases from the decoded HTML
	tally = 0
	length = len(term)
	for section in visible_text:
		tokens = nltk.word_tokenize(section)
		tokens = [x.lower() for x in tokens] #standardize to lowercase
		tokens = [re.sub(r'[^\w\s]','',x) for x in tokens]
		grams=nltk.ngrams(tokens,length)
		fdist = nltk.FreqDist(grams)
		tally += fdist[term[0].lower(), term[1].lower()] #change for specific terms
	#print(term, tally)    
	return tally
            
def counter(file, terms, dates):
    #counts a set of one or two word terms during a single timeframe
    #dates should be in the following form: [starting year, starting month, starting day, ending year, ending month, ending day]
    #terms should be in the format ["term"], as a phrase: ["climate", "change"], or as a set of terms and/or phrases: ["climate", ["climate", "change"]]
    
    with open(file) as csvfile: 
        read = csv.reader(csvfile)
        data = list(read)
    csvfile.close()

    #terms=['adaptation', ['Agency', 'Mission'], ['air', 'quality'], 'anthropogenic', 'benefits', 'Brownfield', ['clean', 'energy'], 'Climate', ['climate', 'change'], 'Compliance', 'Cost-effective', 'Costs', 'Deregulatory', 'deregulation', 'droughts', ['economic', 'certainty'], ['economic', 'impacts'], 'economic', 'Efficiency', 'Emissions', ['endangered', 'species'], ['energy', 'independence'], 'Enforcement', ['environmental', 'justice'], ['federal', 'customer'], ['fossil', 'fuels'], 'Fracking', ['global', 'warming'], 'glyphosate', ['greenhouse', 'gases'], ['horizontal', 'drilling'], ['hydraulic', 'fracturing'], 'Impacts', 'Innovation', 'Jobs', 'Mercury', 'Methane', 'pesticides', 'pollution', 'Precautionary', ['regulatory', 'certainty'], 'regulation', 'Resilience', 'Risk', 'Safe', 'Safety', ['sensible', 'regulations'], 'state', 'storms', 'sustainability', 'Toxic', 'transparency', ['Unconventional', 'gas'], ['unconventional', 'oil'], ['Water', 'quality'], 'wildfires']
    #counter("EDGI/inputs/all Versionista URLs 10-16-18.csv", terms, [2016, 1,1,2016,7,1]) #[2018,1,1,2018,7,1]
    
    final_urls={}
    
    row_count = len(data)
    column_count = len(terms) 
    matrix = numpy.full((row_count,column_count), 999, dtype=numpy.int16) #default is 999 until counted otherwise
    print(row_count, column_count) 
    
    for pos, row in enumerate(data[10:100]):
          thisPage = row[0] #change for specific CSVs
          final_urls[thisPage]=""
          try:
              with internetarchive.WaybackClient() as client: #https://energy.gov/eere/geothermal/articles/third-round-sbv-pilot-open-requests
                   dump = client.list_versions(thisPage, from_date=datetime(dates[0], dates[1],dates[2]), to_date=datetime(dates[3], dates[4], dates[5])) # list_versions calls the CDX API from internetarchive.py from the webmonitoring repo
                   versions = reversed(list(dump))
                   for version in versions: # For each version in all the snapshots
                       if version.status_code == '200' or version.status_code == '-': # If the IA snapshot was viable...
                          url=version.raw_url
                          contents = requests.get(url, timeout=120).content.decode() # Decode the url's HTML # Handle the request so that it doesn't hang
                          contents = BeautifulSoup(contents, 'lxml')
                          body=contents.find('body')
                          d=[s.extract() for s in body('footer')]
                          d=[s.extract() for s in body('header')]
                          d=[s.extract() for s in body('nav')]
                          d=[s.extract() for s in body('script')]
                          d=[s.extract() for s in body('style')]
                          d=[s.extract() for s in body.select('div > #menuh')] #FWS
                          d=[s.extract() for s in body.select('div > #siteFooter')] #FWS
                          d=[s.extract() for s in body.select('div.primary-nav')] #DOE
                          d=[s.extract() for s in body.select('div > #nav-homepage-header')] #OSHA
                          d=[s.extract() for s in body.select('div > #footer-two')] #OSHA
                          del d
                          body=[text for text in body.stripped_strings]
                          for p, t in enumerate(terms):
                              if type(t) is list:
                                  page_sum = two_count(t, body)
                              else:
                                  page_sum = count(t, body)
                              matrix[pos][p]=page_sum #put the count of the term in the matrix
                          final_urls[thisPage]=url
                          print(pos)
                          break
                       else:
                          pass
          except:
              print("No snapshot or can't decode", thisPage)
              final_urls[thisPage]=""
              matrix[pos]=999
         
    unique, counts = numpy.unique(matrix, return_counts=True)
    results = dict(zip(unique, counts))
    print (results)
    
    #for writing term count to a csv. you will need to convert delimited text to columns and replace the first column with the list of URLs

    with open('counts.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in matrix:
            writer.writerow(row)
    csvfile.close()

    #print out urls in separate file
    with open('urls.csv','w') as output:
        writer=csv.writer(output)
        for item in final_urls.items():
            writer.writerow([item[0], item[1]])
    output.close()

    print("The program is finished!")
    
# =============================================================================
    # correct processing errors
#  file="EDGI/outputs/dump/count_processedTZ.csv"
#  
#  with open(file)as csvfile:
#      read=csv.reader(csvfile)
#      newcounts=list(read)
#  
#  file="EDGI/outputs/main/term count trump1-7/trump_count_WMcorrected.csv"
#  
#  with open(file)as csvfile:
#      read=csv.reader(csvfile)
#      t=list(read)
# 
# 
# for r in t:
#     url=r[0]
#     if len(r[2])==0:
#         for row in newcounts:
#             if row[0]==url:
#                 r[2:59]=row[1:58]
#           
#  for rr in t:
#      if len(rr[2])==0:
#          rr[2] = "NA"    
# 
# 
#  with open('EDGI/outputs/dump/count_outputFINALTZ.csv', 'w', newline='') as csvfile:
#      writer = csv.writer(csvfile, delimiter=' ')
#      for x in t:
#          writer.writerow(x)
# =============================================================================

### MATRIX
#Prepares output for Gephi network visualization 

with open(file) as csvfile: 
    read = csv.reader(csvfile)
    data =  {rows[0]:[rows[1],rows[2]] for rows in read}
csvfile.close()

l=list(data.keys()) #master list of urls (from Wayback Machine scraping)

#2016 - End of Term
#none = 0 
connection = 1
decoding_error = 8

#S19 #Comment these out to run 2016
#none = 0 
connection = 3
decoding_error = 14

# 0 - no connections either timeframe
# 1 - connection in obama, removed in Trump
# 3 - connection in trump, not in obama
# 4 - connections in both
# 8 - error in obama, no connection trump
# 11 - error in obama, connection in trump
# 14 - no connection obama, error trump
# 15 - connection obama, error trump
# 22 = error boths	

matrix_a = numpy.zeros((len(l), len(l)),dtype=numpy.int8) #indicate matrix_a or matrix_b in order to compare


for pos,url in enumerate(l[30:50]):
    wmurl=data[url][0] #2016-EOT = [0], [1] = summer19
    try:
        contents = requests.get(wmurl).content.decode() #decode the url's HTML
        contents = BeautifulSoup(contents, 'lxml')
        d=[s.extract() for s in contents('script')]
        d=[s.extract() for s in contents('style')]
        del d
        contents=contents.find("body")
        links = contents.find_all('a') #find all outgoing links
        for link in links:
            try:
                index = l.index(link['href'])
                matrix[pos][index] = connection
            except ValueError: #link not in our list l
                index = -1
            except KeyError: #no href in the link
                pass
        print(pos)   
    except:
        print("decoding error")
        matrix[pos] = decoding_error # code for indicating decoding error

diffmatrix = matrix_a + matrix_b
	    
	    
#construct the network graph (for gephi)
#form: 
# urlA urlA self
# urlA urlB both
	# urlA urlC removed
	# urlB urlA both
	# urlB urlB self
	# urlB urlC both
	# in this example, uralA does not link to C in 2019

fullresults=[]

results_lost = numpy.where(diffmatrix == 1)
results_added = numpy.where(diffmatrix == 3)
results_both = numpy.where(diffmatrix == 4)  

listOfCoordinates= list(zip(results_added[0], results_added[1])) #do this separately for results_lost, added, AND both
for coord in listOfCoordinates:
    cs = list(coord)
    fr = l[cs[0]]
    to = l[cs[1]]
    typ = "add" 
    fullresults.append([fr, to, typ])
    
	#find the pages not represented i.e. with columns 8/0 and rows 8/0 ????
	# just add all pages to end of full results?
	#for url in l_full:
	    #fullresults.append([url,"",""])

#Save as CSV. You will need to convert delimited text to columns 

with open('links.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    for row in fullresults:
        writer.writerow(row)
csvfile.close()
