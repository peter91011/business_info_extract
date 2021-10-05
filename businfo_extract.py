from bs4 import BeautifulSoup
import re
from nltk.tokenize import sent_tokenize
import pandas as pd 
from collections import Counter
from nltk.util import ngrams 
from difflib import SequenceMatcher
import tldextract
import pyap
import usaddress
import wordninja
import requests
from collections import defaultdict 
from html import unescape
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize  
import random
import time
import phonenumbers
from collections import OrderedDict    
import logging
from tqdm import tqdm
import random
from urllib.parse import urlparse
import xlsxwriter
import sys
from datetime import datetime
import glob
import os
import warnings
warnings.filterwarnings('ignore')



USER_AGENTS = [
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
    'Opera/9.25 (Windows NT 5.1; U; en)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.142 Safari/535.19',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:8.0.1) Gecko/20100101 Firefox/8.0.1',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.151 Safari/535.19',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)'
]


SAVE_EVERY = 500

TODAY = datetime.now()
REPORT_NAME = TODAY.strftime("%d%b%Y").lower()

if len(sys.argv) > 1:
    FILE_NAME = sys.argv[1]
    REPORT_NAME = FILE_NAME.replace('.xlsx','')+'_'+REPORT_NAME
else:
    FILE_NAME = 'sample.xlsx'
    REPORT_NAME = FILE_NAME.replace('.xlsx','')+'_'+REPORT_NAME

    
logging.basicConfig(filename=f'business_info_extraction_{REPORT_NAME}.log', 
                    format='%(levelname)s:%(message)s', level=logging.INFO)
logging.info(
    f'**** starting processing file {FILE_NAME}')
logging.info(
    f'**** output will be named as {REPORT_NAME}.xlsx in the output folder')



def containsNumber(value):
    
    for character in value:
        if character.isdigit():
            return True
    return False

def get_domain(url):
    
    domain = re.sub('^(www\.)?', '', urlparse(
      url).netloc).lower()
    return domain

def crawl(url):
    
    headers = {'User-Agent': USER_AGENTS[random.randint(0, 8)]}
    page_request = requests.get(url, timeout=25, headers = headers, verify = False, allow_redirects = True)
    
    return page_request

def get_contact_page(url, page):
    """
    Get the contact page from the given Business URL.

    """

    data = page
    soup = BeautifulSoup(data, 'html.parser')
    contact_page = ""

    pattern_expr = "contact.*"
    pattern = re.compile(pattern_expr, re.I)

    for link in soup.find_all('a'):
        sub_url = link.get('href')
        if sub_url is not None:
            if re.search(pattern, sub_url):
                contact_page = sub_url  
                break     

    if not pd.isna(contact_page):
        if contact_page.startswith("/"):
            contact_page = contact_page[1:]

    suffixes = ['.com', '.org', '.net', '.info']
    ext = tldextract.extract(url)
    parent_url = ""
    if ext.subdomain:
        parent_url = "https://" + ext.subdomain 
    else:
        parent_url = "https://"
    if ext.domain:
        if not parent_url.endswith("https://"):
            parent_url = parent_url + "." + ext.domain
        else:
            parent_url = parent_url  + ext.domain

    if ext.suffix:
        parent_url = parent_url + "." + ext.suffix
    
    if not any(suffix in contact_page for suffix in suffixes):
        if parent_url.endswith("/"):
            contact_page_full = parent_url + contact_page 
        else:
            contact_page_full = parent_url + "/" + contact_page
    else:
        contact_page_full = contact_page

    return contact_page_full

def extract_businfo(sp,txt):
    
    bus_info_check = ['contact us','address','get in touch']
    
    if pyap.parse(txt,country='US'): 
        info = str(pyap.parse(txt,country='US')[-1])
        way = 'pyap'

    elif sp.find_all(lambda tag:'@' in tag.text.lower()):
        address_tag = sp.find_all(lambda tag:'@' in tag.text.lower())[-1]
        address_tag_text = address_tag.text
        parent_tag = address_tag.find_parent(lambda t: containsNumber(t.text.lower().replace(address_tag_text,'')) and ',' in t.text)
        info = parent_tag.text.replace('\n',' ').replace('\t',' ').replace('\xa0',' ')
        way = 'email'

    elif sp.find_all(lambda tag:tag.text.lower() in bus_info_check):
        address_tag = sp.find_all(lambda tag:tag.text.lower() in bus_info_check)[-1]
        parent_tag = address_tag.find_parent(lambda t:',' in t.text)
        info = parent_tag.text.replace('\n',' ').replace('\t',' ').replace('\xa0',' ')
        way = 'keyword'

    else:
        info = txt
        way = 'contact page text'
        
    return (info,way)


