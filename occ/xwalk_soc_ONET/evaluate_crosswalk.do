* Evaluate crosswalk quality

cd "C:\Users\anikb\Dropbox\Github\TheCrosswalkProject\occ\"
local years "2000 2006 2009 2010 2019"

use xwalk_soc_occ1990dd\soc_descriptions, clear 
ren onetsoc_code onetsoc_code_8dig
gen onetsoc_code = substr(onetsoc_code_8dig,1,7)
tempfile socdesc
save `socdesc', replace

foreach y in `years'{
	import delimited using xwalk_soc_ONET\onetsoc_`y'_to_SOC_AB.csv, clear 
	drop v1 
	ren classification soc_ab
	ren onet onetsoc_code
	gen year = `y'
	tempfile data`y'
	save `data`y'', replace
}

clear 
foreach y in `years'{
	append using `data`y''
}

merge 1:m onetsoc_code year using `socdesc', nogen 
order onetsoc_code_8dig onetsoc_title onetsoc_desc onetsoc_code soc_ab

bys soc_ab: egen N = count(soc_ab)

local GoodLevel = 8
tab N if N>=`GoodLevel'