############################################################################
# Construct a consistent SOC Coding (the equivalent to occ1990dd)
############################################################################

import networkx as nx
import pandas as pd, fnmatch 

# Preallocation
years = [2000,2006,2009,2010,2019]
dfs,xwalks,xwalks8 = {},{},{}

def VariableNamesONET(year,stub=''):
    varcode = 'O*NET-SOC '+str(year)+' Code'+stub
    vartitle = 'O*NET-SOC '+str(year)+' Title'+stub
    return varcode,vartitle

def MultiXwalk2Classification_Exhaustive(df,classlist,noisily=True):
    Nclasses = len(classlist)
    Classification,xwalks = {},{}
    for i in range(Nclasses):
        Classification[i] = {}
    # Step 1: Construct NodeLists
    if noisily==True:
        print('constructing node lists')
    nodelist,nodelistG = {},{}
    for i in range(Nclasses):
        class_i = classlist[i]
        nodelist[i] = df.loc[pd.notna(df[class_i]),class_i].unique()
        nodelistG[i] = ['g'+str(i)+':'+x for x in nodelist[i]]
    # Step 2: Define Graph
    if noisily==True:
        print('constructing graph and adding edges')
    G = nx.Graph()
    for i in range(Nclasses):
        G.add_nodes_from(nodelistG[i])
    # Step 3: Exhaustive Links
    for i_start in range(Nclasses):
        if noisily==True:
            print(f'    on starting class {i_start} of {Nclasses}')
        c0 = classlist[i_start]
        for i_end in range(Nclasses):
            c1 = classlist[i_end]
            if i_start != i_end:
                for x in nodelist[i_start]:
                    y = df.loc[ (df[c0]==x) & (pd.notna(df[c1])),c1 ].unique()
                    G.add_edges_from([('g'+str(i_start)+':'+x,'g'+str(i_end)+':'+iy) for iy in y])
    # Step 4: Construct Connected Components and Loop
    if noisily==True:
        print('constructing connected components')
    ConnectedComponents = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    Ncomponents = len(ConnectedComponents)
    for ic in range(Ncomponents):
        NODES = ConnectedComponents[ic].nodes()
        for i in range(Nclasses):
            Classification[i][ic] = fnmatch.filter(NODES,'g'+str(i)+':*')
    # Step 5: Convert Classification into "Consistent" Crosswalks
    for i in range(Nclasses):
        dftemp = df[[classlist[i]]].drop_duplicates()
        dftemp = dftemp.loc[pd.notna(dftemp[classlist[i]])]
        dftemp['classification'] = -9999
        for ic in range(Ncomponents):
            values = [x.replace('g'+str(i)+':','') for x in Classification[i][ic]]
            dftemp.loc[dftemp[classlist[i]].isin(values),'classification'] = ic
        xwalks[i] = dftemp
    return Classification,xwalks

# Step 1: Load Crosswalks and construct 6-digit crosswalks

for iy in range(5):
    y = years[iy]
    
    # Load classification values for each year
    dfs[y] = pd.read_csv("occ/raw/onetsoc dynamic/"+str(y)+"_Occupations.csv")
    
    if iy < 4:
        
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

# Step 3: Construct Merge Groupings
classlist = ['O*NET-SOC '+str(y)+' Code, 6dig' for y in years]
savelist = ['onetsoc_'+str(y)+'_to_SOC_AB.csv' for y in years]

Classification,Xwalks = MultiXwalk2Classification_Exhaustive(df,classlist,noisily=True)

for i in range(len(classlist)):
    dfx = Xwalks[i]
    dfx.to_csv("occ/xwalk_soc_ONET/"+savelist[i])