def parse_info(info):
    
    try:
        parsed_add = usaddress.parse(info)
        category = [i[1] for i in parsed_add]
        name = [i[0] for i in parsed_add]
        street=[]
        occupancy=[]
        placename=[]
        stat = []
        zipc = []

        for j in parsed_add:
            if 'Street' in j[1] or 'AddressNumber' in j[1]:
                street.append(j[0].replace('llc','').replace('LLC',''))
            elif j[1]=='OccupancyIdentifier':
                occupancy.append(j[0])
            elif j[1]=='PlaceName':
                placename.append(j[0])
            elif j[1]=='StateName':
                stat.append(j[0])
            elif j[1]=='ZipCode':
                zipc.append(j[0])
                break

        add = ' '.join(street).replace(',','').strip()
        occ = ' '.join(occupancy).replace(',','').strip()
        city = ' '.join(placename).replace(',','').strip()
        state = ' '.join(stat).replace(',','').strip()
        zipcode = ' '.join(zipc).replace(',','').strip()
        
    except:
        add=''
        occ=''
        city=''
        state=''
        zipcode=''
        
    return (add,occ,city,state,zipcode)


def get_bus_name(url,sp):
    
    domain = get_domain(url)
    title = sp.find('title').string
    titles = title.split()
    
    name_list = []
    for index in range(len(titles)):
        if titles[index].lower() in domain.lower():
            name_list.append(titles[index])
            cur_index = index-1
            while cur_index>=0 and titles[cur_index].replace("'",'').isalpha():
                name_list = [titles[cur_index]]+name_list
                cur_index -= 1
            cur_index = index+1
            while cur_index<len(titles) and titles[cur_index].replace("'",'').isalpha():
                name_list.append(titles[cur_index])
                cur_index += 1
            break
            
    if name_list:
        business_name = ' '.join(name_list).replace('Contact','').replace('contact','')
    else:
        business_name = domain.split('.')[0]
        
    return business_name


def get_email(txt):
    try:
        email = re.findall(r"[A-Za-z_%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,3}", txt)[0]
    except:
        email = ''
    return email

def get_phone(txt):
    try:
        phone = re.findall(r"(\d{3}[-\.\s]\d{3}[-\.\s]\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]\d{4}|\d{3}[-\.\s]\d{4})",txt)[0]
    except:
        phone = ''
    return phone  


