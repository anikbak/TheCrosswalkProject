##############################################################################################################################
# THE CROSSWALK PROJECT
##############################################################################################################################

import numpy as np, pandas as pd, networkx as nx, fnmatch 

# Routines that convert datasets to crosswalks
def DatasetToCountDF(df,indexvar,attribvar,weightvar):
    '''
    Converts a dataset to a new dataset with attribute-level counts.
    '''

    # Step 0: Deal with Types
    if type(indexvar)==str:
        indexvar = [indexvar]
    if type(attribvar)==str:
        attribvar = [attribvar]
    if type(weightvar)==str:
        weightvar = [weightvar]
    if type(df) != pd.DataFrame:
        print(f'df is not a Pandas DataFrame, and it must be one.')
        raise TypeError
    if len(weightvar)>1:
        print(f'Only a single weighting variable is allowed. Maybe you want to multiply the variables {weightvar} together.')
        raise TypeError
    if list(df.columns).intersection(indexvar) != indexvar:
        print(f'At least one of the required observation id variables is missing.')
        raise IndexError
    if list(df.columns).intersection(attribvar) != attribvar:
        print(f'At least one of the required attribute definition variables is missing.')
        raise IndexError
    if list(df.columns).intersection(weightvar) != weightvar:
        print(f'The required weighting variable is missing.')
        raise IndexError
    
    # Collapse 
    df2 = df[indexvar+attribvar+weightvar].copy()
    df2 = df2.set_index(attribvar)
    df2['N'] = df2.groupby(attribvar)[weightvar].sum()
    df2 = df2.reset_index()
    df2 = df2[attribvar+['N']]
    df2 = df2.drop_duplicates()
    return df2

def DatasetToWeightedMultiCrosswalk(df,attrib1,attrib2,weightvar):
    '''
    Converts a Dataset containing two classification systems to a weighted multi-crosswalk 
    '''

    # Step 0: Deal with Types
    if type(attrib1)==str:
        attrib1 = [attrib1]
    if type(attrib2)==str:
        attrib2 = [attrib2]
    if type(weightvar)==str:
        weightvar = [weightvar]
    if type(df) != pd.DataFrame:
        print(f'df is not a Pandas DataFrame, and it must be one.')
        raise TypeError
    if len(weightvar)>1:
        print(f'Only a single weighting variable is allowed. Maybe you want to multiply the variables {weightvar} together.')
        raise TypeError

    # Step 1: Construct Two-Dimensional Collapse
    attribs = attrib1+attrib2
    df2 = df[attribs+weightvar].copy()
    df2 = df2.set_index(attribs)
    df2['N'] = df2.groupby(attribs)[weightvar].sum()
    df2 = df2.reset_index()
    df2 = df2[attribs+['N']].drop_duplicates()
    return df2

def MultiCrosswalkToIdealCrosswalk_randomtiebreaking(multixwalk,attrib1,attrib2,Nvar='N'):
    '''
    Convert a multicrosswalk to a modal ideal crosswalk with random tie breaking
    '''
    # Step 0: Deal with Types
    if type(attrib1)==str:
        attrib1 = [attrib1]
    if type(attrib2)==str:
        attrib2 = [attrib2]
    if type(multixwalk) != pd.DataFrame:
        print(f'multixwalk is not a Pandas DataFrame, and it must be one.')
        raise TypeError
    attribs = attrib1+attrib2
    
    # Step 1: Compute best match
    df = multixwalk.set_index(attrib1)
    df['NMAX'] = df.groupby(attrib1)[Nvar].max()
    df = df.reset_index()
    df = df.loc[df[Nvar]==df['NMAX'],attribs+[Nvar]].copy()

    # Step 2: Duplicates
    ValueCounts = df[attrib1].value_counts()
    if ValueCounts.max() == 1:
        return df
    else:
        df[Nvar+'fake'] = df[Nvar] + np.random.rand(len(df.index)) 
        df = df.set_index(attrib1)
        df['NMAX'] = df.groupby(attrib1)[Nvar+'fake'].max()
        df = df.reset_index()
        df = df.loc[df[Nvar+'fake']==df['NMAX'],attribs+[Nvar]].copy()
        return df

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
