# Download Data on ZipCodes from zipdatamaps.com/ 

import numpy as np, pandas as pd, requests, pickle as pkl
from bs4 import BeautifulSoup

df = pd.read_csv("geo/zipcodes_geonames.csv",encoding='latin_1')
zipList = list(df['zipcode'])

def ZipCodeDataExtract(zipcode):
    # Step 0: Verify Existence
    zipcode = str(zipcode)
    url = "https://www.zipdatamaps.com/"+zipcode
    page = requests.get(url)
    soup = BeautifulSoup(page.text)
    ZipName = soup.findAll('table')[0].findAll('a')[0].text
    if ZipName == "":
        print(f'Not a good zipcode')
        return {}
    else:
        print(f'****************************** ZIP Code {zipcode} *************************************')
        # Step 1: Get list of tables
        tables = soup.findAll('table')
        if tables != []:
            NTables = len(tables)
            # Step 2: Extract from tables
            dict_of_zip_values = {}
            for i in range(NTables):
                Table = tables[i]
                Rows = Table.findAll('tr')
                NRows = len(Rows)
                if NRows > 0:
                    for r in range(NRows):
                        Row = Rows[r]
                        Cols = Row.findAll('td')
                        attribute,value = Cols[0].text, Cols[1].text
                        print(f'{attribute}: {value}')
                        dict_of_zip_values[attribute] = value
                    return dict_of_zip_values
                else:
                    continue
        else:
            return {}

zipDict = {}

for z in zipList:
    zipDict[z] = ZipCodeDataExtract(z)

with open('ZipcodeData.pkl','wb') as handle:
    pkl.dump(zipDict,handle)