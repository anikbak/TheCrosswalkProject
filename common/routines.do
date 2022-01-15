/*==============================================================================
CROSSWALKS IN STATA
*******************

==============================================================================*/

cap program drop DatasetToClassificationSystem
program define DatasetToClassificationSystem
	
	* Define Syntax
	syntax, weights(numeric) pop_id(varlist) class_id(varname) save(integer) [filename(string,asis)]
	
	if `save' == 1{
		preserve
	}
	
	* Construct crosswalk dataset
	collapse (sum) `weights' , by(`class_id')
	
	if `save' == 1{
		save "`filename'", replace 
		restore
	}

end

