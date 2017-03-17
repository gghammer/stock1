
# coding: utf-8

# In[1]:

from yahoo_finance import Share
import requests
import base64
from bs4 import BeautifulSoup
import pandas
import sqlite3 as lite
from shutil import copyfileobj
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime , date 
import sys
import os
import re
from time import sleep

#define max stock id
max_stock_id = 1000

#payload data for twse
payload={}
dt_str = []
#gmail setting
emailfrom = "gghammer@gmail.com"
emailto = "gghammer@gmail.com"
#fileToSend = "daily.xlsx"
username = "gghammer"
password = "ggpudin81161"



def send_to_gmail(source,attach_name):    
    #save to xlsx file
    twse = pandas.read_csv(source,encoding = "big5",header=1)    
    writer = pandas.ExcelWriter(attach_name, engine='xlsxwriter')
    twse.to_excel(writer, sheet_name='Sheet1')
    writer.save()

    #gmail send 
    msg = MIMEMultipart()
    msg["From"] = emailfrom
    msg["To"] = emailto
    today = date.today()    
    #msg["Subject"] = "哈墨投顧日報 "+currenttime.strftime('%Y-%m-%d')
    msg["Subject"] = "哈墨投顧日報 "+str(today)    
    msg.preamble = "help I cannot send an attachment to save my life"

    ctype, encoding = mimetypes.guess_type(attach_name)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"

    maintype, subtype = ctype.split("/", 1)

    if maintype == "text":
        fp = open(attach_name)
        # Note: we should handle calculating the charset
        attachment = MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "image":
        fp = open(attach_name, "rb")
        attachment = MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "audio":
        fp = open(attach_name, "rb")
        attachment = MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(attach_name, "rb")
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(fp.read())
        fp.close()
        encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=attach_name)
    msg.attach(attachment)

    server = smtplib.SMTP("smtp.gmail.com:587")
    server.starttls()
    server.login(username,password)
    server.sendmail(emailfrom, emailto, msg.as_string())
    server.quit()
    print("Send Gmail done")

def crawl_stock_id(name):  
    #catch payload 
    res = requests.post('http://www.tse.com.tw/ch/trading/exchange/BWIBBU/BWIBBU_d.php#')
    res.encoding = 'big5'

    #find key & Encryption 
    soup = BeautifulSoup(res.text, 'html.parser') 

    for inp in soup.select('input'):
        if 'hidden' in inp.get('type'): 
            payload[inp.get('name')] = base64.b64encode(inp.get('value').encode('utf-8')) 
        
    #download csw file        
    res2 = requests.post('http://www.tse.com.tw/ch/trading/exchange/BWIBBU/BWIBBU_print.php?language=ch&save=csv',data = payload ,stream = True)

    #save to twse.csv 
    f = open(name,'wb')
    copyfileobj (res2.raw,f)
    f.close()  
    
    
def crawl(target):  
    
    
    #catch payload 
    res = requests.post('http://www.tse.com.tw/ch/trading/exchange/BWIBBU/BWIBBU_d.php#')
    res.encoding = 'big5'

    #find key & Encryption 
    soup = BeautifulSoup(res.text, 'html.parser') 

    #get & translate date 
    dt = soup.select('input')[2].get('value')
    dt = dt.replace(dt[0:3], str(int(dt[0:3])+ 1911))
    dt = dt.replace(dt[4:5],'-')
    dt_str = dt.split(' ')

    for inp in soup.select('input'):
        if 'hidden' in inp.get('type'): 
            payload[inp.get('name')] = base64.b64encode(inp.get('value').encode('utf-8')) 
        
    #download csw file        
    res2 = requests.post('http://www.tse.com.tw/ch/trading/exchange/BWIBBU/BWIBBU_print.php?language=ch&save=csv',data = payload ,stream = True)

    #save to twse.csv 
    f = open('twse.csv','wb')
    copyfileobj (res2.raw,f)
    f.close()  

    #read csw to pandas 
    twse = pandas.read_csv('twse.csv',encoding = "big5",header=1)

    with lite.connect(target) as conn:   
        for i in range(0,max_stock_id):
            col = twse.iloc[i]
            col = col.tolist()
            stock_id = col[0]
            if len(stock_id)>10 :
                break
            else:    
                data = dt_str + col
                conn.execute('INSERT INTO 指標 (日期,代號,名稱,本益比,殖利率,股價淨值比) VALUES (?,?,?,?,?,?);', data)
    conn.close()
    
    print("crawl 指標 is Done")
    