if __name__ == '__main__':
    
    start_time = datetime.now()
    start_row = 1
    if len(sys.argv) > 2:
        start_row = int(sys.argv[2])
    
    logging.info(
    f'**** starting from row {str(start_row)}')
        
    file = pd.read_excel('input/' + FILE_NAME)
    total = len(file)
    file.index = [x+1 for x in range(len(file))]
    
    # start from the requested line
    file = file.tail(len(file)-start_row+1)
    
    try:
        file['url'] = file['url'].map(lambda x: x if x.startswith('http') else 'https://www.'+x+'/')
    except:
        logging.info(
        '**** no column named url, please change the column name')
        sys.exit()
    
    append_dic = {'contact_page':[], 'text':[], 'contact_page_text':[], 'info':[], 
                  'way':[], 'email':[], 'phone':[], 'business_name':[], 
                 'add':[], 'occ':[], 'city':[], 'state':[], 
                 'zipcode':[]}
    
    start = file.index[0]
    end = file.index[0]

    logging.info(
        f'**** start processing row{str(start)} to row{str(start+SAVE_EVERY-1)}')
    for index in file.index:
        url = file['url'][index]

        try: 
            
            req = crawl(url)
            contact_page = get_contact_page(url,req.content)
            contact_req = crawl(contact_page)
            
            if str(contact_req) == '<Response [200]>' and str(req) == '<Response [200]>':
                append_dic['contact_page'].append(contact_page)
                soup1 = BeautifulSoup(req.content, "html.parser")
                append_dic['text'].append(' '.join(list(soup1.stripped_strings)).replace('\n','').replace('\t','').replace('\xa0',''))
                soup = BeautifulSoup(contact_req.content, "html.parser")
                contact_text = ' '.join(list(soup.stripped_strings)).replace('\n','').replace('\t','').replace('\xa0','')
                append_dic['contact_page_text'].append(contact_text)
            
                info,way = extract_businfo(soup,contact_text)
                append_dic['info'].append(info)
                append_dic['way'].append(way)
                
                address,occupancy,city,state,zipcode = parse_info(info)
                
                if address == '' and way != 'contact page text':
                    append_dic['way'][-1] = 'contact page text'
                    address,occupancy,city,state,zipcode = parse_info(contact_text)
                    
                append_dic['add'].append(address)
                append_dic['occ'].append(occupancy)
                append_dic['city'].append(city)
                append_dic['state'].append(state)
                append_dic['zipcode'].append(zipcode)
                
                business_name = get_bus_name(url,soup1)
                append_dic['business_name'].append(business_name)
                
                append_dic['email'].append(get_email(contact_req.text))
                append_dic['phone'].append(get_phone(contact_req.text))
            
            else:
                for i in append_dic.keys():
                    if i=='way':
                        append_dic[i].append('page 403 error')
                    else:
                        append_dic[i].append('')
                    
        except:
            for i in append_dic.keys():
                if i=='way':
                    append_dic[i].append('page not found')
                else:
                    append_dic[i].append('')
                    
        current_processed = len(append_dic['way'])
        for i in append_dic.keys():
            if len(append_dic[i]) != current_processed:
                logging.info(
                f'**** issues happened at url {url}, please check the code')
                sys.exit()
                    
        end+=1
        if end-start == SAVE_EVERY or end==file.index[-1]+1:

            save_df = file.loc[start:end-1,:].copy()
            save_df['way'] = append_dic['way']
            save_df['business_name'] = append_dic['business_name']
            save_df['address'] = append_dic['add']
            save_df['door'] = append_dic['occ']
            save_df['city'] = append_dic['city']
            save_df['state'] = append_dic['state']
            save_df['zipcode'] = append_dic['zipcode']
            save_df['email'] = append_dic['email']
            save_df['phone'] = append_dic['phone']
            save_df['contact_page'] = append_dic['contact_page']
            save_df['text'] = append_dic['text']
            save_df['contact_page_text'] = append_dic['contact_page_text']
            save_df['info'] = append_dic['info']
            save_df.to_excel('tmp/'+str(FILE_NAME).replace('.xlsx','')+'_'+str(start)+'_'+str(end)+'.xlsx',index=False)
            
            
            append_dic = {'contact_page':[], 'text':[], 'contact_page_text':[], 'info':[], 
              'way':[], 'email':[], 'phone':[], 'business_name':[], 
             'add':[], 'occ':[], 'city':[], 'state':[], 
             'zipcode':[]}
            
            time_now = datetime.now()
            proc_time_so_far = (time_now - start_time).total_seconds() / 60
            logging.info(
                    f'**** Running for {proc_time_so_far:.2f} minutes ')
            file_name1 = FILE_NAME.replace('.xlsx','')
            logging.info(
                f'**** row{str(start)} to row{str(end-1)} finished processing, file saved as tmp/{file_name1}_{str(start)}_{str(end)}.xlsx')
            start = end
            if end-1 != total:
                logging.info(
                f'**** start processing row{str(start)} to row{str(start+SAVE_EVERY-1)}')
            
        if end-1 == total:
            path = r'tmp'
            filenames = glob.glob(path + "/*.xlsx")

            finalexcelsheet = pd.DataFrame()
            for file in filenames:

                df = pd.concat(pd.read_excel(file, sheet_name=None),
                               ignore_index=True, sort=False)

                finalexcelsheet = finalexcelsheet.append(
                  df, ignore_index=True)
            
            finalexcelsheet.to_excel('output/'+REPORT_NAME+'.xlsx',index=False)
            
            logging.info(
                    f'**** all files finished processing, file saved as output/{REPORT_NAME}.xlsx ')
            time_now = datetime.now()
            proc_time_so_far = (time_now - start_time).total_seconds() / 60
            logging.info(
                    f'**** Finished Running after {proc_time_so_far:.2f} minutes ')
            files = glob.glob('tmp/*')
            for f in files:
                os.remove(f)
            logging.info(
                    f'**** all files deleted under tmp folder ')   
            