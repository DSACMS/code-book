*-------------------------------------------------------------------------------------*;
* Purpose: MCBS Codebook Program for Annual File Documentation 
* Created by: JR and DSR                                              
* 9/19/2017 
* Modified:  PC version of MF codebook program to use existing formated SAS dataset, 
*            read in EXCEL version of Notes file and to make all calls generic --  DSR
* 10/24/2017 Modified to extend question number output to allow multiple 
*            question numbers - DSR
*
* 12/5/2017  This version modified to run the PUF file for 2015 -- DSR
*            Includes multi line notes
* 08/30/2019  This version modified to run the PUF file for 2017 to run for 3 separate PUF files -- DSR
* 
* 08/08/2023  Updated with new directory locations -- JR  
* 08/08/2023  Deleted the column "Order" from the PUFNotes2021.xlsx file as it is not used in codebook creation and
                it has not been updated since new 2020 vars were added-- JR
* 9/1/2023    Streamlined code by deleting some of the special formatting that is not used for PUF files, eg. BASIED -JR
* 9/10/2024   Updated with new BOX directory locations -- JR  
*----------------------------------------------------------------------------------------------------------------------*;
ods html close; /* This will erase the previous results view */
ods html;
run;

libname fmts 'C:\Box\Box\SMAG\MCBS\Data and documentation\2023\Survey File PUF\Formats';  /*  Using PUF file formats   */
libname notes 'C:\Box\Box\SMAG\MCBS\Codebook production\Notes\2023 PUF Notes';
libname indata 'C:\Box\Box\SMAG\MCBS\Data and documentation\2023\Survey File PUF\PUF SAS Files';

/************************************************************************************************************
Prior to running this program to create the codebook run the formats code to create the
annual format library for this data PUF year -- 2022  
It needs to be run ONCE each time new formats are added, otherwise it just uses the most
recent formats file created.

Replace the file name/codebook name for this codebook run  

Beginning in 2017 there are now 3 files for the PUF by season, Fall (1), Winter (2), Summer (3) 

++ Note: Do an "Edit/Find/Replace" of the previous year before running the new year to make sure all 
++ previous year file locations have been updated -- JR
*****************************************************************************************************************/

*** Comment out the PUF file/season not need below; * Added all seasons files 8/8/2023 - JR;

%let CODEBK = sfpuf2023_1_fall;   /* filename sfpufyyyy_#_season */ 
%let CODEBOOK = 'C:\Box\Box\SMAG\MCBS\Data and documentation\2023\Survey File PUF\2023 PUF Codebook\MCBSPUF_2023_1_fall.txt'; /* PUF codebook name MCBSPUF_yyyy_#_Season */ 

*%let CODEBK = sfpuf2023_2_winter;   /* filename pufyyyy_#_season */ 
*%let CODEBOOK = 'C:\Box\Box\SMAG\MCBS\Data and documentation\2023\Survey File PUF\2023 PUF Codebook\MCBSPUF_2023_2_winter.txt'; /* PUF codebook name MCBSPUF_yyyy_#_Season */ 

*%let CODEBK = sfpuf2023_3_summer;   /* filename pufyyyy_#_season */ 
*%let CODEBOOK = 'C:\Box\Box\SMAG\MCBS\Data and documentation\2023\Survey File PUF\2023 PUF Codebook\MCBSPUF_2023_3_summer.txt'; /* PUF codebook name MCBSPUF_yyyy_#_Season */ 


options FMTSEARCH=(fmts);
*options nofmterr;

proc contents data=indata.&codebk; run;

/*  This annual notes file for 2023 has all unique notes/question for PUF files - remove years > 4 years before survey year  */
PROC IMPORT OUT= notes.PUFNotes2023 DATAFILE= "C:\Box\Box\SMAG\MCBS\Codebook production\Notes\2023 PUF Notes\PUFNotes2023.xlsx" 
            DBMS=xlsx REPLACE;
     SHEET="PUF Notes"; 
     GETNAMES=YES;
RUN;
Data notes.PUFNotes2023;
   set notes.PUFNotes2023;
   var_nm=trim(var_nm);
   qnbr=trim(qnbr);
   yr=trim(yr);
run;

/*get info from the sas dataset for the codebook to be created*/
/*data set should ALREADY have the formats and labels applied   */
/*the data should already be ordered by position during creation  */

/*   add formats for the special dates and for the continuous variables   */

data newdata;
   set indata.&codebk;

   format PUF_ID PUFFMT.;

  /*   add regrouping code here for the current codebook so that continuous and date
	   variables -- especiallly the weights -- are grouped according to grouped values and missings
	   comment it out if not applicable -- NOTE PUF should NOT have dates and only weights should be continuous   */

  /*** each of the 3 PUF files will have their own weights now.
   Comment out the appropriate lines when running each round ***/
  If &codebk = 'sfpuf2023_1_fall' then do;   
      format PUFF001-PUFF100 PUFFWGT CONTIN.;
  end; 
 /*If &codebk = 'sfpuf2023_2_winter' then do;   
      format PUFW001-PUFW100 PUFWWGT CONTIN.;
   end;  
  If &codebk = 'sfpuf2023_3_summer' then do;   
     format PUFS001-PUFS100 PUFSWGT CONTIN.;
  end;*/

  drop &codebk;
run;

/*   write the proc contents out to a file   */
proc contents data=newdata noprint out=TMPCONT;
run;

/*  rename values for creating the codebook   */
data TMPCONT2(keep=var_nm var_type var_pos var_fmt var_label);
   set TMPCONT;
   rename name=var_nm type=var_type varnum=var_pos label=var_label format=var_fmt; 
run;

/*set the data type*/;
data TMPCONT3;
   set TMPCONT2;
      length var_fmt_type $1.;
	  if var_type=2 then var_fmt_type='C';
	     else if var_type=1 then var_fmt_type='N';	
      var_fmt_type=put(trim(var_fmt_type),$1. -r);
	  
run;

/*  sort in data order */
proc sort data=TMPCONT3;
   by var_pos;
run;

/*   create the main codebook information by joining with the notes file   */
proc sql;
   create table codebook_main as
   select distinct a.var_nm, /*variable name*/
                   a.var_fmt, /*format name*/
			       a.var_fmt_type, /*C or N*/
				   a.var_label, /*variable label*/
				   a.var_pos, /*position or order*/
				   b.qnbr, /*question number*/
				   b.yr, /*year question came in*/
				   b.notes, /*question notes*/
				   b.notes2,
				   b.notes3
   from TMPCONT3 a left join notes.PUFNotes2023 b
                        on a.var_nm=b.var_nm 
						order by a.var_pos;
quit;

/*   delete old codebook version in memory   */
proc datasets;
   delete codebook_all; 
run;

/*   get the frequencies for the codebook one variable at a time  */

%macro rec_cnt(varnm, fmtnm);

*proc freq data=indata.&CODEBK.;
proc freq data=newdata;
   tables &varnm./ missing norow nocol nopercent out=rec_cnt1_&varnm.(rename=(count=rec_cnt));
run;

data rec_cnt1_&varnm.;
   set rec_cnt1_&varnm.;
   length var_fmt var_nm $16.;
   length var_fmt_value $16.;
   length var_fmt_label $75.;
   var_fmt_label=put(&varnm.,&fmtnm..);
   var_fmt="&fmtnm.";
   var_nm="&varnm.";
   var_fmt_value=put(&varnm.,$16.); 

/*   fix these special formats for codebook printing   */   
   select (var_nm);
	  when ('PUF_ID') var_fmt_value='LOW-HIGH';
      when ('H_RESCTY')
         do;
            var_fmt = '$CTYFMT';
            if var_fmt_value ne . then
               var_fmt_value = 'County Code';
         end;
      when ('PROV')
         do;
            var_fmt = '$FIDFMT';
            if var_fmt_value ne ' ' then
               var_fmt_value = 'Provider Number';
         end;
	  otherwise;
   end;
   
   /* formats that had to be modified for the codebook */
   Select (var_fmt);
      when ('DTE6FMT')
         do;
            if var_fmt_value ne . then
               var_fmt_value= 'YYYYMM';
	        var_fmt = 'YYMMn6';
         end;
      when ('DTE8FMT')
         do;
            if var_fmt_value ne . then
               var_fmt_value= 'MMDDYYYY';
	        var_fmt = 'MMDDYYn8';
         end;
      when ('CONTIN')
         do;
            if var_fmt_value ne . then
               var_fmt_value = 'LOW-HIGH';
	        var_fmt = ' ';
         end;
      when ('$CONTIN')
         do;
            if var_fmt_value ne ' ' then
               var_fmt_value = 'Range of values';
	        var_fmt = ' ';
         end;
      when ('SEQFMT','TOTINFMT','LENFMT','COST2FMT','ADIFMT','AGEFMT','HLPRNUMF')
         do;
			if var_fmt_value ne . then
               var_fmt_value = 'Range of values';
         end;
      when ('DAYKFMT')
         do;
			if (var_fmt_value ne . ) and
               (var_fmt_value ne 0) then
               var_fmt_value = 'Range of values';
         end;
      when ('MONYFMT','PREM_F')
         do;
			if var_fmt_value ne . then
               var_fmt_value = 'Range of values';
         end;
       when ('NUM4FMT')
         do;
			if var_fmt_value ne . then
               var_fmt_value = 'Range of values';
         end;
       when ('EVENTMM')
         do;
			if var_fmt_value ne . then
               var_fmt_value = 'Range of values';
         end;
       when ('YRFMT')
         do;
			if var_fmt_value ne . then
               var_fmt_value = 'Range of values';
         end;
      when ('BEDSFMT', 'RESFMT')
         do;
            if var_fmt_value not in (0,.) then
               var_fmt_value = 'Range of values';
         end;
      when ('$CONTRCT', '$MACYFMT')
         do;
            if var_fmt_value not in (' ','N') then
               var_fmt_value = 'Values/Codes';
			var_fmt = ' ';
         end;
	  otherwise;
   end;
   *put &varnm.= var_nm= var_fmt= var_fmt_value= rec_cnt=;
run;

proc sort data=codebook_main; by var_nm;run;
proc sort data=rec_cnt1_&varnm.; by var_nm; run;

/*   combine the main codebook information with the frequencies for this variable */
data codebook_&varnm.;
   merge codebook_main rec_cnt1_&varnm. (in=a); by var_nm;
   if a;
run;

/*   Add all of the information together variable by variable   */
proc append base=codebook_all data=codebook_&varnm. force; run;

%mend;

/*   call the macro for each variable in the dataset   */
Data _null_;
   set codebook_main;
   call execute ('%rec_cnt('|| var_nm ||','||var_fmt||');');
run;

proc sort data=codebook_all;
   by var_pos var_nm;
run;

/*   print it out, one variable at a time   */
data _null_;          
    file &CODEBOOK.;
	if _n_=1 then do;
       put @1  'Variable'   /*   this is the header information */
           @20 'Format'
	       @30 'Q#/Freq'
           @50 'Description/Label'; 
       put @1 ' ';
    end;
    set codebook_all;   /*   This is all of the variables and their codebook informaiton   */
	   by var_pos;      /*   put it out in variable order   */
	   if first.var_pos then do;  /*   this is the first line with variable name, format, question number */
	      put @1  var_nm $16.  /*   and variable label */ 
              @20 var_fmt $8.
		      @30 qnbr $17.
              @50 var_label $41.; /*  extra position for linefeed */
	   end;
	   /*  these are the lines of the values for the variable */
          put @24 rec_cnt comma12. /* freqs -- Changed it to position 24 to more align with header -J. Regan 9-22-2022*/
	          @40 var_fmt_value $16. /* values */
	          @58 var_fmt_label $75.; /* descriptions */
       if last.var_pos then do;   /*  these are the notes and the year the variable was added */
          if notes ne ' ' then do;
	         put @10 'Notes:  ' notes;
			 if notes2 ne ' ' then put @18 notes2;
			 if notes3 ne ' ' then put @18 notes3;
		  end;
		  if yr ne . then 
	         put @18 'First available in ' yr;
		  put @1 ' ';
	   end;
run;