def update_stock_id(name):    

    crawl_stock_id('temp.csv')
    #read csw to pandas 
    twse = pandas.read_csv('temp.csv',encoding = "big5",header=1)
    
    with lite.connect(name) as conn:   
        cur = conn.cursor()
        for i in range(0,max_stock_id):
            col = twse.iloc[i]
            col = col.tolist()
            del col[2:5]   
            stock_id = col[0]
            stock_name = col[1]
            if len(stock_id)>10:
                break
            else:   
                cur.execute("UPDATE 股票代號 SET 代號=?,名稱=? WHERE rowid=?",(stock_id,stock_name,i+1))         
    conn.commit()
    conn.close()  
    
    os.remove("temp.csv")
    print("Stock ID update success !")
    
def create_sql_lib(name):    
    #create sqlite lib
    conn = lite.connect(name)
    with lite.connect(name) as conn:
        conn.execute('''CREATE TABLE 股票代號 
                    (代號 VARCHAR(10),名稱 VARCHAR(10));''')       

        conn.execute('''CREATE TABLE 股價
                    (日期 DATE,代號 VARCHAR(10),名稱 VARCHAR(10),
                    開盤價 INTEGER,收盤價 INTEGER,漲跌 INTEGER,漲跌百分比 INTEGER,
                    最高 INTEGER,最低 INTEGER,日量 INTEGER,均線50 INTEGER,均線200 INTEGER
                    本益比,殖利率,股價淨值比);''')          

        conn.execute('''CREATE TABLE 指標
                    (日期 DATE,代號 VARCHAR(10),名稱 VARCHAR(10),本益比 INTEGER,殖利率 INTEGER,股價淨值比 INTEGER);''')    
    
        conn.execute('''CREATE TABLE 營收
                    (日期 DATE,代號 VARCHAR(10),名稱 VARCHAR(10),EPS INTEGER,月營收 INTEGER,季營收 INTEGER,年營收 INTEGER,配息 INTEGER,配股 INTEGER);''')     

    conn.close()   
    
    print ("SQLite LIB created successfully")  
    
    crawl_stock_id('temp.csv')
    
    #read csw to pandas 
    twse = pandas.read_csv('temp.csv',encoding = "big5",header=1)

    #update to sqlite file 
    with lite.connect(name) as conn:   
        for i in range(0,max_stock_id):
            col = twse.iloc[i]
            col = col.tolist()
            del col[2:5]
            if len(col[0]) >10:
                break
            else:    
                conn.execute('INSERT INTO 股票代號 (代號,名稱) VALUES (?,?);', col)  
    conn.close()      
    
    os.remove("temp.csv")
    print ("Stock ID created successfully") 
    
    
def getStock_history(id,start,end):
    stock = Share(str(id)+'.TW')
    data = stock.get_historical(start, end)
    return data


def crawl_history(target): 
    today = date.today() #todays date 
    with lite.connect('stock.sqlite') as conn:
        cur  = conn.cursor()
        cur.execute("SELECT * FROM 股票代號")
        for i in range(0,max_stock_id):     
            sql = cur.fetchone()
            print(sql)
            if sql: 
                try:
                    stock = getStock_history(sql[0],'2008-01-01',str(today))                        
                    for i in range(0,len(stock)):                            
                        data = stock[i]
                        if data['Date']:
                            stock_date = data['Date']
                        if data['Open']:    
                            stock_open = data['Open']
                        if data['High']:                         
                            stock_high = data['High']
                        if data['Low']:                         
                            stock_low = data['Low']
                        if data['Close']:         
                            stock_close = data['Close']
                        if data['Volume']:
                            stock_volume = data['Volume']
                        if int(stock_volume):      
                            sql_list = []
                            sql_list = [stock_date]+[sql[0]]+[sql[1]]+[stock_open]+[stock_close]+[stock_high]+[stock_low]+[stock_volume]
                            conn.execute('INSERT INTO 股價 (日期,代號,名稱,開盤價,收盤價,最高,最低,日量) VALUES (?,?,?,?,?,?,?,?);',sql_list)     
                            conn.commit()    
                    print(datetime.now())
                    #sleep(30)    
                except:
                    print("Not support ID =",sql[0])
    conn.close()    
    print("Crawl history is done")
                        
#main   
def main(function):
        
    if function == 'create_lib':
        create_sql_lib('stock.sqlite')      
        
    elif function == 'update_stock_lib':
        update_stock_id('stock.sqlite')  
    
    elif function == 'crawl':      
        crawl('stock.sqlite')  #target sql file name , para    
        stock = crawl_history('stock.sqlite')  
    elif function == 'crawl_history':      
        stock = crawl_history('stock.sqlite')   
    elif function == 'report':
        send_to_gmail('twse.csv','daily.xlsx') #source pandas structure , target excel file name        
    else:
        print(' Usag   hamu create_lib          #建立資料庫')
        print('        hamu update_stock_id     #更新股票代號')
        print('        hamu crawl               #爬當日資料')
        print('        hamu crawl               #爬歷史資料')
        print('        hamu report              #透過gmail寄出電子報')
        
        
if __name__ == '__main__':
    main(sys.argv[1])        


# In[ ]:



