############################################################################
# Construct a consistent SOC Coding (the equivalent to occ1990dd)
# ---------------------------------------------------------------
# Operates on raw data downloaded from O*NET's data archives. 
############################################################################

import pandas as pd
import sys 
sys.path.append("occ/code")
from routines import MultiXwalk2Classification_Exhaustive 

# Preallocation
years = [2000,2006,2009,2010,2019] 
dfs,xwalks,xwalks8 = {},{},{}

def VariableNamesONET(year,stub=''):
    varcode = 'O*NET-SOC '+str(year)+' Code'+stub
    vartitle = 'O*NET-SOC '+str(year)+' Title'+stub
    return varcode,vartitle

def RemoveDuplicatesFromColumns(row,year):
    vc,vt = VariableNamesONET(year,'s, 8dig')
    codes,titles = row[vc].split(" AND "),row[vt].split(" AND ")
    df = pd.DataFrame({'c':codes,'t':titles})
    df = df.drop_duplicates()
    codes,titles = df['c'].values,df['t'].values
    return " AND ".join(codes)," AND ".join(titles)

# Step 1: Load Crosswalks and construct 6-digit crosswalks

for iy in range(4):
    y = years[iy]
    
    # Load 8-digit crosswalks
    # -----------------------
    yp = years[iy+1]
    df8 = pd.read_csv("occ/raw/onetsoc dynamic/"+str(y)+"_to_"+str(yp)+"_Crosswalk.csv")
    xwalks8[str(y)+'_'+str(yp)] = df8 
    
    # Construct 6-digit crosswalks
    # ----------------------------
    # Define variable names
    vc,vt = VariableNamesONET(y)
    vcp,vtp = VariableNamesONET(yp)
    vc6,vt6 = VariableNamesONET(y,', 6dig')
    vcp6,vtp6 = VariableNamesONET(yp,', 6dig')
    vc8,vt8 = VariableNamesONET(y,'s, 8dig')
    vcp8,vtp8 = VariableNamesONET(yp,'s, 8dig')
    
    # Step 1.0: Create 6-digit codes
    df8[vc6],df8[vcp6] = df8[vc].str[:7],df8[vcp].str[:7]
    df8[vc8],df8[vcp8],df8[vt8],df8[vtp8] = '','','',''

    # Step 1.1: count number of 8-digit codes for each 6-digit pairing
    df8 = df8.sort_values([vc6,vcp6])
    df8 = df8.set_index([vc6,vcp6])
    df8['idx'] = df8.groupby([vc6,vcp6]).cumcount()
    df8 = df8.reset_index()

    # Step 1.2: reshape dataset to wide format
    Nlevels = df8['idx'].max()
    df6 = df8.loc[df8['idx']==0].copy()
    df6[vc8] = df6[vc]
    df6[vt8] = df6[vt]
    df6[vcp8] = df6[vcp]
    df6[vtp8] = df6[vtp]
    df6 = df6.drop(columns=['idx',vc,vt,vcp,vtp])
    
    for i in range(1,Nlevels):
        temp = df8.loc[df8['idx']==i,[vc6,vcp6,vc,vt,vcp,vtp]]
        temp = temp.rename(columns={X:X+'_'+str(i) for X in [vc,vt,vcp,vtp]})
        df6 = df6.merge(temp,on=[vc6,vcp6],how='outer')
        cols = [X+'_'+str(i) for X in [vc,vt,vcp,vtp]]
        for col in [X+'_'+str(i) for X in [vc,vt,vcp,vtp]]:
            df6.loc[pd.isna(df6[col]),col] = ''

    # Step 1.3: Concatenation
    colso = [vc,vt,vcp,vtp]
    cols8 = [vc8,vt8,vcp8,vtp8]
    for i in range(1,Nlevels):
        for ic in range(4):
            df6[cols8[ic]] = df6[cols8[ic]]+' AND '+df6[colso[ic]+'_'+str(i)]
            df6.loc[df6[cols8[ic]].str[-5:]==' AND ',cols8[ic]] = df6.loc[df6[cols8[ic]].str[-5:]==' AND ',cols8[ic]].str[:-5]
            df6 = df6.drop(columns=colso[ic]+'_'+str(i))

    # Step 1.5: Fix Duplication
    df6[[vc8,vt8]] = df6.apply(lambda row: RemoveDuplicatesFromColumns(row,y),axis=1).tolist()
    df6[[vcp8,vtp8]] = df6.apply(lambda row: RemoveDuplicatesFromColumns(row,yp),axis=1).tolist()

    # Step 1.4: Assign to Dictionary    
    xwalks[str(y)+'_'+str(yp)] = df6

# Step 2: Construct "Grand" Multi-crosswalk by outer-merging
df = xwalks['2000_2006']
vc8,vt8 = VariableNamesONET(2000,'s, 8dig')
vcp8,vtp8 = VariableNamesONET(2006,'s, 8dig')
df = df.rename(columns={X:X+', Left' for X in [vcp8,vtp8]})

for iy in range(1,4):

    y,yp = years[iy],years[iy+1]
    dfm = xwalks[str(y)+'_'+str(yp)]
    
    # Define variable names
    vc6,_ = VariableNamesONET(y,', 6dig')
    vcp6,_ = VariableNamesONET(yp,', 6dig')
    vc8,vt8 = VariableNamesONET(y,'s, 8dig')
    vcp8,vtp8 = VariableNamesONET(yp,'s, 8dig')

    # Left/Right Renames
    dfm = dfm.rename(columns={X:X+', Left' for X in [vcp8,vtp8]}) 
    dfm = dfm.rename(columns={X:X+', Right' for X in [vc8,vt8,]})

    # Merge
    df = df.merge(dfm,on=vc6,how='outer')

# Step 3: Construct Merge Groupings based on sub-connected graphs
classlist = ['O*NET-SOC '+str(y)+' Code, 6dig' for y in years]
savelist = ['onetsoc_'+str(y)+'_to_SOC_AB.csv' for y in years]
Classification,Xwalks = MultiXwalk2Classification_Exhaustive(df,classlist,noisily=True)

# Step 4: Reclassify some occupations for each period
# ---------------------------------------------------
# Step 4.1: Create new categories for category soc_ab == 7 (which is too large to be valid)

# Managers: Subcategorized 
# ------------------------
# Administrative Services:              7 -> 801
# Financial Managers:                   7 -> 802
# Logistics Managers:                   7 -> 803
# Education Managers:                   7 -> 804
# Inspectors:                           7 -> 805
# Service Coordinators:                 7 -> 806
# Compliance/Regulatory Managers:       7 -> 807
# Healthcare Managers:                  7 -> 808
# NEC:                                  7 -> 899

Init,New = {},{}
Init[0],New[0] = ['11-3011','11-3031','11-3071','11-9039','11-9199'],[801,802,803,804,899]    # 2000
Init[1],New[1] = ['11-3011','11-3031','11-3071','11-9039','11-9199'],[801,802,803,804,899]    # 2006
Init[2],New[2] = ['11-3011','11-3031','11-3071','11-9039','11-9199'],[801,802,803,804,899]    # 2006
Init[3],New[3] = ['11-3011','11-3031','11-3071','11-9039','11-9199'],[801,802,803,804,899]    # 2010
Init[4],New[4] = ['11-3012','11-3031','11-3071','11-9039','11-3013','11-9199'],[801,802,803,804,899,899]    # 2019

for i in range(len(classlist)):
    if len(Init[i]) == 0:
        continue
    else:
        dft = Xwalks[i].copy()
        for ic in range(len(Init[i])):
            dft.loc[dft['O*NET-SOC '+str(years[i])+' Code, 6dig']==Init[i][ic],'classification'] = New[i][ic]
        Xwalks[i] = dft

# Computer Scientists
# -------------------
# Software:                 7 -> 901
# Hardware:                 7 -> 902
# Networking:               7 -> 903
# Data/Database:            7 -> 904
# NEC:                      7 -> 999

Init,New = {},{}
Init[0],New[0] = [],[]                                          # 2000
Init[1],New[1] = [],[]                                          # 2006
Init[2],New[2] = [],[]                                          # 2009
Init[3],New[3] = [],[]                                          # 2010
Init[4],New[4] = [],[]                                          # 2019

for i in range(len(classlist)):
    if len(Init[i]) == 0:
        continue
    else:
        dft = Xwalks[i].copy()
        for ic in range(len(Init[i])):
            dft.loc[dft['O*NET-SOC '+str(years[i])+' Code, 6dig']==Init[i][ic],'classification'] = New[i][ic]
        Xwalks[i] = dft

# Engineers
# -------------------
# Biomedical:               68 -> 1001
# Hardware:                 68 -> 1002
# Networking:               68 -> 1003
# Data/Database:            68 -> 1004
# NEC:                      68 -> 1099

Init,New = {},{}
Init[0],New[0] = ['17-2031','17-2112','17-2199'],[1001,1099,1099]                                          # 2000
Init[1],New[1] = ['17-2031','17-2112','17-2199'],[1001,1099,1099]                                          # 2006
Init[2],New[2] = ['17-2031','17-2112','17-2199'],[1001,1099,1099]                                          # 2009
Init[3],New[3] = ['17-2031','17-2112','17-2199'],[1001,1099,1099]                                          # 2010
Init[4],New[4] = ['17-2031','17-2112','17-2199'],[1001,1099,1099]                                         # 2019

for i in range(len(classlist)):
    if len(Init[i]) == 0:
        continue
    else:
        dft = Xwalks[i].copy()
        for ic in range(len(Init[i])):
            dft.loc[dft['O*NET-SOC '+str(years[i])+' Code, 6dig']==Init[i][ic],'classification'] = New[i][ic]
        Xwalks[i] = dft

# Step 4.2: Existing occupations directly reclassified to existing categories
Init,New = {},{}
Init[0],New[0] = ['15-2091','15-2099','15-2041'],[60,60,60]                                          # 2000
Init[1],New[1] = ['15-2091','15-2099','15-2041'],[60,60,60]                                          # 2006
Init[2],New[2] = ['15-2091','15-2099','15-2041'],[60,60,60]                                          # 2006
Init[3],New[3] = ['11-9061','13-1131','15-2091','15-2099','15-2041','21-1094','29-1128','29-2035','31-9097','43-3099','51-3099'],[21,6,60,60,60,143,205,286,308,418,596]   # 2010
Init[4],New[4] = ['11-9171','13-1131','15-2091','15-2099','15-2041','21-1094','29-1128','29-2035','31-9097','43-3099','51-3099'],[21,6,60,60,60,143,205,286,308,418,596]   # 2019

for i in range(len(classlist)):
    if len(Init[i]) == 0:
        continue
    else:
        dft = Xwalks[i].copy()
        for ic in range(len(Init[i])):
            dft.loc[dft['O*NET-SOC '+str(years[i])+' Code, 6dig']==Init[i][ic],'classification'] = New[i][ic]
        Xwalks[i] = dft

# Save Results
for i in range(len(classlist)):
    dfx = Xwalks[i]
    dfx.to_csv("occ/xwalk_soc_ONET/"+savelist[i])
